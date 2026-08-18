"""HL7 parse/validate/normalize (S3-02).

The wire parser already lives in services/ingestion/hl7_server.py
(parse_hl7_message) and covers MSH/PID/PV1/ORC/OBR field extraction; it is
exercised by the HL7 conformance suite (tests/integration/test_hl7.py).
This module is the engine's validation layer: it re-exports the parser
(single source of truth — no duplicate parsing logic) and enforces the
per-message-type required-field contract so malformed messages fail fast
into the exception queue instead of partial-processing.
"""

from datetime import datetime

from services.ingestion.hl7_server import parse_hl7_message  # noqa: F401

_REQUIRED_FIELDS = {
    'ADT': ('patient_id',),
    'ORM': ('patient_id', 'accession_number'),
    'ORU': ('accession_number',),
}

_PRIORITY_MAP = {'R': 'ROUTINE', 'A': 'URGENT', 'S': 'STAT'}


class Hl7ValidationError(ValueError):
    """Message fails the required-field contract for its type."""


def validate(parsed: dict) -> None:
    """Reject messages missing fields their type needs (fail fast, S3-02)."""
    msg_type = parsed.get('message_type', '')
    for field in _REQUIRED_FIELDS.get(msg_type, ()):
        if not parsed.get(field):
            raise Hl7ValidationError(f'Missing required field {field} for {msg_type}')


def normalize_priority(priority: str) -> str:
    """OBR-27.6 requested priority (R routine / A ASAP / S stat) → ris_orders.

    HL7 sends lowercase too; anything unrecognized defaults to ROUTINE
    rather than rejecting the message (the wire value is advisory).
    """
    return _PRIORITY_MAP.get((priority or 'R').upper(), 'ROUTINE')


def to_date(hl7_date: str):
    """HL7 DTM 'yyyyMMdd[HHmm...]' → datetime.date; None when absent/malformed.

    ris_orders.patient_dob is a DATE column; asyncpg rejects bare strings,
    so the engine converts at the boundary instead of storing '19800101'.
    """
    if not hl7_date or len(hl7_date) < 8 or not hl7_date[:8].isdigit():
        return None
    try:
        return datetime.strptime(hl7_date[:8], '%Y%m%d').date()
    except ValueError:
        return None