import webbrowser
from tkinter import messagebox
import customtkinter as ctk

from core.config import load_config, save_config
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)


class SettingsView(ctk.CTkFrame):
    """Configuration, API Keys Management, Engine Specs, and OSINT Cheat-Sheet."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.config = load_config()
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Settings & API Integrations", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Manage optional OSINT API keys, engine parameters, and reference curated investigation portals.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Scrollable container for settings & docs
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Card 1: API Keys Management
        card_api = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        card_api.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(card_api, text="OPTIONAL OSINT API KEYS", font=FONT_BODY_BOLD, text_color=ACCENT_BLUE).pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(
            card_api,
            text="VORTEX runs 100% free without keys using public endpoints. Entering keys unlocks higher rate limits.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=15, pady=(0, 12))

        self.api_entries = {}
        api_fields = [
            ("alienvault_otx", "AlienVault OTX Key", "Get free key at otx.alienvault.com"),
            ("shodan", "Shodan API Key", "Account API Key from account.shodan.io"),
            ("virustotal", "VirusTotal API Key", "Free Community API Key"),
            ("abuseipdb", "AbuseIPDB Key", "Free API Key from abuseipdb.com"),
            ("github", "GitHub Personal Token", "Classic token with public repo read"),
        ]

        grid_api = ctk.CTkFrame(card_api, fg_color="transparent")
        grid_api.pack(fill="x", padx=15, pady=(0, 15))
        grid_api.grid_columnconfigure(1, weight=1)

        saved_keys = self.config.get("api_keys", {})
        for idx, (key_id, label, placeholder) in enumerate(api_fields):
            lbl = ctk.CTkLabel(grid_api, text=label, font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, width=170, anchor="w")
            lbl.grid(row=idx, column=0, padx=(0, 10), pady=6, sticky="w")

            entry = ctk.CTkEntry(
                grid_api,
                placeholder_text=placeholder,
                font=FONT_CODE,
                height=34,
                fg_color=BG_INPUT,
                border_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY,
                show="●"
            )
            entry.grid(row=idx, column=1, sticky="ew", pady=6)
            if key_id in saved_keys and saved_keys[key_id]:
                entry.insert(0, saved_keys[key_id])
            self.api_entries[key_id] = entry

        btn_save_keys = ctk.CTkButton(
            card_api,
            text="Save API Configuration",
            font=FONT_BODY_BOLD,
            height=34,
            width=180,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.save_keys_action
        )
        btn_save_keys.pack(anchor="w", padx=15, pady=(0, 15))

        # Card 2: Essential External OSINT Portals
        card_links = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        card_links.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(card_links, text="EXTERNAL INVESTIGATION PORTALS", font=FONT_BODY_BOLD, text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(12, 6))

        portals = [
            ("Shodan (IoT Search)", "https://www.shodan.io"),
            ("Censys Search", "https://search.censys.io"),
            ("Wayback Machine", "https://web.archive.org"),
            ("VirusTotal", "https://www.virustotal.com"),
            ("AlienVault OTX", "https://otx.alienvault.com"),
            ("Have I Been Pwned", "https://haveibeenpwned.com"),
            ("CRT.sh Certificates", "https://crt.sh"),
            ("Epieos Footprints", "https://epieos.com"),
            ("DNSDumpster", "https://dnsdumpster.com"),
        ]

        grid_frame = ctk.CTkFrame(card_links, fg_color="transparent")
        grid_frame.pack(fill="x", padx=15, pady=(0, 15))

        for idx, (name, url) in enumerate(portals):
            btn = ctk.CTkButton(
                grid_frame,
                text=f"{name} ↗",
                font=FONT_SMALL,
                height=32,
                fg_color=BG_INPUT,
                hover_color=BORDER_COLOR,
                command=lambda u=url: webbrowser.open(u)
            )
            r = idx // 3
            c = idx % 3
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            grid_frame.grid_columnconfigure(c, weight=1)

        # Card 3: OSINT Search Operators (Google Dorks Quick Ref)
        card_dorks = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        card_dorks.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(card_dorks, text="GOOGLE DORKING CHEAT-SHEET", font=FONT_BODY_BOLD, text_color=ACCENT_ORANGE).pack(anchor="w", padx=15, pady=(12, 6))

        dorks = (
            "• site:target.com filetype:pdf (Exposed PDF documentation)\n"
            "• site:target.com inurl:admin | inurl:login (Authentication portals)\n"
            "• site:target.com ext:env | ext:log | ext:sql (Leaked credentials & config)\n"
            "• \"username\" site:instagram.com | site:twitter.com | site:github.com (Targeted handle search)\n"
            "• intitle:\"index of\" \"target_domain\" (Directory listings / open indexes)"
        )
        ctk.CTkLabel(card_dorks, text=dorks, font=FONT_CODE, text_color=TEXT_PRIMARY, justify="left", wraplength=700).pack(anchor="w", padx=15, pady=(0, 15))

    def save_keys_action(self):
        new_keys = {}
        for key_id, entry in self.api_entries.items():
            new_keys[key_id] = entry.get().strip()

        self.config["api_keys"] = new_keys
        if save_config(self.config):
            messagebox.showinfo("Settings", "API configuration successfully saved!")
        else:
            messagebox.showerror("Error", "Failed to write configuration file.")
