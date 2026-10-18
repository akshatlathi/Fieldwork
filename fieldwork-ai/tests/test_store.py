"""LocalStore on a temp dir; CloudStore with the Firestore and Storage clients mocked."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fieldwork.store import CloudStore, LocalStore


def test_local_store(tmp_path):
    s = LocalStore(tmp_path)
    assert s.get_json("records", "a") is None and s.list_json("records") == []
    s.put_json("records", "a", {"id": "a", "n": "é"})
    s.put_json("records", "b", {"id": "b"})
    assert s.get_json("records", "a") == {"id": "a", "n": "é"}
    assert [r["id"] for r in s.list_json("records")] == ["a", "b"]
    src = tmp_path / "src.jpg"
    src.write_bytes(b"x")
    dst = s.put_file("a", src, "f1.jpg")
    assert dst == s.item_dir("a") / "f1.jpg" and dst.read_bytes() == b"x"
    assert s.get_file("a", "f1.jpg") == dst
    assert s.get_file("a", "../../src.jpg") is None and s.get_file("a", "nope.jpg") is None
    s.sync_item("a")
    assert s.media_url("a", "f1.jpg") == "/media/a/f1.jpg"


def _cloud(tmp_path):
    fs, gcs = MagicMock(), MagicMock()
    mods = {"google.cloud.firestore": MagicMock(Client=MagicMock(return_value=fs)),
            "google.cloud.storage": MagicMock(Client=MagicMock(return_value=gcs))}
    with patch.dict(sys.modules, mods), patch("google.cloud.firestore", mods["google.cloud.firestore"], create=True), \
            patch("google.cloud.storage", mods["google.cloud.storage"], create=True):
        return CloudStore("b", tmp_path, "p"), fs, gcs.bucket.return_value


def test_cloud_json(tmp_path):
    s, fs, _ = _cloud(tmp_path)
    s.put_json("records", "a", {"id": "a"})
    fs.collection.assert_called_with("records")
    fs.collection.return_value.document.assert_called_with("a")
    fs.collection.return_value.document.return_value.set.assert_called_with({"id": "a"})
    snap = fs.collection.return_value.document.return_value.get.return_value
    snap.exists, snap.to_dict.return_value = True, {"id": "a"}
    assert s.get_json("records", "a") == {"id": "a"}
    snap.exists = False
    assert s.get_json("records", "zz") is None
    d = MagicMock()
    d.to_dict.return_value = {"id": "a"}
    fs.collection.return_value.stream.return_value = [d]
    assert s.list_json("records") == [{"id": "a"}]


def test_cloud_sync_and_fallback(tmp_path):
    s, _, bucket = _cloud(tmp_path)
    d = s.item_dir("a")
    (d / "sub").mkdir()
    (d / "f1.jpg").write_bytes(b"1")
    (d / "sub" / "f2.jpg").write_bytes(b"22")
    s.sync_item("a")
    names = sorted(c.args[0] for c in bucket.blob.call_args_list)
    assert names == ["items/a/f1.jpg", "items/a/sub/f2.jpg"]
    bucket.blob.reset_mock()
    s.sync_item("a")  # nothing new
    bucket.blob.assert_not_called()
    (d / "f3.jpg").write_bytes(b"3")
    s.sync_item("a")
    assert [c.args[0] for c in bucket.blob.call_args_list] == ["items/a/f3.jpg"]

    # local hit does not touch GCS; local miss downloads
    bucket.blob.reset_mock()
    assert s.get_file("a", "f1.jpg") == d / "f1.jpg"
    bucket.blob.assert_not_called()
    blob = bucket.blob.return_value
    blob.exists.return_value = True
    blob.download_to_filename.side_effect = lambda p: Path(p).write_bytes(b"remote")
    got = s.get_file("a", "gone.jpg")
    assert got is not None and got.read_bytes() == b"remote"
    blob.exists.return_value = False
    assert s.get_file("a", "missing.jpg") is None
    assert s.get_file("a", "../../etc/x") is None
