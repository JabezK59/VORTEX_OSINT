import requests
from typing import Dict, Any, List, Optional
from core.config import get_api_key

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def query_rdap_domain(domain: str) -> Dict[str, Any]:
    """Query authoritative ICANN RDAP for domain registration & ownership metadata."""
    url = f"https://rdap.org/domain/{domain.strip().lower()}"
    info = {
        "status": "not_found",
        "domain": domain,
        "registrar": "Unknown",
        "creation_date": "N/A",
        "expiration_date": "N/A",
        "updated_date": "N/A",
        "status_codes": [],
        "nameservers": [],
        "entities": [],
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            info["status"] = "success"

            # Parse Events (Registration, Expiration)
            for event in data.get("events", []):
                action = event.get("eventAction", "")
                date_val = event.get("eventDate", "")
                if action == "registration":
                    info["creation_date"] = date_val
                elif action == "expiration":
                    info["expiration_date"] = date_val
                elif action == "last changed":
                    info["updated_date"] = date_val

            # Nameservers
            for ns in data.get("nameservers", []):
                ns_name = ns.get("ldhName") or ns.get("handle")
                if ns_name:
                    info["nameservers"].append(ns_name)

            # Status codes
            info["status_codes"] = data.get("status", [])

            # Entities & Registrar
            for entity in data.get("entities", []):
                roles = entity.get("roles", [])
                vcard = entity.get("vcardArray", [])
                name = ""
                if len(vcard) > 1:
                    for prop in vcard[1]:
                        if prop[0] == "fn":
                            name = prop[3]
                            break

                if "registrar" in roles and name:
                    info["registrar"] = name
                elif name:
                    info["entities"].append(f"{name} ({', '.join(roles)})")

    except Exception as e:
        info["error"] = str(e)[:60]

    return info


def query_rdap_ip(ip_str: str) -> Dict[str, Any]:
    """Query Regional Internet Registry (RIR) RDAP for IP allocation & network block."""
    url = f"https://rdap.org/ip/{ip_str.strip()}"
    info = {
        "status": "not_found",
        "ip": ip_str,
        "network_name": "N/A",
        "country": "N/A",
        "start_address": "",
        "end_address": "",
        "entities": [],
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            info["status"] = "success"
            info["network_name"] = data.get("name", "N/A")
            info["country"] = data.get("country", "N/A")
            info["start_address"] = data.get("startAddress", "")
            info["end_address"] = data.get("endAddress", "")

            for entity in data.get("entities", []):
                roles = entity.get("roles", [])
                handle = entity.get("handle", "")
                if handle:
                    info["entities"].append(f"{handle} ({', '.join(roles)})")
    except Exception as e:
        info["error"] = str(e)[:60]

    return info


def query_alienvault_otx(indicator_type: str, indicator: str) -> Dict[str, Any]:
    """
    Query AlienVault OTX (Open Threat Exchange) for threat intelligence pulses.
    `indicator_type`: 'domain' or 'IPv4'
    """
    otx_key = get_api_key("alienvault_otx")
    headers = HEADERS.copy()
    if otx_key:
        headers["X-OTX-API-KEY"] = otx_key

    url = f"https://otx.alienvault.com/api/v1/indicators/{indicator_type}/{indicator.strip()}/general"
    info = {
        "indicator": indicator,
        "type": indicator_type,
        "pulse_count": 0,
        "reputation": "CLEAN",
        "pulses": [],
        "malware_count": 0,
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            pulse_info = data.get("pulse_info", {})
            pulses = pulse_info.get("pulses", [])
            info["pulse_count"] = pulse_info.get("count", len(pulses))

            if info["pulse_count"] > 0:
                info["reputation"] = "SUSPICIOUS / REPORTED"
                for p in pulses[:5]:
                    info["pulses"].append({
                        "name": p.get("name", "Threat Pulse"),
                        "created": p.get("created", ""),
                        "tags": p.get("tags", [])[:5],
                        "author": p.get("author_name", "Security Researcher")
                    })
    except Exception:
        pass

    return info


def inspect_threat_intel(target: str, target_type: str = "domain") -> Dict[str, Any]:
    """Consolidated threat intelligence and registry lookup."""
    target = target.strip()
    is_ip = target_type.lower() in ("ip", "ipv4")

    if is_ip:
        rdap = query_rdap_ip(target)
        otx = query_alienvault_otx("IPv4", target)
    else:
        rdap = query_rdap_domain(target)
        otx = query_alienvault_otx("domain", target)

    return {
        "target": target,
        "type": "IP" if is_ip else "Domain",
        "rdap": rdap,
        "otx_threat": otx,
    }
