import socket
import ssl
import datetime
import requests
import dns.resolver
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse


def clean_domain(domain_str: str) -> str:
    domain_str = domain_str.strip()
    if domain_str.startswith("http://") or domain_str.startswith("https://"):
        parsed = urlparse(domain_str)
        return parsed.netloc.split(":")[0]
    return domain_str.split("/")[0].split(":")[0]


def get_dns_records(domain: str) -> Dict[str, List[str]]:
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]
    results = {}

    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(domain, rtype, lifetime=4)
            entries = []
            for rdata in answers:
                if rtype == "MX":
                    entries.append(f"{rdata.preference} {str(rdata.exchange).rstrip('.')}")
                elif rtype == "TXT":
                    entries.append(b"".join(rdata.strings).decode(errors="ignore"))
                else:
                    entries.append(str(rdata).rstrip("."))
            if entries:
                results[rtype] = entries
        except Exception:
            pass

    # Check for DMARC record specifically
    try:
        dmarc_answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT", lifetime=4)
        dmarc_entries = [b"".join(rdata.strings).decode(errors="ignore") for rdata in dmarc_answers]
        if dmarc_entries:
            results["DMARC"] = dmarc_entries
    except Exception:
        pass

    return results


def find_subdomains_crtsh(domain: str, max_subdomains: int = 100) -> List[str]:
    """Find discovered subdomains using crt.sh Certificate Transparency logs."""
    subdomains: Set[str] = set()
    url = f"https://crt.sh/?q=%.{domain}&output=json"

    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            for entry in data:
                name_value = entry.get("name_value", "")
                for sub in name_value.split("\n"):
                    sub = sub.strip().lower()
                    if "*" in sub:
                        sub = sub.replace("*.", "")
                    if sub.endswith(f".{domain}") or sub == domain:
                        subdomains.add(sub)
                        if len(subdomains) >= max_subdomains:
                            break
                if len(subdomains) >= max_subdomains:
                    break
    except Exception:
        pass

    sorted_subs = sorted(list(subdomains))
    return sorted_subs


def inspect_http_headers(domain: str) -> Dict[str, Any]:
    """Analyze server banners and essential security headers."""
    target_url = f"https://{domain}"
    info = {
        "status_code": None,
        "server": "Not disclosed",
        "powered_by": "Not disclosed",
        "redirect_url": None,
        "security_headers": {
            "Strict-Transport-Security (HSTS)": False,
            "Content-Security-Policy (CSP)": False,
            "X-Frame-Options": False,
            "X-Content-Type-Options": False,
            "Referrer-Policy": False,
        },
        "all_headers": {},
    }

    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        resp = session.get(target_url, timeout=7, allow_redirects=True)
        info["status_code"] = resp.status_code
        info["redirect_url"] = resp.url if resp.url != target_url else None

        for k, v in resp.headers.items():
            info["all_headers"][k] = v

        k_lower = {k.lower(): v for k, v in resp.headers.items()}
        if "server" in k_lower:
            info["server"] = k_lower["server"]
        if "x-powered-by" in k_lower:
            info["powered_by"] = k_lower["x-powered-by"]

        sec_map = {
            "Strict-Transport-Security (HSTS)": "strict-transport-security",
            "Content-Security-Policy (CSP)": "content-security-policy",
            "X-Frame-Options": "x-frame-options",
            "X-Content-Type-Options": "x-content-type-options",
            "Referrer-Policy": "referrer-policy",
        }

        for title, hkey in sec_map.items():
            if hkey in k_lower:
                info["security_headers"][title] = k_lower[hkey]
            else:
                info["security_headers"][title] = "MISSING"

    except Exception as e:
        info["error"] = str(e)[:80]

    return info


def inspect_ssl_cert(domain: str, port: int = 443) -> Dict[str, Any]:
    """Inspect SSL/TLS certificate details."""
    context = ssl.create_default_context()
    info = {
        "valid": False,
        "issuer": {},
        "subject": {},
        "valid_from": "",
        "valid_until": "",
        "days_remaining": 0,
        "san": [],
    }

    try:
        with socket.create_connection((domain, port), timeout=6) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                info["valid"] = True

                # Extract Issuer
                for item in cert.get("issuer", ()):
                    for key, val in item:
                        info["issuer"][key] = val

                # Extract Subject
                for item in cert.get("subject", ()):
                    for key, val in item:
                        info["subject"][key] = val

                # Validity dates
                not_before = cert.get("notBefore", "")
                not_after = cert.get("notAfter", "")
                info["valid_from"] = not_before
                info["valid_until"] = not_after

                try:
                    fmt = "%b %d %H:%M:%S %Y %Z"
                    expiry = datetime.datetime.strptime(not_after, fmt)
                    remaining = (expiry - datetime.datetime.utcnow()).days
                    info["days_remaining"] = remaining
                except Exception:
                    pass

                # SANs
                sans = [entry[1] for entry in cert.get("subjectAltName", ()) if entry[0] == "DNS"]
                info["san"] = sans[:20]

    except Exception as e:
        info["error"] = str(e)[:80]

    return info


def inspect_domain(domain_str: str, find_subdomains: bool = True) -> Dict[str, Any]:
    domain = clean_domain(domain_str)

    dns_records = get_dns_records(domain)
    ssl_info = inspect_ssl_cert(domain)
    http_info = inspect_http_headers(domain)

    subdomains = []
    if find_subdomains:
        subdomains = find_subdomains_crtsh(domain)

    return {
        "domain": domain,
        "dns_records": dns_records,
        "ssl_certificate": ssl_info,
        "http_headers": http_info,
        "subdomains": subdomains,
    }
