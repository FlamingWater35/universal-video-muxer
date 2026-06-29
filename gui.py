import customtkinter as ctk
from pathlib import Path
import subprocess
import re
import threading
import shutil
import sys
import tkinter as tk
from tkinter import filedialog

# --- Set CustomTkinter Appearance ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class MuxerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal Video Muxer")
        self.geometry("850x850")
        self.minsize(700, 600)

        # --- Main Scrollable Container ---
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Helper: Clearable Entry Widget ---
        def make_clearable_entry(parent, var, width=200):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            entry = ctk.CTkEntry(frame, textvariable=var, width=width)
            entry.pack(side="left", fill="x", expand=True)

            clear_btn = ctk.CTkButton(
                frame,
                text="✕",
                width=20,
                height=20,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray40", "gray50"),
                command=lambda: var.set(""),
                corner_radius=10,
            )
            clear_btn.pack(side="left", padx=(2, 0))
            return frame, entry

        # --- Helper: Directory Row ---
        def create_dir_row(parent, label_text, var):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(
                side="left", padx=(10, 5)
            )
            entry_frame, _ = make_clearable_entry(row, var)
            entry_frame.pack(side="left", fill="x", expand=True, padx=5)
            ctk.CTkButton(
                row, text="Browse", width=80, command=lambda: self.browse_dir(var)
            ).pack(side="left", padx=(5, 10))

        # --- Helper: File Row ---
        def create_file_row(parent, label_text, var, ftype):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(
                side="left", padx=(10, 5)
            )
            entry_frame, _ = make_clearable_entry(row, var)
            entry_frame.pack(side="left", fill="x", expand=True, padx=5)
            ctk.CTkButton(
                row,
                text="Browse",
                width=80,
                command=lambda: self.browse_file(var, ftype),
            ).pack(side="left", padx=(5, 10))

        # --- Variables ---
        base_dir = str(Path(".").resolve())
        self.video_dir_var = ctk.StringVar(value=base_dir)
        self.sub_dir_var = ctk.StringVar(value=str(Path(base_dir) / "sub"))
        self.font_dir_var = ctk.StringVar(value=str(Path(base_dir) / "sub" / "font"))
        self.single_video_var = ctk.StringVar()
        self.single_sub_var = ctk.StringVar()
        self.series_name_var = ctk.StringVar()
        self.output_template_var = ctk.StringVar()
        self.mode_var = ctk.StringVar(value="Batch Mode")
        self.add_jump_points_var = ctk.BooleanVar(value=False)

        # --- Mode Selection Frame ---
        mode_frame = ctk.CTkFrame(self.main_scroll)
        mode_frame.pack(fill="x", padx=15, pady=(15, 10))
        self.mode_switch = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Batch Mode", "Single File Mode"],
            variable=self.mode_var,
            command=self.on_mode_change,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.mode_switch.pack(pady=10)

        # --- Source Frame (Directories / Files) ---
        self.source_frame = ctk.CTkFrame(self.main_scroll)
        self.source_frame.pack(fill="x", padx=15, pady=5)

        self.batch_ui = ctk.CTkFrame(self.source_frame, fg_color="transparent")
        create_dir_row(self.batch_ui, "Video Directory:", self.video_dir_var)
        create_dir_row(self.batch_ui, "Subtitle Directory:", self.sub_dir_var)

        self.single_ui = ctk.CTkFrame(self.source_frame, fg_color="transparent")
        create_file_row(self.single_ui, "Video File:", self.single_video_var, "Video")
        create_file_row(
            self.single_ui, "Subtitle File:", self.single_sub_var, "Subtitle"
        )
        self.batch_ui.pack(fill="x")

        # --- Font Directory (Shared) ---
        font_frame = ctk.CTkFrame(self.main_scroll)
        font_frame.pack(fill="x", padx=15, pady=5)
        create_dir_row(font_frame, "Font Directory (Optional):", self.font_dir_var)

        # --- Settings Frame ---
        settings_frame = ctk.CTkFrame(self.main_scroll)
        settings_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(settings_frame, text="Series Name (Optional):").pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        series_frame, _ = make_clearable_entry(
            settings_frame, self.series_name_var, width=550
        )
        series_frame.pack(anchor="w", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            settings_frame, text="Output Template (Optional, e.g., {series} EP{ep2}):"
        ).pack(anchor="w", padx=10, pady=(10, 0))
        template_frame, self.output_template_entry = make_clearable_entry(
            settings_frame, self.output_template_var, width=550
        )
        template_frame.pack(anchor="w", padx=10, pady=(0, 5))

        var_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        var_frame.pack(anchor="w", padx=10, pady=(0, 10))
        for var in ["{series}", "{ep}", "{ep2}", "{video_stem}"]:
            btn = ctk.CTkButton(
                var_frame,
                text=var,
                width=90,
                height=28,
                command=lambda v=var: self.insert_template_var(v),
            )
            btn.pack(side="left", padx=(0, 5))

        # --- Jump Points Frame ---
        self.jump_frame = ctk.CTkFrame(self.main_scroll)
        self.jump_frame.pack(fill="x", padx=15, pady=10)

        self.jump_switch = ctk.CTkSwitch(
            self.jump_frame,
            text="Add Jump Points (Chapters)",
            variable=self.add_jump_points_var,
            command=self.toggle_jump_points,
        )
        self.jump_switch.pack(anchor="w", padx=10, pady=(10, 5))

        self.jp_input_frame = ctk.CTkFrame(self.jump_frame, fg_color="transparent")
        ctk.CTkLabel(self.jp_input_frame, text="Title:").grid(
            row=0, column=0, padx=(0, 5), pady=5, sticky="e"
        )
        self.jp_title_entry = ctk.CTkEntry(self.jp_input_frame, width=250)
        self.jp_title_entry.grid(row=0, column=1, padx=(0, 15), pady=5)

        ctk.CTkLabel(self.jp_input_frame, text="Time:").grid(
            row=0, column=2, padx=(0, 5), pady=5, sticky="e"
        )
        self.jp_hh_entry = ctk.CTkEntry(
            self.jp_input_frame, width=40, placeholder_text="HH"
        )
        self.jp_hh_entry.grid(row=0, column=3, pady=5)
        ctk.CTkLabel(self.jp_input_frame, text=":").grid(row=0, column=4, padx=2)
        self.jp_mm_entry = ctk.CTkEntry(
            self.jp_input_frame, width=40, placeholder_text="MM"
        )
        self.jp_mm_entry.grid(row=0, column=5, pady=5)
        ctk.CTkLabel(self.jp_input_frame, text=":").grid(row=0, column=6, padx=2)
        self.jp_ss_entry = ctk.CTkEntry(
            self.jp_input_frame, width=50, placeholder_text="SS.ms"
        )
        self.jp_ss_entry.grid(row=0, column=7, pady=5)

        self.jp_add_btn = ctk.CTkButton(
            self.jp_input_frame,
            text="Add Chapter",
            width=120,
            command=self.add_jump_point,
        )
        self.jp_add_btn.grid(row=0, column=8, padx=(15, 0), pady=5)

        self.jp_list_frame = ctk.CTkScrollableFrame(self.jump_frame, height=140)
        self.jump_points = []

        # --- Control Frame ---
        ctrl_frame = ctk.CTkFrame(self.main_scroll)
        ctrl_frame.pack(fill="x", padx=15, pady=10)
        self.start_btn = ctk.CTkButton(
            ctrl_frame,
            text="Start Muxing",
            command=self.start_muxing,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_btn.pack(side="left", padx=10, pady=10)
        self.clear_btn = ctk.CTkButton(
            ctrl_frame, text="Clear Log", command=self.clear_log, width=100
        )
        self.clear_btn.pack(side="right", padx=10, pady=10)

        # --- Log Output Frame ---
        log_frame = ctk.CTkFrame(self.main_scroll)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        self.log_text = ctk.CTkTextbox(
            log_frame,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            height=150,
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # --- FFmpeg Detection ---
        self.ffmpeg_path = self.find_executable("ffmpeg")
        self.ffprobe_path = self.find_executable("ffprobe")

        if self.ffmpeg_path and self.ffprobe_path:
            self.log(f"Ready. Detected ffmpeg at: {self.ffmpeg_path}")
        else:
            self.log(
                "WARNING: ffmpeg or ffprobe not found in project root or system PATH!"
            )
            self.log(
                "Please place ffmpeg.exe and ffprobe.exe in the same folder as this script."
            )

    # --- Core Methods (Unchanged Logic) ---
    def find_executable(self, name):
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.resolve()
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
        if value == "Batch Mode":
            self.single_ui.pack_forget()
            self.batch_ui.pack(fill="x")
        else:
            self.batch_ui.pack_forget()
            self.single_ui.pack(fill="x")

    def toggle_jump_points(self):
        if self.add_jump_points_var.get():
            self.jp_input_frame.pack(fill="x", padx=10, pady=(5, 0))
            self.jp_list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
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
        ctk.CTkLabel(row_frame, text=f"{title} ({time_str})").pack(side="left", padx=10)
        del_btn = ctk.CTkButton(
            row_frame,
            text="Delete",
            width=60,
            fg_color="#D9534F",
            hover_color="#C9302C",
        )
        del_btn.pack(side="right", padx=10)
        jp_data = {"title": title, "ms": ms, "row_frame": row_frame, "del_btn": del_btn}
        self.jump_points.append(jp_data)
        del_btn.configure(command=lambda: self.delete_jump_point(jp_data))
        self.jp_title_entry.delete(0, "end")
        self.jp_hh_entry.delete(0, "end")
        self.jp_mm_entry.delete(0, "end")
        self.jp_ss_entry.delete(0, "end")
        self.jp_title_entry.focus()

    def delete_jump_point(self, jp_data):
        self.jump_points.remove(jp_data)
        jp_data["row_frame"].destroy()

    def clear_jump_points(self):
        for jp in self.jump_points:
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

    def start_muxing(self):
        if not self.ffmpeg_path or not self.ffprobe_path:
            self.log("\n[ERROR] Cannot start muxing. ffmpeg or ffprobe is missing.")
            return
        self.start_btn.configure(state="disabled")
        self.log("=" * 40)
        self.log("Starting muxing process...")
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
            self.after(0, lambda: self.start_btn.configure(state="normal"))

    def run_muxing_logic(self):
        ffmpeg_path, ffprobe_path = self.ffmpeg_path, self.ffprobe_path
        is_batch = self.mode_var.get() == "Batch Mode"
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
        VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".mov", ".avi", ".webm"}
        MUX_TAG = "universal_mux_v1"
        series_name = self.series_name_var.get().strip()
        output_template = self.output_template_var.get().strip()
        jump_points_data = self.jump_points if self.add_jump_points_var.get() else []

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
                )
                return res.stdout.strip() == MUX_TAG
            except:
                return False

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
                if is_already_muxed(v):
                    continue
                ep = extract_episode(v.stem)
                video_order.append((v, ep))
                if ep is not None and ep not in video_by_ep:
                    video_by_ep[ep] = v
            subtitle_by_ep, subtitle_order = {}, []
            for s in subtitle_files:
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
        self.log(f"Found {len(fonts)} font(s)\nMatched {len(paired)} item(s)\n")

        for video, subtitle, ep in paired:
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
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if final_out.exists() and final_out.resolve() != video.resolve():
                    final_out.unlink()
                if temp_out.exists():
                    video.unlink()
                    temp_out.replace(final_out)
                self.log(f"[EP{ep:02d}] Done.")
            except subprocess.CalledProcessError as e:
                self.log(f"[EP{ep:02d}] Failed!")
                if e.stderr:
                    for line in e.stderr.strip().split("\n")[:3]:
                        self.log(f"  FFmpeg Error: {line}")
                if temp_out.exists():
                    temp_out.unlink()
        if chapter_file and chapter_file.exists():
            chapter_file.unlink()
        self.log("\nAll operations completed successfully.")


if __name__ == "__main__":
    app = MuxerApp()
    app.mainloop()
