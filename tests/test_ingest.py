import csv
import io
import zipfile

import pytest

from pm10.ingest import HEADERS, extract, ingest, sha256, validate_archive


def archive(path, row, name="hourly_81102_2024.csv"):
    data = io.StringIO()
    w = csv.DictWriter(data, fieldnames=HEADERS)
    w.writeheader()
    w.writerow(row)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, data.getvalue())
    return path


def test_snapshot_manifest_and_integrity(tmp_path, row):
    source = archive(tmp_path / "source.zip", row)
    m = ingest(tmp_path / "data", 2024, source, sha256(source))
    assert m["acquisition"] == "local_archive"
    assert len(list(extract(tmp_path / "data", m, tmp_path / "work").glob("*.csv.gz"))) == 1
    second = ingest(tmp_path / "data", 2024, source)
    assert second["sha256"] == m["sha256"]
    assert len(list((tmp_path / "data/manifests").glob("*.json"))) == 2
    assert len(list((tmp_path / "data/raw").glob("*.zip"))) == 1


@pytest.mark.parametrize(
    "name", ["../hourly_81102_2024.csv", "other.csv", "folder/hourly_81102_2024.csv"]
)
def test_reject_unexpected_member(tmp_path, row, name):
    with pytest.raises(ValueError, match="exactly"):
        validate_archive(archive(tmp_path / "source.zip", row, name), 2024)


def test_expected_hash_and_bad_header(tmp_path, row):
    source = archive(tmp_path / "source.zip", row)
    with pytest.raises(ValueError, match="SHA-256"):
        ingest(tmp_path / "data", 2024, source, "0" * 64)
    with zipfile.ZipFile(source, "w") as z:
        z.writestr("hourly_81102_2024.csv", "wrong,header\n")
    with pytest.raises(ValueError, match="header"):
        validate_archive(source, 2024)
    assert not list((tmp_path / "data/raw").glob("*.part"))


def test_crc_and_malformed_csv_record(tmp_path, row):
    path = tmp_path / "broken.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr("hourly_81102_2024.csv", ",".join(HEADERS) + "\n" + "x" * 100)
    content = path.read_bytes().replace(b"x" * 100, b"y" * 100)
    path.write_bytes(content)
    with pytest.raises(zipfile.BadZipFile):
        validate_archive(path, 2024)
    source = archive(tmp_path / "source.zip", row)
    manifest = ingest(tmp_path / "data", 2024, source)
    stored = tmp_path / "data" / manifest["archive"]
    stored.chmod(0o644)
    stored.write_bytes(b"changed")
    with pytest.raises(ValueError, match="integrity"):
        extract(tmp_path / "data", manifest, tmp_path / "work")
