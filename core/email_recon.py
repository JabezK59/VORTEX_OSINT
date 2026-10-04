import re
import hashlib
import json
import os
import requests
import dns.resolver
from typing import Dict, Any, List, Optional

FREE_PROVIDERS = {
    "gmail.com": "Google Mail",
    "googlemail.com": "Google Mail",
    "yahoo.com": "Yahoo Mail",
    "hotmail.com": "Microsoft Hotmail",
    "outlook.com": "Microsoft Outlook",
    "live.com": "Microsoft Live",
    "msn.com": "Microsoft MSN",
    "icloud.com": "Apple iCloud",
    "me.com": "Apple Mail",
    "mac.com": "Apple Mail",
    "proton.me": "Proton Mail",
    "protonmail.com": "Proton Mail",
    "zoho.com": "Zoho Mail",
    "aol.com": "AOL Mail",
    "mail.com": "Mail.com",
    "gmx.com": "GMX Mail",
    "tutanota.com": "Tuta Mail",
    "tuta.com": "Tuta Mail",
    "fastmail.com": "Fastmail",
    "yandex.com": "Yandex Mail",
    "yandex.ru": "Yandex Mail",
}

DISPOSABLE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "disposable_domains.json")


def load_disposable_domains() -> set:
    if os.path.exists(DISPOSABLE_FILE):
        try:
            with open(DISPOSABLE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return {"10minutemail.com", "guerrillamail.com", "mailinator.com", "tempmail.com"}


DISPOSABLE_DOMAINS = load_disposable_domains()


def validate_email_syntax(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def get_mx_records(domain: str) -> List[Dict[str, Any]]:
    records = []
    try:
        answers = dns.resolver.resolve(domain, "MX")
        for rdata in answers:
            records.append({
                "host": str(rdata.exchange).rstrip("."),
                "preference": rdata.preference,
            })
        records.sort(key=lambda x: x["preference"])
    except Exception:
        pass
    return records


def check_gravatar(email: str) -> Dict[str, Any]:
    clean_email = email.strip().lower()
    md5_hash = hashlib.md5(clean_email.encode("utf-8")).hexdigest()
    sha256_hash = hashlib.sha256(clean_email.encode("utf-8")).hexdigest()

    gravatar_info = {
        "exists": False,
        "avatar_url": f"https://www.gravatar.com/avatar/{md5_hash}?s=200",
        "profile_url": f"https://gravatar.com/{md5_hash}",
        "profile_data": None,
        "display_name": "",
        "about": "",
        "location": "",
        "accounts": [],
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # Check avatar image presence
        check_img_url = f"https://www.gravatar.com/avatar/{md5_hash}?d=404"
        r_img = requests.head(check_img_url, headers=headers, timeout=5)
        if r_img.status_code == 200:
            gravatar_info["exists"] = True

        # Check JSON profile
        json_url = f"https://en.gravatar.com/{md5_hash}.json"
        r_json = requests.get(json_url, headers=headers, timeout=5)
        if r_json.status_code == 200:
            gravatar_info["exists"] = True
            data = r_json.json()
            if "entry" in data and len(data["entry"]) > 0:
                entry = data["entry"][0]
                gravatar_info["display_name"] = entry.get("displayName", "")
                gravatar_info["about"] = entry.get("aboutMe", "")
                gravatar_info["location"] = entry.get("currentLocation", "")
                gravatar_info["profile_url"] = entry.get("profileUrl", gravatar_info["profile_url"])
                gravatar_info["accounts"] = entry.get("accounts", [])
                gravatar_info["profile_data"] = entry
    except Exception:
        pass

    return gravatar_info


def inspect_email(email: str) -> Dict[str, Any]:
    email = email.strip()
    is_valid_format = validate_email_syntax(email)

    if not is_valid_format:
        return {
            "email": email,
            "valid_syntax": False,
            "error": "Invalid email syntax format"
        }

    username, domain = email.split("@", 1)
    domain_lower = domain.lower()

    # Provider classification
    is_free = domain_lower in FREE_PROVIDERS
    free_provider_name = FREE_PROVIDERS.get(domain_lower, "")
    is_disposable = domain_lower in DISPOSABLE_DOMAINS

    # MX Lookup
    mx_records = get_mx_records(domain_lower)
    has_mx = len(mx_records) > 0

    # Gravatar OSINT
    gravatar = check_gravatar(email)

    # Email provider category
    if is_disposable:
        provider_category = "Disposable / Burner Email"
    elif is_free:
        provider_category = f"Free Webmail ({free_provider_name})"
    elif has_mx:
        provider_category = "Custom Business / Organization Domain"
    else:
        provider_category = "Inactive or Invalid Domain (No MX records)"

    return {
        "email": email,
        "username": username,
        "domain": domain_lower,
        "valid_syntax": True,
        "has_mx": has_mx,
        "mx_records": mx_records,
        "is_free_provider": is_free,
        "free_provider_name": free_provider_name,
        "is_disposable": is_disposable,
        "category": provider_category,
        "gravatar": gravatar,
    }
