import os
import re
import math
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ExifTags, ImageStat


def calculate_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Calculate difference hash (dHash) for visual image fingerprinting."""
    try:
        # Resize to (hash_size + 1, hash_size) in grayscale
        resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())

        difference = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + col + 1]
                difference.append(pixel_left > pixel_right)

        # Convert boolean list to hexadecimal string
        decimal_val = 0
        hex_str = []
        for index, value in enumerate(difference):
            if value:
                decimal_val += 2 ** (index % 4)
            if (index % 4) == 3:
                hex_str.append(hex(decimal_val)[2:])
                decimal_val = 0
        return "".join(hex_str)
    except Exception:
        return "0000000000000000"


def _convert_gps_to_float(value) -> Optional[float]:
    """Helper to convert EXIF GPS coordinate tuples to decimal degrees."""
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def extract_gps_data(image: Image.Image) -> Optional[Dict[str, Any]]:
    """Extract decimal GPS coordinates, altitude, and maps links from image EXIF."""
    try:
        raw_exif = image._getexif()
        if not raw_exif:
            return None

        gps_info = {}
        for tag_id, val in raw_exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if tag_name == "GPSInfo":
                for gps_id in val:
                    gps_tag = ExifTags.GPSTAGS.get(gps_id, str(gps_id))
                    gps_info[gps_tag] = val[gps_id]

        if not gps_info:
            return None

        lat, lon = None, None
        if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
            lat = _convert_gps_to_float(gps_info["GPSLatitude"])
            if lat and gps_info["GPSLatitudeRef"] == "S":
                lat = -lat

        if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
            lon = _convert_gps_to_float(gps_info["GPSLongitude"])
            if lon and gps_info["GPSLongitudeRef"] == "W":
                lon = -lon

        if lat is not None and lon is not None:
            lat_f = round(lat, 6)
            lon_f = round(lon, 6)
            return {
                "latitude": lat_f,
                "longitude": lon_f,
                "coordinates": f"{lat_f}, {lon_f}",
                "google_maps": f"https://www.google.com/maps?q={lat_f},{lon_f}",
                "google_earth": f"https://earth.google.com/web/search/{lat_f},{lon_f}",
                "openstreetmap": f"https://www.openstreetmap.org/?mlat={lat_f}&mlon={lon_f}#map=16/{lat_f}/{lon_f}",
                "geohack": f"https://geohack.toolforge.org/geohack.php?params={lat_f}_N_{lon_f}_E",
            }
    except Exception:
        pass
    return None


def analyze_image_environment(image: Image.Image) -> Dict[str, Any]:
    """Analyze image color distribution to estimate terrain, vegetation, and lighting."""
    try:
        rgb_img = image.convert("RGB")
        stat = ImageStat.Stat(rgb_img)
        avg_r, avg_g, avg_b = stat.mean[:3]
        brightness = (avg_r * 299 + avg_g * 587 + avg_b * 114) / 1000

        # Downsample to 64x64 to quickly compute dominant color buckets
        small = rgb_img.resize((64, 64), Image.Resampling.BILINEAR)
        pixels = list(small.getdata())
        total_px = len(pixels)

        green_veg_count = 0
        arid_desert_count = 0
        sky_water_count = 0
        snow_white_count = 0
        urban_asphalt_count = 0

        for r, g, b in pixels:
            # Vegetation (Green is higher than Red and Blue)
            if g > r * 1.15 and g > b * 1.15 and g > 40:
                green_veg_count += 1
            # Arid / Desert / Red Soil (High red & warm tones)
            elif r > g * 1.1 and g > b * 1.1 and r > 70:
                arid_desert_count += 1
            # Sky / Water (Blue dominant)
            elif b > r * 1.15 and b > g * 1.05 and b > 70:
                sky_water_count += 1
            # Snow / Clouds / Overcast (High values, close together)
            elif r > 210 and g > 210 and b > 210 and max(abs(r-g), abs(g-b)) < 20:
                snow_white_count += 1
            # Urban / Concrete / Dark Asphalt
            elif r < 90 and g < 90 and b < 90 and max(abs(r-g), abs(g-b)) < 25:
                urban_asphalt_count += 1

        veg_pct = round((green_veg_count / total_px) * 100, 1)
        arid_pct = round((arid_desert_count / total_px) * 100, 1)
        sky_pct = round((sky_water_count / total_px) * 100, 1)
        snow_pct = round((snow_white_count / total_px) * 100, 1)
        urban_pct = round((urban_asphalt_count / total_px) * 100, 1)

        # Environment estimation
        primary_biome = "Mixed / Indeterminate"
        if veg_pct > 25:
            primary_biome = "Temperate / Woodland / Grassland"
        elif arid_pct > 25:
            primary_biome = "Arid / Desert / Savanna / Drylands"
        elif snow_pct > 30:
            primary_biome = "Snow / Alpine / Polar Region"
        elif urban_pct > 35:
            primary_biome = "Dense Urban / Industrial / Paved"
        elif sky_pct > 35:
            primary_biome = "Open Horizon / Maritime / Coastal"

        # Lighting estimation
        lighting = "Daylight"
        if brightness < 45:
            lighting = "Night / Dark Scene"
        elif brightness < 90:
            lighting = "Dawn / Dusk / Overcast Low Light"
        elif brightness > 200:
            lighting = "High Exposure / Intense Direct Sunlight"

        return {
            "brightness_score": round(brightness, 1),
            "lighting_condition": lighting,
            "primary_biome": primary_biome,
            "vegetation_pct": veg_pct,
            "arid_soil_pct": arid_pct,
            "sky_water_pct": sky_pct,
            "snow_pct": snow_pct,
            "urban_pavement_pct": urban_pct,
            "dominant_rgb": (round(avg_r), round(avg_g), round(avg_b)),
            "dominant_hex": f"#{round(avg_r):02x}{round(avg_g):02x}{round(avg_b):02x}",
        }
    except Exception:
        return {
            "brightness_score": 0,
            "lighting_condition": "Unknown",
            "primary_biome": "Analysis unavailable",
            "vegetation_pct": 0,
            "arid_soil_pct": 0,
            "sky_water_pct": 0,
            "snow_pct": 0,
            "urban_pavement_pct": 0,
            "dominant_rgb": (0, 0, 0),
            "dominant_hex": "#000000",
        }


# Curated GeoGuessr & Bellingcat Photo OSINT Field Database
GEOGUESSR_COUNTRY_META = {
    "Japan": {
        "driving_side": "Left",
        "poles": "Concrete poles with yellow/black spiraling guy wire protectors; low transformers",
        "plates": "White plates with green text; small yellow plates for kei cars",
        "road_lines": "White outer lines, yellow or white center lines, blue pedestrian crossing posts",
        "clues": "Kanji / Kana characters on signs, narrow residential streets with no street parking, pristine asphalt."
    },
    "United Kingdom": {
        "driving_side": "Left",
        "poles": "Wooden poles with yellow/black base markings; metal lattice masts in rural spots",
        "plates": "White front plate, Yellow rear plate",
        "road_lines": "White dashed center lines, double yellow lines on curbs (no parking)",
        "clues": "Bilingual signs in Wales, brick terrace housing, red post boxes and phone kiosks."
    },
    "Australia": {
        "driving_side": "Left",
        "poles": "Wooden Stobie poles (concrete with steel edges in South Australia); round wooden poles elsewhere",
        "plates": "Standard white/yellow varying by state; wide variety of state slogans",
        "road_lines": "White center lines (broken white), single white lines on edges",
        "clues": "Red or ochre soil in the Outback, distinctive eucalyptus / gum trees, yellow diamond kangaroo/wombat road signs."
    },
    "France": {
        "driving_side": "Right",
        "poles": "Concrete poles with hollow holes or holes with steps; wooden poles with metal blue tags",
        "plates": "EU standard (blue strip on left with 'F', blue strip on right with department number)",
        "road_lines": "Long dashed white center lines (French 10m lines with 3m gaps), white edge lines",
        "clues": "Red and white striped bollards, town entry signs in dark blue font inside white rectangles with red borders."
    },
    "Germany": {
        "driving_side": "Right",
        "poles": "Concrete or wooden poles, low transformers; clean roadside marker posts (black and white)",
        "plates": "EU standard with 'D' and regional city codes (e.g. B for Berlin, M for Munich)",
        "road_lines": "Thick solid or dashed white lines, yellow markings strictly for roadworks",
        "clues": "Curved house numbering signs, blue street signs with serif font, highly maintained Autobahn infrastructure."
    },
    "Brazil": {
        "driving_side": "Right",
        "poles": "Distinctive 'Ladder' concrete poles (horizontal steps up the pole)",
        "plates": "Mercosul plates (blue top banner with country name, white background)",
        "road_lines": "Continuous yellow center lines, white dashed lanes, yellow double center lines",
        "clues": "Rich red clay soil (Terra Roxa), black backs on highway regulatory signs, Portuguese signage."
    },
    "South Africa": {
        "driving_side": "Left",
        "poles": "Wooden poles with metal caps; yellow painted bottom sections",
        "plates": "White plates with green or black letters; yellow plates in some provinces",
        "road_lines": "Yellow dashed or solid outer lines, white dashed center lines",
        "clues": "Savanna grass (veld), high security electric fences in suburban neighborhoods, bilingual English/Afrikaans signs."
    },
    "Norway": {
        "driving_side": "Right",
        "poles": "Wooden poles with distinctive diagonal metal struts; tall marker poles with reflectors for snow",
        "plates": "EU-style blue strip with Norwegian flag and 'N'; green plates for commercial 2-seater vehicles",
        "road_lines": "Solid or dashed yellow center lines on major routes; white lines on edges",
        "clues": "Fjord topography, wooden stave houses painted red or yellow, white rectangular road signs with black borders."
    },
    "United States": {
        "driving_side": "Right",
        "poles": "Tall thick dark creosote wooden poles with abundant overhead transformers and cable clutter",
        "plates": "Rear license plate standard; highly colorful state-specific designs with state names",
        "road_lines": "Double solid yellow lines (no passing), single solid white lines on right edge",
        "clues": "Yellow diamond warning signs, green highway exit markers, fire hydrants on sidewalks, mailboxes at curbs."
    },
    "Poland": {
        "driving_side": "Right",
        "poles": "Pre-stressed concrete poles with hollow circular holes or A-frame concrete supports",
        "plates": "EU standard with 'PL' on blue strip",
        "road_lines": "White center lines, red/white reflective roadside marker posts",
        "clues": "Distinctive red pedestrian crossing signs with yellow-green background, bilingual Kashubian signs in north."
    }
}


def generate_multimodal_osint_prompt(image_meta: Dict[str, Any], env_meta: Dict[str, Any]) -> str:
    """Generate a structured forensic prompt for LLMs/multimodal models to geolocate the image."""
    return f"""### PHOTO OSINT & GEOLOCATION INVESTIGATION DOSSIER
