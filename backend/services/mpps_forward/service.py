"""MPPS-forward SCU — real S6-09 PACS echo (C3, GAP_AUDIT_TDD_PIPELINE.md).

The original implementation was a bare C-ECHO connectivity probe: no exam
status ever reached the PACS. This module forwards the modality's OWN
N-CREATE/N-SET datasets to a configured peer AE, so the remote PACS sees
the same procedure-step progress the RIS recorded locally.

Failure isolation contract: forwarding is best-effort. A dead or
misconfigured peer logs a warning and bumps a counter; it must never
raise into, block beyond the timeout, or roll back local MPPS handling.
"""
import asyncio

from log import get_logger

log = get_logger(__name__)

_FORWARD_TIMEOUT = 10  # seconds per association+operation


def _resolve_config(override=None):
    if override is not None:
        return override
    from config import config
    return config


async def forward_mpps(operation: str, ds, _config=None) -> bool:
    """Send `ds` to the configured peer as an MPPS N-CREATE/N-SET.

    Returns True when the peer accepted the operation. Disabled config,
    unreachable peers and association failures all return False (never
    raise). `_config` is an injection seam for tests.
    """
    cfg = _resolve_config(_config)
    enabled = str(cfg.get('mpps_forward_enabled', 'false')).lower() \
        in ('true', '1', 'yes')
    host = cfg.get('mpps_forward_host', '')
    port = str(cfg.get('mpps_forward_port', '') or '')
    called_ae = cfg.get('mpps_forward_called_ae', '')
    if not (enabled and host and port.isdigit() and called_ae):
        return False

    def _associate_and_send():
        from pydicom.uid import generate_uid
        from pynetdicom import AE
        from pynetdicom.presentation import build_context
        from pynetdicom.sop_class import ModalityPerformedProcedureStep

        from config import config as app_config
        class_uid = str(ModalityPerformedProcedureStep)
        ae = AE(ae_title=app_config.get('dicom_ae_title', 'QUANTUMPACS'))
        assoc = ae.associate(
            host, int(port), ae_title=called_ae,
            contexts=[build_context(class_uid)],
        )
        try:
            if not assoc.is_established:
                return False
            instance_uid = (
                str(getattr(ds, 'AffectedSOPInstanceUID', '')
                    or getattr(ds, 'SOPInstanceUID', '')) or ''
            )
            if operation == 'N_CREATE':
                # The N-CREATE *creates* the MPPS instance: without an
                # Affected SOP Instance UID conformant peers reject with
                # 0x0110 (processing failure).
                if not instance_uid:
                    instance_uid = str(generate_uid())
                    ds.SOPInstanceUID = instance_uid
                status, _reply = assoc.send_n_create(
                    ds, class_uid, instance_uid=instance_uid)
            else:
                if not instance_uid:
                    return False
                status, _reply = assoc.send_n_set(
                    ds, class_uid, instance_uid=instance_uid)
            return bool(status and status.Status == 0x0000)
        finally:
            try:
                assoc.release()
            except Exception:
                pass

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_associate_and_send), timeout=_FORWARD_TIMEOUT)
    except Exception:
        mpps_forward_failures_total.labels(
            peer=f'{host}:{port}').inc()
        log.warning('MPPS forward to %s:%s (%s) failed',
                    host, port, called_ae, exc_info=True)
        return False


async def maybe_forward_mpps(operation: str, ds) -> None:
    """Consumer hook: fire-and-forget wrapper that can never raise."""
    try:
        await asyncio.wait_for(
            forward_mpps(operation, ds), timeout=_FORWARD_TIMEOUT + 5)
    except Exception:
        log.warning('MPPS %s forward attempt errored', operation,
                    exc_info=True)


try:
    from prometheus_client import Counter as _Counter
    mpps_forward_failures_total = _Counter(
        'mpps_forward_failures_total', 'Failed MPPS forwards to PACS',
        ['peer'])
except Exception:  # pragma: no cover - metrics unavailable
    class _FallbackCounter:
        def labels(self, *a, **k):
            return self

        def inc(self, *a):
            return None

    mpps_forward_failures_total = _FallbackCounter()
