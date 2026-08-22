"""R2-06-03 — coding-suggestion outcome instrumentation.

record_outcome('accepted' | 'overridden') bumps the pilot counters so
the acceptance-rate gate is queryable from Prometheus without log math.
"""

from api.telemetry import (
    coding_suggestions_accepted_total,
    coding_suggestions_overridden_total,
)


async def record_outcome(kind):
    if kind == 'accepted':
        coding_suggestions_accepted_total.inc()
    elif kind == 'overridden':
        coding_suggestions_overridden_total.inc()
