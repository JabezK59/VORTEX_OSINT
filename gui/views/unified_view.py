import re
import threading
from tkinter import messagebox
import customtkinter as ctk

from core.ip_recon import is_valid_ip, inspect_ip
from core.email_recon import validate_email_syntax, inspect_email
from core.domain_recon import clean_domain, inspect_domain
from core.web_intel import fingerprint_technologies
from core.threat_intel import inspect_threat_intel
from core.phone_recon import inspect_phone
from core.username_recon import search_username
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class UnifiedView(ctk.CTkFrame):
    """Unified Search Engine: Auto-detects target and routes to correct intelligence pipeline."""
    def __init__(self, master, switch_tab_callback=None):
        super().__init__(master, fg_color="transparent")
        self.switch_tab_callback = switch_tab_callback
        self.last_detected_type = "Username / Alias"
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Unified Multi-Target OSINT Search", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Paste any target (IP, Domain, Email, Phone, or Handle). The engine classifies and executes cross-source intelligence.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=(15, 8))

        self.entry_target = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter target (e.g. 1.1.1.1, user@gmail.com, target_user, github.com, +14155552671)...",
            font=FONT_BODY,
            height=40,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_target.bind("<KeyRelease>", self._on_target_typing)
        self.entry_target.bind("<Return>", lambda event: self.start_search())

        self.btn_search = ctk.CTkButton(
            input_row,
            text="Execute Deep Recon",
            font=FONT_BODY_BOLD,
            height=40,
            width=170,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_search
        )
        self.btn_search.pack(side="left")

        # Classification pill row
        class_row = ctk.CTkFrame(input_card, fg_color="transparent")
        class_row.pack(fill="x", padx=15, pady=(0, 12))

        self.lbl_class_title = ctk.CTkLabel(class_row, text="Target Auto-Classification: ", font=FONT_SMALL, text_color=TEXT_SECONDARY)
        self.lbl_class_title.pack(side="left")

        self.lbl_class_pill = ctk.CTkLabel(
            class_row,
            text="[ Username / Handle ]",
            font=FONT_CODE,
            text_color=ACCENT_GREEN
        )
        self.lbl_class_pill.pack(side="left")

        # Stats Cards Row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 15))

        self.card_type = StatCard(stats_row, title="Target Type", value="Auto", color=ACCENT_BLUE)
        self.card_type.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_status = StatCard(stats_row, title="Scan Status", value="Idle", color=TEXT_SECONDARY)
        self.card_status.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_hits = StatCard(stats_row, title="Intelligence Points", value="0", color=ACCENT_GREEN)
        self.card_hits.pack(side="left", fill="x", expand=True)

        # Output / Results Box
        self.log_box = ResultLogBox(self, height=360)
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def detect_target_type(self, raw_input: str) -> str:
        text = raw_input.strip()
        if not text:
            return "Empty"

        if is_valid_ip(text):
            return "IP Address"

        if validate_email_syntax(text):
            return "Email Address"

        if text.startswith("+") and len(re.sub(r"\D", "", text)) >= 7:
            return "Phone Number"

        if "." in text and not " " in text and not "@" in text:
            parts = text.split(".")
            if len(parts[-1]) >= 2 and not parts[-1].isdigit():
                return "Domain / Host"

        return "Username / Handle"

    def _on_target_typing(self, event=None):
        val = self.entry_target.get().strip()
        detected = self.detect_target_type(val)
        self.last_detected_type = detected
        self.lbl_class_pill.configure(text=f"[ {detected} ]")

    def start_search(self):
        target = self.entry_target.get().strip()
        if not target:
            messagebox.showwarning("Input Required", "Please enter a target to investigate.")
            return

        target_type = self.detect_target_type(target)
        self.card_type.update_value(target_type)
        self.card_status.update_value("Investigating...")
        self.card_status.label_value.configure(text_color=ACCENT_ORANGE)
        self.btn_search.configure(state="disabled")

        self.log_box.clear()
        self.log_box.log(f"[*] Starting Unified Deep Recon for: '{target}'")
        self.log_box.log(f"[*] Auto-Detected Target Type: {target_type}\n")

        threading.Thread(target=self._run_unified_recon, args=(target, target_type), daemon=True).start()

    def _run_unified_recon(self, target: str, target_type: str):
        hits = 0
        lines = []

        if target_type == "IP Address":
            res = inspect_ip(target, run_port_scan=True)
            threat = inspect_threat_intel(target, "ip")
            geo = res.get("geolocation", {})
            open_ports = res.get("open_ports", [])
            otx = threat.get("otx_threat", {})
            hits = len(open_ports) + (3 if geo.get("status") == "success" else 0)

            lines = [
                f"[+] Resolved IP       : {res.get('ip')}",
                f"[+] Geolocation       : {geo.get('city')}, {geo.get('country')}",
                f"[+] ISP & Org         : {geo.get('isp')} ({geo.get('asn')})",
                f"[+] Reverse DNS (PTR) : {res.get('reverse_dns')}",
                f"[+] Threat Reputation : {otx.get('reputation', 'CLEAN')} ({otx.get('pulse_count', 0)} threat pulses)",
                f"[+] Open Ports Found  : {len(open_ports)}",
            ]
            for p in open_ports:
                lines.append(f"     -> Port {p['port']} ({p['service']}) - [{p['state']}]")

        elif target_type == "Email Address":
            res = inspect_email(target)
            has_mx = res.get("has_mx", False)
            grav = res.get("gravatar", {})
            hits = (2 if has_mx else 0) + (3 if grav.get("exists") else 1)

            lines = [
                f"[+] Email Address    : {res.get('email')}",
                f"[+] Classification   : {res.get('category')}",
                f"[+] Deliverable MX   : {'YES' if has_mx else 'NO'}",
                f"[+] Disposable Inbox : {'YES' if res.get('is_disposable') else 'NO'}",
                f"[+] Gravatar Profile : {'FOUND' if grav.get('exists') else 'Not Registered'}",
            ]
            if grav.get("exists") and grav.get("display_name"):
                lines.append(f"[+] Display Name     : {grav.get('display_name')}")
            if grav.get("profile_url"):
                lines.append(f"[+] Gravatar URL     : {grav.get('profile_url')}")

        elif target_type == "Domain / Host":
            cleaned = clean_domain(target)
            res = inspect_domain(cleaned, find_subdomains=True)
            tech = fingerprint_technologies(cleaned)
            threat = inspect_threat_intel(cleaned, "domain")

            dns_recs = res.get("dns_records", {})
            subs = res.get("subdomains", [])
            ssl_info = res.get("ssl_certificate", {})
            rdap = threat.get("rdap", {})
            otx = threat.get("otx_threat", {})
            hits = len(subs) + len(dns_recs)

            lines = [
                f"[+] Target Domain    : {res.get('domain')}",
                f"[+] Registrar (RDAP) : {rdap.get('registrar', 'Unknown')}",
                f"[+] Created / Expiry : {rdap.get('creation_date', 'N/A')}  -->  {rdap.get('expiration_date', 'N/A')}",
                f"[+] Threat Status    : {otx.get('reputation', 'CLEAN')} ({otx.get('pulse_count', 0)} OTX pulses)",
                f"[+] DNS Types Found  : {', '.join(dns_recs.keys()) if dns_recs else 'None'}",
                f"[+] SSL Cert Status  : {'VALID' if ssl_info.get('valid') else 'INVALID/NONE'} ({ssl_info.get('days_remaining', 0)} days remaining)",
                f"[+] Subdomains Found : {len(subs)} discovered via CRT.sh",
                f"[+] Tech Detected    : {', '.join(tech.get('cms', []) + tech.get('frameworks', []) + tech.get('cdn', [])) or 'Standard stack'}",
            ]
            if subs:
                lines.append("    (Sample Subdomains):")
                for s in subs[:8]:
                    lines.append(f"     -> {s}")

        elif target_type == "Phone Number":
            res = inspect_phone(target)
            hits = 4 if res.get("valid") else 0

            lines = [
                f"[+] E.164 Standard   : {res.get('e164', 'Invalid')}",
                f"[+] Geographic Origin: {res.get('location', 'Unknown')}",
                f"[+] Telecom Carrier  : {res.get('carrier', 'Unknown')}",
                f"[+] Telephony Line   : {res.get('line_type', 'Unknown')}",
                f"[+] Timezone(s)      : {', '.join(res.get('timezones', []))}",
            ]

        else:  # Username / Handle
            self.log_box.log("[*] Probing 60+ social & developer platforms for alias presence...")
            res_list = search_username(target, max_workers=20)
            found = [r for r in res_list if r.get("status") == "FOUND"]
            hits = len(found)

            lines = [
                f"[+] Target Handle    : {target}",
                f"[+] Platforms Probed : {len(res_list)} services",
                f"[+] Accounts Found   : {len(found)} active profiles",
                "",
                "[FOUND PROFILES]:",
            ]
            for f in found:
                lines.append(f"   * {f.get('service'):<18} -> {f.get('profile_url')}")

        self.after(0, lambda: self._finish_unified_recon(lines, hits))

    def _finish_unified_recon(self, lines: list, hits: int):
        self.btn_search.configure(state="normal")
        self.card_status.update_value("Complete")
        self.card_status.label_value.configure(text_color=ACCENT_GREEN)
        self.card_hits.update_value(str(hits))

        for line in lines:
            self.log_box.log(line)

        self.log_box.log("\n[✓] Deep Recon complete. Use specialized tabs in the sidebar for in-depth data, scraping, or graphs.")
