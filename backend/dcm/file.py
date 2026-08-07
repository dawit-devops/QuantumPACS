import pydicom


def clean(text, strict=False):
    ret = str(text).strip()
    if len(ret) and ret[0] == '\'':
        ret = ret[1:-1]
    if len(ret) and ret[0] == '"':
        ret = ret[1:-1]
    if strict:
        ret = ret.replace('/', '-')
    return ret


def _safe_repval(v):
    try:
        return clean(v.repval)
    except Exception:
        return ''


def get_meta(data):
    # Binary "Other" VRs carry pixel/encapsulated payloads, never searchable
    # metadata. Skip them so C-STORE datasets (full pixel data) don't leak
    # noise into `cleaned` → meta JSONB/ES.
    _BINARY_VRS = frozenset({'OB', 'OD', 'OF', 'OL', 'OV', 'OW', 'UN'})

    # Explicit iteration keeps this stable across pydicom majors (dict(ds)
    # semantics changed); iterating a Dataset yields DataElements in 2.x–3.x.
    cleaned = {}
    for elem in data:
        if elem.VR in _BINARY_VRS:
            continue
        key = elem.name
        if key in cleaned:
            # Element names are not unique — every private tag is named
            # 'Private tag data'. Disambiguate by tag so no metadata is
            # silently dropped from the persisted `cleaned` dict.
            key = f'{key} ({elem.tag})'
        cleaned[key] = _safe_repval(elem)

    ret = {
        'patient_id': clean(getattr(data, 'PatientID', ''), strict=True),
        'patient_name': clean(getattr(data, 'PatientName', '')),
        'patient_birth_date': clean(getattr(data, 'PatientBirthDate', '')),
        'patient_sex': clean(getattr(data, 'PatientSex', '')),
        'study_id': clean(getattr(data, 'StudyID', ''), strict=True),
        'study_description': clean(getattr(data, 'StudyDescription', '')),
        'study_date': clean(getattr(data, 'StudyDate', '')),
        # UIDs and accession numbers are identity keys — preserve them
        # verbatim. Non-conformant values containing '/' occur in the wild;
        # rewriting them breaks WADO-RS/QIDO lookups and worklist matching
        # against the originals.
        'study_instance_uid': clean(getattr(data, 'StudyInstanceUID', '')),
        'accession_number': clean(getattr(data, 'AccessionNumber', '')),
        'referring_physician': clean(getattr(data, 'ReferringPhysicianName', '')),
        'performing_physician': clean(getattr(data, 'PerformingPhysicianName', '')),
        # ME-04: capture the reading physician and the MWL priority code when
        # a C-STORE dataset carries them (rare; (0040,1003) travels with
        # requested-procedure/SPS objects). Stored in files.meta JSONB.
        'reading_physician': clean(getattr(data, 'ReadingPhysicianName', '')),
        'requested_procedure_priority': clean(
            getattr(data, 'RequestedProcedurePriority', ''),
        ),
        'series_number': clean(getattr(data, 'SeriesNumber', ''), strict=True),
        'series_instance_uid': clean(getattr(data, 'SeriesInstanceUID', '')),
        'modality': clean(getattr(data, 'Modality', '')),
        'series_description': clean(getattr(data, 'SeriesDescription', '')),
        'sop_instance_uid': clean(getattr(data, 'SOPInstanceUID', '')),
        'sop_class_uid': clean(getattr(data, 'SOPClassUID', '')),
        'instance_number': clean(getattr(data, 'InstanceNumber', '')),
        'cleaned': cleaned,
    }
    return ret


def parse_dcm(file):
    data = pydicom.dcmread(file, stop_before_pixels=True)
    return get_meta(data)
