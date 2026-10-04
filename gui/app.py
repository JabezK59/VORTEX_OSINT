import customtkinter as ctk
from gui.theme import (
    BG_DARK, BG_CARD, BG_INPUT, BG_HOVER, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL
)
from gui.views import (
    UnifiedView, UsernameView, EmailView, DomainView,
    WebIntelView, ThreatIntelView, GraphView, PhotoOSINTView,
    IPView, PhoneView, MetadataView, SettingsView
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class VortexApp(ctk.CTk):
    """Main Application Window for VORTEX OSINT Suite."""
    def __init__(self):
        super().__init__()

        self.title("VORTEX OSINT // Advanced Investigation & GeoSpy Suite")
        self.geometry("1300x860")
        self.minsize(1100, 720)
        self.configure(fg_color=BG_DARK)

        # Main Layout: 2 Columns (Sidebar + Content Container)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Select default view (Unified Search)
        self.select_view("unified")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=265, corner_radius=0, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Brand / Logo Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(22, 16))

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="◈ VORTEX OSINT",
            font=("Segoe UI", 20, "bold"),
            text_color=ACCENT_BLUE
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            brand_frame,
            text="INTELLIGENCE & GEOSPY // v2.5",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Scrollable sidebar navigation items
        self.nav_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.nav_scroll.pack(fill="both", expand=True, padx=4, pady=0)

        # Nav Buttons list
        self.nav_buttons = {}
        nav_items = [
            ("unified", "🔍  Unified Deep Search"),
            ("graph", "🕸️  Visual Knowledge Graph"),
            ("photo_osint", "📷  Photo OSINT & GeoSpy"),
            ("username", "👤  Username Recon (60+)"),
            ("email", "✉️  Email & Gravatar"),
            ("web_intel", "🌐  Web Stack & Archives"),
            ("threat", "🛡️  Threat Intel & RDAP"),
            ("domain", "📡  Domain & DNS Infra"),
            ("ip", "📍  IP Geolocation & Ports"),
            ("phone", "📱  Phone Telephony"),
            ("metadata", "📁  File & EXIF Forensics"),
            ("settings", "⚙️  API Keys & Settings"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.nav_scroll,
                text=label,
                anchor="w",
                font=FONT_BODY,
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color=TEXT_SECONDARY,
                hover_color=BG_HOVER,
                command=lambda k=key: self.select_view(k)
            )
            btn.pack(fill="x", padx=8, pady=3)
            self.nav_buttons[key] = btn

        # Footer Badge
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(fill="x", padx=16, pady=12)

        lbl_ver = ctk.CTkLabel(
            footer_frame,
            text="● Engine Active // 12 Modules Ready",
            font=FONT_SMALL,
            text_color=ACCENT_GREEN
        )
        lbl_ver.pack(anchor="w")

    def _build_content_area(self):
        self.container = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Initialize view instances
        self.views = {
            "unified": UnifiedView(self.container, switch_tab_callback=self.select_view),
            "graph": GraphView(self.container),
            "photo_osint": PhotoOSINTView(self.container),
            "username": UsernameView(self.container),
            "email": EmailView(self.container),
            "web_intel": WebIntelView(self.container),
            "threat": ThreatIntelView(self.container),
            "domain": DomainView(self.container),
            "ip": IPView(self.container),
            "phone": PhoneView(self.container),
            "metadata": MetadataView(self.container),
            "settings": SettingsView(self.container),
        }

        # Grid all views in the same cell
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def select_view(self, view_key: str):
        if view_key in self.views:
            self.views[view_key].tkraise()

            for key, btn in self.nav_buttons.items():
                if key == view_key:
                    btn.configure(
                        fg_color=BG_INPUT,
                        text_color=TEXT_PRIMARY,
                        border_width=1,
                        border_color=BORDER_COLOR
                    )
                else:
                    btn.configure(
                        fg_color="transparent",
                        text_color=TEXT_SECONDARY,
                        border_width=0
                    )
