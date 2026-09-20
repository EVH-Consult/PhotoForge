from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from photoforge.metadata_extractors.xmp import extract_xmp_metadata


def test_xmp_sidecar_extracts_timestamp_keywords_and_gps(tmp_path: Path) -> None:
    media = tmp_path / "photo.jpg"
    media.write_bytes(b"not-read-by-xmp-extractor")
    (tmp_path / "photo.xmp").write_text(
        """<?xml version="1.0"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/"
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:xmp="http://ns.adobe.com/xap/1.0/"
  xmlns:exif="http://ns.adobe.com/exif/1.0/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:RDF><rdf:Description xmp:CreateDate="2024-01-02T03:04:05+02:30"
    exif:GPSLatitude="50.8N" exif:GPSLongitude="4.3E">
    <dc:subject><rdf:Bag><rdf:li>Travel</rdf:li><rdf:li>Family</rdf:li></rdf:Bag></dc:subject>
  </rdf:Description></rdf:RDF>
</x:xmpmeta>
""",
        encoding="utf-8",
    )

    result = extract_xmp_metadata(media)

    assert result.path == tmp_path / "photo.xmp"
    assert result.timestamp_candidates[0].naive_timestamp == datetime(
        2024, 1, 2, 3, 4, 5
    )
    assert result.timestamp_candidates[0].timezone_offset == timedelta(
        hours=2, minutes=30
    )
    assert result.keywords == ("Family", "Travel")
    assert result.gps_latitude == 50.8
    assert result.gps_longitude == 4.3


def test_invalid_xmp_is_reported_without_raising(tmp_path: Path) -> None:
    media = tmp_path / "photo.jpg"
    media.write_bytes(b"")
    (tmp_path / "photo.xmp").write_text("<broken", encoding="utf-8")

    result = extract_xmp_metadata(media)

    assert result.timestamp_candidates == ()
    assert result.diagnostics[0].source_kind == "xmp"
    assert result.diagnostics[0].diagnostic_type == "unreadable"
