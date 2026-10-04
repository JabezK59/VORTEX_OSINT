import socket
import ipaddress
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

COMMON_PORTS = [
    (21, "FTP"),
    (22, "SSH"),
    (23, "Telnet"),
    (25, "SMTP"),
    (53, "DNS"),
    (80, "HTTP"),
    (110, "POP3"),
    (143, "IMAP"),
    (443, "HTTPS"),
    (445, "SMB"),
    (1433, "MSSQL"),
    (3306, "MySQL"),
    (3389, "RDP"),
    (5432, "PostgreSQL"),
    (6379, "Redis"),
    (8080, "HTTP-Proxy"),
    (8443, "HTTPS-Alt"),
    (9200, "Elasticsearch"),
    (27017, "MongoDB"),
]


def is_valid_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except ValueError:
        return False


def is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return ip.is_private or ip.is_loopback or ip.is_reserved
    except ValueError:
        return False


def get_ip_geolocation(ip_str: str) -> Dict[str, Any]:
    """Fetch rich geolocation & ASN info for an IP."""
    target_ip = ip_str.strip()

    if is_private_ip(target_ip):
        return {
            "status": "success",
            "ip": target_ip,
            "country": "Local / Private Network",
            "country_code": "LOC",
            "region": "Private",
            "city": "Internal / Loopback",
            "lat": 0.0,
            "lon": 0.0,
            "isp": "Local Network (RFC1918 / Loopback)",
            "org": "Internal",
            "asn": "N/A",
            "timezone": "Local",
        }

    try:
        url = f"http://ip-api.com/json/{target_ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "status": "success",
                    "ip": data.get("query", target_ip),
                    "country": data.get("country", "Unknown"),
                    "country_code": data.get("countryCode", "??"),
                    "region": data.get("regionName", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "zip": data.get("zip", ""),
                    "lat": data.get("lat", 0.0),
                    "lon": data.get("lon", 0.0),
                    "isp": data.get("isp", "Unknown"),
                    "org": data.get("org", "Unknown"),
                    "asn": data.get("as", "Unknown"),
                    "timezone": data.get("timezone", "Unknown"),
                }
    except Exception:
        pass

    # Fallback to ipinfo.io
    try:
        url = f"https://ipinfo.io/{target_ip}/json"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            loc = data.get("loc", "0,0").split(",")
            lat = float(loc[0]) if len(loc) > 0 else 0.0
            lon = float(loc[1]) if len(loc) > 1 else 0.0
            return {
                "status": "success",
                "ip": data.get("ip", target_ip),
                "country": data.get("country", "Unknown"),
                "country_code": data.get("country", "??"),
                "region": data.get("region", "Unknown"),
                "city": data.get("city", "Unknown"),
                "zip": data.get("postal", ""),
                "lat": lat,
                "lon": lon,
                "isp": data.get("org", "Unknown"),
                "org": data.get("org", "Unknown"),
                "asn": data.get("org", "Unknown"),
                "timezone": data.get("timezone", "Unknown"),
            }
    except Exception:
        pass

    return {
        "status": "error",
        "ip": target_ip,
        "error": "Failed to fetch geolocation data",
    }


def get_reverse_dns(ip_str: str) -> str:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_str.strip())
        return hostname
    except Exception:
        return "No PTR record found"


def probe_port(ip: str, port: int, service: str, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        if result == 0:
            # Port is open, try banner grab
            banner = ""
            try:
                sock.send(b"\r\n")
                data = sock.recv(1024)
                banner = data.decode(errors="ignore").strip()[:80]
            except Exception:
                pass
            return {
                "port": port,
                "service": service,
                "state": "OPEN",
                "banner": banner,
            }
    except Exception:
        pass
    finally:
        sock.close()
    return None


def scan_ports(ip_str: str, ports: Optional[List[Tuple[int, str]]] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    if ports is None:
        ports = COMMON_PORTS

    open_ports = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(probe_port, ip_str, p, s): (p, s) for p, s in ports}
        for future in as_completed(futures):
            res = future.result()
            if res:
                open_ports.append(res)

    open_ports.sort(key=lambda x: x["port"])
    return open_ports


def inspect_ip(ip_str: str, run_port_scan: bool = True) -> Dict[str, Any]:
    clean_ip = ip_str.strip()

    # If domain passed instead of IP, resolve it
    resolved_from_domain = None
    if not is_valid_ip(clean_ip):
        try:
            resolved_ip = socket.gethostbyname(clean_ip)
            resolved_from_domain = clean_ip
            clean_ip = resolved_ip
        except Exception:
            return {
                "input": ip_str,
                "valid": False,
                "error": f"Could not resolve host '{ip_str}' to a valid IP address",
            }

    geo = get_ip_geolocation(clean_ip)
    ptr = get_reverse_dns(clean_ip)

    open_ports = []
    if run_port_scan and not is_private_ip(clean_ip):
        open_ports = scan_ports(clean_ip)

    return {
        "input": ip_str,
        "ip": clean_ip,
        "resolved_from": resolved_from_domain,
        "valid": True,
        "reverse_dns": ptr,
        "geolocation": geo,
        "open_ports": open_ports,
    }
