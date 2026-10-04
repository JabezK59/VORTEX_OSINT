import threading
import json
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.phone_recon import inspect_phone
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class PhoneView(ctk.CTkFrame):
    """Phone Number Intelligence & Telephony OSINT View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Phone Number Intelligence", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Validate international phone numbers, identify telecommunication carrier, line type, and geographic origin.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_phone = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter phone number with country code (e.g. +14155552671, +447911123456)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_phone.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_phone.bind("<Return>", lambda event: self.start_analysis())

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Analyze Number",
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

        self.card_valid = StatCard(stats_row, title="Validity Status", value="-", color=TEXT_SECONDARY)
        self.card_valid.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_carrier = StatCard(stats_row, title="Telecom Carrier", value="-", color=ACCENT_BLUE)
        self.card_carrier.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_type = StatCard(stats_row, title="Line Type", value="-", color=ACCENT_ORANGE)
        self.card_type.pack(side="left", fill="x", expand=True)

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
        number_str = self.entry_phone.get().strip()
        if not number_str:
            messagebox.showwarning("Input Required", "Please enter a phone number.")
            return

        self.btn_inspect.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Analyzing phone number: '{number_str}'...")

        threading.Thread(target=self._run_analysis, args=(number_str,), daemon=True).start()

    def _run_analysis(self, number_str: str):
        result = inspect_phone(number_str)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        if not res.get("valid"):
            self.card_valid.update_value("INVALID")
            self.card_valid.label_value.configure(text_color=ACCENT_RED)
            self.card_carrier.update_value("N/A")
            self.card_type.update_value("N/A")
            self.log_box.log(f"[!] ERROR: {res.get('error', 'Invalid number format')}")
            return

        self.card_valid.update_value("VALID")
        self.card_valid.label_value.configure(text_color=ACCENT_GREEN)

        carrier_name = res.get("carrier", "Unknown")
        self.card_carrier.update_value(carrier_name[:18] + ("..." if len(carrier_name) > 18 else ""))

        self.card_type.update_value(res.get("line_type", "Unknown"))

        # Build detailed report
        lines = [
            "----------------------------------------------------------------------",
            f" PHONE NUMBER OSINT REPORT: {res.get('e164')}",
            "----------------------------------------------------------------------",
            f" Input String      : {res.get('input')}",
            f" Validity          : Valid ITU-T Telephony Record",
            f" E.164 Format      : {res.get('e164')}",
            f" International     : {res.get('international')}",
            f" National Format   : {res.get('national')}",
            f" RFC3966 URI       : {res.get('rfc3966')}",
            "",
            " [LOCATION & TELECOM INFRASTRUCTURE]",
            f"   * Country Code   : {res.get('country_code')}",
            f"   * National Num   : {res.get('national_number')}",
            f"   * Region/City    : {res.get('location')}",
            f"   * Network Carrier: {res.get('carrier')}",
            f"   * Line Type      : {res.get('line_type')}",
            f"   * Timezone(s)    : {', '.join(res.get('timezones', [])) or 'Unknown'}",
            "----------------------------------------------------------------------",
        ]

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
            if export_to_txt(text, path, "PHONE NUMBER OSINT REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
