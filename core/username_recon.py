import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional, Dict, Any, List

SERVICES = [
    # --- Code & Development ---
    {
        "name": "GitHub",
        "category": "Code & Dev",
        "url": "https://github.com/{}",
        "check_url": "https://api.github.com/users/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "GitLab",
        "category": "Code & Dev",
        "url": "https://gitlab.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Bitbucket",
        "category": "Code & Dev",
        "url": "https://bitbucket.org/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Docker Hub",
        "category": "Code & Dev",
        "url": "https://hub.docker.com/u/{}",
        "check_url": "https://hub.docker.com/v2/users/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "npm",
        "category": "Code & Dev",
        "url": "https://www.npmjs.com/~{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "PyPI",
        "category": "Code & Dev",
        "url": "https://pypi.org/user/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Crates.io (Rust)",
        "category": "Code & Dev",
        "url": "https://crates.io/users/{}",
        "check_url": "https://crates.io/api/v1/users/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Dev.to",
        "category": "Code & Dev",
        "url": "https://dev.to/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Hashnode",
        "category": "Code & Dev",
        "url": "https://hashnode.com/@{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Replit",
        "category": "Code & Dev",
        "url": "https://replit.com/@{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "LeetCode",
        "category": "Code & Dev",
        "url": "https://leetcode.com/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Codeforces",
        "category": "Code & Dev",
        "url": "https://codeforces.com/profile/{}",
        "check_url": "https://codeforces.com/api/user.info?handles={}",
        "check_type": "text_contains",
        "expected_text": '"status":"OK"',
    },
    {
        "name": "SourceForge",
        "category": "Code & Dev",
        "url": "https://sourceforge.net/u/{}/profile/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Kaggle",
        "category": "Data Science",
        "url": "https://www.kaggle.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "HackerNews",
        "category": "Tech News",
        "url": "https://news.ycombinator.com/user?id={}",
        "check_type": "text_not_contains",
        "error_text": "No such user.",
    },
    {
        "name": "TryHackMe",
        "category": "Cybersecurity",
        "url": "https://tryhackme.com/p/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Pastebin",
        "category": "Text & Tools",
        "url": "https://pastebin.com/u/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },

    # --- Social & Communities ---
    {
        "name": "Reddit",
        "category": "Social",
        "url": "https://www.reddit.com/user/{}",
        "check_url": "https://www.reddit.com/user/{}/about.json",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Pinterest",
        "category": "Social",
        "url": "https://www.pinterest.com/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Telegram",
        "category": "Messaging",
        "url": "https://t.me/{}",
        "check_type": "text_not_contains",
        "error_text": "If you have <strong>Telegram</strong>, you can contact",
    },
    {
        "name": "Linktree",
        "category": "Social",
        "url": "https://linktr.ee/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Substack",
        "category": "Blogging",
        "url": "https://{}.substack.com",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Medium",
        "category": "Blogging",
        "url": "https://medium.com/@{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Mastodon.social",
        "category": "Social",
        "url": "https://mastodon.social/@{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Bluesky",
        "category": "Social",
        "url": "https://bsky.app/profile/{}.bsky.social",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Disqus",
        "category": "Social",
        "url": "https://disqus.com/by/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "About.me",
        "category": "Identity",
        "url": "https://about.me/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Keybase",
        "category": "Identity",
        "url": "https://keybase.io/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Gravatar",
        "category": "Identity",
        "url": "https://gravatar.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Wikipedia",
        "category": "Reference",
        "url": "https://en.wikipedia.org/wiki/User:{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },

    # --- Media, Audio & Video ---
    {
        "name": "YouTube",
        "category": "Media",
        "url": "https://www.youtube.com/@{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Vimeo",
        "category": "Media",
        "url": "https://vimeo.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "DailyMotion",
        "category": "Media",
        "url": "https://www.dailymotion.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "SoundCloud",
        "category": "Audio",
        "url": "https://soundcloud.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Spotify",
        "category": "Audio",
        "url": "https://open.spotify.com/user/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Bandcamp",
        "category": "Audio",
        "url": "https://bandcamp.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Mixcloud",
        "category": "Audio",
        "url": "https://www.mixcloud.com/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Last.fm",
        "category": "Audio",
        "url": "https://www.last.fm/user/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },

    # --- Design, Art & Photography ---
    {
        "name": "Behance",
        "category": "Design",
        "url": "https://www.behance.net/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Dribbble",
        "category": "Design",
        "url": "https://dribbble.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "ArtStation",
        "category": "Design",
        "url": "https://www.artstation.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Flickr",
        "category": "Photography",
        "url": "https://www.flickr.com/people/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "500px",
        "category": "Photography",
        "url": "https://500px.com/p/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "DeviantArt",
        "category": "Design",
        "url": "https://www.deviantart.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },

    # --- Gaming & Esports ---
    {
        "name": "Steam",
        "category": "Gaming",
        "url": "https://steamcommunity.com/id/{}",
        "check_type": "text_not_contains",
        "error_text": "The specified profile could not be found",
    },
    {
        "name": "Twitch",
        "category": "Gaming",
        "url": "https://www.twitch.tv/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Chess.com",
        "category": "Gaming",
        "url": "https://www.chess.com/member/{}",
        "check_url": "https://api.chess.com/pub/player/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Lichess",
        "category": "Gaming",
        "url": "https://lichess.org/@/{}",
        "check_url": "https://lichess.org/api/user/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Speedrun.com",
        "category": "Gaming",
        "url": "https://www.speedrun.com/users/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },

    # --- Finance, Creator & Commerce ---
    {
        "name": "TradingView",
        "category": "Finance",
        "url": "https://www.tradingview.com/u/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "ProductHunt",
        "category": "Tech & Startups",
        "url": "https://www.producthunt.com/@{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Patreon",
        "category": "Creator",
        "url": "https://www.patreon.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Buy Me a Coffee",
        "category": "Creator",
        "url": "https://www.buymeacoffee.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Ko-fi",
        "category": "Creator",
        "url": "https://ko-fi.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Goodreads",
        "category": "Books",
        "url": "https://www.goodreads.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Instructables",
        "category": "DIY",
        "url": "https://www.instructables.com/member/{}/",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "Tumblr",
        "category": "Blogging",
        "url": "https://{}.tumblr.com",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
    {
        "name": "VK (Vkontakte)",
        "category": "Social",
        "url": "https://vk.com/{}",
        "check_type": "status_code",
        "found_codes": [200],
        "not_found_codes": [404],
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def check_single_service(service: Dict[str, Any], username: str, timeout: int = 8) -> Dict[str, Any]:
    """Probe if username exists on a specific service."""
    profile_url = service["url"].format(username)
    target_url = service.get("check_url", service["url"]).format(username)
    check_type = service.get("check_type", "status_code")

    start_time = time.time()
    result = {
        "service": service["name"],
        "category": service["category"],
        "profile_url": profile_url,
        "status": "UNKNOWN",
        "response_time_ms": 0,
        "details": "",
    }

    try:
        session = requests.Session()
        resp = session.get(target_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        elapsed = int((time.time() - start_time) * 1000)
        result["response_time_ms"] = elapsed

        if check_type == "status_code":
            found_codes = service.get("found_codes", [200])
            not_found_codes = service.get("not_found_codes", [404])
            if resp.status_code in found_codes:
                result["status"] = "FOUND"
                result["details"] = f"HTTP {resp.status_code} OK"
            elif resp.status_code in not_found_codes:
                result["status"] = "NOT_FOUND"
                result["details"] = f"HTTP {resp.status_code} Not Found"
            else:
                result["status"] = "UNCERTAIN"
                result["details"] = f"HTTP {resp.status_code}"

        elif check_type == "text_not_contains":
            error_text = service.get("error_text", "")
            if error_text and error_text in resp.text:
                result["status"] = "NOT_FOUND"
                result["details"] = "Error indicator found in response"
            elif resp.status_code == 200:
                result["status"] = "FOUND"
                result["details"] = "Profile page exists"
            else:
                result["status"] = "NOT_FOUND"
                result["details"] = f"HTTP {resp.status_code}"

        elif check_type == "text_contains":
            expected_text = service.get("expected_text", "")
            if expected_text and expected_text in resp.text:
                result["status"] = "FOUND"
                result["details"] = "Positive signature verified"
            else:
                result["status"] = "NOT_FOUND"
                result["details"] = "Signature missing"

    except requests.exceptions.Timeout:
        result["status"] = "TIMEOUT"
        result["details"] = "Connection timed out"
    except requests.exceptions.RequestException as e:
        result["status"] = "ERROR"
        result["details"] = str(e)[:60]
    except Exception as e:
        result["status"] = "ERROR"
        result["details"] = str(e)[:60]

    return result


def search_username(
    username: str,
    max_workers: int = 20,
    callback: Optional[Callable[[Dict[str, Any], int, int], None]] = None,
    stop_event = None
) -> List[Dict[str, Any]]:
    """
    Search for username across all configured services with concurrent threads.
    `callback(result, completed_count, total_count)` is invoked on each finished check.
    """
    results = []
    total = len(SERVICES)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_single_service, srv, username): srv for srv in SERVICES}

        for future in as_completed(futures):
            if stop_event and stop_event.is_set():
                break

            res = future.result()
            results.append(res)
            completed += 1

            if callback:
                try:
                    callback(res, completed, total)
                except Exception:
                    pass

    return results
