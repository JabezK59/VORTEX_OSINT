import phonenumbers
from phonenumbers import geocoder, carrier, timezone, PhoneNumberType
from typing import Dict, Any, Optional

NUMBER_TYPE_MAP = {
    PhoneNumberType.FIXED_LINE: "Fixed Line (Landline)",
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
    PhoneNumberType.TOLL_FREE: "Toll-Free",
    PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    PhoneNumberType.SHARED_COST: "Shared Cost",
    PhoneNumberType.VOIP: "VoIP (Virtual Number)",
    PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "Universal Access Number (UAN)",
    PhoneNumberType.VOICEMAIL: "Voicemail",
    PhoneNumberType.UNKNOWN: "Unknown Type",
}


def inspect_phone(number_str: str, default_region: Optional[str] = None) -> Dict[str, Any]:
    """Analyze phone number for validity, format, location, carrier, and line type."""
    cleaned = number_str.strip()
    if not cleaned.startswith("+") and not default_region:
        # Default fallback guess if user enters country code without '+'
        if cleaned.startswith("1") and len(cleaned) == 11:
            default_region = "US"
        elif cleaned.startswith("44") and len(cleaned) == 12:
            default_region = "GB"
        elif cleaned.startswith("91") and len(cleaned) == 12:
            default_region = "IN"

    try:
        parsed = phonenumbers.parse(cleaned, default_region)
    except phonenumbers.NumberParseException as e:
        return {
            "input": number_str,
            "valid": False,
            "error": f"Parse error: {e}",
        }

    is_possible = phonenumbers.is_possible_number(parsed)
    is_valid = phonenumbers.is_valid_number(parsed)

    if not is_possible:
        return {
            "input": number_str,
            "valid": False,
            "error": "Number format is impossible for any known telephony standard",
        }

    # Formatting
    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    natl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    rfc = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.RFC3966)

    # Carrier & Geolocation
    carrier_name = carrier.name_for_number(parsed, "en")
    geo_location = geocoder.description_for_number(parsed, "en")
    country_code = parsed.country_code
    national_number = parsed.national_number

    # Line type
    raw_type = phonenumbers.number_type(parsed)
    type_name = NUMBER_TYPE_MAP.get(raw_type, "Unknown")

    # Timezones
    tz_list = list(timezone.time_zones_for_number(parsed))

    return {
        "input": number_str,
        "valid": is_valid,
        "e164": e164,
        "international": intl,
        "national": natl,
        "rfc3966": rfc,
        "country_code": f"+{country_code}",
        "national_number": str(national_number),
        "location": geo_location or "Unknown Geographic Region",
        "carrier": carrier_name or "Unknown Carrier",
        "line_type": type_name,
        "timezones": tz_list,
    }
