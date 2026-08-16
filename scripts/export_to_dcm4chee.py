#!/usr/bin/env python3
"""ADR-028 Phase 2: backfill QuantumPACS studies into the dcm4chee archive.

Reads all studies from the QuantumPACS main database and C-STOREs every
instance to the dcm4chee archive (AE DCM4CHEE on 11112), replicating the
ArchiveQuery path the backend will use in production.

Usage: backend/.venv/bin/python scripts/export_to_dcm4chee.py [--dry-run]

Exit codes: 0 = all studies exported, 1 = any instance failed, 2 = no
association.
"""
import argparse
import asyncio
import os
import sys
import yaml

from pynetdicom import AE, sop_class

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
STORAGE_DEFAULT = os.path.abspath(os.path.join(BACKEND_DIR, '..', 'data', 'files'))

_SOP_CLASS_BY_UID = {
    '1.2.840.10008.5.1.4.1.1.1': sop_class.ComputedRadiographyImageStorage,
    '1.2.840.10008.5.1.4.1.1.2': sop_class.CTImageStorage,
    '1.2.840.10008.5.1.4.1.1.4': sop_class.MRImageStorage,
    '1.2.840.10008.5.1.4.1.1.6.1': sop_class.UltrasoundImageStorage,
    '1.2.840.10008.5.1.4.1.1.7': sop_class.SecondaryCaptureImageStorage,
    '1.2.840.10008.5.1.4.1.1.9.1.1': sop_class.VLPhotographicImageStorage,
    '1.2.840.10008.5.1.4.1.1.11.1': sop_class.XRayAngiographicImageStorage,
    '1.2.840.10008.5.1.4.1.1.12.1': sop_class.XRayRadiofluoroscopicImageStorage,
    '1.2.840.10008.5.1.4.1.1.13.1.3': sop_class.XRay3DAngiographicImageStorage,
    '1.2.840.10008.5.1.4.1.1.20': sop_class.NuclearMedicineImageStorage,
    '1.2.840.10008.5.1.4.1.1.77.1.4': sop_class.VLWholeSlideMicroscopyImageStorage,
    '1.2.840.10008.5.1.4.1.1.88.1': sop_class.OphthalmicPhotography8BitImageStorage,
    '1.2.840.10008.5.1.4.1.1.128': sop_class.PositronEmissionTomographyImageStorage,
    '1.2.840.10008.5.1.4.1.1.3.1': sop_class.EnhancedCTImageStorage,
    '1.2.840.10008.5.1.4.1.1.4.1': sop_class.EnhancedMRImageStorage,
    '1.2.840.10008.5.1.4.1.1.130': sop_class.EnhancedPETImageStorage,
    '1.2.840.10008.5.1.4.1.1.66.4': sop_class.SegmentationStorage,
}


def load_config():
    path = os.path.join(BACKEND_DIR, 'config.local.yaml')
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    return {
        'host': cfg.get('db_host', '127.0.0.1'),
        'port': int(cfg.get('db_port', '5432')),
        'database': cfg.get('db_database', 'quantumpacs'),
        'user': cfg.get('db_user', 'quantumpacs'),
        'password': cfg.get('db_password', ''),
    }


async def fetch_studies(cfg):
    import asyncpg
    conn = await asyncpg.connect(**cfg)
    try:
        rows = await conn.fetch(
            """
            SELECT s.study_instance_uid AS study_uid,
                   p.patient_id AS patient_key,
                   s.study_id AS study_key,
                   sr.number AS series_number,
                   f.name AS file_name,
                   f.sop_class_uid,
                   f.sop_instance_uid,
                   f.tenant
            FROM files f
            JOIN series sr ON sr.id = f.series_id
            JOIN studies s ON s.id = f.study_id
            JOIN patients p ON p.id = f.patient_id
            WHERE f.deleted = FALSE
              AND f.sop_instance_uid IS NOT NULL
              AND f.sop_instance_uid <> ''
            ORDER BY s.id, sr.id, f.id
            """
        )
    finally:
        await conn.close()
    return rows


def file_path(row, storage_dir):
    # Mirror LocalStorage.get_path(): {storage}/{PatientID}/{StudyID
    # or empty}/{SeriesNumber or empty}/{name}
    parts = [row['patient_key'], row['study_key'] or 'empty', row['series_number'] or 'empty', row['file_name']]
    safe = [os.path.basename(os.path.normpath(str(part))) for part in parts]
    return os.path.join(storage_dir, *safe)


