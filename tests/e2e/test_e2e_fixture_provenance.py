from PIL import Image

from tests.e2e.helpers import fixture_input_source_dir, load_manifest


def test_demo_fixture_is_declared_and_structurally_synthetic() -> None:
    manifest = load_manifest("demo")
    assert manifest["synthetic"] is True
    assert manifest["provenance"] == "tests/e2e/fixtures/demo/README.md"

    input_root = fixture_input_source_dir("demo")
    image_paths = tuple(
        path
        for path in sorted(input_root.rglob("*.jpg"))
        if path.name != "corrupt.jpg"
    )
    assert image_paths

    for path in image_paths:
        with Image.open(path) as image:
            assert image.size == (96, 64)
            exif = image.getexif()
            assert exif.get(271) == "PhotoForge"
            assert exif.get(272) == "Synthetic E2E Camera"
            assert exif.get(36867) is not None
            assert exif.get(36881) == "+00:00"
            assert exif.get_ifd(34853)
