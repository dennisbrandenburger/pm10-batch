import csv
from pathlib import Path

import pytest

from pm10.ingest import HEADERS


@pytest.fixture
def row():
    return dict(
        zip(
            HEADERS,
            [
                "01",
                "001",
                "0001",
                "81102",
                "1",
                "30",
                "-80",
                "WGS84",
                "PM10 Total 0-10um STP",
                "2024-01-01",
                "00:00",
                "2024-01-01",
                "06:00",
                "10",
                "Micrograms/cubic meter (25 C)",
                "0.1",
                "",
                "",
                "FEM",
                "239",
                "test method",
                "Test State",
                "Test County",
                "2025-01-01",
            ],
        )
    )


def write_csv(path, rows):
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
