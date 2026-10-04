import threading
import json
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.domain_recon import inspect_domain, clean_domain
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class DomainView(ctk.CTkFrame):
    """Domain, DNS, Subdomains, and SSL Intelligence View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Domain & DNS Reconnaissance", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Extract authoritative DNS records, query Certificate Transparency for subdomains, and assess SSL/headers.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_domain = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter target domain (e.g. github.com, cloudflare.com)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_domain.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_domain.bind("<Return>", lambda event: self.start_analysis())

        self.chk_subdomains = ctk.CTkCheckBox(
            input_row,
            text="CRT.sh Subdomains",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY
        )
        self.chk_subdomains.select()
        self.chk_subdomains.pack(side="left", padx=(0, 10))

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Analyze Domain",
            font=FONT_BODY_BOLD,
            height=38,
            width=140,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_analysis
        )
        self.btn_inspect.pack(side="left")

        # Stats Cards Row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 15))

        self.card_dns = StatCard(stats_row, title="DNS Types Found", value="-", color=ACCENT_BLUE)
        self.card_dns.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_subs = StatCard(stats_row, title="Subdomains Found", value="-", color=ACCENT_GREEN)
        self.card_subs.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_ssl = StatCard(stats_row, title="SSL Days Left", value="-", color=ACCENT_ORANGE)
        self.card_ssl.pack(side="left", fill="x", expand=True)

        # Output / Results Box
        self.log_box = ResultLogBox(self, height=350)
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Bottom Actions
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_export_json = ctk.CTkButton(
            actions_bar,
            text="Export JSON",
            font=FONT_SMALL,
            width=100,
            height=30,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            command=self.export_json
        )
        self.btn_export_json.pack(side="right", padx=(8, 0))

        self.btn_export_txt = ctk.CTkButton(
            actions_bar,
            text="Export Report",
            font=FONT_SMALL,
            width=110,
            height=30,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            command=self.export_txt
        )
        self.btn_export_txt.pack(side="right")

    def start_analysis(self):
        raw_dom = self.entry_domain.get().strip()
        if not raw_dom:
            messagebox.showwarning("Input Required", "Please enter a domain name.")
            return

        domain = clean_domain(raw_dom)
        check_subs = self.chk_subdomains.get() == 1

        self.btn_inspect.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Starting Domain & DNS Reconnaissance for '{domain}'...")
        if check_subs:
            self.log_box.log("    (Fetching Certificate Transparency logs from crt.sh...)")

        threading.Thread(target=self._run_analysis, args=(domain, check_subs), daemon=True).start()

    def _run_analysis(self, domain: str, check_subs: bool):
        result = inspect_domain(domain, find_subdomains=check_subs)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        dns_records = res.get("dns_records", {})
        subdomains = res.get("subdomains", [])
        ssl_info = res.get("ssl_certificate", {})
        http_info = res.get("http_headers", {})

        # Stat cards
        dns_count = len(dns_records)
        self.card_dns.update_value(str(dns_count))

        sub_count = len(subdomains)
        self.card_subs.update_value(str(sub_count))

        days_remaining = ssl_info.get("days_remaining", 0)
        if ssl_info.get("valid"):
            self.card_ssl.update_value(f"{days_remaining} d")
            self.card_ssl.label_value.configure(text_color=ACCENT_GREEN if days_remaining > 30 else ACCENT_RED)
        else:
            self.card_ssl.update_value("No Cert / Err")
            self.card_ssl.label_value.configure(text_color=TEXT_MUTED)

        # Build comprehensive report
        lines = [
            "----------------------------------------------------------------------",
            f" DOMAIN & DNS RECON REPORT: {res.get('domain')}",
            "----------------------------------------------------------------------",
            f" Target Domain   : {res.get('domain')}",
            f" Web Server      : {http_info.get('server', 'Unknown')}",
            f" Technology      : {http_info.get('powered_by', 'None disclosed')}",
            f" HTTP Status     : {http_info.get('status_code', 'N/A')}",
            "",
            " [SECURITY HEADERS POSTURE]",
        ]

        sec_headers = http_info.get("security_headers", {})
        for header, val in sec_headers.items():
            status_str = "MISSING" if val == "MISSING" else "PRESENT"
            lines.append(f"   * {header:<32}: [{status_str}] {val if val != 'MISSING' else ''}")

        lines.extend([
            "",
            " [DNS RECORDS]",
        ])
        if dns_records:
            for rtype, records in dns_records.items():
                lines.append(f"   * {rtype}:")
                for r in records:
                    lines.append(f"       -> {r}")
        else:
            lines.append("   * No DNS records resolved.")

        lines.extend([
            "",
            " [SSL / TLS CERTIFICATE]",
            f"   * Valid Cert     : {ssl_info.get('valid', False)}",
            f"   * Valid From     : {ssl_info.get('valid_from', 'N/A')}",
            f"   * Valid Until    : {ssl_info.get('valid_until', 'N/A')} ({days_remaining} days left)",
        ])

        issuer = ssl_info.get("issuer", {})
        if issuer:
            lines.append(f"   * Issuer Org     : {issuer.get('organizationName', 'N/A')}")
            lines.append(f"   * Issuer CN      : {issuer.get('commonName', 'N/A')}")

        sans = ssl_info.get("san", [])
        if sans:
            lines.append(f"   * SANs (Top 10)  : {', '.join(sans[:10])}")

        lines.extend([
            "",
            f" [DISCOVERED SUBDOMAINS (Total: {len(subdomains)})]",
        ])
        if subdomains:
            for sub in subdomains:
                lines.append(f"   * {sub}")
        else:
            lines.append("   * No subdomains found or CRT.sh query was disabled.")

        lines.append("----------------------------------------------------------------------")

        self.log_box.clear()
        self.log_box.log("\n".join(lines))

    def export_json(self):
        if not self.last_result:
            messagebox.showinfo("Export", "No intelligence data to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if path:
            if export_to_json(self.last_result, path):
                messagebox.showinfo("Export Success", f"Saved to {path}")

    def export_txt(self):
        text = self.log_box.get_text()
        if not text:
            messagebox.showinfo("Export", "No report text to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if path:
            if export_to_txt(text, path, "DOMAIN & DNS RECON REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