def main():
    parser = argparse.ArgumentParser(description='Backfill QuantumPACS studies into dcm4chee')
    parser.add_argument('--dry-run', action='store_true', help='report studies without sending')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=11112)
    parser.add_argument('--aet', default='QUANTUMPACS')
    parser.add_argument('--archive-aet', default='DCM4CHEE')
    parser.add_argument('--storage', default=STORAGE_DEFAULT)
    args = parser.parse_args()

    cfg = load_config()
    rows = asyncio.run(fetch_studies(cfg))

    studies = {}
    for row in rows:
        tenant = row['tenant'] or 'default'
        uid = row['study_uid']
        studies.setdefault(uid, {'tenant': tenant, 'instances': []})['instances'].append(row)

    print(f'Studies to export: {len(studies)} ({sum(len(v["instances"]) for v in studies.values())} instances)')
    for uid, info in sorted(studies.items()):
        print(f'  [{info["tenant"]}] {uid}: {len(info["instances"])} instances')

    if args.dry_run:
        return 0

    # Pre-scan files to collect (SOP class, transfer syntax) pairs so every
    # context can be registered before the association is opened.
    from pydicom import dcmread

    ds_cache = {}
    pairs = set()
    skipped_prescan = 0
    for row in rows:
        path = file_path(row, args.storage)
        if not os.path.exists(path):
            skipped_prescan += 1
            continue
        try:
            ds = dcmread(path)
        except Exception:
            # Not a valid DICOM file (missing DICM header, truncated, ...).
            # Ignore it — only standard-clean files are exported.
            skipped_prescan += 1
            continue
        ds_cache[path] = ds
        sop_uid = str(ds.file_meta.MediaStorageSOPClassUID or getattr(ds, 'SOPClassUID', ''))
        ts_uid = str(ds.file_meta.TransferSyntaxUID)
        pairs.add((sop_uid, ts_uid))

    if skipped_prescan:
        print(f'Ignored {skipped_prescan} non-valid file(s) (missing or unreadable on disk)')

    ae = AE(ae_title=args.aet.encode())
    # The archive's DCM4CHEE AE negotiates one transfer syntax per context,
    # so request a dedicated context per (SOP class, syntax) pair (Gate 3).
    for sop_uid, ts_uid in sorted(pairs):
        context = _SOP_CLASS_BY_UID.get(sop_uid, sop_uid)
        ae.add_requested_context(context, [ts_uid])
    print(f'Registered {len(pairs)} presentation context(s)')

    assoc = ae.associate(args.host, args.port, ae_title=args.archive_aet.encode())
    if not assoc.is_established:
        print(f'FATAL: association failed: {assoc.acceptor.reason}', file=sys.stderr)
        return 2
    print('Association established with', args.archive_aet)

    total_ok = total_dup = total_fail = total_skip = 0
    failures = []
    for uid, info in sorted(studies.items()):
        study_ok = study_dup = study_fail = study_skip = 0
        for row in info['instances']:
            path = file_path(row, args.storage)
            ds = ds_cache.get(path)
            if ds is None:
                study_skip += 1
                continue
            # C-STORE requires SOPClassUID + SOPInstanceUID in the dataset.
            # Legacy rows may lack them — synthesize from File Meta or skip.
            if not getattr(ds, 'SOPClassUID', None):
                sop_uid = ds.file_meta.get('MediaStorageSOPClassUID')
                if sop_uid:
                    ds.SOPClassUID = sop_uid
                else:
                    study_skip += 1
                    continue
            if not getattr(ds, 'SOPInstanceUID', None):
                ds.SOPInstanceUID = row['sop_instance_uid'] or ds.file_meta.get('MediaStorageSOPInstanceUID')
                if not ds.SOPInstanceUID:
                    study_skip += 1
                    continue
            status = assoc.send_c_store(ds)
            if status is None:
                study_fail += 1
                failures.append((row['sop_instance_uid'], 'no status', path))
            elif status.Status == 0x0000:
                study_ok += 1
            elif status.Status == 0x0110:
                # Duplicate SOP Instance: already archived — not an error.
                study_dup += 1
            else:
                study_fail += 1
                failures.append((row['sop_instance_uid'], f'status {status.Status:04X}', path))
        total_ok += study_ok
        total_dup += study_dup
        total_fail += study_fail
        total_skip += study_skip
        print(f'  {uid}: stored {study_ok}, duplicate {study_dup}, skipped {study_skip}, failed {study_fail}')

    assoc.release()

    print(f'\nTotal: stored {total_ok}, duplicate {total_dup}, skipped {total_skip}, failed {total_fail}')
    if failures:
        print('Failures:')
        for sop_uid, reason, path in failures[:20]:
            print(f'  {sop_uid}: {reason} ({path})')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())