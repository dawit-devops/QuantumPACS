"""C-ECHO SCU stub (S6-09).

Best-effort DICOM verification echo to the PACS archive fired after an MPPS
COMPLETED: confirms the archive is reachable and speaking DICOM. A "stub" in
the sense that it is connectivity-probing only — no state is exchanged and
failures are logged, never raised, so the MPPS consumer never fails because
the archive is down. Disabled when pacs_echo_host is empty (dev default).
"""
import asyncio
import time

from config import config
from log import get_logger

log = get_logger(__name__)


def _echo_sync(host: str, port: int, ae_title: str, calling_ae: str) -> float:
    """Blocking pynetdicom C-ECHO; returns round-trip seconds."""
    from pynetdicom import AE
    verification = '1.2.840.10008.1.1'  # Verification SOP Class
    ae = AE(ae_title=calling_ae)
    ae.add_requested_context(verification)
    started = time.monotonic()
    with ae.association(host, port, ae_title=ae_title) as assoc:
        if not assoc.is_established:
            raise RuntimeError('association not established')
        status = assoc.send_c_echo()
        if not status or status.Status != 0x0000:
            raise RuntimeError(f'C-ECHO rejected: {status}')
        return time.monotonic() - started


async def echo_to_pacs() -> bool:
    """Fire a C-ECHO SCU to the configured PACS. Never raises.

    Returns True when the echo succeeded (or was a silent no-op because no
    PACS is configured), False when the archive is unreachable.
    """
    host = config.get('pacs_echo_host', '')
    if not host:
        return False
    port = int(config.get('pacs_echo_port', '11112'))
    ae_title = config.get('pacs_echo_ae', 'DCM4CHEE')
    calling = config.get('dicom_ae_title', 'QUANTUMPACS')
    try:
        # pynetdicom is blocking; run it off the event loop with a hard
        # cap so a black-holed archive cannot stall the MPPS handler.
        elapsed = await asyncio.wait_for(
            asyncio.to_thread(_echo_sync, host, port, ae_title, calling),
            timeout=10,
        )
        log.info('C-ECHO to %s:%s OK in %.1fms', host, port, elapsed * 1000)
        return True
    except Exception as exc:
        log.warning('C-ECHO to %s:%s failed: %s', host, port, exc)
        return False