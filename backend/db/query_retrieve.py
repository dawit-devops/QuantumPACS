"""DICOM Query/Retrieve C-FIND support (PS3.4 C.6).

Runs study-, series- or instance-level queries against the relational store
(patients/studies/series/files) and returns pydicom datasets whose attributes
are those requested in the query identifier.

Matching follows PS3.4 C.2.2.2: string keys use wildcard matching ('*' acts as
a match-all prefix/suffix), UID keys match exactly. Response identifiers
always carry the level UIDs so SCUs can correlate results.
"""
import re

from pydicom.dataset import Dataset

from log import get_logger

log = get_logger(__name__)

# keyword -> (sql column, row key). Patients/studies/series/files columns
# use the unaliased table prefix so they resolve at every query level.
_ATTRS = {
    'PatientName': ('patients.patient_name', 'patient_name'),
    'PatientID': ('patients.patient_id', 'patient_id'),
    'PatientBirthDate': ('patients.patient_birth_date', 'birth_date'),
    'PatientSex': ('patients.patient_sex', 'sex'),
    'StudyInstanceUID': ('studies.study_instance_uid', 'study_instance_uid'),
    'StudyID': ('studies.study_id', 'study_id'),
    'StudyDescription': ('studies.description', 'description'),
    'StudyDate': ('studies.study_date', 'study_date'),
    'AccessionNumber': ('studies.accession_number', 'accession_number'),
    'ReferringPhysicianName': ('studies.referring_physician', 'referring_physician'),
    'PerformingPhysicianName': ('studies.performing_physician', 'performing_physician'),
    'SeriesInstanceUID': ('series.series_instance_uid', 'series_instance_uid'),
    'SeriesNumber': ('series.number', 'series_number'),
    'SeriesDescription': ('series.description', 'series_description'),
    'Modality': ('series.modality', 'modality'),
    'SOPInstanceUID': ('files.sop_instance_uid', 'sop_instance_uid'),
    'SOPClassUID': ('files.sop_class_uid', 'sop_class_uid'),
    'InstanceNumber': ('files.instance_number', 'instance_number'),
}

# Keys whose values use wildcard matching (ILIKE) instead of exact equality.
_WILDCARD_KEYS = frozenset({
    'PatientName', 'PatientID', 'StudyID', 'StudyDescription',
    'AccessionNumber', 'SeriesDescription', 'ReferringPhysicianName',
    'PerformingPhysicianName',
})

_UID_KEYS = frozenset({
    'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'SOPClassUID',
})

# Computed (non-column) attributes are computed inline in the SQL below.
_EXACT_KEYS = _UID_KEYS | frozenset({'PatientBirthDate', 'PatientSex', 'SeriesNumber', 'Modality', 'InstanceNumber'})

_SQL_ESCAPE = re.compile(r'([\\%_])')


def _wildcard_to_like(value: str) -> str:
    """Translate a DICOM wildcard pattern into an escaped ILIKE pattern.

    '*' is the only wildcard per PS3.4 C.2.2.2; literal %, _ and backslash
    in the pattern are escaped so they match literally.
    """
    escaped = _SQL_ESCAPE.sub(r'\\\1', value)
    return escaped.replace('*', '%')


def _date_range(value: str):
    """Split a StudyDate range ('20230101-20230201', '20230101-', '-20230201')."""
    value = value.strip()
    if '-' in value:
        parts = [p.strip() for p in value.split('-', 1)]
        return parts[0] or None, parts[1] or None
    return value, value


def _determine_level(query_ds: Dataset) -> str:
    if hasattr(query_ds, 'SOPInstanceUID') and query_ds.SOPInstanceUID:
        return 'instance'
    if hasattr(query_ds, 'SeriesInstanceUID') and query_ds.SeriesInstanceUID:
        return 'series'
    return 'study'


