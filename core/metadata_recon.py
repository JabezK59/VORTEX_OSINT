import os
import hashlib
import mimetypes
import datetime
from typing import Dict, Any, Optional
from PIL import Image, ExifTags


def _convert_to_degrees(value) -> Optional[float]:
    """Helper function to convert GPS coordinates stored in EXIF to degrees in float."""
    try:
        d0 = value[0]
        d1 = value[1]
        d2 = value[2]

        d = float(d0)
        m = float(d1)
        s = float(d2)

        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def extract_image_exif(image_path: str) -> Dict[str, Any]:
    """Extract EXIF metadata and GPS from images."""
    exif_data = {}
    gps_info = {}

    try:
        with Image.open(image_path) as img:
            raw_exif = img._getexif()
            if not raw_exif:
                return {"has_exif": False, "tags": {}, "gps": None}

            for tag_id, value in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                if tag_name == "GPSInfo":
                    for gps_id in value:
                        gps_tag = ExifTags.GPSTAGS.get(gps_id, str(gps_id))
                        gps_info[gps_tag] = value[gps_id]
                else:
                    # Clean binary or non-serializable values
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="ignore").strip()
                        except Exception:
                            value = f"<Binary data {len(value)} bytes>"
                    exif_data[tag_name] = str(value)

        # Process GPS if available
        gps_payload = None
        if gps_info:
            lat = None
            lon = None
            if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
                lat = _convert_to_degrees(gps_info["GPSLatitude"])
                if lat and gps_info["GPSLatitudeRef"] == "S":
                    lat = -lat

            if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
                lon = _convert_to_degrees(gps_info["GPSLongitude"])
                if lon and gps_info["GPSLongitudeRef"] == "W":
                    lon = -lon

            if lat is not None and lon is not None:
                gps_payload = {
                    "latitude": lat,
                    "longitude": lon,
                    "maps_url": f"https://www.google.com/maps?q={lat},{lon}",
                }

        return {
            "has_exif": True,
            "tags": exif_data,
            "gps": gps_payload,
        }

    except Exception as e:
        return {
            "has_exif": False,
            "error": str(e),
            "tags": {},
            "gps": None,
        }


def inspect_file_metadata(file_path: str) -> Dict[str, Any]:
    """Extract comprehensive metadata, hashes, and EXIF from local files."""
    if not os.path.exists(file_path):
        return {"error": "File does not exist", "path": file_path}

    stat = os.stat(file_path)
    size_bytes = stat.st_size
    created_time = datetime.datetime.fromtimestamp(stat.st_ctime).isoformat()
    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
    mime_type, _ = mimetypes.guess_type(file_path)

    # Compute Hashes
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            md5_hash.update(chunk)
            sha256_hash.update(chunk)

    result = {
        "filename": os.path.basename(file_path),
        "path": os.path.abspath(file_path),
        "size_bytes": size_bytes,
        "size_human": f"{size_bytes / 1024:.2f} KB" if size_bytes < 1024*1024 else f"{size_bytes / (1024*1024):.2f} MB",
        "mime_type": mime_type or "application/octet-stream",
        "created": created_time,
        "modified": modified_time,
        "md5": md5_hash.hexdigest(),
        "sha256": sha256_hash.hexdigest(),
        "exif": None,
    }

    if mime_type and mime_type.startswith("image/"):
        result["exif"] = extract_image_exif(file_path)

    return result
