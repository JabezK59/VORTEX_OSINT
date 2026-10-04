import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.threat_intel import inspect_threat_intel
from core.ip_recon import is_valid_ip
from core.domain_recon import clean_domain
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class ThreatIntelView(ctk.CTkFrame):
    """Threat Intelligence, AlienVault OTX, and RDAP/WHOIS View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Threat Intelligence & RDAP Registry", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Query ICANN RDAP registries for domain/IP lifecycle dates, and query AlienVault OTX for threat pulses.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_target = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter IP or Domain (e.g. 1.1.1.1, github.com, suspicious-domain.com)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_target.bind("<Return>", lambda event: self.start_analysis())

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Assess Threat Intel",
            font=FONT_BODY_BOLD,
            height=38,
            width=160,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_analysis
        )
        self.btn_inspect.pack(side="left")

        # Stats Cards Row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 15))

        self.card_rep = StatCard(stats_row, title="Reputation Status", value="-", color=TEXT_SECONDARY)
        self.card_rep.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_pulses = StatCard(stats_row, title="OTX Threat Pulses", value="-", color=ACCENT_BLUE)
        self.card_pulses.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_reg = StatCard(stats_row, title="Registrar / Org", value="-", color=ACCENT_GREEN)
        self.card_reg.pack(side="left", fill="x", expand=True)

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
        target = self.entry_target.get().strip()
        if not target:
            messagebox.showwarning("Input Required", "Please enter an IP address or domain.")
            return

        is_ip = is_valid_ip(target)
        if not is_ip:
            target = clean_domain(target)

        target_type = "IP" if is_ip else "Domain"
        self.btn_inspect.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Querying ICANN RDAP and AlienVault OTX for {target_type}: '{target}'...")

        threading.Thread(target=self._run_analysis, args=(target, target_type), daemon=True).start()

    def _run_analysis(self, target: str, target_type: str):
        result = inspect_threat_intel(target, target_type)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        rdap = res.get("rdap", {})
        otx = res.get("otx_threat", {})
        is_ip = res.get("type") == "IP"

        # Update cards
        rep = otx.get("reputation", "CLEAN")
        self.card_rep.update_value(rep)
        self.card_rep.label_value.configure(text_color=ACCENT_RED if "SUSPICIOUS" in rep else ACCENT_GREEN)

        pulse_cnt = otx.get("pulse_count", 0)
        self.card_pulses.update_value(str(pulse_cnt))

        if is_ip:
            org = rdap.get("network_name", "N/A")
        else:
            org = rdap.get("registrar", "N/A")
        self.card_reg.update_value(org[:20])

        # Detailed Report
        lines = [
            "----------------------------------------------------------------------",
            f" THREAT INTELLIGENCE & RDAP REPORT: {res.get('target')}",
            "----------------------------------------------------------------------",
            f" Target           : {res.get('target')}",
            f" Target Type      : {res.get('type')}",
            f" Threat Status    : {rep}",
            f" OTX Threat Pulses: {pulse_cnt}",
            "",
            " [REGISTRATION & RDAP RECORDS]",
        ]

        if is_ip:
            lines.extend([
                f"   * Network Name : {rdap.get('network_name')}",
                f"   * Country Code : {rdap.get('country')}",
                f"   * CIDR Range   : {rdap.get('start_address')} - {rdap.get('end_address')}",
                f"   * Entities     : {', '.join(rdap.get('entities', [])) or 'N/A'}",
            ])
        else:
            lines.extend([
                f"   * Registrar    : {rdap.get('registrar')}",
                f"   * Created Date : {rdap.get('creation_date')}",
                f"   * Expiry Date  : {rdap.get('expiration_date')}",
                f"   * Last Updated : {rdap.get('updated_date')}",
                f"   * Status Codes : {', '.join(rdap.get('status_codes', [])) or 'N/A'}",
                f"   * Nameservers  : {', '.join(rdap.get('nameservers', [])) or 'N/A'}",
                f"   * Entities     : {', '.join(rdap.get('entities', [])) or 'N/A'}",
            ])

        lines.extend([
            "",
            f" [ALIENVAULT OTX SECURITY COMMUNITY PULSES ({len(otx.get('pulses', []))} shown)]",
        ])

        pulses = otx.get("pulses", [])
        if pulses:
            for p in pulses:
                lines.append(f"   * Threat: {p.get('name')}")
                lines.append(f"       Reported: {p.get('created')} by {p.get('author')}")
                lines.append(f"       Tags: {', '.join(p.get('tags', []))}")
        else:
            lines.append("   * Zero malicious threat pulses reported for this indicator in AlienVault OTX.")

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
            if export_to_txt(text, path, "THREAT INTEL & RDAP REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
