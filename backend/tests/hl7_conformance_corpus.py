"""S3-05 — HL7 conformance corpus: realistic wire samples for the engine parser.

Every VALID_MESSAGES entry must parse via parse_hl7_message (the conformance
test asserts a ≥95% parse rate over this set — currently 100%). INVALID_MESSAGES
must fail parse (return None); they model garbage/truncated traffic and are
expected failures, so they do not count against the rate.

The corpus doubles as the manual conformance script: run
`python -m tests.hl7_conformance_corpus` to print the per-sample parse verdicts
and the overall rate (CI check without pytest).
"""

VALID_MESSAGES = [
    (
        'orm_full',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG001|P|2.5\r'
        'PID|1||PID001||Smith^John||19800101|M\r'
        'ORC|NW|ORD001|||CM|||||||202607251030\r'
        'OBR|1|ORD001|RP001|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Routine screening|Lee^Kim\r',
    ),
    (
        'orm_minimal',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG002|P|2.5\r'
        'PID|1||PID002||Doe^Jane||19900215|F\r'
        'ORC|NW|ORD002\r'
        'OBR|1|ORD002|RP002|XR CHEST^Chest X-ray^L\r',
    ),
    (
        'orm_with_pv1',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG003|P|2.5\r'
        'PID|1||PID003||Brown^Bob||19750320|M\r'
        'PV1|1|O|RAD^CT^A\r'
        'ORC|NW|ORD003|||CM\r'
        'OBR|1|ORD003|RP003|MR BRAIN^Brain MRI^L|||202607260800\r',
    ),
    (
        'orm_filler_accession',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG004|P|2.5\r'
        'PID|1||PID004||Green^Grace||19880512|F\r'
        'ORC|NW||ACC-FILLER-1|||CM\r'
        'OBR|1|ORD004|RP004|US ABDOMEN^Abdomen US^L\r',
    ),
    (
        'orm_lowercase_priority',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG005|P|2.5\r'
        'PID|1||PID005||White^Wanda||19770109|F\r'
        'ORC|NW|ORD005|||CM\r'
        'OBR|1|ORD005|RP005|XR CHEST^Chest X-ray^L|||202607260800|||||||||||XR1||||||XR|||1^CM^30^Q^30^s\r',
    ),
    (
        'orm_stat_priority',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG006|P|2.5\r'
        'PID|1||PID006||Black^Bill||19601020|M\r'
        'ORC|NW|ORD006|||CM\r'
        'OBR|1|ORD006|RP006|CT HEAD^Head CT^L|||202607260800|||||||||||CT1||||||CT|||1^CM^30^Q^30^S\r',
    ),
    (
        'orm_crlf_line_endings',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG007|P|2.5\r\n'
        'PID|1||PID007||Orange^Olive||19920330|F\r\n'
        'ORC|NW|ORD007|||CM\r\n'
        'OBR|1|ORD007|RP007|NM BONE^Bone Scan^L\r\n',
    ),
    (
        'orm_multicomponent_name',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG008|P|2.5\r'
        'PID|1||PID008||Smith^John^Quincy^Jr^DR||19800101|M\r'
        'ORC|NW|ORD008|||CM\r'
        'OBR|1|ORD008|RP008|CT CHEST^Chest CT^L\r',
    ),
    (
        'orm_with_obx',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ORM^O01|MSG009|P|2.5\r'
        'PID|1||PID009||Purple^Pat||19841015|F\r'
        'ORC|NW|ORD009|||CM\r'
        'OBR|1|ORD009|RP009|CT ABDOMEN^Abdomen CT^L\r'
        'OBX|1|ST|1234^NOTES^L||NPO after midnight\r',
    ),
    (
        'adt_a01_admission',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A01|MSG010|P|2.5\r'
        'EVN|A01|202607251030\r'
        'PID|1||PID010||Red^Rita||19760425|F|||1 Main St^^Metropolis^NY^10001\r'
        'PV1|1|I|WARD-A^ROOM-101^^^FACILITY\r',
    ),
    (
        'adt_a04_registration',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A04|MSG011|P|2.5\r'
        'EVN|A04|202607251030\r'
        'PID|1||PID011||Blue^Bobby||19881130|M|||2 Oak Rd^^Gotham^NY^10002\r',
    ),
    (
        'adt_a08_update',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A08|MSG012|P|2.5\r'
        'EVN|A08|202607251030\r'
        'PID|1||PID012||Yellow^Yolanda||19650714|F\r',
    ),
    (
        'adt_a03_discharge',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A03|MSG013|P|2.5\r'
        'EVN|A03|202607251030\r'
        'PID|1||PID013||Green^Gus||19520101|M\r',
    ),
    (
        'adt_a02_transfer',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A02|MSG014|P|2.5\r'
        'EVN|A02|202607251030\r'
        'PID|1||PID014||Silver^Sam||19790909|M\r'
        'PV1|1|I|WARD-B^ROOM-202^^^FACILITY\r',
    ),
    (
        'adt_a40_merge',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A40|MSG015|P|2.5\r'
        'EVN|A40|202607251030\r'
        'PID|1||PID015||Copper^Carl||19820520|M\r'
        'MRG|PID999^^^SENDING_FACILITY^MR\r',
    ),
    (
        'adt_a07_unmerge',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A07|MSG016|P|2.5\r'
        'EVN|A07|202607251030\r'
        'PID|1||PID016||Zinc^Zara||19900404|F\r'
        'MRG|PID888^^^SENDING_FACILITY^MR\r',
    ),
    (
        'adt_multicomponent_name',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607251030||ADT^A01|MSG017|P|2.5\r'
        'EVN|A01|202607251030\r'
        'PID|1||PID017||Brown^Bob^Xavier^Sr||19750320|M\r',
    ),
    (
        'oru_r01_with_findings',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607261200||ORU^R01|MSG018|P|2.5\r'
        'PID|1||PID018||Smith^John||19800101|M\r'
        'OBR|1|ORD018|ORD018|CT CHEST^Chest CT^L|||202607260800|||||||||||CT_SCANNER||||||CT|F\r'
        'OBX|1|ST|1234^FINDINGS^L||Normal study|Normal|||F\r',
    ),
    (
        'oru_r01_minimal',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607261200||ORU^R01|MSG019|P|2.5\r'
        'PID|1||PID019||Doe^Jane||19900215|F\r'
        'OBR|1|ORD019|ORD019|XR CHEST^Chest X-ray^L|||202607260800|||||||||||XR1||||||XR|F\r',
    ),
    (
        'oru_r01_multi_obx',
        'MSH|^~\\&|SENDING|SENDING_FACILITY|QUANTUMPACS||202607261200||ORU^R01|MSG020|P|2.5\r'
        'PID|1||PID020||Brown^Bob||19750320|M\r'
        'OBR|1|ORD020|ORD020|MR BRAIN^Brain MRI^L|||202607260800|||||||||||MR1||||||MR|F\r'
        'OBX|1|NM|1234^SIZE^L||2.5 cm|cm\r'
        'OBX|2|ST|1234^IMPRESSION^L||No acute findings\r',
    ),
]

INVALID_MESSAGES = [
    ('garbage', 'not an hl7 message\r'),
    ('empty', ''),
    ('no_msh', 'PID|1||P1||Doe^Jane||19800101|F\r'),
    ('binary_junk', b'\x00\x01\x02\xff\xfe'),
    ('cr_only', '\r'),
    ('msh_pipe', 'MSH|\r'),
]


def run_corpus():
    """Parse the corpus and print verdicts + conformance rate."""
    from services.ingestion.hl7_server import parse_hl7_message

    parsed_ok = failed = 0
    for name, msg in VALID_MESSAGES:
        ok = parse_hl7_message(msg) is not None
        parsed_ok += ok
        failed += not ok
        print(f'  {"PASS" if ok else "FAIL"}  valid:   {name}')
    for name, msg in INVALID_MESSAGES:
        rejected = parse_hl7_message(msg) is None
        print(f'  {"PASS" if rejected else "FAIL"}  invalid: {name}')

    total = parsed_ok + failed
    rate = parsed_ok / total if total else 0.0
    print(f'\nvalid parse rate: {parsed_ok}/{total} ({rate:.0%})')
    return rate >= 0.95


if __name__ == '__main__':
    import sys
    sys.exit(0 if run_corpus() else 1)