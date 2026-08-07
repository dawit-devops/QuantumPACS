def _pn(value):
    if not value:
        return None
    return [{'Alphabetic': value}]


def _str(value):
    if not value:
        return None
    return [str(value)]


# Internal study_status values (receiving/complete/incomplete) map onto the
# DICOM StudyStatus codes (PARTIAL/COMPLETE/INCOMPLETE) so QIDO consumers
# get standard vocabulary.
def _study_status(value):
    if not value:
        return None
    return [_STUDY_STATUS_TO_DICOM.get(value, str(value))]


_STUDY_STATUS_TO_DICOM = {
    'receiving': 'PARTIAL',
    'complete': 'COMPLETE',
    'incomplete': 'INCOMPLETE',
}


def _da(value):
    if not value:
        return None
    return [str(value)]


_STUDY_TAGS = {
    '0020000D': ('UI', 'study_instance_uid', _str),
    '00080020': ('DA', 'study_date', _da),
    '00080030': ('TM', 'study_time', _str),
    '00080050': ('SH', 'accession_number', _str),
    '00080056': ('CS', 'study_status', _study_status),
    '00080061': ('CS', 'modalities_in_study', _str),
    '00080090': ('PN', 'referring_physician', _pn),
    '00081030': ('LO', 'study_description', _str),
    '00100010': ('PN', 'patient_name', _pn),
    '00100020': ('LO', 'patient_id', _str),
    '00100030': ('DA', 'patient_birth_date', _da),
    '00100040': ('CS', 'patient_sex', _str),
    '00200010': ('SH', 'study_id', _str),
}


_SERIES_TAGS = {
    '00080060': ('CS', 'modality', _str),
    '0008103E': ('LO', 'series_description', _str),
    '0020000E': ('UI', 'series_instance_uid', _str),
    '00200011': ('IS', 'series_number', _str),
}


_INSTANCE_TAGS = {
    '00080016': ('UI', 'sop_class_uid', _str),
    '00080018': ('UI', 'sop_instance_uid', _str),
    '00200013': ('IS', 'instance_number', _str),
}


def row_to_study_json(row):
    result = {}
    for tag, (vr, col, fmt) in _STUDY_TAGS.items():
        val = row.get(col)
        if val is not None:
            result[tag] = {'vr': vr, 'Value': fmt(val)}
    return result


def row_to_series_json(row):
    result = {}
    for tag, (vr, col, fmt) in _SERIES_TAGS.items():
        val = row.get(col)
        if val is not None:
            result[tag] = {'vr': vr, 'Value': fmt(val)}
    return result


def row_to_instance_json(row):
    result = {}
    for tag, (vr, col, fmt) in _INSTANCE_TAGS.items():
        val = row.get(col)
        if val is not None:
            result[tag] = {'vr': vr, 'Value': fmt(val)}
    return result
