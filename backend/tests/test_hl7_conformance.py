"""S3-05 — HL7 conformance: the engine parser must handle realistic wire traffic.

The corpus (tests/hl7_conformance_corpus.py) holds 20 realistic ORM/ADT/ORU
samples plus 6 expected-failure messages. Acceptance: ≥95% of valid samples
parse (currently 100%), and every invalid sample is rejected. The manual
runner doubles as a CI-able script: python -m tests.hl7_conformance_corpus.
"""

import pytest

from services.ingestion.hl7_server import parse_hl7_message
from tests.hl7_conformance_corpus import INVALID_MESSAGES, VALID_MESSAGES

MIN_PARSE_RATE = 0.95


class TestHl7Conformance:
    @pytest.mark.parametrize('name,msg', VALID_MESSAGES, ids=[n for n, _ in VALID_MESSAGES])
    def test_valid_sample_parses(self, name, msg):
        parsed = parse_hl7_message(msg)
        assert parsed is not None, f'valid sample failed to parse: {name}'
        assert parsed.get('message_type'), f'parsed sample missing message_type: {name}'

    @pytest.mark.parametrize('name,msg', INVALID_MESSAGES, ids=[n for n, _ in INVALID_MESSAGES])
    def test_invalid_sample_rejected(self, name, msg):
        assert parse_hl7_message(msg) is None, f'invalid sample unexpectedly parsed: {name}'

    def test_parse_rate_at_least_95_percent(self):
        parsed = sum(1 for _, msg in VALID_MESSAGES if parse_hl7_message(msg) is not None)
        rate = parsed / len(VALID_MESSAGES)
        assert rate >= MIN_PARSE_RATE, f'conformance rate {rate:.0%} < {MIN_PARSE_RATE:.0%}'

    def test_corpus_has_reasonable_coverage(self):
        # ≥95% means something; a 3-message corpus would trivially pass.
        assert len(VALID_MESSAGES) >= 15
        types = {parse_hl7_message(m)['message_type'] for _, m in VALID_MESSAGES}
        assert {'ORM', 'ADT', 'ORU'} <= types