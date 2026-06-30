import customtkinter as ctk
from pathlib import Path
import subprocess
import re
import threading
import shutil
import sys
import time
import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as messagebox
import urllib.request
import urllib.parse
import urllib.error
import ssl

# Hide console windows for subprocesses on Windows
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# --- Set CustomTkinter Appearance ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class MuxerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal Video Muxer")
        self.geometry("900x900")
        self.minsize(800, 700)

        # --- Main Scrollable Container ---
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Threading Event for Cancellation ---
        self.cancel_event = threading.Event()
        self.confirm_event = threading.Event()
        self.confirm_result = False

        # --- List to track editable widgets for disabling/enabling ---
        self.editable_widgets = []

        # --- Helper: Card Container ---
        def create_card(parent, title=None):
            card = ctk.CTkFrame(parent, fg_color=("gray95", "gray16"), corner_radius=8)
            if title:
                header = ctk.CTkLabel(
                    card, text=title, font=ctk.CTkFont(size=14, weight="bold")
                )
                header.pack(anchor="w", padx=15, pady=(15, 5))
            return card

        # --- Helper: Clearable Entry Widget ---
        def make_clearable_entry(parent, var, width=200):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            entry = ctk.CTkEntry(frame, textvariable=var, width=width)
            entry.pack(side="left", fill="x", expand=True)

            clear_btn = ctk.CTkButton(
                frame,
                text="✕",
                width=24,
                height=24,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray40", "gray50"),
                command=lambda: var.set(""),
                corner_radius=12,
            )
            clear_btn.pack(side="left", padx=(4, 0))
            self.editable_widgets.extend([entry, clear_btn])
            return frame, entry

        # --- Helper: Grid-Aligned Directory Row ---
        def create_dir_row(parent, row_idx, label_text, var):
            ctk.CTkLabel(parent, text=label_text, anchor="w", width=160).grid(
                row=row_idx, column=0, padx=(15, 10), pady=8, sticky="w"
            )
            entry_frame, _ = make_clearable_entry(parent, var)
            entry_frame.grid(row=row_idx, column=1, padx=5, pady=8, sticky="ew")
            btn = ctk.CTkButton(
                parent,
                text="📂 Browse",
                width=90,
                fg_color="transparent",
                border_width=1,
                text_color=("gray10", "gray90"),
                command=lambda: self.browse_dir(var),
            )
            btn.grid(row=row_idx, column=2, padx=(5, 15), pady=8)
            parent.columnconfigure(1, weight=1)
            self.editable_widgets.append(btn)

        # --- Helper: Grid-Aligned File Row ---
        def create_file_row(parent, row_idx, label_text, var, ftype):
            ctk.CTkLabel(parent, text=label_text, anchor="w", width=160).grid(
                row=row_idx, column=0, padx=(15, 10), pady=8, sticky="w"
            )
            entry_frame, _ = make_clearable_entry(parent, var)
            entry_frame.grid(row=row_idx, column=1, padx=5, pady=8, sticky="ew")
            btn = ctk.CTkButton(
                parent,
                text="📄 Browse",
                width=90,
                fg_color="transparent",
                border_width=1,
                text_color=("gray10", "gray90"),
                command=lambda: self.browse_file(var, ftype),
            )
            btn.grid(row=row_idx, column=2, padx=(5, 15), pady=8)
            parent.columnconfigure(1, weight=1)
            self.editable_widgets.append(btn)

        # --- Variables ---
        base_dir = str(Path(".").resolve())
        self.video_dir_var = ctk.StringVar(value=base_dir)
        self.sub_dir_var = ctk.StringVar(value=str(Path(base_dir) / "sub"))
        self.font_dir_var = ctk.StringVar(value=str(Path(base_dir) / "sub" / "font"))
        self.single_video_var = ctk.StringVar()
        self.single_sub_var = ctk.StringVar()
        self.source_sub_dir_var = ctk.StringVar(value=base_dir)
        self.target_sub_dir_var = ctk.StringVar(value=base_dir)

        self.edit_sub_dir_var = ctk.StringVar(value=str(Path(base_dir) / "sub"))
        self.edit_single_sub_var = ctk.StringVar()
        self.edit_type_var = ctk.StringVar(value="Folder")

        self.download_sub_dir_var = ctk.StringVar(value=str(Path(base_dir) / "sub"))
        self.download_single_sub_var = ctk.StringVar()
        self.download_type_var = ctk.StringVar(value="Folder")
        self.download_out_dir_var = ctk.StringVar(
            value=str(Path(base_dir) / "sub" / "fonts")
        )

        self.series_name_var = ctk.StringVar()
        self.output_template_var = ctk.StringVar()
        self.mode_var = ctk.StringVar(value="Batch Mode")
        self.add_jump_points_var = ctk.BooleanVar(value=False)

        # --- Mode Selection Card ---
        self.mode_card = create_card(self.main_scroll, "Operation Mode")
        self.mode_card.pack(fill="x", padx=10, pady=(0, 10))

        self.mode_switch = ctk.CTkSegmentedButton(
            self.mode_card,
            values=[
                "Batch Mode",
                "Single File",
                "Copy Subtitles",
                "Remove Subtitles",
                "Edit Fonts",
                "Download Fonts",
            ],
            variable=self.mode_var,
            command=self.on_mode_change,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.mode_switch.pack(fill="x", padx=15, pady=(5, 15))
        self.editable_widgets.append(self.mode_switch)

        # --- Source Configuration Card ---
        self.source_card = create_card(self.main_scroll, "Source Configuration")
        self.source_card.pack(fill="x", padx=10, pady=10)

        self.batch_ui = ctk.CTkFrame(self.source_card, fg_color="transparent")
        create_dir_row(self.batch_ui, 0, "Video Directory:", self.video_dir_var)
        create_dir_row(self.batch_ui, 1, "Subtitle Directory:", self.sub_dir_var)

        self.single_ui = ctk.CTkFrame(self.source_card, fg_color="transparent")
        create_file_row(
            self.single_ui, 0, "Video File:", self.single_video_var, "Video"
        )
        create_file_row(
            self.single_ui, 1, "Subtitle File:", self.single_sub_var, "Subtitle"
        )

        self.copy_subs_ui = ctk.CTkFrame(self.source_card, fg_color="transparent")
        create_dir_row(
            self.copy_subs_ui, 0, "Source Dir (with subs):", self.source_sub_dir_var
        )
        create_dir_row(
            self.copy_subs_ui, 1, "Target Dir (no subs):", self.target_sub_dir_var
        )

        self.remove_subs_ui = ctk.CTkFrame(self.source_card, fg_color="transparent")
        create_dir_row(self.remove_subs_ui, 0, "Video Directory:", self.video_dir_var)

        # --- Edit Fonts Mode UI ---
        self.edit_fonts_ui = ctk.CTkFrame(self.source_card, fg_color="transparent")

        rb_frame = ctk.CTkFrame(self.edit_fonts_ui, fg_color="transparent")
        rb_frame.pack(fill="x", padx=15, pady=(5, 5))
        ctk.CTkLabel(rb_frame, text="Source Type:", width=150, anchor="w").pack(
            side="left"
        )
        self.edit_folder_rb = ctk.CTkRadioButton(
            rb_frame,
            text="Subtitle Folder",
            variable=self.edit_type_var,
            value="Folder",
            command=self.toggle_edit_source,
        )
        self.edit_folder_rb.pack(side="left", padx=10)
        self.edit_file_rb = ctk.CTkRadioButton(
            rb_frame,
            text="Single Subtitle File",
            variable=self.edit_type_var,
            value="File",
            command=self.toggle_edit_source,
        )
        self.edit_file_rb.pack(side="left", padx=10)
        self.editable_widgets.extend([self.edit_folder_rb, self.edit_file_rb])

        self.edit_folder_frame = ctk.CTkFrame(
            self.edit_fonts_ui, fg_color="transparent"
        )
        create_dir_row(
            self.edit_folder_frame, 0, "Subtitle Directory:", self.edit_sub_dir_var
        )

        self.edit_file_frame = ctk.CTkFrame(self.edit_fonts_ui, fg_color="transparent")
        create_file_row(
            self.edit_file_frame,
            0,
            "Subtitle File:",
            self.edit_single_sub_var,
            "Subtitle",
        )

        self.scan_btn = ctk.CTkButton(
            self.edit_fonts_ui,
            text="🔍 Scan Subtitles for Fonts",
            command=self.scan_fonts,
            width=200,
        )
        self.scan_btn.pack(pady=10)
        self.editable_widgets.append(self.scan_btn)

        self.font_editor_frame = ctk.CTkScrollableFrame(
            self.edit_fonts_ui, height=200, fg_color=("gray90", "gray13")
        )
        self.font_editor_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.font_mapping_vars = {}
        self.common_fonts = [
            # --- Sans-Serif (Regular & Weights) ---
            "Roboto",
            "Roboto Medium",
            "Roboto Bold",
            "Roboto Light",
            "Roboto Black",
            "Roboto Condensed",
            "Roboto Condensed Bold",
            "Open Sans",
            "Open Sans SemiBold",
            "Open Sans Bold",
            "Open Sans Light",
            "Montserrat",
            "Montserrat Medium",
            "Montserrat SemiBold",
            "Montserrat Bold",
            "Montserrat Light",
            "Lato",
            "Lato Medium",
            "Lato Bold",
            "Lato Light",
            "Lato Black",
            "Oswald",
            "Oswald Medium",
            "Oswald Bold",
            "Oswald Light",
            "Inter",
            "Inter Medium",
            "Inter SemiBold",
            "Inter Bold",
            "Inter Light",
            "Poppins",
            "Poppins Medium",
            "Poppins SemiBold",
            "Poppins Bold",
            "Poppins Light",
            "Nunito",
            "Nunito SemiBold",
            "Nunito Bold",
            "Nunito Light",
            "Fira Sans",
            "Fira Sans Medium",
            "Fira Sans Bold",
            "Fira Sans Light",
            "Work Sans",
            "Work Sans Medium",
            "Work Sans Bold",
            "Raleway",
            "Raleway Medium",
            "Raleway SemiBold",
            "Raleway Bold",
            # --- Serif (Regular & Weights) ---
            "Merriweather",
            "Merriweather Bold",
            "Merriweather Light",
            "Merriweather Black",
            "PT Serif",
            "PT Serif Bold",
            "Libre Baskerville",
            "Libre Baskerville Bold",
            "EB Garamond",
            "EB Garamond Medium",
            "EB Garamond Bold",
            "EB Garamond SemiBold",
            "Playfair Display",
            "Playfair Display Bold",
            "Playfair Display Black",
            "Crimson Text",
            "Crimson Text Bold",
            "Crimson Text SemiBold",
            "Source Serif 4",
            "Source Serif 4 Bold",
            "Source Serif 4 SemiBold",
            "Noto Serif",
            "Noto Serif Bold",
            "Noto Serif SemiBold",
            # --- Monospace (Regular & Weights) ---
            "Roboto Mono",
            "Roboto Mono Bold",
            "Roboto Mono Medium",
            "Fira Code",
            "Fira Code Bold",
            "Fira Code Medium",
            "Fira Code Light",
            "Source Code Pro",
            "Source Code Pro Bold",
            "Source Code Pro SemiBold",
            "Source Code Pro Medium",
            "JetBrains Mono",
            "JetBrains Mono Bold",
            "JetBrains Mono Medium",
            "JetBrains Mono SemiBold",
            "Space Mono",
            "Space Mono Bold",
            "Inconsolata",
            "Inconsolata Bold",
            "Inconsolata Medium",
            "Cascadia Code",
            "Cascadia Code Bold",
            "Cascadia Mono",
            # --- CJK / International (Open Source) ---
            "Noto Sans CJK JP",
            "Noto Sans CJK JP Bold",
            "Noto Sans CJK JP Medium",
            "Noto Sans CJK JP Black",
            "Noto Sans CJK SC",
            "Noto Sans CJK SC Bold",
            "Noto Sans CJK SC Medium",
            "Noto Sans CJK TC",
            "Noto Sans CJK TC Bold",
            "Noto Sans CJK TC Medium",
            "Noto Sans CJK KR",
            "Noto Sans CJK KR Bold",
            "Noto Sans CJK KR Medium",
            "Noto Serif CJK JP",
            "Noto Serif CJK JP Bold",
            "Noto Serif CJK JP SemiBold",
            "Noto Serif CJK SC",
            "Noto Serif CJK SC Bold",
            "Source Han Sans",
            "Source Han Sans Bold",
            "Source Han Sans Medium",
            "Source Han Serif",
            "Source Han Serif Bold",
            "Source Han Serif SemiBold",
            # --- Handwriting / Display ---
            "Caveat",
            "Caveat Bold",
            "Pacifico",
            "Dancing Script",
            "Dancing Script Bold",
            "Comfortaa",
            "Comfortaa Bold",
            "Comfortaa Medium",
            "Permanent Marker",
            "Bebas Neue",
            "Anton",
            "Lobster",
        ]

        self.toggle_edit_source()  # Initialize visibility

        # --- Download Fonts Mode UI ---
        self.download_fonts_ui = ctk.CTkFrame(self.source_card, fg_color="transparent")

        dl_rb_frame = ctk.CTkFrame(self.download_fonts_ui, fg_color="transparent")
        dl_rb_frame.pack(fill="x", padx=15, pady=(5, 5))
        ctk.CTkLabel(dl_rb_frame, text="Source Type:", width=150, anchor="w").pack(
            side="left"
        )
        self.dl_folder_rb = ctk.CTkRadioButton(
            dl_rb_frame,
            text="Subtitle Folder",
            variable=self.download_type_var,
            value="Folder",
            command=self.toggle_download_source,
        )
        self.dl_folder_rb.pack(side="left", padx=10)
        self.dl_file_rb = ctk.CTkRadioButton(
            dl_rb_frame,
            text="Single Subtitle File",
            variable=self.download_type_var,
            value="File",
            command=self.toggle_download_source,
        )
        self.dl_file_rb.pack(side="left", padx=10)
        self.editable_widgets.extend([self.dl_folder_rb, self.dl_file_rb])

        self.dl_folder_frame = ctk.CTkFrame(
            self.download_fonts_ui, fg_color="transparent"
        )
        create_dir_row(
            self.dl_folder_frame, 0, "Subtitle Directory:", self.download_sub_dir_var
        )

        self.dl_file_frame = ctk.CTkFrame(
            self.download_fonts_ui, fg_color="transparent"
        )
        create_file_row(
            self.dl_file_frame,
            0,
            "Subtitle File:",
            self.download_single_sub_var,
            "Subtitle",
        )

        self.dl_out_frame = ctk.CTkFrame(self.download_fonts_ui, fg_color="transparent")
        create_dir_row(
            self.dl_out_frame, 0, "Output Directory:", self.download_out_dir_var
        )

        self.dl_scan_btn = ctk.CTkButton(
            self.download_fonts_ui,
            text="🔍 Scan Subtitles for Fonts",
            command=self.scan_download_fonts,
            width=200,
        )
        self.dl_scan_btn.pack(pady=10)
        self.editable_widgets.append(self.dl_scan_btn)

        self.dl_font_list_frame = ctk.CTkScrollableFrame(
            self.download_fonts_ui, height=200, fg_color=("gray90", "gray13")
        )
        self.dl_font_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.dl_font_vars = {}

        self.toggle_download_source()
        self.batch_ui.pack(fill="x", pady=(0, 10))  # Default Active Source UI

        # --- Optional Settings Card ---
        self.settings_card = create_card(self.main_scroll, "Output Settings")
        self.settings_card.pack(fill="x", padx=10, pady=10)

        # Font Directory
        self.font_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.font_frame.pack(fill="x")
        create_dir_row(self.font_frame, 0, "Font Dir (Optional):", self.font_dir_var)

        settings_inner = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        settings_inner.pack(fill="x", padx=15, pady=(5, 15))

        # Series Name
        ctk.CTkLabel(
            settings_inner, text="Series Name (Optional):", width=200, anchor="w"
        ).grid(row=0, column=0, pady=5, sticky="w")
        series_frame, _ = make_clearable_entry(settings_inner, self.series_name_var)
        series_frame.grid(row=0, column=1, pady=5, sticky="ew")

        # Output Template
        ctk.CTkLabel(
            settings_inner,
            text="Output Template (e.g., {series} EP{ep2}):",
            width=250,
            anchor="w",
        ).grid(row=1, column=0, pady=5, sticky="w")
        template_frame, self.output_template_entry = make_clearable_entry(
            settings_inner, self.output_template_var
        )
        template_frame.grid(row=1, column=1, pady=5, sticky="ew")
        settings_inner.columnconfigure(1, weight=1)

        # Template Variables Row
        var_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        var_frame.grid(row=2, column=1, pady=(2, 10), sticky="w")
        for var in ["{series}", "{ep}", "{ep2}", "{video_stem}"]:
            btn = ctk.CTkButton(
                var_frame,
                text=var,
                width=80,
                height=24,
                fg_color=("gray85", "gray25"),
                text_color=("black", "white"),
                hover_color=("gray75", "gray35"),
                command=lambda v=var: self.insert_template_var(v),
            )
            btn.pack(side="left", padx=(0, 5))
            self.editable_widgets.append(btn)

        # --- Jump Points Card ---
        self.jump_card = create_card(self.main_scroll)
        self.jump_card.pack(fill="x", padx=10, pady=10)

        self.jump_switch = ctk.CTkSwitch(
            self.jump_card,
            text="Add Jump Points (Chapters)",
            font=ctk.CTkFont(weight="bold"),
            variable=self.add_jump_points_var,
            command=self.toggle_jump_points,
        )
        self.jump_switch.pack(anchor="w", padx=15, pady=15)
        self.editable_widgets.append(self.jump_switch)

        self.jp_input_frame = ctk.CTkFrame(self.jump_card, fg_color="transparent")

        # Grid alignment for Jump Points
        ctk.CTkLabel(self.jp_input_frame, text="Chapter Title:").grid(
            row=0, column=0, padx=(15, 5), pady=5, sticky="e"
        )
        self.jp_title_entry = ctk.CTkEntry(self.jp_input_frame, width=200)
        self.jp_title_entry.grid(row=0, column=1, padx=(0, 15), pady=5, sticky="we")
        self.editable_widgets.append(self.jp_title_entry)

        ctk.CTkLabel(self.jp_input_frame, text="Time:").grid(
            row=0, column=2, padx=(0, 5), pady=5, sticky="e"
        )
        time_container = ctk.CTkFrame(self.jp_input_frame, fg_color="transparent")
        time_container.grid(row=0, column=3, pady=5, sticky="w")

        self.jp_hh_entry = ctk.CTkEntry(
            time_container, width=45, placeholder_text="HH", justify="center"
        )
        self.jp_hh_entry.pack(side="left")
        self.editable_widgets.append(self.jp_hh_entry)
        ctk.CTkLabel(time_container, text=":").pack(side="left", padx=3)

        self.jp_mm_entry = ctk.CTkEntry(
            time_container, width=45, placeholder_text="MM", justify="center"
        )
        self.jp_mm_entry.pack(side="left")
        self.editable_widgets.append(self.jp_mm_entry)
        ctk.CTkLabel(time_container, text=":").pack(side="left", padx=3)

        self.jp_ss_entry = ctk.CTkEntry(
            time_container, width=60, placeholder_text="SS.ms", justify="center"
        )
        self.jp_ss_entry.pack(side="left")
        self.editable_widgets.append(self.jp_ss_entry)

        self.jp_add_btn = ctk.CTkButton(
            self.jp_input_frame, text="➕ Add", width=80, command=self.add_jump_point
        )
        self.jp_add_btn.grid(row=0, column=4, padx=(15, 15), pady=5)
        self.editable_widgets.append(self.jp_add_btn)
        self.jp_input_frame.columnconfigure(1, weight=1)

        self.jp_list_frame = ctk.CTkScrollableFrame(
            self.jump_card, height=120, fg_color=("gray90", "gray13")
        )
        self.jump_points = []

        # --- Controls & Progress ---
        self.ctrl_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=10, pady=10)

        self.start_btn = ctk.CTkButton(
            self.ctrl_frame,
            text="▶ Start Operation",
            command=self.start_muxing,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#28a745",
            hover_color="#218838",
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        self.editable_widgets.append(self.start_btn)

        self.cancel_btn = ctk.CTkButton(
            self.ctrl_frame,
            text="🛑 Cancel",
            command=self.cancel_muxing,
            width=100,
            height=45,
            fg_color="#D9534F",
            hover_color="#C9302C",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
        )
        self.cancel_btn.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            self.ctrl_frame,
            text="🗑️ Clear Log",
            command=self.clear_log,
            width=110,
            height=45,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
        )
        self.clear_btn.pack(side="right")

        # --- Progress Bar Frame (Hidden initially) ---
        self.progress_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=12)
        self.progress_bar.pack(fill="x", expand=True, pady=(5, 5))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="Progress: 0/0", font=ctk.CTkFont(weight="bold")
        )
        self.progress_label.pack(anchor="w")

        # --- Terminal-Style Log Output ---
        self.log_card = create_card(self.main_scroll, "Console Output")
        self.log_card.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        self.log_text = ctk.CTkTextbox(
            self.log_card,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            height=180,
            fg_color="#1E1E1E",
            text_color="#00FF00",  # Hacker/Terminal styling
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        # --- FFmpeg Detection ---
        self.ffmpeg_path = self.find_executable("ffmpeg")
        self.ffprobe_path = self.find_executable("ffprobe")

        if self.ffmpeg_path and self.ffprobe_path:
            self.log(f"[SYS] Ready. Detected ffmpeg at: {self.ffmpeg_path}")
        else:
            self.log(
                "[WARN] ffmpeg or ffprobe not found in 'tools' folder or system PATH!"
            )

    # --- Core Methods ---
    def toggle_download_source(self):
        if self.download_type_var.get() == "Folder":
            self.dl_folder_frame.pack(fill="x", pady=4)
            self.dl_file_frame.pack_forget()
        else:
            self.dl_folder_frame.pack_forget()
            self.dl_file_frame.pack(fill="x", pady=4)

    def scan_download_fonts(self):
        source_type = self.download_type_var.get()
        sub_files = []
        if source_type == "Folder":
            sub_dir = Path(self.download_sub_dir_var.get())
            if not sub_dir.exists():
                self.log("[ERROR] Subtitle directory does not exist.")
                return
            sub_files = [
                p
                for p in sub_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in {".ass", ".ssa"}
            ]
        else:
            sub_file = Path(self.download_single_sub_var.get().strip())
            if not sub_file.exists():
                self.log("[ERROR] Subtitle file does not exist.")
                return
            if sub_file.suffix.lower() in {".ass", ".ssa"}:
                sub_files = [sub_file]
            else:
                self.log("[ERROR] Only .ass and .ssa files are supported.")
                return

        if not sub_files:
            self.log("No subtitle files found to scan.")
            return

        fonts_found = set()
        for f in sub_files:
            try:
                content = f.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                try:
                    content = f.read_text(encoding="cp1252", errors="ignore")
                except Exception:
                    continue

            in_styles = False
            font_idx = -1
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("[V4") or stripped.startswith("[V4+"):
                    in_styles = True
                    font_idx = -1
                    continue
                if stripped.startswith("[") and in_styles:
                    in_styles = False
                    continue

                if in_styles:
                    if stripped.lower().startswith("format:"):
                        parts = [p.strip().lower() for p in stripped[7:].split(",")]
                        if "fontname" in parts:
                            font_idx = parts.index("fontname")
                    elif stripped.lower().startswith("style:"):
                        if font_idx != -1:
                            parts = [p.strip() for p in stripped[6:].split(",")]
                            if len(parts) > font_idx:
                                fonts_found.add(parts[font_idx])

        for widget in self.dl_font_list_frame.winfo_children():
            widget.destroy()
        self.dl_font_vars.clear()

        if not fonts_found:
            self.log("No fonts found in the selected subtitle(s).")
            return

        for font in sorted(fonts_found):
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.dl_font_list_frame, text=font, variable=var)
            cb.pack(anchor="w", padx=15, pady=4)
            self.dl_font_vars[font] = var
            self.editable_widgets.append(cb)

        self.log(
            f"Scan complete. Found {len(fonts_found)} unique font(s). Uncheck any you don't need, then click 'Start Operation'."
        )

    def ask_confirmation(self, title, message):
        self.confirm_event.clear()
        self.confirm_result = False

        def show_dialog():
            res = messagebox.askyesno(title, message, parent=self)
            self.confirm_result = res
            self.confirm_event.set()

        self.after(0, show_dialog)
        self.confirm_event.wait()
        return self.confirm_result

    def toggle_edit_source(self):
        if self.edit_type_var.get() == "Folder":
            self.edit_folder_frame.pack(fill="x", pady=4)
            self.edit_file_frame.pack_forget()
        else:
            self.edit_folder_frame.pack_forget()
            self.edit_file_frame.pack(fill="x", pady=4)

    def scan_fonts(self):
        source_type = self.edit_type_var.get()
        sub_files = []
        if source_type == "Folder":
            sub_dir = Path(self.edit_sub_dir_var.get())
            if not sub_dir.exists():
                self.log("[ERROR] Subtitle directory does not exist.")
                return
            sub_files = [
                p
                for p in sub_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in {".ass", ".ssa"}
            ]
        else:
            sub_file = Path(self.edit_single_sub_var.get().strip())
            if not sub_file.exists():
                self.log("[ERROR] Subtitle file does not exist.")
                return
            if sub_file.suffix.lower() in {".ass", ".ssa"}:
                sub_files = [sub_file]
            else:
                self.log("[ERROR] Only .ass and .ssa files are supported.")
                return

        if not sub_files:
            self.log("No subtitle files found to scan.")
            return

        fonts_found = set()
        for f in sub_files:
            try:
                content = f.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                continue

            in_styles = False
            font_idx = -1
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("[V4") or stripped.startswith("[V4+"):
                    in_styles = True
                    font_idx = -1
                    continue
                if stripped.startswith("[") and in_styles:
                    in_styles = False
                    continue

                if in_styles:
                    if stripped.lower().startswith("format:"):
                        parts = [p.strip().lower() for p in stripped[7:].split(",")]
                        if "fontname" in parts:
                            font_idx = parts.index("fontname")
                    elif stripped.lower().startswith("style:"):
                        if font_idx != -1:
                            parts = [p.strip() for p in stripped[6:].split(",")]
                            if len(parts) > font_idx:
                                fonts_found.add(parts[font_idx])

        # Clear existing editor rows
        for widget in self.font_editor_frame.winfo_children():
            widget.destroy()
        self.font_mapping_vars.clear()

        if not fonts_found:
            self.log("No fonts found in the selected subtitle(s).")
            return

        # Create header
        header = ctk.CTkFrame(self.font_editor_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(
            header,
            text="Original Font",
            width=200,
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=5)
        ctk.CTkLabel(
            header,
            text="Replacement Font",
            width=300,
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=5)

        for font in sorted(fonts_found):
            row = ctk.CTkFrame(self.font_editor_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(row, text=font, width=200, anchor="w").pack(
                side="left", padx=5
            )

            var = ctk.StringVar(value=font)
            combo = ctk.CTkComboBox(
                row, variable=var, values=self.common_fonts, width=300
            )
            combo.pack(side="left", padx=5)
            self.font_mapping_vars[font] = var

            entry_widget = getattr(combo, "_entry", combo)
            entry_widget.bind(
                "<KeyRelease>", lambda e, c=combo: self.update_font_dropdown(c)
            )

        self.log(f"Scan complete. Found {len(fonts_found)} unique font(s).")

    def update_font_dropdown(self, combo):
        entry = getattr(combo, "_entry", None)
        typed = entry.get().lower() if entry else combo.get().lower()
        if not typed:
            combo.configure(values=self.common_fonts)
        else:
            filtered = [f for f in self.common_fonts if typed in f.lower()]
            combo.configure(values=filtered if filtered else self.common_fonts)

    def set_ui_state(self, state):
        for widget in self.editable_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def update_progress(self, current, total):
        if total > 0:
            self.progress_bar.set(current / total)
        else:
            self.progress_bar.set(0)
        self.progress_label.configure(text=f"Progress: {current}/{total}")

    def find_executable(self, name):
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.resolve() / "tools"

        for ext in ([".exe", ""] if sys.platform == "win32" else [""]):
            candidate = base_path / f"{name}{ext}"
            if candidate.exists():
                return str(candidate)
        return shutil.which(name)

    def browse_dir(self, var):
        initial = var.get()
        if not initial or not Path(initial).exists():
            initial = str(Path(".").resolve())
        elif Path(initial).is_file():
            initial = str(Path(initial).parent)
        dir_path = filedialog.askdirectory(initialdir=initial)
        if dir_path:
            var.set(dir_path)

    def browse_file(self, var, ftype):
        initial = var.get()
        if not initial or not Path(initial).exists():
            initial = self.video_dir_var.get()
            if not initial or not Path(initial).exists():
                initial = str(Path(".").resolve())
        elif Path(initial).is_file():
            initial = str(Path(initial).parent)
        filetypes = (
            [
                ("Video files", "*.mkv *.mp4 *.m4v *.mov *.avi *.webm"),
                ("All files", "*.*"),
            ]
            if ftype == "Video"
            else (
                [
                    ("Subtitle files", "*.ass *.ssa *.srt *.vtt *.sub"),
                    ("All files", "*.*"),
                ]
                if ftype == "Subtitle"
                else [("All files", "*.*")]
            )
        )
        file_path = filedialog.askopenfilename(initialdir=initial, filetypes=filetypes)
        if file_path:
            var.set(file_path)

    def on_mode_change(self, value):
        self.batch_ui.pack_forget()
        self.single_ui.pack_forget()
        self.copy_subs_ui.pack_forget()
        self.remove_subs_ui.pack_forget()
        self.edit_fonts_ui.pack_forget()
        self.download_fonts_ui.pack_forget()

        self.settings_card.pack_forget()
        self.jump_card.pack_forget()

        if value == "Batch Mode":
            self.batch_ui.pack(fill="x", pady=(0, 10))
        elif value == "Single File":
            self.single_ui.pack(fill="x", pady=(0, 10))
        elif value == "Copy Subtitles":
            self.copy_subs_ui.pack(fill="x", pady=(0, 10))
        elif value == "Remove Subtitles":
            self.remove_subs_ui.pack(fill="x", pady=(0, 10))
        elif value == "Edit Fonts":
            self.edit_fonts_ui.pack(fill="x", pady=(0, 10))
        elif value == "Download Fonts":
            self.download_fonts_ui.pack(fill="x", pady=(0, 10))

        if value not in [
            "Edit Fonts",
            "Remove Subtitles",
            "Copy Subtitles",
            "Download Fonts",
        ]:
            self.settings_card.pack(fill="x", padx=10, pady=10, before=self.ctrl_frame)
            self.jump_card.pack(fill="x", padx=10, pady=10, before=self.ctrl_frame)

    def toggle_jump_points(self):
        if self.add_jump_points_var.get():
            self.jp_input_frame.pack(fill="x", padx=15, pady=(5, 0))
            self.jp_list_frame.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        else:
            self.jp_input_frame.pack_forget()
            self.jp_list_frame.pack_forget()
            self.clear_jump_points()

    def add_jump_point(self):
        title = self.jp_title_entry.get().strip()
        hh, mm, ss = (
            self.jp_hh_entry.get().strip(),
            self.jp_mm_entry.get().strip(),
            self.jp_ss_entry.get().strip(),
        )
        if not title:
            self.log("Warning: Chapter title cannot be empty.")
            return
        h = int(hh) if hh.isdigit() else 0
        m = int(mm) if mm.isdigit() else 0
        try:
            s_float = float(ss) if ss else 0.0
            if s_float >= 60.0:
                self.log("Warning: Seconds cannot exceed 59.999.")
                return
            s_int, ms_frac = int(s_float), int(round((s_float - int(s_float)) * 1000))
        except ValueError:
            self.log("Warning: Invalid seconds format.")
            return
        if m >= 60:
            self.log("Warning: Minutes cannot exceed 59.")
            return
        ms = (h * 3600 + m * 60 + s_int) * 1000 + ms_frac
        time_str = f"{h:02d}:{m:02d}:{s_int:02d}.{ms_frac:03d}"

        row_frame = ctk.CTkFrame(self.jp_list_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(
            row_frame, text=f"• {title} ({time_str})", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=10)
        del_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=30,
            height=24,
            corner_radius=12,
            fg_color="#D9534F",
            hover_color="#C9302C",
        )
        del_btn.pack(side="right", padx=10)

        jp_data = {"title": title, "ms": ms, "row_frame": row_frame, "del_btn": del_btn}
        self.jump_points.append(jp_data)
        del_btn.configure(command=lambda: self.delete_jump_point(jp_data))
        self.editable_widgets.append(del_btn)

        self.jp_title_entry.delete(0, "end")
        self.jp_hh_entry.delete(0, "end")
        self.jp_mm_entry.delete(0, "end")
        self.jp_ss_entry.delete(0, "end")
        self.jp_title_entry.focus()

    def delete_jump_point(self, jp_data):
        self.jump_points.remove(jp_data)
        if jp_data["del_btn"] in self.editable_widgets:
            self.editable_widgets.remove(jp_data["del_btn"])
        jp_data["row_frame"].destroy()

    def clear_jump_points(self):
        for jp in self.jump_points:
            if jp["del_btn"] in self.editable_widgets:
                self.editable_widgets.remove(jp["del_btn"])
            jp["row_frame"].destroy()
        self.jump_points.clear()

    def insert_template_var(self, text):
        self.output_template_entry.focus()
        self.output_template_entry.insert(tk.INSERT, text)

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def log(self, message):
        def update():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.after(0, update)

    def cancel_muxing(self):
        self.cancel_event.set()
        self.cancel_btn.configure(state="disabled")
        self.log(
            "\n[CANCEL] Requested cancellation... Please wait for the current process to terminate."
        )

    def start_muxing(self):
        mode = self.mode_var.get()
        if mode not in ["Edit Fonts", "Download Fonts"]:
            if not self.ffmpeg_path or not self.ffprobe_path:
                self.log(
                    "\n[ERROR] Cannot start operation. ffmpeg or ffprobe is missing."
                )
                return

        self.cancel_event.clear()

        self.set_ui_state("disabled")
        self.cancel_btn.configure(state="normal")

        self.progress_bar.set(0)
        self.progress_label.configure(text="Progress: 0/0")
        self.progress_frame.pack(fill="x", padx=10, pady=(0, 10), before=self.log_card)

        self.log("=" * 50)
        self.log("Starting operation...")
        threading.Thread(target=self.run_muxing_thread, daemon=True).start()

    def run_muxing_thread(self):
        try:
            self.run_muxing_logic()
        except FileNotFoundError:
            self.log(
                "\n[ERROR] 'ffmpeg' or 'ffprobe' command not found during execution."
            )
        except Exception as e:
            self.log(f"\n[CRITICAL ERROR] An unexpected error occurred: {e}")
        finally:
            self.after(0, lambda: self.set_ui_state("normal"))
            self.after(0, lambda: self.cancel_btn.configure(state="disabled"))
            self.after(0, self.progress_frame.pack_forget)

    def run_muxing_logic(self):
        ffmpeg_path, ffprobe_path = self.ffmpeg_path, self.ffprobe_path
        mode = self.mode_var.get()
        is_batch = mode == "Batch Mode"
        is_copy_subs = mode == "Copy Subtitles"
        is_remove_subs = mode == "Remove Subtitles"
        is_edit_fonts = mode == "Edit Fonts"
        is_download_fonts = mode == "Download Fonts"

        VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".mov", ".avi", ".webm"}
        MUX_TAG = "universal_mux_v1"

        def extract_episode(name):
            for p in [
                r"(?i)s\d+e(\d+)",
                r"(?i)(\d+)x(\d+)",
                r"(?i)(?:ep|episode)[\s._-]*(\d+)",
                r"(?i)(?:^|[\s._-])(\d{1,3})(?:$|[\s._-])",
            ]:
                m = re.search(p, name)
                if m:
                    return int(
                        m.group(2)
                        if len(m.groups()) >= 2 and m.group(2)
                        else m.group(1)
                    )
            nums = re.findall(r"(?<!\d)(\d{1,3})(?!\d)", name)
            return int(nums[-1]) if nums else None

        def is_already_muxed(path):
            if self.cancel_event.is_set():
                return False
            try:
                res = subprocess.run(
                    [
                        ffprobe_path,
                        "-v",
                        "error",
                        "-show_entries",
                        "format_tags=muxed_by",
                        "-of",
                        "default=nk=1:nw=1",
                        str(path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    creationflags=CREATE_NO_WINDOW,
                )
                return res.stdout.strip() == MUX_TAG
            except:
                return False

        def get_duration(path):
            if self.cancel_event.is_set():
                return None
            cmd = [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    creationflags=CREATE_NO_WINDOW,
                )
                return float(res.stdout.strip())
            except:
                return None

        def has_subtitles(path):
            if self.cancel_event.is_set():
                return False
            cmd = [
                ffprobe_path,
                "-v",
                "error",
                "-select_streams",
                "s",
                "-show_entries",
                "stream=index",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    creationflags=CREATE_NO_WINDOW,
                )
                return bool(res.stdout.strip())
            except:
                return False

        # --- Copy Subtitles Mode Logic ---
        if is_copy_subs:
            source_dir = Path(self.source_sub_dir_var.get())
            target_dir = Path(self.target_sub_dir_var.get())

            if not source_dir.exists() or not target_dir.exists():
                self.log("[ERROR] Source or Target directory does not exist.")
                return

            source_files = {
                p.stem: p
                for p in source_dir.iterdir()
                if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
            }
            target_files = {
                p.stem: p
                for p in target_dir.iterdir()
                if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
            }

            matched_stems = set(source_files.keys()) & set(target_files.keys())

            if not matched_stems:
                self.log(
                    "No matching video filenames found between the two directories."
                )
                return

            self.log(f"Found {len(matched_stems)} matching video pairs.\n")
            total_items = len(matched_stems)
            self.after(0, self.update_progress, 0, total_items)

            success_count = 0
            for i, stem in enumerate(sorted(matched_stems)):
                if self.cancel_event.is_set():
                    self.log("\n[CANCELLED] Operation cancelled by user.")
                    break

                self.after(0, self.update_progress, i + 1, total_items)

                v_source = source_files[stem]
                v_target = target_files[stem]

                self.log(f"Checking: {stem}")

                if not has_subtitles(v_source):
                    self.log(f"  [SKIP] Source video has no subtitle tracks.")
                    continue

                dur_source = get_duration(v_source)
                dur_target = get_duration(v_target)

                if dur_source is None or dur_target is None:
                    self.log(f"  [ERROR] Could not determine duration. Skipping.")
                    continue

                if abs(dur_source - dur_target) > 1.5:  # 1.5 second tolerance
                    self.log(
                        f"  [SKIP] Duration mismatch! Source: {dur_source:.2f}s, Target: {dur_target:.2f}s"
                    )
                    continue

                self.log(f"  Durations match ({dur_target:.2f}s). Copying subtitles...")

                temp_out = target_dir / f".mux_{v_target.stem}.mkv"
                final_out = target_dir / f"{v_target.stem}.mkv"

                cmd = [
                    ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "warning",
                    "-y",
                    "-i",
                    str(v_source),  # Input 0: Source (with subs)
                    "-i",
                    str(v_target),  # Input 1: Target (without subs)
                    "-map",
                    "1:v",  # Video from target
                    "-map",
                    "1:a?",  # Audio from target
                    "-map",
                    "0:s?",  # Subtitles from source
                    "-c",
                    "copy",  # Copy all codecs
                    "-disposition:s:0",
                    "default",
                    str(temp_out),
                ]

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                cancelled = False
                while process.poll() is None:
                    if self.cancel_event.is_set():
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        cancelled = True
                        break
                    time.sleep(0.2)

                if cancelled:
                    self.log(f"  [CANCELLED] Stopped by user.")
                    if temp_out.exists():
                        temp_out.unlink()
                    break

                if process.returncode != 0:
                    self.log(f"  [FAILED] FFmpeg error.")
                    stderr = process.stderr.read()
                    if stderr:
                        for line in stderr.strip().split("\n")[:3]:
                            self.log(f"    {line}")
                    if temp_out.exists():
                        temp_out.unlink()
                else:
                    if final_out.exists() and final_out.resolve() != v_target.resolve():
                        final_out.unlink()
                    v_target.unlink()
                    temp_out.replace(final_out)
                    self.log(f"  [DONE] Successfully copied subtitles.")
                    success_count += 1

            if not self.cancel_event.is_set():
                self.log(
                    f"\nFinished! Successfully processed {success_count} out of {len(matched_stems)} pairs."
                )
            return

        # --- Remove Subtitles Mode Logic ---
        if is_remove_subs:
            video_dir = Path(self.video_dir_var.get())
            if not video_dir.exists():
                self.log("[ERROR] Video directory does not exist.")
                return

            video_files = sorted(
                [
                    p
                    for p in video_dir.iterdir()
                    if p.is_file()
                    and p.suffix.lower() in VIDEO_EXTENSIONS
                    and not p.name.startswith("temp_")
                    and not p.name.startswith(".mux_")
                ],
                key=lambda p: p.name.lower(),
            )

            if not video_files:
                self.log("No video files found.")
                return

            self.log(f"Found {len(video_files)} video(s) to process.\n")
            total_items = len(video_files)
            self.after(0, self.update_progress, 0, total_items)

            success_count = 0
            for i, video in enumerate(video_files):
                if self.cancel_event.is_set():
                    self.log("\n[CANCELLED] Operation cancelled by user.")
                    break

                self.after(0, self.update_progress, i + 1, total_items)

                if not has_subtitles(video):
                    self.log(f"[SKIP] {video.name} has no subtitle tracks.")
                    continue

                self.log(f"Removing subtitles from: {video.name}")

                temp_out = video_dir / f".mux_{video.stem}{video.suffix}"
                final_out = video_dir / f"{video.stem}{video.suffix}"

                cmd = [
                    ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "warning",
                    "-y",
                    "-i",
                    str(video),
                    "-map",
                    "0:v",
                    "-map",
                    "0:a?",
                    "-map",
                    "0:t?",  # Keep attachments like fonts
                    "-c",
                    "copy",
                    str(temp_out),
                ]

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                cancelled = False
                while process.poll() is None:
                    if self.cancel_event.is_set():
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        cancelled = True
                        break
                    time.sleep(0.2)

                if cancelled:
                    self.log(f"[CANCELLED] Stopped by user.")
                    if temp_out.exists():
                        temp_out.unlink()
                    break

                if process.returncode != 0:
                    self.log(f"[FAILED] FFmpeg error.")
                    stderr = process.stderr.read()
                    if stderr:
                        for line in stderr.strip().split("\n")[:3]:
                            self.log(f"  {line}")
                    if temp_out.exists():
                        temp_out.unlink()
                else:
                    if final_out.exists() and final_out.resolve() != video.resolve():
                        final_out.unlink()
                    video.unlink()
                    temp_out.replace(final_out)
                    self.log(f"[DONE] Successfully removed subtitles.")
                    success_count += 1

            if not self.cancel_event.is_set():
                self.log(
                    f"\nFinished! Successfully processed {success_count} out of {len(video_files)} videos."
                )
            return

        # --- Edit Fonts Mode Logic ---
        if is_edit_fonts:
            source_type = self.edit_type_var.get()

            font_map = {orig: var.get() for orig, var in self.font_mapping_vars.items()}

            if not font_map:
                self.log(
                    "[ERROR] No font mappings found. Please scan the subtitles first."
                )
                return

            sub_files = []
            if source_type == "Folder":
                sub_dir = Path(self.edit_sub_dir_var.get())
                if not sub_dir.exists():
                    self.log("[ERROR] Subtitle directory does not exist.")
                    return
                sub_files = [
                    p
                    for p in sub_dir.rglob("*")
                    if p.is_file() and p.suffix.lower() in {".ass", ".ssa"}
                ]
            else:
                sub_file = Path(self.edit_single_sub_var.get().strip())
                if not sub_file.exists():
                    self.log("[ERROR] Subtitle file does not exist.")
                    return
                if sub_file.suffix.lower() in {".ass", ".ssa"}:
                    sub_files = [sub_file]
                else:
                    self.log(
                        "[ERROR] Only .ass and .ssa files are supported for font editing."
                    )
                    return

            if not sub_files:
                self.log("No .ass or .ssa subtitle files found to edit.")
                return

            self.log(f"Found {len(sub_files)} subtitle file(s) to process.\n")
            total_items = len(sub_files)
            self.after(0, self.update_progress, 0, total_items)

            success_count = 0
            for i, sub_file in enumerate(sub_files):
                if self.cancel_event.is_set():
                    self.log("\n[CANCELLED] Operation cancelled by user.")
                    break

                self.after(0, self.update_progress, i + 1, total_items)
                self.log(f"Editing fonts in: {sub_file.name}")

                try:
                    content = ""
                    encoding_used = "utf-8-sig"
                    try:
                        with open(sub_file, "r", encoding="utf-8-sig") as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        try:
                            with open(sub_file, "r", encoding="cp1252") as f:
                                content = f.read()
                            encoding_used = "cp1252"
                        except Exception as e:
                            self.log(f"  [ERROR] Could not read file: {e}")
                            continue

                    lines = content.splitlines(True)
                    in_styles_section = False
                    modified = False
                    font_idx = -1

                    new_lines = []
                    for line in lines:
                        stripped = line.strip()
                        if stripped.startswith("[V4") or stripped.startswith("[V4+"):
                            in_styles_section = True
                            font_idx = -1
                            new_lines.append(line)
                            continue
                        elif stripped.startswith("[") and in_styles_section:
                            in_styles_section = False
                            new_lines.append(line)
                            continue

                        if in_styles_section:
                            if stripped.lower().startswith("format:"):
                                parts = [
                                    p.strip().lower() for p in stripped[7:].split(",")
                                ]
                                if "fontname" in parts:
                                    font_idx = parts.index("fontname")
                                new_lines.append(line)
                                continue
                            elif stripped.lower().startswith("style:"):
                                m = re.match(
                                    r"^(\s*Style:\s*)(.*?)(\r?\n?)$",
                                    line,
                                    re.IGNORECASE,
                                )
                                if m and font_idx != -1:
                                    prefix = m.group(1)
                                    values_str = m.group(2)
                                    newline = m.group(3)

                                    parts = values_str.split(",")

                                    if len(parts) > font_idx:
                                        orig_font = parts[font_idx].strip()
                                        if orig_font in font_map:
                                            new_font = font_map[orig_font]
                                            if orig_font != new_font:
                                                parts[font_idx] = parts[
                                                    font_idx
                                                ].replace(orig_font, new_font)
                                                new_line = (
                                                    prefix + ",".join(parts) + newline
                                                )
                                                new_lines.append(new_line)
                                                modified = True
                                                continue
                        new_lines.append(line)

                    if modified:
                        with open(sub_file, "w", encoding=encoding_used) as f:
                            f.writelines(new_lines)
                        self.log(f"  [DONE] Updated fonts based on mapping.")
                        success_count += 1
                    else:
                        self.log(
                            f"  [SKIP] No mapped fonts required updating in this file."
                        )

                except Exception as e:
                    self.log(f"  [ERROR] Failed to process file: {e}")

            if not self.cancel_event.is_set():
                self.log(
                    f"\nFinished! Successfully edited {success_count} out of {len(sub_files)} files."
                )
            return

        # --- Download Fonts Mode Logic ---
        if is_download_fonts:
            if not self.dl_font_vars:
                self.log("[ERROR] No fonts scanned. Please scan the subtitles first.")
                return

            fonts_to_download = [
                font for font, var in self.dl_font_vars.items() if var.get()
            ]
            if not fonts_to_download:
                self.log("[ERROR] No fonts selected for download.")
                return

            out_dir = Path(self.download_out_dir_var.get())

            if not out_dir.exists():
                try:
                    out_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.log(f"[ERROR] Could not create output directory: {e}")
                    return

            self.log(f"Preparing to download {len(fonts_to_download)} font(s).\n")
            total_items = len(fonts_to_download)
            self.after(0, self.update_progress, 0, total_items)

            success_count = 0
            failed_fonts = []

            def parse_font_for_google_fonts(font_name):
                font_name = font_name.strip()
                weights = {
                    "thin": 100,
                    "hairline": 100,
                    "extralight": 200,
                    "ultralight": 200,
                    "light": 300,
                    "regular": 400,
                    "normal": 400,
                    "medium": 500,
                    "semibold": 600,
                    "demibold": 600,
                    "bold": 700,
                    "extrabold": 800,
                    "ultrabold": 800,
                    "black": 900,
                    "heavy": 900,
                }
                name_lower = font_name.lower()
                for w_name, w_val in sorted(
                    weights.items(), key=lambda x: len(x[0]), reverse=True
                ):
                    if name_lower.endswith(f" {w_name}"):
                        family = font_name[: -(len(w_name) + 1)].strip()
                        return family, w_val
                    elif name_lower.endswith(w_name) and len(font_name) > len(w_name):
                        if not font_name[-len(w_name) - 1].isalpha():
                            family = font_name[: -(len(w_name) + 1)].strip("-_ ")
                            return family, w_val
                return font_name, 400

            for i, font_name in enumerate(sorted(fonts_to_download)):
                if self.cancel_event.is_set():
                    self.log("\n[CANCELLED] Operation cancelled by user.")
                    break

                self.after(0, self.update_progress, i + 1, total_items)

                family, wght = parse_font_for_google_fonts(font_name)
                self.log(
                    f"Searching for: {font_name} (Family: {family}, Weight: {wght})"
                )

                family_url = urllib.parse.quote(family)
                url = f"https://fonts.googleapis.com/css?family={family_url}:{wght}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/531.21.8 (KHTML, like Gecko) Version/4.0.4 Safari/531.21.10"
                }

                try:
                    req = urllib.request.Request(url, headers=headers)
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE

                    with urllib.request.urlopen(
                        req, context=ctx, timeout=10
                    ) as response:
                        css_content = response.read().decode("utf-8")

                    if not css_content or "@font-face" not in css_content:
                        url_fallback = (
                            f"https://fonts.googleapis.com/css?family={family_url}"
                        )
                        req = urllib.request.Request(url_fallback, headers=headers)
                        with urllib.request.urlopen(
                            req, context=ctx, timeout=10
                        ) as response:
                            css_content = response.read().decode("utf-8")

                    urls = re.findall(r"url\((.*?)\)", css_content)
                    if not urls:
                        self.log(f"  [FAILED] Could not extract font URL from CSS.")
                        failed_fonts.append(font_name)
                        continue

                    font_url = urls[0]
                    ext = font_url.split(".")[-1]
                    if "?" in ext:
                        ext = ext.split("?")[0]
                    if len(ext) > 5 or not ext.isalnum():
                        ext = "ttf"
                    safe_filename = re.sub(r'[\\/*?:"<>|]', "", font_name) + f".{ext}"
                    out_path = out_dir / safe_filename

                    if out_path.exists():
                        self.log(f"  [SKIP] {safe_filename} already exists.")
                        success_count += 1
                        continue

                    req_font = urllib.request.Request(font_url)
                    with urllib.request.urlopen(
                        req_font, context=ctx, timeout=15
                    ) as font_res:
                        font_data = font_res.read()

                    with open(out_path, "wb") as f:
                        f.write(font_data)
                    self.log(f"  [DONE] Saved as {safe_filename}")
                    success_count += 1

                except urllib.error.HTTPError as e:
                    self.log(f"  [FAILED] HTTP Error {e.code}: {e.reason}")
                    failed_fonts.append(font_name)
                except Exception as e:
                    self.log(f"  [ERROR] Network exception: {e}")
                    failed_fonts.append(font_name)

            if not self.cancel_event.is_set():
                self.log(
                    f"\nFinished! Successfully downloaded {success_count} out of {len(fonts_to_download)} fonts."
                )
                if failed_fonts:
                    self.log(f"Could not download: {', '.join(sorted(failed_fonts))}")
            return

        # --- Standard Muxing Logic (Batch & Single) ---
        VIDEO_DIR = (
            Path(self.video_dir_var.get())
            if is_batch
            else (
                Path(self.single_video_var.get().strip()).parent
                if self.single_video_var.get().strip()
                else Path(self.video_dir_var.get())
            )
        )
        SUB_DIR = Path(self.sub_dir_var.get()) if is_batch else None
        FONT_DIR = Path(self.font_dir_var.get())
        SUB_EXTENSIONS = {".ass", ".ssa", ".srt", ".vtt", ".sub"}
        SUB_PREFERENCE = {".ass": 0, ".ssa": 1, ".srt": 2, ".vtt": 3, ".sub": 4}

        series_name = self.series_name_var.get().strip()
        output_template = self.output_template_var.get().strip()
        jump_points_data = self.jump_points if self.add_jump_points_var.get() else []

        chapter_file = None
        if jump_points_data:
            self.log("Processing jump points...")
            jump_points_data = sorted(jump_points_data, key=lambda x: x["ms"])
            chapter_file = VIDEO_DIR / ".jump_points.ffmeta"
            text = ";FFMETADATA1\n"
            for i, jp in enumerate(jump_points_data):
                end_ms = (
                    jump_points_data[i + 1]["ms"]
                    if i + 1 < len(jump_points_data)
                    else 999999999
                )
                text += f"\n[CHAPTER]\nTIMEBASE=1/1000\nSTART={jp['ms']}\nEND={end_ms}\ntitle={jp['title']}\n"
            chapter_file.write_text(text, encoding="utf-8")

        fonts = (
            sorted(
                [
                    f
                    for f in FONT_DIR.iterdir()
                    if f.is_file() and f.suffix.lower() in {".ttf", ".otf", ".ttc"}
                ],
                key=lambda p: p.name.lower(),
            )
            if FONT_DIR.exists()
            else []
        )
        paired = []

        if is_batch:
            if not VIDEO_DIR.exists():
                self.log(f"[ERROR] Video directory does not exist: {VIDEO_DIR}")
                return
            video_files = sorted(
                [
                    p
                    for p in VIDEO_DIR.iterdir()
                    if p.is_file()
                    and p.suffix.lower() in VIDEO_EXTENSIONS
                    and p.name != "test.mkv"
                    and not p.name.startswith("temp_")
                    and not p.name.startswith(".mux_")
                ],
                key=lambda p: p.name.lower(),
            )
            subtitle_files = (
                sorted(
                    [
                        p
                        for p in SUB_DIR.rglob("*")
                        if p.is_file() and p.suffix.lower() in SUB_EXTENSIONS
                    ],
                    key=lambda p: (
                        SUB_PREFERENCE.get(p.suffix.lower(), 99),
                        p.name.lower(),
                    ),
                )
                if SUB_DIR and SUB_DIR.exists()
                else []
            )
            if not video_files:
                self.log("No video files found.")
                return
            video_by_ep, video_order = {}, []
            for v in video_files:
                if self.cancel_event.is_set():
                    break
                if is_already_muxed(v):
                    continue
                ep = extract_episode(v.stem)
                video_order.append((v, ep))
                if ep is not None and ep not in video_by_ep:
                    video_by_ep[ep] = v
            subtitle_by_ep, subtitle_order = {}, []
            for s in subtitle_files:
                if self.cancel_event.is_set():
                    break
                ep = extract_episode(s.stem)
                subtitle_order.append((s, ep))
                if ep is not None:
                    cur = subtitle_by_ep.get(ep)
                    if not cur or (
                        SUB_PREFERENCE.get(s.suffix.lower(), 99),
                        s.name.lower(),
                    ) < (SUB_PREFERENCE.get(cur.suffix.lower(), 99), cur.name.lower()):
                        subtitle_by_ep[ep] = s
            used_v, used_s = set(), set()
            for ep in sorted(set(video_by_ep) & set(subtitle_by_ep)):
                if self.cancel_event.is_set():
                    break
                paired.append((video_by_ep[ep], subtitle_by_ep[ep], ep))
                used_v.add(video_by_ep[ep])
                used_s.add(subtitle_by_ep[ep])
            rem_v = sorted(
                [v for v, _ in video_order if v not in used_v],
                key=lambda p: p.name.lower(),
            )
            rem_s = sorted(
                [s for s, _ in subtitle_order if s not in used_s],
                key=lambda p: (
                    SUB_PREFERENCE.get(p.suffix.lower(), 99),
                    p.name.lower(),
                ),
            )
            if not paired and len(rem_v) == len(rem_s) and rem_v:
                for i, v in enumerate(rem_v):
                    if self.cancel_event.is_set():
                        break
                    paired.append((v, rem_s[i], i + 1))
        else:
            vp, sp = (
                self.single_video_var.get().strip(),
                self.single_sub_var.get().strip(),
            )
            if not vp or not sp:
                self.log("[ERROR] Please select both a video and subtitle file.")
                return
            v, s = Path(vp), Path(sp)
            if not v.exists() or not s.exists():
                self.log("[ERROR] Selected file does not exist.")
                return
            paired = [(v, s, extract_episode(v.stem) or 1)]

        paired.sort(key=lambda x: (x[2], x[0].name.lower()))
        if not paired:
            self.log("No matching episodes found.")
            return
        if self.cancel_event.is_set():
            return  # Cancelled during pairing

        # --- Font Verification Check ---
        sub_files_to_check = [s for v, s, ep in paired]
        fonts_needed = set()

        for sub_file in sub_files_to_check:
            if sub_file.suffix.lower() not in {".ass", ".ssa"}:
                continue
            try:
                content = sub_file.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                try:
                    content = sub_file.read_text(encoding="cp1252", errors="ignore")
                except Exception:
                    continue

            in_styles = False
            font_idx = -1
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("[V4") or stripped.startswith("[V4+"):
                    in_styles = True
                    font_idx = -1
                    continue
                if stripped.startswith("[") and in_styles:
                    in_styles = False
                    continue

                if in_styles:
                    if stripped.lower().startswith("format:"):
                        parts = [p.strip().lower() for p in stripped[7:].split(",")]
                        if "fontname" in parts:
                            font_idx = parts.index("fontname")
                    elif stripped.lower().startswith("style:"):
                        if font_idx != -1:
                            parts = [p.strip() for p in stripped[6:].split(",")]
                            if len(parts) > font_idx:
                                fonts_needed.add(parts[font_idx])

        if fonts_needed:

            def normalize_font_name(name):
                return re.sub(r"[^a-z0-9]", "", name.lower())

            available_normalized = set()
            for f in fonts:
                available_normalized.add(normalize_font_name(f.stem))

            missing_fonts = set()
            for needed in fonts_needed:
                needed_norm = normalize_font_name(needed)
                found = False
                for avail in available_normalized:
                    if needed_norm in avail or avail in needed_norm:
                        found = True
                        break
                if not found:
                    missing_fonts.add(needed)

            if missing_fonts:
                missing_list = "\n".join(sorted(missing_fonts))
                msg = f"The following fonts required by the subtitles were not found in the Font Directory:\n\n{missing_list}\n\nDo you want to proceed anyway?"
                if not self.ask_confirmation("Missing Fonts", msg):
                    self.log(
                        "\n[ABORTED] Operation cancelled by user due to missing fonts."
                    )
                    return

        self.log(f"Found {len(fonts)} font(s)\nMatched {len(paired)} item(s)\n")

        total_items = len(paired)
        self.after(0, self.update_progress, 0, total_items)

        for i, (video, subtitle, ep) in enumerate(paired):
            if self.cancel_event.is_set():
                self.log("\n[CANCELLED] Operation cancelled by user.")
                break

            self.after(0, self.update_progress, i + 1, total_items)

            try:
                out_name = (
                    output_template.format(
                        series=series_name,
                        ep=ep,
                        ep2=f"{ep:02d}",
                        video_stem=video.stem,
                    ).strip()
                    if output_template
                    else f"{series_name} EP{ep:02d}" if series_name else video.stem
                )
            except KeyError as e:
                self.log(f"[ERROR] Unknown template variable: {e}")
                out_name = video.stem
            if not out_name.lower().endswith(".mkv"):
                out_name += ".mkv"
            final_out, temp_out = (
                VIDEO_DIR / out_name,
                VIDEO_DIR / f".mux_{video.stem}.mkv",
            )
            cmd = [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "warning",
                "-y",
                "-i",
                str(video),
                "-i",
                str(subtitle),
            ]
            if chapter_file:
                cmd += ["-i", str(chapter_file)]
            cmd += [
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-map",
                "1:0",
                "-map_metadata",
                "0",
            ]
            if chapter_file:
                cmd += ["-map_chapters", "2"]
            cmd += [
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-c:s",
                "ass",
                "-disposition:s:0",
                "default",
                "-metadata:s:s:0",
                "language=eng",
                "-metadata:s:s:0",
                "title=English",
                "-metadata",
                f"muxed_by={MUX_TAG}",
            ]
            for idx, font in enumerate(fonts):
                mime = (
                    "application/vnd.ms-opentype"
                    if font.suffix.lower() == ".otf"
                    else "application/x-truetype-font"
                )
                cmd += [
                    "-attach",
                    str(font),
                    f"-metadata:s:t:{idx}",
                    f"mimetype={mime}",
                    f"-metadata:s:t:{idx}",
                    f"filename={font.name}",
                ]
            cmd.append(str(temp_out))

            self.log(f"[EP{ep:02d}] Processing: {video.name} + {subtitle.name}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=CREATE_NO_WINDOW,
            )
            cancelled = False
            while process.poll() is None:
                if self.cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    cancelled = True
                    break
                time.sleep(0.2)

            if cancelled:
                self.log(f"[EP{ep:02d}] Cancelled by user.")
                if temp_out.exists():
                    temp_out.unlink()
                break

            if process.returncode != 0:
                self.log(f"[EP{ep:02d}] Failed!")
                stderr = process.stderr.read()
                if stderr:
                    for line in stderr.strip().split("\n")[:3]:
                        self.log(f"  FFmpeg Error: {line}")
                if temp_out.exists():
                    temp_out.unlink()
            else:
                if final_out.exists() and final_out.resolve() != video.resolve():
                    final_out.unlink()
                if temp_out.exists():
                    video.unlink()
                    temp_out.replace(final_out)
                self.log(f"[EP{ep:02d}] Done.")

        if chapter_file and chapter_file.exists():
            chapter_file.unlink()
        if not self.cancel_event.is_set():
            self.log("\nAll operations completed successfully.")


if __name__ == "__main__":
    app = MuxerApp()
    app.mainloop()
