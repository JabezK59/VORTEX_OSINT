import threading
import json
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.ip_recon import inspect_ip
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class IPView(ctk.CTkFrame):
    """IP Intelligence, Geolocation, and Port Reconnaissance View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="IP & Geolocation Intelligence", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Locate physical infrastructure, identify ISPs/ASNs, resolve PTR records, and scan common network services.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_ip = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter IP address or host (e.g. 1.1.1.1, 8.8.8.8, scanme.nmap.org)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_ip.bind("<Return>", lambda event: self.start_analysis())

        self.chk_portscan = ctk.CTkCheckBox(
            input_row,
            text="Port Scan (Top 19 Ports)",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY
        )
        self.chk_portscan.select()
        self.chk_portscan.pack(side="left", padx=(0, 10))

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Analyze IP",
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

        self.card_location = StatCard(stats_row, title="Location", value="-", color=ACCENT_GREEN)
        self.card_location.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_isp = StatCard(stats_row, title="ISP / ASN", value="-", color=ACCENT_BLUE)
        self.card_isp.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_ports = StatCard(stats_row, title="Open Ports Detected", value="-", color=ACCENT_ORANGE)
        self.card_ports.pack(side="left", fill="x", expand=True)

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
        ip_input = self.entry_ip.get().strip()
        if not ip_input:
            messagebox.showwarning("Input Required", "Please enter an IP address or hostname.")
            return

        run_scan = self.chk_portscan.get() == 1

        self.btn_inspect.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Starting IP reconnaissance for '{ip_input}'...")
        if run_scan:
            self.log_box.log("    (Running multi-threaded port scan on top services...)")

        threading.Thread(target=self._run_analysis, args=(ip_input, run_scan), daemon=True).start()

    def _run_analysis(self, ip_input: str, run_scan: bool):
        result = inspect_ip(ip_input, run_port_scan=run_scan)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        if not res.get("valid"):
            self.card_location.update_value("INVALID")
            self.card_isp.update_value("INVALID")
            self.card_ports.update_value("0")
            self.log_box.log(f"[!] ERROR: {res.get('error')}")
            return

        geo = res.get("geolocation", {})
        open_ports = res.get("open_ports", [])

        # Update stat cards
        city = geo.get("city", "Unknown")
        country = geo.get("country", "Unknown")
        self.card_location.update_value(f"{city}, {country[:10]}")

        isp = geo.get("isp", "Unknown")
        self.card_isp.update_value(isp[:18] + ("..." if len(isp) > 18 else ""))

        self.card_ports.update_value(str(len(open_ports)))
        self.card_ports.label_value.configure(text_color=ACCENT_ORANGE if open_ports else ACCENT_GREEN)

        # Build detailed report
        lines = [
            "----------------------------------------------------------------------",
            f" IP & GEOLOCATION INTELLIGENCE REPORT: {res.get('ip')}",
            "----------------------------------------------------------------------",
            f" Target Input      : {res.get('input')}",
            f" Resolved IP       : {res.get('ip')}",
            f" Reverse DNS (PTR) : {res.get('reverse_dns')}",
            "",
            " [GEOGRAPHICAL LOCATION]",
            f"   * Country        : {geo.get('country')} ({geo.get('country_code')})",
            f"   * Region / State : {geo.get('region')}",
            f"   * City           : {geo.get('city')}",
            f"   * Postal Code    : {geo.get('zip') or 'N/A'}",
            f"   * Coordinates    : {geo.get('lat')}, {geo.get('lon')}",
            f"   * Maps Link      : https://www.google.com/maps?q={geo.get('lat')},{geo.get('lon')}",
            f"   * Timezone       : {geo.get('timezone')}",
            "",
            " [NETWORK & ROUTING]",
            f"   * ISP            : {geo.get('isp')}",
            f"   * Organization   : {geo.get('org')}",
            f"   * ASN            : {geo.get('asn')}",
            "",
            f" [OPEN NETWORK PORTS ({len(open_ports)} detected)]",
        ]

        if open_ports:
            for p in open_ports:
                banner_str = f" | Banner: {p.get('banner')}" if p.get("banner") else ""
                lines.append(f"   * Port {p['port']:<5} -> {p['service']:<14} [{p['state']}]{banner_str}")
        else:
            lines.append("   * No common open ports detected (or scan was skipped / filtered by firewall).")

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
            if export_to_txt(text, path, "IP INTELLIGENCE REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
