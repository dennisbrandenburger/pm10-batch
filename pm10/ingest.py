"""Download and preserve an auditable source snapshot before processing."""

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HEADERS = [
    "State Code",
    "County Code",
    "Site Num",
    "Parameter Code",
    "POC",
    "Latitude",
    "Longitude",
    "Datum",
    "Parameter Name",
    "Date Local",
    "Time Local",
    "Date GMT",
    "Time GMT",
    "Sample Measurement",
    "Units of Measure",
    "MDL",
    "Uncertainty",
    "Qualifier",
    "Method Type",
    "Method Code",
    "Method Name",
    "State Name",
    "County Name",
    "Date of Last Change",
]
MAX_ARCHIVE = 256 * 1024**2
MAX_CSV = 3 * 1024**3


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    tmp.replace(path)


def validate_archive(path, year):
    expected = f"hourly_81102_{year}.csv"
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != expected:
            raise ValueError("ZIP must contain exactly the expected CSV, without subdirectories")
        entry = entries[0]
        if entry.file_size > MAX_CSV or entry.flag_bits & 1:
            raise ValueError("Oversized or encrypted archive")
        # Reading the entire member verifies its CRC, including bytes after the header.
        with archive.open(entry) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            if next(csv.reader(text), None) != HEADERS:
                raise ValueError("Unexpected CSV header")
            for _ in iter(lambda: text.read(1024**2), ""):
                pass
        return entry.file_size


def _ingest(data, year, archive_path=None, expected_sha=None):
    if not 1990 <= year <= datetime.now().year:
        raise ValueError("Year outside supported interval")
    data = Path(data)
    raw = data / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    url = f"https://aqs.epa.gov/aqsweb/airdata/hourly_81102_{year}.zip"
    fd, name = tempfile.mkstemp(prefix="download-", suffix=".part", dir=raw)
    os.close(fd)
    temp = Path(name)
    headers = {}
    try:
        if archive_path:
            if Path(archive_path).stat().st_size > MAX_ARCHIVE:
                raise ValueError("Archive exceeds size limit")
            shutil.copyfile(archive_path, temp)
        else:
            request = urllib.request.Request(
                url, headers={"User-Agent": "pm10-batch/1.0 (academic data pipeline)"}
            )
            with (
                urllib.request.urlopen(request, timeout=90) as response,
                temp.open("wb") as output,
            ):
                if not response.url.startswith("https://aqs.epa.gov/"):
                    raise ValueError("Unexpected download redirect")
                headers = {k: response.headers.get(k) for k in ["ETag", "Last-Modified"]}
                size = 0
                while block := response.read(1024**2):
                    size += len(block)
                    if size > MAX_ARCHIVE:
                        raise ValueError("Archive exceeds size limit")
                    output.write(block)
        digest = sha256(temp)
        if expected_sha and digest != expected_sha:
            raise ValueError("Source SHA-256 does not match the requested snapshot")
        csv_size = validate_archive(temp, year)
        target = raw / f"{digest}.zip"
        if target.exists():
            if sha256(target) != digest:
                raise ValueError("Stored raw snapshot has been modified")
            temp.unlink()
        else:
            temp.replace(target)
            target.chmod(0o444)
        manifest = {
            "dataset": f"epa_pm10_{year}",
            "year": year,
            "sha256": digest,
            "archive_bytes": target.stat().st_size,
            "csv_bytes": csv_size,
            "url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "acquisition": "local_archive" if archive_path else "https_download",
            "http_headers": headers,
            "archive": f"raw/{digest}.zip",
        }
        # Each acquisition remains auditable, even if EPA returns identical bytes.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        write_json(data / "manifests" / f"{year}-{stamp}.json", manifest)
        write_json(data / f"source-{year}.json", manifest)
        return manifest
    finally:
        temp.unlink(missing_ok=True)


def ingest(data, year, archive_path=None, expected_sha=None):
    import fcntl

    data = Path(data)
    data.mkdir(parents=True, exist_ok=True)
    with (data / f".ingest-{year}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _ingest(data, year, archive_path, expected_sha)


def extract(data, manifest, target_dir):
    """Split the ZIP member into bounded gzip CSV parts without a 1 GiB disk copy."""
    import gzip

    archive = Path(data) / manifest["archive"]
    if sha256(archive) != manifest["sha256"]:
        raise ValueError("Raw archive integrity check failed")
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(target_dir).free < 256 * 1024**2:
        raise OSError("Less than 256 MiB free before extraction")
    csv.field_size_limit(1024**2)
    stream = None
    try:
        with (
            zipfile.ZipFile(archive) as z,
            z.open(f"hourly_81102_{manifest['year']}.csv") as member,
        ):
            reader = csv.reader(io.TextIOWrapper(member, encoding="utf-8-sig", newline=""))
            if next(reader) != HEADERS:
                raise ValueError("Unexpected CSV header")
            for index, row in enumerate(reader):
                if len(row) != len(HEADERS):
                    raise ValueError(f"Unexpected column count in source record {index + 2}")
                if index % 100000 == 0:
                    if stream:
                        stream.close()
                    if shutil.disk_usage(target_dir).free < 128 * 1024**2:
                        raise OSError("Disk reserve reached during extraction")
                    stream = gzip.open(
                        target_dir / f"part-{index // 100000:05d}.csv.gz",
                        "wt",
                        encoding="utf-8",
                        newline="",
                        compresslevel=1,
                    )
                    writer = csv.writer(stream)
                    writer.writerow(HEADERS)
                writer.writerow(row)
    finally:
        if stream:
            stream.close()
    return target_dir
