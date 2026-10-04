import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.graph_builder import generate_investigation_graph
from core.domain_recon import clean_domain, get_dns_records, find_subdomains_crtsh
from core.web_intel import fingerprint_technologies
from core.ip_recon import is_valid_ip
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_CODE
)


class GraphView(ctk.CTkFrame):
    """Visual OSINT Entity-Relationship Knowledge Graph."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.current_fig = None
        self.canvas_widget = None
        self._build_ui()

    def _build_ui(self):
        # Header
        lbl_head = ctk.CTkLabel(self, text="Visual OSINT Knowledge Graph", font=FONT_TITLE, text_color=TEXT_PRIMARY)
        lbl_head.pack(anchor="w", padx=20, pady=(20, 2))
        
        lbl_desc = ctk.CTkLabel(
            self,
            text="Generate interactive node-and-edge visual maps connecting targets, resolved IPs, subdomains, mail servers, and tech stacks.",
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
            placeholder_text="Enter target domain or organization (e.g. github.com, target.com)...",
            font=FONT_BODY,
            height=38,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_target.bind("<Return>", lambda event: self.start_graph_build())

        self.btn_build = ctk.CTkButton(
            input_row,
            text="Generate Visual Graph",
            font=FONT_BODY_BOLD,
            height=38,
            width=180,
            fg_color=ACCENT_BLUE,
            hover_color="#388bfd",
            command=self.start_graph_build
        )
        self.btn_build.pack(side="left")

        # Graph Canvas Container
        self.graph_container = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        self.graph_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Action bar at bottom
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.pack(fill="x", padx=20, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(actions_bar, text="Ready. Enter a target to generate graph.", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_status.pack(side="left")

        self.btn_save_png = ctk.CTkButton(
            actions_bar,
            text="Save Graph as PNG",
            font=FONT_SMALL,
            width=140,
            height=30,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            state="disabled",
            command=self.save_png
        )
        self.btn_save_png.pack(side="right")

        # Initial placeholder graph
        self._render_placeholder()

    def _render_placeholder(self):
        fig = generate_investigation_graph("VORTEX OSINT", target_type="System")
        self._display_fig(fig)

    def start_graph_build(self):
        target = self.entry_target.get().strip()
        if not target:
            messagebox.showwarning("Input Required", "Please enter a target domain.")
            return

        domain = clean_domain(target)
        self.btn_build.configure(state="disabled")
        self.lbl_status.configure(text=f"Mapping entities for '{domain}'...", text_color=ACCENT_ORANGE)

        threading.Thread(target=self._gather_and_build, args=(domain,), daemon=True).start()

    def _gather_and_build(self, domain: str):
        # 1. DNS Records
        dns_recs = get_dns_records(domain)
        ips = dns_recs.get("A", [])
        mx_raw = dns_recs.get("MX", [])
        mx_clean = [m.split()[-1] for m in mx_raw]
        ns_records = dns_recs.get("NS", [])

        # 2. Subdomains (top 8)
        subdomains = find_subdomains_crtsh(domain, max_subdomains=8)

        # 3. Technologies
        tech = fingerprint_technologies(domain)
        all_techs = tech.get("cms", []) + tech.get("frameworks", []) + tech.get("web_servers", []) + tech.get("cdn", [])

        # Generate Figure
        fig = generate_investigation_graph(
            target_name=domain,
            target_type="Domain",
            ips=ips,
            subdomains=subdomains,
            mx_records=mx_clean,
            nameservers=ns_records,
            techs=all_techs,
        )

        self.after(0, lambda: self._on_build_complete(fig, domain))

    def _on_build_complete(self, fig, domain: str):
        self.btn_build.configure(state="normal")
        self.btn_save_png.configure(state="normal")
        self.lbl_status.configure(text=f"Graph synthesized successfully for '{domain}'.", text_color=ACCENT_GREEN)
        self._display_fig(fig)

    def _display_fig(self, fig):
        self.current_fig = fig

        # Remove previous canvas if exists
        if self.canvas_widget:
            self.canvas_widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        canvas.draw()
        self.canvas_widget = canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=4, pady=4)

    def save_png(self):
        if not self.current_fig:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if path:
            self.current_fig.savefig(path, dpi=200, facecolor=self.current_fig.get_facecolor())
            messagebox.showinfo("Export Success", f"Graph image saved to {path}")
