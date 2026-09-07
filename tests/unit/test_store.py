from cicada.store import put_bytes, sha256_bytes, get_bytes


def test_put_and_get_roundtrip(tmp_path, monkeypatch):
    data = b"vertical-slice-payload"
    rec = put_bytes(data, hint_name="slice.txt")
    assert rec["sha256"] == sha256_bytes(data)
    assert rec["byte_length"] == len(data)
    assert get_bytes(rec["sha256"]) == data


def test_same_bytes_same_digest():
    a = put_bytes(b"abc")
    b = put_bytes(b"abc")
    assert a["sha256"] == b["sha256"]
