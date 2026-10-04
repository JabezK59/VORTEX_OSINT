import threading
import json
import webbrowser
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.metadata_recon import inspect_file_metadata
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class MetadataView(ctk.CTkFrame):
    """File Metadata & Image EXIF Intelligence View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="File Metadata & EXIF Analyzer", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Extract forensic image EXIF tags, GPS geolocations, device signatures, and cryptographic file hashes.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_path = ctk.CTkEntry(
            input_row,
            placeholder_text="Select a local file or paste full path (JPG, PNG, PDF, etc.)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse = ctk.CTkButton(
            input_row,
            text="Browse...",
            font=FONT_BODY,
            height=38,
            width=90,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            command=self.browse_file
        )
        self.btn_browse.pack(side="left", padx=(0, 10))

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Extract Metadata",
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

        self.card_size = StatCard(stats_row, title="File Size", value="-", color=TEXT_SECONDARY)
        self.card_size.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_mime = StatCard(stats_row, title="MIME Type", value="-", color=ACCENT_BLUE)
        self.card_mime.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_exif = StatCard(stats_row, title="EXIF / GPS Data", value="-", color=ACCENT_ORANGE)
        self.card_exif.pack(side="left", fill="x", expand=True)

        # Output / Results Box
        self.log_box = ResultLogBox(self, height=350)
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Bottom Actions
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_open_maps = ctk.CTkButton(
            actions_bar,
            text="Open GPS in Maps ↗",
            font=FONT_SMALL,
            width=150,
            height=30,
            fg_color=BG_INPUT,
            hover_color=ACCENT_GREEN,
            state="disabled",
            command=self.open_maps
        )
        self.btn_open_maps.pack(side="left")

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

    def browse_file(self):
        fpath = filedialog.askopenfilename(
            title="Select File for OSINT Metadata Extraction",
            filetypes=[
                ("All Supported Files", "*.*"),
                ("Images", "*.jpg;*.jpeg;*.png;*.webp;*.tiff"),
                ("Documents", "*.pdf;*.docx;*.xlsx"),
            ]
        )
        if fpath:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, fpath)
            self.start_analysis()

    def start_analysis(self):
        fpath = self.entry_path.get().strip().strip('"').strip("'")
        if not fpath:
            messagebox.showwarning("Input Required", "Please select a file to extract metadata.")
            return

        self.btn_inspect.configure(state="disabled")
        self.btn_open_maps.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Extracting metadata for: {fpath}...")

        threading.Thread(target=self._run_analysis, args=(fpath,), daemon=True).start()

    def _run_analysis(self, fpath: str):
        result = inspect_file_metadata(fpath)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        if "error" in res:
            self.card_size.update_value("ERROR")
            self.card_mime.update_value("ERROR")
            self.card_exif.update_value("ERROR")
            self.log_box.log(f"[!] ERROR: {res.get('error')}")
            return

        self.card_size.update_value(res.get("size_human", "0 B"))
        mime = res.get("mime_type", "Unknown")
        self.card_mime.update_value(mime[:20])

        exif = res.get("exif")
        has_exif = exif and exif.get("has_exif", False)
        gps = exif.get("gps") if exif else None

        if gps:
            self.card_exif.update_value("GPS LOCATED")
            self.card_exif.label_value.configure(text_color=ACCENT_GREEN)
            self.btn_open_maps.configure(state="normal")
        elif has_exif:
            self.card_exif.update_value("EXIF FOUND")
            self.card_exif.label_value.configure(text_color=ACCENT_BLUE)
        else:
            self.card_exif.update_value("NO EXIF")
            self.card_exif.label_value.configure(text_color=TEXT_MUTED)

        # Build detailed report
        lines = [
            "----------------------------------------------------------------------",
            f" FILE METADATA & FORENSIC REPORT: {res.get('filename')}",
            "----------------------------------------------------------------------",
            f" Absolute Path : {res.get('path')}",
            f" File Size     : {res.get('size_human')} ({res.get('size_bytes')} bytes)",
            f" MIME Type     : {res.get('mime_type')}",
            f" Created Date  : {res.get('created')}",
            f" Modified Date : {res.get('modified')}",
            "",
            " [CRYPTOGRAPHIC CHECKSUMS]",
            f"   * MD5    : {res.get('md5')}",
            f"   * SHA256 : {res.get('sha256')}",
        ]

        if gps:
            lines.extend([
                "",
                " [GEOLOCATION COORDINATES (GPS)]",
                f"   * Latitude  : {gps['latitude']}",
                f"   * Longitude : {gps['longitude']}",
                f"   * Maps URL  : {gps['maps_url']}",
            ])

        if exif and exif.get("tags"):
            lines.extend([
                "",
                " [EXIF CAMERA & DEVICE METADATA]",
            ])
            for k, v in sorted(exif["tags"].items()):
                lines.append(f"   * {k:<25}: {v}")
        elif has_exif is False and mime.startswith("image/"):
            lines.extend([
                "",
                " [EXIF METADATA]",
                "   * No EXIF header found. (May have been stripped by messaging apps or camera settings)",
            ])

        lines.append("----------------------------------------------------------------------")

        self.log_box.clear()
        self.log_box.log("\n".join(lines))

    def open_maps(self):
        if self.last_result and self.last_result.get("exif") and self.last_result["exif"].get("gps"):
            url = self.last_result["exif"]["gps"]["maps_url"]
            webbrowser.open(url)

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
            if export_to_txt(text, path, "FILE METADATA REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
