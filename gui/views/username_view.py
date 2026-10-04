import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.username_recon import search_username, SERVICES
from core.exporter import export_to_json, export_username_results_to_csv, export_to_txt
from gui.theme import (
    BG_DARK, BG_CARD, BG_INPUT, BG_HOVER, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard


class UsernameView(ctk.CTkFrame):
    """Username Reconnaissance & Footprint Scanner View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.results = []
        self.is_running = False
        self.stop_event = threading.Event()
        
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Username Footprint Scanner", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Probe 40+ social networks, developer hubs, blogging platforms, and gaming communities for an alias.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_username = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter username / alias (e.g. torvalds, satoshi)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_username.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_username.bind("<Return>", lambda event: self.start_scan())

        self.btn_scan = ctk.CTkButton(
            input_row,
            text="Scan Username",
            font=FONT_BODY_BOLD,
            height=38,
            width=140,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_scan
        )
        self.btn_scan.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            input_row,
            text="Stop",
            font=FONT_BODY_BOLD,
            height=38,
            width=80,
            fg_color=BG_INPUT,
            hover_color=ACCENT_RED,
            state="disabled",
            command=self.stop_scan
        )
        self.btn_stop.pack(side="left")

        # Stats Cards Row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 10))

        self.card_found = StatCard(stats_row, title="Profiles Found", value="0", color=ACCENT_GREEN)
        self.card_found.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_checked = StatCard(stats_row, title="Tested Services", value="0", color=ACCENT_BLUE)
        self.card_checked.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_total = StatCard(stats_row, title="Total Platforms", value=str(len(SERVICES)), color=TEXT_PRIMARY)
        self.card_total.pack(side="left", fill="x", expand=True)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, height=6, fg_color=BG_INPUT, progress_color=ACCENT_BLUE)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 15))

        # Results Container
        results_header = ctk.CTkFrame(self, fg_color="transparent")
        results_header.pack(fill="x", padx=20, pady=(0, 6))

        lbl_res_title = ctk.CTkLabel(results_header, text="DISCOVERED PROFILES", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY)
        lbl_res_title.pack(side="left")

        self.filter_var = ctk.StringVar(value="Found Only")
        self.filter_dropdown = ctk.CTkOptionMenu(
            results_header,
            values=["Found Only", "All Tested", "Not Found"],
            variable=self.filter_var,
            width=120,
            height=28,
            fg_color=BG_INPUT,
            button_color=BORDER_COLOR,
            command=lambda v: self.render_results()
        )
        self.filter_dropdown.pack(side="right", padx=(8, 0))

        btn_export = ctk.CTkButton(
            results_header,
            text="Export CSV",
            font=FONT_SMALL,
            width=85,
            height=28,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            command=self.export_csv
        )
        btn_export.pack(side="right", padx=(8, 0))

        btn_export_json = ctk.CTkButton(
            results_header,
            text="Export JSON",
            font=FONT_SMALL,
            width=85,
            height=28,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            command=self.export_json
        )
        btn_export_json.pack(side="right")

        # Scrollable frame for results
        self.results_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.results_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def start_scan(self):
        username = self.entry_username.get().strip()
        if not username:
            messagebox.showwarning("Input Required", "Please enter a username to scan.")
            return

        if self.is_running:
            return

        self.results = []
        self.stop_event.clear()
        self.is_running = True
        self.btn_scan.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.card_found.update_value("0")
        self.card_checked.update_value("0")
        self.progress_bar.set(0.0)

        # Clear scroll area
        for widget in self.results_scroll.winfo_children():
            widget.destroy()

        # Run search in separate thread
        thread = threading.Thread(target=self._run_scan_thread, args=(username,), daemon=True)
        thread.start()

    def _run_scan_thread(self, username: str):
        found_count = 0

        def on_service_checked(res, completed, total):
            nonlocal found_count
            self.results.append(res)
            if res.get("status") == "FOUND":
                found_count += 1

            progress = completed / total if total > 0 else 0
            
            # Update GUI safely
            self.after(0, lambda: self._update_progress_ui(found_count, completed, progress, res))

        search_username(username, max_workers=15, callback=on_service_checked, stop_event=self.stop_event)

        self.after(0, self._scan_finished)

    def _update_progress_ui(self, found, completed, progress, latest_res):
        self.card_found.update_value(str(found))
        self.card_checked.update_value(str(completed))
        self.progress_bar.set(progress)

        # If latest is FOUND and current filter is "Found Only", append row immediately
        filter_mode = self.filter_var.get()
        if filter_mode == "Found Only" and latest_res.get("status") == "FOUND":
            self._create_result_row(latest_res)
        elif filter_mode == "All Tested":
            self._create_result_row(latest_res)

    def _scan_finished(self):
        self.is_running = False
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.progress_bar.set(1.0)
        self.render_results()

    def stop_scan(self):
        if self.is_running:
            self.stop_event.set()
            self.btn_stop.configure(state="disabled")

    def render_results(self):
        for widget in self.results_scroll.winfo_children():
            widget.destroy()

        filter_mode = self.filter_var.get()
        filtered = []

        if filter_mode == "Found Only":
            filtered = [r for r in self.results if r.get("status") == "FOUND"]
        elif filter_mode == "Not Found":
            filtered = [r for r in self.results if r.get("status") == "NOT_FOUND"]
        else:
            filtered = self.results

        if not filtered:
            lbl_empty = ctk.CTkLabel(
                self.results_scroll,
                text="No matching profiles discovered.",
                font=FONT_BODY,
                text_color=TEXT_MUTED
            )
            lbl_empty.pack(pady=30)
            return

        for item in filtered:
            self._create_result_row(item)

    def _create_result_row(self, item: dict):
        status = item.get("status", "UNKNOWN")
        color = ACCENT_GREEN if status == "FOUND" else (TEXT_MUTED if status == "NOT_FOUND" else ACCENT_ORANGE)

        row = ctk.CTkFrame(self.results_scroll, fg_color=BG_INPUT, corner_radius=8, height=44)
        row.pack(fill="x", pady=3, padx=2)

        # Service name & category
        lbl_srv = ctk.CTkLabel(
            row,
            text=f"{item.get('service')}  ({item.get('category')})",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY
        )
        lbl_srv.pack(side="left", padx=14)

        # Status badge
        lbl_stat = ctk.CTkLabel(
            row,
            text=f"[{status}]",
            font=FONT_CODE,
            text_color=color
        )
        lbl_stat.pack(side="left", padx=10)

        # Response time
        lbl_time = ctk.CTkLabel(
            row,
            text=f"{item.get('response_time_ms', 0)}ms",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="left", padx=5)

        # Link action
        url = item.get("profile_url")
        if status == "FOUND" and url:
            btn_open = ctk.CTkButton(
                row,
                text="Open Profile ↗",
                font=FONT_SMALL,
                width=110,
                height=26,
                fg_color=BG_CARD,
                hover_color=ACCENT_BLUE,
                text_color=ACCENT_BLUE,
                command=lambda u=url: webbrowser.open(u)
            )
            btn_open.pack(side="right", padx=10)

    def export_csv(self):
        if not self.results:
            messagebox.showinfo("Export", "No results available to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            if export_username_results_to_csv(self.results, path):
                messagebox.showinfo("Export Success", f"Results exported to {path}")

    def export_json(self):
        if not self.results:
            messagebox.showinfo("Export", "No results available to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if path:
            if export_to_json(self.results, path):
                messagebox.showinfo("Export Success", f"Results exported to {path}")
