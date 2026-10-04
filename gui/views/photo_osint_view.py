import os
import threading
import webbrowser
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from core.photo_osint import (
    inspect_photo_osint,
    GEOGUESSR_COUNTRY_META
)
from core.exporter import export_to_json, export_to_txt
from gui.theme import (
    BG_CARD, BG_INPUT, BG_HOVER, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, ACCENT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)
from gui.components.widgets import StatCard, ResultLogBox


class PhotoOSINTView(ctk.CTkFrame):
    """Photo OSINT & GeoSpy-style Geolocation Studio."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.last_result = None
        self.loaded_image_path = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Photo OSINT & Geolocation Studio", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Extract EXIF GPS coordinates, analyze environmental biomes/lighting, compute visual fingerprints, and explore GeoGuessr clues.",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Input Card
        input_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        input_card.pack(fill="x", padx=20, pady=(0, 15))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.entry_img = ctk.CTkEntry(
            input_row,
            placeholder_text="Select a photo to analyze (JPG, PNG, WebP, HEIC)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_img.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse = ctk.CTkButton(
            input_row,
            text="Browse Photo...",
            font=FONT_BODY,
            height=38,
            width=120,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            command=self.browse_photo
        )
        self.btn_browse.pack(side="left", padx=(0, 10))

        self.btn_analyze = ctk.CTkButton(
            input_row,
            text="Geolocate & Analyze",
            font=FONT_BODY_BOLD,
            height=38,
            width=160,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_analysis
        )
        self.btn_analyze.pack(side="left")

        # Main Workspace Container: 2 Columns
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        content_frame.grid_columnconfigure(0, weight=0)  # Left column fixed
        content_frame.grid_columnconfigure(1, weight=1)  # Right column flexible
        content_frame.grid_rowconfigure(0, weight=1)

        # LEFT COLUMN: Image Preview & Reverse Image Search Engines
        left_col = ctk.CTkFrame(content_frame, width=280, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        left_col.grid_propagate(False)

        ctk.CTkLabel(left_col, text="VISUAL PREVIEW", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", padx=15, pady=(12, 8))

        # Thumbnail canvas / label
        self.preview_frame = ctk.CTkFrame(left_col, width=250, height=220, fg_color=BG_INPUT, corner_radius=8)
        self.preview_frame.pack(padx=15, pady=(0, 10))
        self.preview_frame.pack_propagate(False)

        self.lbl_thumbnail = ctk.CTkLabel(self.preview_frame, text="No Image Loaded", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_thumbnail.pack(expand=True)

        # Image Dimensions & Hash
        self.lbl_img_info = ctk.CTkLabel(left_col, text="Size: -  |  dHash: -", font=FONT_SMALL, text_color=TEXT_SECONDARY)
        self.lbl_img_info.pack(padx=15, pady=(0, 12))

        # Reverse Search Section
        ctk.CTkLabel(left_col, text="REVERSE IMAGE SEARCH", font=FONT_BODY_BOLD, text_color=ACCENT_CYAN).pack(anchor="w", padx=15, pady=(4, 6))

        engines = [
            ("Google Lens ↗", "https://lens.google.com/upload"),
            ("Yandex Images ↗", "https://yandex.com/images/search?rpt=imageview"),
            ("Bing Visual Search ↗", "https://www.bing.com/visualsearch"),
            ("TinEye Search ↗", "https://tineye.com"),
        ]

        for name, url in engines:
            btn = ctk.CTkButton(
                left_col,
                text=name,
                font=FONT_SMALL,
                height=30,
                fg_color=BG_INPUT,
                hover_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY,
                command=lambda u=url: webbrowser.open(u)
            )
            btn.pack(fill="x", padx=15, pady=3)

        # RIGHT COLUMN: Stats, Coordinates, Environmental Heuristics & Reports
        right_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")

        # Stats Cards Row
        stats_row = ctk.CTkFrame(right_col, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 10))

        self.card_gps = StatCard(stats_row, title="EXIF Coordinates", value="No GPS", color=TEXT_SECONDARY)
        self.card_gps.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_biome = StatCard(stats_row, title="Estimated Biome", value="-", color=ACCENT_GREEN)
        self.card_biome.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.card_light = StatCard(stats_row, title="Lighting Condition", value="-", color=ACCENT_ORANGE)
        self.card_light.pack(side="left", fill="x", expand=True)

        # Interactive Map Launchers (if GPS found)
        self.map_bar = ctk.CTkFrame(right_col, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        self.map_bar.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self.map_bar, text="GPS LAUNCHERS:", font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(side="left", padx=14, pady=10)

        self.btn_gmaps = ctk.CTkButton(
            self.map_bar,
            text="Google Maps ↗",
            font=FONT_SMALL,
            width=110,
            height=28,
            fg_color=BG_INPUT,
            hover_color=ACCENT_GREEN,
            state="disabled",
            command=self.open_gmaps
        )
        self.btn_gmaps.pack(side="left", padx=(0, 6))

        self.btn_gearth = ctk.CTkButton(
            self.map_bar,
            text="Google Earth 3D ↗",
            font=FONT_SMALL,
            width=120,
            height=28,
            fg_color=BG_INPUT,
            hover_color=ACCENT_BLUE,
            state="disabled",
            command=self.open_gearth
        )
        self.btn_gearth.pack(side="left", padx=(0, 6))

        self.btn_osm = ctk.CTkButton(
            self.map_bar,
            text="OpenStreetMap ↗",
            font=FONT_SMALL,
            width=120,
            height=28,
            fg_color=BG_INPUT,
            hover_color=ACCENT_PURPLE,
            state="disabled",
            command=self.open_osm
        )
        self.btn_osm.pack(side="left")

        # GeoGuessr Field Clues Selector
        clues_card = ctk.CTkFrame(right_col, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        clues_card.pack(fill="x", pady=(0, 10))

        clues_top = ctk.CTkFrame(clues_card, fg_color="transparent")
        clues_top.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(clues_top, text="GEOGUESSR COUNTRY OSINT REFERENCE:", font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(side="left")

        self.country_var = ctk.StringVar(value="Japan")
        self.country_menu = ctk.CTkOptionMenu(
            clues_top,
            values=list(GEOGUESSR_COUNTRY_META.keys()),
            variable=self.country_var,
            width=140,
            height=26,
            fg_color=BG_INPUT,
            button_color=BORDER_COLOR,
            command=self._on_country_select
        )
        self.country_menu.pack(side="right")

        self.lbl_country_clues = ctk.CTkLabel(
            clues_card,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_PRIMARY,
            justify="left",
            wraplength=640
        )
        self.lbl_country_clues.pack(anchor="w", padx=14, pady=(0, 10))
        self._on_country_select("Japan")

        # Output / Results Box
        self.log_box = ResultLogBox(right_col, height=200)
        self.log_box.pack(fill="both", expand=True)

        # Bottom Action Bar
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_copy_prompt = ctk.CTkButton(
            actions_bar,
            text="Copy AI Geo-Dossier Prompt",
            font=FONT_SMALL,
            width=180,
            height=30,
            fg_color=BG_INPUT,
            hover_color=ACCENT_BLUE,
            command=self.copy_ai_prompt
        )
        self.btn_copy_prompt.pack(side="left")

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

    def _on_country_select(self, country_name: str):
        data = GEOGUESSR_COUNTRY_META.get(country_name, {})
        txt = (
            f"• Drive Side: {data.get('driving_side')}  |  Plates: {data.get('plates')}\n"
            f"• Poles: {data.get('poles')}\n"
            f"• Road Lines & Marks: {data.get('road_lines')}\n"
            f"• Key Landscape Clues: {data.get('clues')}"
        )
        self.lbl_country_clues.configure(text=txt)

    def browse_photo(self):
        fpath = filedialog.askopenfilename(
            title="Select Image for Photo OSINT Geolocation",
            filetypes=[
                ("Image Files", "*.jpg;*.jpeg;*.png;*.webp;*.heic;*.tiff;*.bmp"),
                ("All Files", "*.*")
            ]
        )
        if fpath:
            self.entry_img.delete(0, "end")
            self.entry_img.insert(0, fpath)
            self._display_preview(fpath)
            self.start_analysis()

    def _display_preview(self, fpath: str):
        try:
            pil_img = Image.open(fpath)
            pil_img.thumbnail((240, 200))
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            self.lbl_thumbnail.configure(image=ctk_img, text="")
            self.loaded_image_path = fpath
        except Exception:
            self.lbl_thumbnail.configure(image=None, text="Failed to render preview")

    def start_analysis(self):
        fpath = self.entry_img.get().strip().strip('"').strip("'")
        if not fpath:
            messagebox.showwarning("Input Required", "Please select a photo to analyze.")
            return

        if not self.loaded_image_path or self.loaded_image_path != fpath:
            self._display_preview(fpath)

        self.btn_analyze.configure(state="disabled")
        self.log_box.clear()
        self.log_box.log(f"[*] Running Photo OSINT and Geolocation heuristics on: {os.path.basename(fpath)}...")

        threading.Thread(target=self._run_analysis, args=(fpath,), daemon=True).start()

    def _run_analysis(self, fpath: str):
        result = inspect_photo_osint(fpath)
        self.last_result = result
        self.after(0, lambda: self._render_results(result))

    def _render_results(self, res: dict):
        self.btn_analyze.configure(state="normal")

        if "error" in res:
            self.card_gps.update_value("ERROR")
            self.card_biome.update_value("ERROR")
            self.card_light.update_value("ERROR")
            self.log_box.log(f"[!] ERROR: {res.get('error')}")
            return

        gps = res.get("gps")
        env = res.get("environment", {})

        # Update preview subtitle
        dim_str = f"{res.get('width')}x{res.get('height')} ({res.get('aspect_ratio')})"
        dhash_str = f"dHash: {res.get('dhash')[:8]}..."
        self.lbl_img_info.configure(text=f"Size: {dim_str} | {dhash_str}")

        # Update cards
        if gps:
            self.card_gps.update_value(f"{gps['latitude']}, {gps['longitude']}")
            self.card_gps.label_value.configure(text_color=ACCENT_GREEN, font=("Segoe UI", 13, "bold"))
            self.btn_gmaps.configure(state="normal")
            self.btn_gearth.configure(state="normal")
            self.btn_osm.configure(state="normal")
        else:
            self.card_gps.update_value("No EXIF GPS")
            self.card_gps.label_value.configure(text_color=TEXT_MUTED, font=("Segoe UI", 16, "bold"))
            self.btn_gmaps.configure(state="disabled")
            self.btn_gearth.configure(state="disabled")
            self.btn_osm.configure(state="disabled")

        biome = env.get("primary_biome", "Indeterminate")
        self.card_biome.update_value(biome[:18])

        lighting = env.get("lighting_condition", "Daylight")
        self.card_light.update_value(lighting[:18])

        # Write detailed report to log box
        lines = [
            "----------------------------------------------------------------------",
            f" PHOTO OSINT & GEOLOCATION DOSSIER: {res.get('filename')}",
            "----------------------------------------------------------------------",
            f" File Name         : {res.get('filename')}",
            f" Visual Fingerprint: {res.get('dhash')} (dHash)",
            f" Dimensions / Aspect: {dim_str}",
            f" Camera Make/Model : {res.get('camera_make')} {res.get('camera_model')}",
            f" Lens Model        : {res.get('lens_model')}",
            f" Date Original     : {res.get('date_taken')}",
            "",
            " [EXIF GEOLOCATION METADATA]",
        ]

        if gps:
            lines.extend([
                f"   * Status         : EXACT GPS RECORDED",
                f"   * Coordinates    : {gps['latitude']}, {gps['longitude']}",
                f"   * Google Maps    : {gps['google_maps']}",
                f"   * Google Earth   : {gps['google_earth']}",
                f"   * OpenStreetMap  : {gps['openstreetmap']}",
            ])
        else:
            lines.extend([
                "   * Status         : No GPS coordinates embedded in EXIF.",
                "   * Tip            : Use the visual heuristics below and reverse search engines to locate the target.",
            ])

        lines.extend([
            "",
            " [ENVIRONMENTAL & BIOME HEURISTICS]",
            f"   * Inferred Biome  : {env.get('primary_biome')}",
            f"   * Lighting State  : {env.get('lighting_condition')} (Brightness: {env.get('brightness_score')}/255)",
            f"   * Vegetation Cover: {env.get('vegetation_pct')}%",
            f"   * Arid / Soil Hue : {env.get('arid_soil_pct')}%",
            f"   * Pavement / Urban: {env.get('urban_pavement_pct')}%",
            f"   * Sky / Water Tone: {env.get('sky_water_pct')}%",
            f"   * Dominant Color  : {env.get('dominant_hex')} (RGB: {env.get('dominant_rgb')})",
            "",
            " [INVESTIGATION ACTIONS]",
            "   1. Click 'Google Lens' or 'Yandex Images' on the left to find identical landmarks.",
            "   2. Select a candidate country from the GeoGuessr reference above to compare poles and road markings.",
            "   3. Click 'Copy AI Geo-Dossier Prompt' below to run a forensic query in Gemini, Claude, or GeoSpy.",
            "----------------------------------------------------------------------",
        ])

        self.log_box.clear()
        self.log_box.log("\n".join(lines))

    def open_gmaps(self):
        if self.last_result and self.last_result.get("gps"):
            webbrowser.open(self.last_result["gps"]["google_maps"])

    def open_gearth(self):
        if self.last_result and self.last_result.get("gps"):
            webbrowser.open(self.last_result["gps"]["google_earth"])

    def open_osm(self):
        if self.last_result and self.last_result.get("gps"):
            webbrowser.open(self.last_result["gps"]["openstreetmap"])

    def copy_ai_prompt(self):
        if self.last_result and self.last_result.get("ai_prompt"):
            self.clipboard_clear()
            self.clipboard_append(self.last_result["ai_prompt"])
            self.btn_copy_prompt.configure(text="Prompt Copied!", text_color=ACCENT_GREEN)
            self.after(1500, lambda: self.btn_copy_prompt.configure(text="Copy AI Geo-Dossier Prompt", text_color=TEXT_PRIMARY))
        else:
            messagebox.showinfo("Prompt", "Analyze an image first to generate its AI Geo-Dossier prompt.")

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
            if export_to_txt(text, path, "PHOTO OSINT GEOLOCATION REPORT"):
                messagebox.showinfo("Export Success", f"Saved report to {path}")
