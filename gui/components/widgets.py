"""
Custom reusable UI components for VORTEX OSINT.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import Any
from gui.theme import (
    BG_CARD, BG_INPUT, BORDER_COLOR, TEXT_PRIMARY,
    TEXT_SECONDARY, ACCENT_BLUE, ACCENT_GREEN, FONT_BODY,
    FONT_BODY_BOLD, FONT_CODE, FONT_SMALL, FONT_SUBTITLE
)


class StatCard(ctk.CTkFrame):
    """A KPI / metric summary card."""
    def __init__(self, master, title: str, value: str = "0", color: str = ACCENT_BLUE, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR, **kwargs)
        
        self.label_title = ctk.CTkLabel(
            self,
            text=title.upper(),
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY
        )
        self.label_title.pack(anchor="w", padx=14, pady=(10, 2))
        
        self.label_value = ctk.CTkLabel(
            self,
            text=str(value),
            font=("Segoe UI", 20, "bold"),
            text_color=color
        )
        self.label_value.pack(anchor="w", padx=14, pady=(0, 10))

    def update_value(self, new_val: Any):
        self.label_value.configure(text=str(new_val))


class ResultLogBox(ctk.CTkFrame):
    """A rich scrollable code/log output widget with clipboard copy and clear actions."""
    def __init__(self, master, height: int = 300, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR, **kwargs)
        
        # Action Bar
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=32)
        self.top_bar.pack(fill="x", padx=10, pady=(6, 4))
        
        self.lbl_title = ctk.CTkLabel(self.top_bar, text="INTELLIGENCE REPORT & LOG", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY)
        self.lbl_title.pack(side="left")
        
        self.btn_clear = ctk.CTkButton(
            self.top_bar,
            text="Clear",
            width=65,
            height=26,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            text_color=TEXT_SECONDARY,
            font=FONT_SMALL,
            command=self.clear
        )
        self.btn_clear.pack(side="right", padx=(6, 0))
        
        self.btn_copy = ctk.CTkButton(
            self.top_bar,
            text="Copy All",
            width=75,
            height=26,
            fg_color=BG_INPUT,
            hover_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            font=FONT_SMALL,
            command=self.copy_all
        )
        self.btn_copy.pack(side="right")
        
        # Text Box
        self.textbox = ctk.CTkTextbox(
            self,
            font=FONT_CODE,
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            corner_radius=8,
            wrap="word",
            height=height
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def log(self, text: str):
        self.textbox.insert("end", text + "\n")
        self.textbox.see("end")

    def clear(self):
        self.textbox.delete("1.0", "end")

    def get_text(self) -> str:
        return self.textbox.get("1.0", "end").strip()

    def copy_all(self):
        content = self.get_text()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.btn_copy.configure(text="Copied!", text_color=ACCENT_GREEN)
            self.after(1500, lambda: self.btn_copy.configure(text="Copy All", text_color=TEXT_PRIMARY))