class QueryRetrieve:
    """Executes a C-FIND query identifier against the relational store."""

    def __init__(self, query_ds: Dataset):
        self.query_ds = query_ds
        self.level = _determine_level(query_ds)

    def _requested(self):
        return [k for k in _ATTRS if hasattr(self.query_ds, k)]

    def _filters(self, level):
        """Build (sql, params) for the query identifier, level-aware.

        Modality lives on series at every level; at study level it must be
        filtered through EXISTS because studies carry no modality column.
        """
        conditions = []
        params = []

        def add(expr, value):
            params.append(value)
            conditions.append(f'{expr} = ${len(params)}')

        def add_like(expr, value):
            params.append(_wildcard_to_like(value))
            conditions.append(f'{expr} ILIKE ${len(params)} ESCAPE \'\\\'')

        for key in self._requested():
            value = str(getattr(self.query_ds, key))
            if not value or value == '*':
                continue
            column, _ = _ATTRS[key]
            if key == 'StudyDate' and level == 'study':
                from_val, to_val = _date_range(value)
                if from_val:
                    params.append(from_val)
                    conditions.append(f'studies.study_date >= ${len(params)}')
                if to_val:
                    params.append(to_val)
                    conditions.append(f'studies.study_date <= ${len(params)}')
            elif key == 'Modality' and level == 'study':
                params.append(value)
                conditions.append(
                    f'EXISTS (SELECT 1 FROM series s_m WHERE s_m.study_id = studies.id AND s_m.modality = ${len(params)})'
                )
            elif key in _EXACT_KEYS:
                add(column, value)
            elif key in _WILDCARD_KEYS:
                add_like(column, value)
            else:
                add(column, value)

        return ' AND '.join(conditions), params

    _STUDY_COLUMNS = (
        'patients.patient_id, patients.patient_name, '
        'patients.patient_birth_date AS birth_date, patients.patient_sex AS sex, '
        'studies.study_id, studies.study_instance_uid, studies.description, '
        'studies.study_date, studies.accession_number, '
        'studies.referring_physician, studies.performing_physician'
    )

    def _sql(self):
        if self.level == 'instance':
            select = (
                self._STUDY_COLUMNS + ', '
                'series.series_instance_uid, series.number AS series_number, '
                'series.description AS series_description, series.modality, '
                'files.sop_instance_uid, files.sop_class_uid, files.instance_number'
            )
            sql = (
                f'SELECT {select}\n'
                'FROM files\n'
                'JOIN series ON series.id = files.series_id\n'
                'JOIN studies ON studies.id = series.study_id\n'
                'JOIN patients ON patients.id = studies.patient_id\n'
                'WHERE NOT files.deleted'
            )
            return sql, 'files.id'
        if self.level == 'series':
            select = (
                self._STUDY_COLUMNS + ', '
                'series.series_instance_uid, series.number AS series_number, '
                'series.description AS series_description, series.modality, '
                '(SELECT COUNT(*) FROM files f1 '
                ' WHERE f1.series_id = series.id AND NOT f1.deleted) AS n_instances'
            )
            sql = (
                f'SELECT {select}\n'
                'FROM series\n'
                'JOIN studies ON studies.id = series.study_id\n'
                'JOIN patients ON patients.id = studies.patient_id'
            )
            return sql, 'series.id'
        select = (
            self._STUDY_COLUMNS + ', '
            "(SELECT COUNT(DISTINCT s2.id) FROM series s2 "
            " WHERE s2.study_id = studies.id) AS n_series, "
            '(SELECT COUNT(*) FROM files f1 '
            ' WHERE f1.study_id = studies.id AND NOT f1.deleted) AS n_instances'
        )
        sql = (
            f'SELECT {select}\n'
            'FROM studies\n'
            'JOIN patients ON patients.id = studies.patient_id'
        )
        return sql, 'studies.id'

    def _row_to_dataset(self, row):
        row = dict(row)
        ds = Dataset()
        requested = set(self._requested())
        for key in requested:
            col, row_key = _ATTRS[key]
            value = row.get(row_key)
            if value:
                setattr(ds, key, str(value))
        # Level UIDs are always echoed so SCUs can correlate responses.
        ds.StudyInstanceUID = str(row.get('study_instance_uid') or '')
        if self.level in ('series', 'instance'):
            ds.SeriesInstanceUID = str(row.get('series_instance_uid') or '')
        if self.level == 'instance':
            ds.SOPInstanceUID = str(row.get('sop_instance_uid') or '')
        if self.level == 'series' and row.get('n_instances') is not None:
            ds.NumberOfSeriesRelatedInstances = int(row['n_instances'])
        if self.level == 'study':
            if row.get('n_series') is not None:
                ds.NumberOfStudyRelatedSeries = int(row['n_series'])
            if row.get('n_instances') is not None:
                ds.NumberOfStudyRelatedInstances = int(row['n_instances'])
        return ds

    async def search(self, conn):
        sql, order_col = self._sql()
        extra_sql, params = self._filters(self.level)
        if extra_sql:
            sql += f' AND {extra_sql}'
        sql += f' ORDER BY {order_col}'
        rows = await conn.fetch(sql, *params)
        results = []
        for row in rows:
            try:
                ds = self._row_to_dataset(row)
                if ds.StudyInstanceUID:
                    results.append(ds)
            except Exception:
                log.warning('Q/R C-FIND row skipped', exc_info=True)
        return results
