import threading
import webbrowser
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.web_intel import inspect_web_intel
from core.domain_recon import clean_domain
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class WebIntelView(ctk.CTkFrame):
    """Web Technology Stack, Archive & Crawler Intelligence View."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Web Stack & Archive Scraping", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Query the Wayback Machine CDX API for historical URLs, extract robots.txt / security.txt, and fingerprint technologies.",
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
            placeholder_text="Enter website / domain (e.g. stripe.com, tesla.com, openai.com)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_domain.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_domain.bind("<Return>", lambda event: self.start_analysis())

        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="Scrape Web Intel",
            font=FONT_BODY_BOLD,
            height=38,
            width=150,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_analysis
        )
        self.btn_inspect.pack(side="left")

        # Stats Cards Row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 15))

        self.card_tech = StatCard(stats_row, title="Tech Fingerprints", value="-", color=ACCENT_BLUE)
        self.card_tech.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_wayback = StatCard(stats_row, title="Historical URLs", value="-", color=ACCENT_GREEN)
        self.card_wayback.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_robots = StatCard(stats_row, title="Robots Rules", value="-", color=ACCENT_ORANGE)
        self.card_robots.pack(side="left", fill="x", expand=True)

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
        self.btn_inspect.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Probing website, crawler directives, and historical archives for '{domain}'...")

        threading.Thread(target=self._run_analysis, args=(domain,), daemon=True).start()

    def _run_analysis(self, domain: str):
        result = inspect_web_intel(domain)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_inspect.configure(state="normal")

        tech = res.get("tech_fingerprint", {})
        wayback = res.get("wayback_urls", [])
        robots = res.get("robots_txt", {})
        sec_txt = res.get("security_txt", {})

        # Count total tech items
        total_techs = (
            len(tech.get("cms", [])) +
            len(tech.get("frameworks", [])) +
            len(tech.get("web_servers", [])) +
            len(tech.get("cdn", [])) +
            len(tech.get("analytics", []))
        )
        self.card_tech.update_value(str(total_techs))
        self.card_wayback.update_value(str(len(wayback)))
        self.card_robots.update_value(str(len(robots.get("disallowed", []))))

        # Detailed Report
        lines = [
            "----------------------------------------------------------------------",
            f" WEB TECHNOLOGY & ARCHIVE REPORT: {res.get('domain')}",
            "----------------------------------------------------------------------",
            f" Target Domain   : {res.get('domain')}",
            f" Page Title      : {tech.get('title') or 'N/A'}",
            f" Meta Generator  : {tech.get('meta_generator') or 'None'}",
            "",
            " [DETECTED TECHNOLOGY STACK]",
            f"   * CMS Platforms : {', '.join(tech.get('cms', [])) or 'None detected'}",
            f"   * JS Frameworks : {', '.join(tech.get('frameworks', [])) or 'None detected'}",
            f"   * Web Servers   : {', '.join(tech.get('web_servers', [])) or 'Undisclosed'}",
            f"   * CDN / Proxy   : {', '.join(tech.get('cdn', [])) or 'Direct / Unknown'}",
            f"   * Analytics     : {', '.join(tech.get('analytics', [])) or 'None detected'}",
            "",
            " [ROBOTS.TXT CRAWLER DIRECTIVES]",
            f"   * Robots Found  : {robots.get('exists', False)}",
            f"   * Disallow Paths: {len(robots.get('disallowed', []))} forbidden endpoints",
        ]

        for path in robots.get("disallowed", [])[:8]:
            lines.append(f"       -> Disallow: {path}")

        lines.extend([
            "",
            " [SECURITY.TXT VULNERABILITY POLICY]",
            f"   * File Present  : {sec_txt.get('exists', False)}",
            f"   * Contact       : {', '.join(sec_txt.get('contacts', [])) or 'N/A'}",
            f"   * Policy URL    : {sec_txt.get('policy') or 'N/A'}",
            "",
            f" [HISTORICAL WAYBACK MACHINE SNAPSHOTS (Total: {len(wayback)})]",
        ])

        for wb in wayback[:15]:
            lines.append(f"   * [{wb.get('timestamp')[:8]}] ({wb.get('status')}) {wb.get('url')}")
            lines.append(f"       Archive Link -> {wb.get('archive_view')}")

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
            if export_to_txt(text, path, "WEB TECH & ARCHIVE REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
