"""F1: honest percentile + timed-fixture utilities (GAP_AUDIT_TDD_PIPELINE.md).

The perf gates previously used `mean = elapsed / N` labeled as p95, which
understates the 95th percentile when variance is non-zero. This module
provides the correct percentile calculation and a timed-fixture helper for
concurrent-workload gates.
"""


def percentile(values, p=95):
    """Return the p-th percentile of a sorted list of durations (seconds).

    Uses linear interpolation between the two nearest ranks (C=1) per
    NIST / ISO 8601 recommended method (same as numpy.percentile with
    the 'linear' default).  When the list is empty, returns 0.
    """
    n = len(values)
    if n == 0:
        return 0.0
    if n == 1:
        return float(values[0])
    sorted_vals = sorted(values)
    # Rank index for the p-th percentile (C=1 method).
    rank = (p / 100.0) * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])