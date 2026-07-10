from __future__ import annotations

import hashlib
import os
import uuid
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PHOTO_BYTES = 15 * 1024 * 1024
MAX_PHOTO_PIXELS = 40_000_000
MAX_PHOTOS_PER_ACTIVITY = 30
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class PhotoValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StoredPhoto:
    path: Path
    file_hash: str
    size_bytes: int
    width: int
    height: int
    content_type: str = "image/webp"


@dataclass(frozen=True)
class StagedPhotoDeletion:
    original_path: Path
    staged_path: Path


def _photo_root(upload_dir: Path) -> Path:
    root = (upload_dir / "activity_photos").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _server_generated_destination(upload_dir: Path, photo_id: str) -> Path:
    try:
        normalized_id = str(uuid.UUID(photo_id))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Ungültige serverseitige Foto-ID.") from exc
    if normalized_id != photo_id.lower():
        raise ValueError("Ungültige serverseitige Foto-ID.")
    root = _photo_root(upload_dir)
    shard = normalized_id.replace("-", "")[:2]
    destination = (root / shard / f"{normalized_id}.webp").resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Der Fotozielpfad liegt außerhalb des Uploadverzeichnisses.")
    return destination


def safe_photo_path(stored_path: str | Path, upload_dir: Path, *, must_exist: bool = False) -> Path:
    root = _photo_root(upload_dir)
    candidate = Path(stored_path).resolve(strict=False)
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError("Unsicherer Fotopfad.")
    if must_exist and (not candidate.is_file() or candidate.is_symlink()):
        raise FileNotFoundError(candidate)
    return candidate


def validate_and_store_photo(data: bytes, photo_id: str, upload_dir: Path) -> StoredPhoto:
    if not data:
        raise PhotoValidationError("Die Bilddatei ist leer.")
    if len(data) > MAX_PHOTO_BYTES:
        raise PhotoValidationError("Das Aktivitätsfoto ist zu groß.")

    digest = hashlib.sha256(data).hexdigest()
    destination = _server_generated_destination(upload_dir, photo_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{uuid.uuid4()}.tmp"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                image_format = (probe.format or "").upper()
                width, height = probe.size
                if image_format not in ALLOWED_IMAGE_FORMATS:
                    raise PhotoValidationError("Unterstützt werden JPEG-, PNG- und WebP-Bilder.")
                if width <= 0 or height <= 0 or width * height > MAX_PHOTO_PIXELS:
                    raise PhotoValidationError("Das Aktivitätsfoto hat unzulässige Abmessungen.")
                if getattr(probe, "n_frames", 1) != 1:
                    raise PhotoValidationError("Animierte Aktivitätsfotos werden nicht unterstützt.")
                probe.verify()

            with Image.open(BytesIO(data)) as source:
                source.load()
                normalized = ImageOps.exif_transpose(source)
                has_alpha = normalized.mode in {"RGBA", "LA"} or (
                    normalized.mode == "P" and "transparency" in normalized.info
                )
                output = normalized.convert("RGBA" if has_alpha else "RGB")
                try:
                    width, height = output.size
                    output.save(temporary, format="WEBP", quality=90, method=6)
                finally:
                    output.close()
        os.replace(temporary, destination)
    except PhotoValidationError:
        temporary.unlink(missing_ok=True)
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise PhotoValidationError("Die Datei ist kein gültiges, sicher lesbares Bild.") from exc

    return StoredPhoto(
        path=destination,
        file_hash=digest,
        size_bytes=destination.stat().st_size,
        width=width,
        height=height,
    )


def stage_photo_deletions(paths: Iterable[str | Path], upload_dir: Path) -> list[StagedPhotoDeletion]:
    root = _photo_root(upload_dir)
    trash = root / ".trash"
    staged: list[StagedPhotoDeletion] = []
    try:
        for raw_path in paths:
            path = safe_photo_path(raw_path, upload_dir)
            if not path.exists():
                continue
            if not path.is_file() or path.is_symlink():
                raise ValueError("Der gespeicherte Fotopfad verweist nicht auf eine reguläre Datei.")
            trash.mkdir(parents=True, exist_ok=True)
            staged_path = trash / f"{uuid.uuid4()}.deleted"
            os.replace(path, staged_path)
            staged.append(StagedPhotoDeletion(original_path=path, staged_path=staged_path))
    except Exception:
        restore_staged_photo_deletions(staged)
        raise
    return staged


def restore_staged_photo_deletions(staged: Iterable[StagedPhotoDeletion]) -> None:
    for item in reversed(list(staged)):
        if not item.staged_path.exists():
            continue
        item.original_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(item.staged_path, item.original_path)


def finalize_staged_photo_deletions(staged: Iterable[StagedPhotoDeletion]) -> None:
    errors: list[OSError] = []
    for item in staged:
        try:
            item.staged_path.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(exc)
    if errors:
        raise OSError(f"{len(errors)} Fotodatei(en) konnten nicht endgültig entfernt werden.") from errors[0]
