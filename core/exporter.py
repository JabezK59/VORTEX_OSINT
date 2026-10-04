import json
import csv
import datetime
from typing import Dict, Any, List


def export_to_json(data: Any, filepath: str) -> bool:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def export_to_txt(content: str, filepath: str, header_title: str = "OSINT INVESTIGATION REPORT") -> bool:
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"  {header_title.upper()}\n")
            f.write(f"  Generated on: {now}\n")
            f.write("=" * 70 + "\n\n")
            f.write(content)
            f.write("\n\n" + "=" * 70 + "\n")
            f.write("  [END OF REPORT - VORTEX OSINT SUITE]\n")
            f.write("=" * 70 + "\n")
        return True
    except Exception:
        return False


def export_username_results_to_csv(results: List[Dict[str, Any]], filepath: str) -> bool:
    try:
        fieldnames = ["service", "category", "status", "profile_url", "response_time_ms", "details"]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "service": r.get("service", ""),
                    "category": r.get("category", ""),
                    "status": r.get("status", ""),
                    "profile_url": r.get("profile_url", ""),
                    "response_time_ms": r.get("response_time_ms", 0),
                    "details": r.get("details", ""),
                })
        return True
    except Exception:
        return False