Analyze this image using Bellingcat and GeoGuessr methodologies. Deduce the exact country, state/province, or coordinates:

[PRE-EXTRACTED FORENSIC ATTRIBUTES]:
- Visual Fingerprint (dHash): {image_meta.get('dhash', 'N/A')}
- Image Dimensions: {image_meta.get('width', 0)} x {image_meta.get('height', 0)} ({image_meta.get('aspect_ratio', 'N/A')})
- Estimated Lighting Condition: {env_meta.get('lighting_condition', 'N/A')} (Score: {env_meta.get('brightness_score', 0)}/255)
- Predominant Biome: {env_meta.get('primary_biome', 'N/A')}
- Vegetation Index: {env_meta.get('vegetation_pct', 0)}%
- Arid / Red Soil Index: {env_meta.get('arid_soil_pct', 0)}%
- Asphalt / Urban Index: {env_meta.get('urban_pavement_pct', 0)}%

[FORENSIC EVIDENCE CHECKLIST FOR GEOLOCATION]:
1. Driving Orientation: Examine vehicular lane positioning, steering wheel orientation, and side mirrors.
2. Telecommunications & Utility Poles: Inspect pole material (wood, ladder concrete, Stobie), guy wire guards, and transformer shapes.
3. Road Markings & Bollards: Identify center line color (yellow vs white), dash lengths, and reflector post styles.
4. Vegetation & Flora: Classify tree species (coniferous, eucalyptus, deciduous, palm) and soil pigmentation (red clay vs dark loam).
5. Architecture & Signage: Decode language script, chevron warning colors, roof pitches, and building materials.
6. Sun Angle & Shadows: Estimate solar azimuth and hemisphere (North vs South).
"""


def inspect_photo_osint(image_path: str) -> Dict[str, Any]:
    """Execute complete Photo OSINT and Geolocation analysis on an image."""
    if not os.path.exists(image_path):
        return {"error": "Image file not found", "path": image_path}

    try:
        with Image.open(image_path) as img:
            width, height = img.size
            aspect = f"{width / math.gcd(width, height):.0f}:{height / math.gcd(width, height):.0f}" if height > 0 else "N/A"
            dhash_val = calculate_dhash(img)
            gps_data = extract_gps_data(img)
            env_data = analyze_image_environment(img)

            # Camera make/model if present
            camera_make = "Unknown"
            camera_model = "Unknown"
            lens_model = "Unknown"
            date_taken = "N/A"

            raw_exif = img._getexif()
            if raw_exif:
                for tag_id, val in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    if tag_name == "Make":
                        camera_make = str(val).strip()
                    elif tag_name == "Model":
                        camera_model = str(val).strip()
                    elif tag_name == "LensModel":
                        lens_model = str(val).strip()
                    elif tag_name == "DateTimeOriginal":
                        date_taken = str(val).strip()

            meta = {
                "filename": os.path.basename(image_path),
                "path": os.path.abspath(image_path),
                "width": width,
                "height": height,
                "aspect_ratio": aspect,
                "dhash": dhash_val,
                "camera_make": camera_make,
                "camera_model": camera_model,
                "lens_model": lens_model,
                "date_taken": date_taken,
                "gps": gps_data,
                "environment": env_data,
            }

            # Generate structured reverse search URLs
            meta["reverse_search_engines"] = {
                "Google Lens": "https://lens.google.com/upload",
                "Yandex Images": "https://yandex.com/images/search?rpt=imageview",
                "TinEye": "https://tineye.com",
                "Bing Visual Search": "https://www.bing.com/visualsearch",
                "Baidu Image": "https://graph.baidu.com/pcpage/index/similar",
            }

            meta["ai_prompt"] = generate_multimodal_osint_prompt(meta, env_data)
            return meta

    except Exception as e:
        return {"error": f"Failed to process image: {str(e)}", "path": image_path}
