# PhotoForge — Media Format Contract

## Classification

INTERNAL

## Purpose

`src/photoforge/media_formats.py` owns the extension-to-format mapping,
canonical extensions, Live Photo still-format eligibility, and deterministic
structural validation for processable media.

## Validation

- PNG and TIFF use Pillow format matching and full verification.
- HEIC/HEIF and MP4/MOV validate their ISO Base Media `ftyp` box and accepted
  major/compatible brand.
- CR2 validates its Canon TIFF/CR2 signature.
- NEF and ARW validate a TIFF byte-order/version signature.
- JPEG is intentionally not passed through this new gate; its established
  scanner behavior is preserved.

Validation reads only file content and never mutates input. Detailed behavioral
authority remains `SPEC.md`.
