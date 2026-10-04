import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def query_wayback_urls(domain: str, limit: int = 50) -> List[Dict[str, str]]:
    """Query Internet Archive Wayback Machine CDX API for historical URLs."""
    clean_dom = domain.strip().lower()
    url = f"http://web.archive.org/cdx/search/cdx?url=*.{clean_dom}/*&output=json&collapse=urlkey&limit={limit}&fl=original,timestamp,statuscode,mimetype"
    records = []

    try:
        resp = requests.get(url, timeout=12, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                # First row is header: ['original', 'timestamp', 'statuscode', 'mimetype']
                for row in data[1:]:
                    if len(row) >= 4:
                        records.append({
                            "url": row[0],
                            "timestamp": row[1],
                            "status": row[2],
                            "mimetype": row[3],
                            "archive_view": f"https://web.archive.org/web/{row[1]}/{row[0]}"
                        })
    except Exception:
        pass

    return records


def fetch_robots_txt(domain: str) -> Dict[str, Any]:
    """Extract disallowed paths and sitemaps from robots.txt."""
    url = f"https://{domain}/robots.txt"
    info = {
        "exists": False,
        "disallowed": [],
        "sitemaps": [],
        "raw_text": "",
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if resp.status_code == 200 and "user-agent" in resp.text.lower():
            info["exists"] = True
            info["raw_text"] = resp.text[:4000]

            for line in resp.text.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path and path not in info["disallowed"]:
                        info["disallowed"].append(path)
                elif line.lower().startswith("sitemap:"):
                    smap = line.split(":", 1)[1].strip()
                    if smap and smap not in info["sitemaps"]:
                        info["sitemaps"].append(smap)
    except Exception:
        pass

    return info


def fetch_security_txt(domain: str) -> Dict[str, Any]:
    """Check for standard RFC 9116 security.txt vulnerability disclosure file."""
    urls = [
        f"https://{domain}/.well-known/security.txt",
        f"https://{domain}/security.txt"
    ]
    info = {"exists": False, "contacts": [], "policy": "", "raw": ""}

    for u in urls:
        try:
            resp = requests.get(u, headers=HEADERS, timeout=5)
            if resp.status_code == 200 and "contact:" in resp.text.lower():
                info["exists"] = True
                info["raw"] = resp.text[:2000]
                for line in resp.text.splitlines():
                    if line.lower().startswith("contact:"):
                        info["contacts"].append(line.split(":", 1)[1].strip())
                    elif line.lower().startswith("policy:"):
                        info["policy"] = line.split(":", 1)[1].strip()
                break
        except Exception:
            continue

    return info


def fingerprint_technologies(domain: str) -> Dict[str, Any]:
    """Passive web stack analysis from HTTP headers and HTML markup."""
    url = f"https://{domain}"
    findings = {
        "cms": [],
        "frameworks": [],
        "web_servers": [],
        "cdn": [],
        "analytics": [],
        "title": "",
        "meta_generator": "",
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        headers = {k.lower(): v.lower() for k, v in resp.headers.items()}
        html = resp.text.lower()
        soup = BeautifulSoup(resp.text, "html.parser")

        if soup.title and soup.title.string:
            findings["title"] = soup.title.string.strip()

        meta_gen = soup.find("meta", attrs={"name": re.compile(r"generator", re.I)})
        if meta_gen and meta_gen.get("content"):
            findings["meta_generator"] = meta_gen["content"]

        # 1. CDN & Reverse Proxies
        if "cf-ray" in headers or "cloudflare" in headers.get("server", ""):
            findings["cdn"].append("Cloudflare")
        if "x-amz-cf-id" in headers or "cloudfront" in headers.get("via", ""):
            findings["cdn"].append("Amazon CloudFront")
        if "fastly" in headers.get("server", "") or "x-fastly-request-id" in headers:
            findings["cdn"].append("Fastly")
        if "x-vercel-id" in headers or "vercel" in headers.get("server", ""):
            findings["cdn"].append("Vercel")
        if "x-nf-request-id" in headers or "netlify" in headers.get("server", ""):
            findings["cdn"].append("Netlify")

        # 2. Web Servers
        server = headers.get("server", "")
        if "nginx" in server:
            findings["web_servers"].append("Nginx")
        if "apache" in server:
            findings["web_servers"].append("Apache HTTP Server")
        if "caddy" in server:
            findings["web_servers"].append("Caddy")
        if "litespeed" in server:
            findings["web_servers"].append("LiteSpeed")

        # 3. CMS Platforms
        if "wp-content" in html or "wp-includes" in html or "wordpress" in findings["meta_generator"].lower():
            findings["cms"].append("WordPress")
        if "shopify" in html or "myshopify.com" in html:
            findings["cms"].append("Shopify")
        if "ghost" in findings["meta_generator"].lower():
            findings["cms"].append("Ghost CMS")
        if "wix.com" in html:
            findings["cms"].append("Wix")
        if "squarespace" in html:
            findings["cms"].append("Squarespace")
        if "drupal" in findings["meta_generator"].lower():
            findings["cms"].append("Drupal")

        # 4. Frontend & JS Frameworks
        if "__next" in html or "__next_data__" in html:
            findings["frameworks"].append("Next.js / React")
        elif "react" in html or "data-reactroot" in html:
            findings["frameworks"].append("React")
        if "vue" in html or "data-v-" in html:
            findings["frameworks"].append("Vue.js")
        if "ng-" in html or "angular" in html:
            findings["frameworks"].append("Angular")
        if "tailwind" in html:
            findings["frameworks"].append("Tailwind CSS")
        if "bootstrap" in html:
            findings["frameworks"].append("Bootstrap")

        # 5. Analytics & Tag Managers
        if "googletagmanager.com" in html:
            findings["analytics"].append("Google Tag Manager")
        if "google-analytics.com" in html or "gtag(" in html:
            findings["analytics"].append("Google Analytics")
        if "hotjar.com" in html:
            findings["analytics"].append("Hotjar")
        if "segment.com" in html or "analytics.js" in html:
            findings["analytics"].append("Segment")

    except Exception:
        pass

    return findings


def inspect_web_intel(domain: str) -> Dict[str, Any]:
    """Execute complete web technology & archive reconnaissance."""
    dom = domain.strip().lower().split("/")[0].split(":")[0]
    
    wayback_urls = query_wayback_urls(dom, limit=40)
    robots = fetch_robots_txt(dom)
    sec_txt = fetch_security_txt(dom)
    tech = fingerprint_technologies(dom)

    return {
        "domain": dom,
        "tech_fingerprint": tech,
        "robots_txt": robots,
        "security_txt": sec_txt,
        "wayback_urls": wayback_urls,
    }
