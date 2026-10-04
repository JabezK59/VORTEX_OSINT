import threading
import json
import webbrowser
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.email_recon import inspect_email
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class EmailView(ctk.CTkFrame):
    """Email Intelligence & OSINT View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Email Intelligence Analyzer", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Validate deliverability, identify mail servers, detect burner/disposable inboxes, and uncover Gravatar identities.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_email = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter target email (e.g. target@example.com)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_email.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_email.bind("<Return>", lambda event: self.start_analysis())

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Analyze Email",
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

        self.card_mx = StatCard(stats_row, title="MX Deliverable", value="-", color=TEXT_SECONDARY)
        self.card_mx.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_disposable = StatCard(stats_row, title="Disposable / Burner", value="-", color=TEXT_SECONDARY)
        self.card_disposable.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_gravatar = StatCard(stats_row, title="Gravatar Found", value="-", color=TEXT_SECONDARY)
        self.card_gravatar.pack(side="left", fill="x", expand=True)

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
        email = self.entry_email.get().strip()
        if not email:
            messagebox.showwarning("Input Required", "Please enter an email address.")
            return

        self.btn_inspect.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Starting OSINT intelligence lookup for: {email}...")

        threading.Thread(target=self._run_analysis, args=(email,), daemon=True).start()

    def _run_analysis(self, email: str):
        result = inspect_email(email)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        if not res.get("valid_syntax"):
            self.card_mx.update_value("INVALID")
            self.card_disposable.update_value("INVALID")
            self.card_gravatar.update_value("INVALID")
            self.log_box.log(f"[!] ERROR: {res.get('error')}")
            return

        has_mx = res.get("has_mx", False)
        is_disp = res.get("is_disposable", False)
        gravatar = res.get("gravatar", {})
        grav_found = gravatar.get("exists", False)

        # Update Stat Cards
        self.card_mx.update_value("YES" if has_mx else "NO")
        self.card_mx.label_value.configure(text_color=ACCENT_GREEN if has_mx else ACCENT_RED)

        self.card_disposable.update_value("YES" if is_disp else "NO")
        self.card_disposable.label_value.configure(text_color=ACCENT_RED if is_disp else ACCENT_GREEN)

        self.card_gravatar.update_value("FOUND" if grav_found else "NOT FOUND")
        self.card_gravatar.label_value.configure(text_color=ACCENT_GREEN if grav_found else TEXT_SECONDARY)

        # Write detailed report into Log Box
        self.log_box.clear()
        lines = [
            "----------------------------------------------------------------------",
            f" EMAIL OSINT REPORT: {res.get('email')}",
            "----------------------------------------------------------------------",
            f" Target Address   : {res.get('email')}",
            f" Username Part    : {res.get('username')}",
            f" Domain           : {res.get('domain')}",
            f" Classification   : {res.get('category')}",
            f" Syntax Valid     : {res.get('valid_syntax')}",
            f" MX Records Found : {has_mx}",
            f" Disposable Inbox : {is_disp}",
            f" Free Webmail     : {res.get('is_free_provider')} ({res.get('free_provider_name')})",
            "",
            " [MAIL EXCHANGE SERVERS]",
        ]

        mx_records = res.get("mx_records", [])
        if mx_records:
            for mx in mx_records:
                lines.append(f"   * Priority {mx['preference']:2d} -> {mx['host']}")
        else:
            lines.append("   * No MX records found. Domain might not accept incoming mail.")

        lines.extend([
            "",
            " [GRAVATAR DIGITAL FOOTPRINT]",
            f"   * Profile Status : {'ACTIVE / FOUND' if grav_found else 'Not Registered'}",
            f"   * Profile URL    : {gravatar.get('profile_url')}",
            f"   * Display Name   : {gravatar.get('display_name') or 'N/A'}",
            f"   * About / Bio    : {gravatar.get('about') or 'N/A'}",
            f"   * Location       : {gravatar.get('location') or 'N/A'}",
            f"   * Avatar URL     : {gravatar.get('avatar_url')}",
        ])

        accounts = gravatar.get("accounts", [])
        if accounts:
            lines.append("   * Linked Accounts:")
            for acc in accounts:
                lines.append(f"       - {acc.get('shortname', 'account')}: {acc.get('url', '')}")

        lines.append("----------------------------------------------------------------------")

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
            if export_to_txt(text, path, "EMAIL OSINT REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
