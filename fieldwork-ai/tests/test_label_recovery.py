"""Regression checks for original ZIP annotations and missing-versus-absent labels."""
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
from train.recover_labels import match_source, unpack_annotation
from train.evaluate_heads import apply_source_labels, binary_metrics, choose_binary_threshold
from train.labels import defect_label


def test_annotation_crc_and_field_presence():
    buffer = io.BytesIO()
    name = "station1/labels_example.json"
    payload = {"stains": "None"}  # No hole annotation exists.
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, json.dumps(payload))
        info = archive.getinfo(name)
    entry = {"name": name, "offset": info.header_offset, "compressed_size": info.compress_size, "size": info.file_size}
    assert unpack_annotation(entry, buffer.getvalue(), 0) == payload
    bad_entry = {**entry, "size": info.file_size + 1}
    with pytest.raises(ValueError, match="CRC/size"):
        unpack_annotation(bad_entry, buffer.getvalue(), 0)


def test_station_suffix_disambiguates_matching_names():
    lookup = {"labels_2024_01_24_14_10_20.json": [{"name": f"station{i}/labels_2024_01_24_14_10_20.json"} for i in (1, 2, 3)]}
    for suffix, station in (("", 1), ("_station2", 2), ("_station3", 3)):
        matched = match_source({"source_image_path": f"front_2024_01_24_14_10_20{suffix}.jpg"}, lookup)
        assert matched["name"].startswith(f"station{station}/")


def test_source_none_is_clean_but_missing_hole_stays_unknown():
    data = {"row_id": np.array(["row"]), "stains": np.array([None], dtype=object), "holes": np.array([None], dtype=object)}
    source = {"row": {"status": "matched", "labels": {"stains": "None", "holes": None}}}
    counts = apply_source_labels(data, source)
    assert defect_label(data["stains"][0]) == 0
    assert defect_label(data["holes"][0]) == -1
    assert counts["stains_unknown_recovered"] == 1


def test_identity_mismatch_excludes_labels():
    data = {"row_id": np.array(["row"]), "stains": np.array(["Major"], dtype=object), "holes": np.array(["Minor"], dtype=object)}
    apply_source_labels(data, {"row": {"status": "grade_mismatch"}})
    assert defect_label(data["stains"][0]) == defect_label(data["holes"][0]) == -1


def test_calibration_threshold_does_not_use_test_examples():
    threshold = choose_binary_threshold(np.array([0, 0, 1, 1]), np.array([.1, .2, .8, .9]))
    assert threshold == pytest.approx(.8)
    measured = binary_metrics(np.array([1, 0, 1]), np.array([.9, .85, .1]), threshold)
    assert measured["precision"]["k"] == 1 and measured["precision"]["n"] == 2
    assert measured["recall"]["k"] == 1 and measured["recall"]["n"] == 2
