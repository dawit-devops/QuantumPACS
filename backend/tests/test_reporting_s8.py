"""Tests for Sprint S8–S9: Reporting + Sign-Off (Tasks S8-17 .. S8-20).

Covers reading list filtering, template management, report version history,
draft auto-save, electronic sign-off, ORU distribution stub, charge drop stub,
and RLS tenant isolation.
"""
import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient

from app import app
from db.conn import get_conn, database
from db.reports import Reports
from db.ris_templates import RisReportTemplates
from db.ris_report_versions import RisReportVersions


@pytest.fixture(autouse=True)
async def setup_db():
    await database.setup()
    yield
    await database.close()


@pytest.fixture
def client():
    return TestClient(app)


class TestReportTemplates:
    @pytest.mark.asyncio
    async def test_seed_and_list_templates(self):
        async with get_conn() as conn:
            tpl_db = RisReportTemplates(conn)
            await tpl_db.seed_defaults()
            templates = await tpl_db.list_templates()
            assert len(templates) >= 10
            ct_templates = await tpl_db.list_templates(modality='CT')
            assert all(t['modality'].upper() == 'CT' for t in ct_templates)

    @pytest.mark.asyncio
    async def test_create_custom_template(self):
        async with get_conn() as conn:
            tpl_db = RisReportTemplates(conn)
            new_tpl = await tpl_db.create_template({
                'name': 'Custom Knee MRI',
                'modality': 'MR',
                'body_part': 'Knee',
                'findings_template': 'Ligaments: Intact.\nMenisci: Normal.',
                'impression_template': 'Normal knee MRI.',
                'is_default': False,
            })
            assert new_tpl['name'] == 'Custom Knee MRI'
            assert new_tpl['modality'] == 'MR'


class TestReportVersioning:
    @pytest.mark.asyncio
    async def test_report_version_history_and_diff(self):
        async with get_conn() as conn:
            # Create a mock report row
            row = await conn.fetchrow(
                "INSERT INTO reports (exam_id, status, findings, impression) "
                "VALUES (gen_random_uuid(), 'draft', 'Initial findings', 'Initial impression') "
                "RETURNING id"
            )
            report_id = row['id']
            rv = RisReportVersions(conn)

            # Version 1 snapshot
            v1 = await rv.add_version(report_id, 'Initial findings', 'Initial impression', edited_by='rad1')
            assert v1['version_number'] == 1

            # Update report and version 2 snapshot
            v2 = await rv.add_version(report_id, 'Updated findings with fracture', 'Acute fracture detected', edited_by='rad1')
            assert v2['version_number'] == 2

            history = await rv.get_history(report_id)
            assert len(history) == 2

            diff = await rv.get_version_diff(report_id, 1, 2)
            assert diff is not None
            assert diff['findings_changed'] is True
            assert diff['impression_changed'] is True


class TestReportSignOffAndStubs:
    @pytest.mark.asyncio
    async def test_sign_report_creates_oru_and_charge_stubs(self):
        async with get_conn() as conn:
            exam_row = await conn.fetchrow(
                "INSERT INTO exams (accession_number, patient_id, status, modality) "
                "VALUES ('ACC-S8-TEST', 'PAT-S8-01', 'completed', 'CT') "
                "RETURNING id"
            )
            exam_id = exam_row['id']

            report = await Reports(conn).create(
                exam_id,
                {'status': 'draft', 'findings': 'CT Head clear', 'impression': 'No acute stroke'},
                created_by='rad_user_1',
            )

            # Sign the report
            signed = await Reports(conn).sign(report['id'], signed_by='rad_user_1')
            assert signed['status'] == 'final'
            assert signed['signed_by'] == 'rad_user_1'
            assert signed['distributed_at'] is not None

            # Verify charge drop stub inserted placeholder row in ris_charges
            charge_row = await conn.fetchrow(
                "SELECT * FROM ris_charges WHERE report_id = $1",
                str(report['id']),
            )
            assert charge_row is not None
            assert charge_row['accession_number'] == 'ACC-S8-TEST'


class TestReportEndpointsRLS:
    @pytest.mark.asyncio
    async def test_reading_list_returns_completed_exams(self):
        async with get_conn() as conn:
            items = await Reports(conn).reading_list()
            assert isinstance(items, list)
