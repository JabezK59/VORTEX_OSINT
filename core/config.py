import os
import json
from typing import Dict, Any

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")

DEFAULT_CONFIG = {
    "api_keys": {
        "shodan": "",
        "virustotal": "",
        "abuseipdb": "",
        "github": "",
        "alienvault_otx": ""
    },
    "settings": {
        "max_threads": 20,
        "request_timeout": 8,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
}


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if sub_k not in data[k]:
                            data[k][sub_k] = sub_v
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception:
        return False


def get_api_key(service: str) -> str:
    cfg = load_config()
    return cfg.get("api_keys", {}).get(service, "").strip()


def set_api_key(service: str, key_val: str) -> bool:
    cfg = load_config()
    if "api_keys" not in cfg:
        cfg["api_keys"] = {}
    cfg["api_keys"][service] = key_val.strip()
    return save_config(cfg)
