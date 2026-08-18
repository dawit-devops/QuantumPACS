"""Live smoke for S3-10 — RIS patient CRUD against the scratch DB."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db.frontdesk import FrontDesk
from db.conn import create_conn


async def main():
    os.environ.setdefault('DB_DATABASE', 'qpacs_migtest')
    os.environ.setdefault('DB_USER', 'quantumpacs')
    os.environ.setdefault('DB_PASSWORD', '974e03eb34f334cc36859c9d910c0dace7f04c60')
    os.environ.setdefault('DB_HOST', '127.0.0.1')
    os.environ.setdefault('DB_PORT', '5432')

    conn = await create_conn()
    try:
        await conn.execute("DELETE FROM visits WHERE patient_id = 'SMK-001'")
        await conn.execute("DELETE FROM insurance_records WHERE patient_id = 'SMK-001'")
        await conn.execute("DELETE FROM patients WHERE patient_id = 'SMK-001'")
        fd = FrontDesk(conn)

        dup = await fd.find_patient_duplicate('Smoke Patient', '1990-05-05')
        assert dup is None, 'dedup should find nothing first'
        row = await fd.create_patient({
            'patient_id': 'SMK-001', 'name': 'Smoke Patient',
            'birth_date': '1990-05-05', 'sex': 'M', 'meta': {'src': 's3-10-smoke'},
        })
        assert row['patient_id'] == 'SMK-001', row

        dup2 = await fd.find_patient_duplicate('Smoke Patient', '1990-05-05')
        assert dup2 and dup2['patient_id'] == 'SMK-001', 'dedup should now match'

        await fd.update_patient('SMK-001', {'name': 'Smoke Patient II', 'sex': 'F'})
        got = await fd.get_patient('SMK-001')
        assert got['name'] == 'Smoke Patient II' and got['sex'] == 'F', got

        rows = await fd.search_patients('smoke')
        assert any(r['patient_id'] == 'SMK-001' for r in rows), rows

        await fd.create_visit({'patient_id': 'SMK-001', 'destination_room': 'MR3'})
        open_visit = await fd.find_open_visit('SMK-001')
        assert open_visit is not None and open_visit['status'] == 'registered', open_visit
        await fd.update_visit(open_visit['id'], {'status': 'checked_in'})
        after = await fd.find_open_visit('SMK-001')
        assert after['status'] == 'checked_in', after

        ins = await fd.create_insurance({
            'patient_id': 'SMK-001', 'policy_number': 'POL-SMK',
            'guarantor_name': 'Smoke Guarantor', 'authorization_status': 'approved',
            'authorization_number': '', 'notes': '', 'created_by': '1',
        })
        assert ins['policy_number'] == 'POL-SMK', ins

        print('S3-10 smoke OK: dedup, create, update, search, visit, check-in, insurance')
    finally:
        await conn.close()


asyncio.run(main())
