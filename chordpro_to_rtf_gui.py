"""ChordPro to RTF Converter - Tkinter GUI.

Extracts, from a ChordPro (.cho/.crd/.pro) file, two RTF documents:
  - a Lyrics file: words only, chords and tab/grid notation stripped
  - a Chords file: chord symbols only, words stripped
Section labels (verse/chorus/bridge/...) and comments are kept in both,
in bold / italic; lyrics and chords themselves are always plain (non-bold).
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from chordpro_parser import convert_file

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _BASE_CLASS = TkinterDnD.Tk
    _DND_AVAILABLE = True
except ImportError:
    _BASE_CLASS = tk.Tk
    _DND_AVAILABLE = False

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BG = "#f0f2fa"
CARD_BG = "#ffffff"
HEADER_BG = "#2f2c73"
HEADER_FG = "#ffffff"
ACCENT = "#6c5ce7"
ACCENT_DARK = "#5a4cd6"
TEXT = "#26264d"
MUTED = "#6b6f8c"
BORDER = "#d9dcef"
DROP_BG = "#f4f2ff"
DROP_BG_HOVER = "#e6e0ff"

FONT_FAMILY = "Segoe UI"


def _default_output_path(input_path, suffix):
    base, _ = os.path.splitext(input_path)
    return "{}  ({}).rtf".format(base, suffix)


def _parse_dnd_path(data):
    """Parse the raw string tkinterdnd2 hands back from a drop event into a single path."""
    data = data.strip()
    if data.startswith("{") and data.endswith("}"):
        data = data[1:-1]
    else:
        # multiple files may be space-separated with {..} around ones containing spaces
        data = data.split("} {")[0].strip("{}")
    return data


class OutputRow:
    """Checkbox + label + path entry + browse button for one output file."""

    def __init__(self, parent, label_text, default_filetype_desc):
        self.enabled = tk.BooleanVar(value=True)
        self.path = tk.StringVar()

        self.frame = tk.Frame(parent, bg=CARD_BG)
        self.check = tk.Checkbutton(
            self.frame, variable=self.enabled, bg=CARD_BG,
            activebackground=CARD_BG, highlightthickness=0,
        )
        self.check.pack(side="left")
        tk.Label(
            self.frame, text=label_text, width=13, anchor="w",
            bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, 10, "bold"),
        ).pack(side="left")
        self.entry = tk.Entry(
            self.frame, textvariable=self.path, font=(FONT_FAMILY, 10),
            relief="solid", bd=1, highlightthickness=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._filetype_desc = default_filetype_desc
        self.browse_btn = tk.Button(
            self.frame, text="Browse...", command=self._browse,
            bg="#efeaff", fg=ACCENT_DARK, activebackground="#e0d8ff",
            relief="flat", font=(FONT_FAMILY, 9), cursor="hand2", padx=8,
        )
        self.browse_btn.pack(side="left")

    def pack(self, **kw):
        self.frame.pack(**kw)

    def _browse(self):
        initial = self.path.get()
        initialdir = os.path.dirname(initial) if initial else None
        initialfile = os.path.basename(initial) if initial else "output.rtf"
        path = filedialog.asksaveasfilename(
            title="Save {} as".format(self._filetype_desc),
            defaultextension=".rtf",
            filetypes=[("Rich Text Format", "*.rtf"), ("All files", "*.*")],
            initialdir=initialdir,
            initialfile=initialfile,
        )
        if path:
            self.path.set(path)
            self.enabled.set(True)


class App(_BASE_CLASS):
    def __init__(self, initial_file=None):
        super().__init__()
        self.title("ChordPro → RTF Converter")
        self.geometry("620x560")
        self.minsize(560, 480)
        self.configure(bg=BG)

        self.input_path = tk.StringVar()

        self._build_ui()

        if initial_file and os.path.isfile(initial_file):
            self._apply_input_file(initial_file)

    # -------------------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # ---- Header banner ----
        header = tk.Frame(self, bg=HEADER_BG)
        header.pack(fill="x")
        tk.Label(
            header, text="🎸  ChordPro → RTF", bg=HEADER_BG, fg=HEADER_FG,
            font=(FONT_FAMILY, 20, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(18, 2))
        tk.Label(
            header,
            text="Turn a ChordPro song into clean Lyrics and Chords documents.",
            bg=HEADER_BG, fg="#cfc9ff", font=(FONT_FAMILY, 10), anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 16))

        # ---- Body ----
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=16)

        # Card: source file
        source_card = tk.Frame(body, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        source_card.pack(fill="x", pady=(0, 14))

        tk.Label(
            source_card, text="SOURCE FILE", bg=CARD_BG, fg=MUTED,
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        in_frame = tk.Frame(source_card, bg=CARD_BG)
        in_frame.pack(fill="x", padx=16)
        self.input_entry = tk.Entry(
            in_frame, textvariable=self.input_path, font=(FONT_FAMILY, 10),
            relief="solid", bd=1, highlightthickness=0,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(
            in_frame, text="Browse...", command=self.choose_input,
            bg="#efeaff", fg=ACCENT_DARK, activebackground="#e0d8ff",
            relief="flat", font=(FONT_FAMILY, 9), cursor="hand2", padx=8,
        ).pack(side="left")

        drop_text = "⬇  Drag & drop a ChordPro file here  ⬇" if _DND_AVAILABLE else \
                    "(drag and drop unavailable - use Browse above)"
        self.drop_zone = tk.Label(
            source_card, text=drop_text, bg=DROP_BG, fg=ACCENT_DARK,
            font=(FONT_FAMILY, 11, "bold"), height=3,
        )
        self.drop_zone.pack(fill="x", padx=16, pady=14)

        if _DND_AVAILABLE:
            for widget in (self.drop_zone, self.input_entry):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.on_drop)
            self.drop_zone.dnd_bind("<<DropEnter>>", lambda e: self.drop_zone.configure(bg=DROP_BG_HOVER))
            self.drop_zone.dnd_bind("<<DropLeave>>", lambda e: self.drop_zone.configure(bg=DROP_BG))
            self.drop_zone.dnd_bind("<<DropPosition>>", lambda e: None)

        # Card: outputs
        out_card = tk.Frame(body, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        out_card.pack(fill="x", pady=(0, 14))

        tk.Label(
            out_card, text="OUTPUT FILES", bg=CARD_BG, fg=MUTED,
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.lyrics_row = OutputRow(out_card, "Lyrics file:", "Lyrics RTF file")
        self.lyrics_row.pack(fill="x", padx=16, pady=4)
        self.chords_row = OutputRow(out_card, "Chords file:", "Chords RTF file")
        self.chords_row.pack(fill="x", padx=16, pady=(4, 14))

        # Convert button
        convert_btn = tk.Button(
            body, text="⚡  Convert", command=self.do_convert,
            bg=ACCENT, fg="white", activebackground=ACCENT_DARK, activeforeground="white",
            relief="flat", font=(FONT_FAMILY, 12, "bold"), cursor="hand2", padx=20, pady=8,
        )
        convert_btn.pack(anchor="w", pady=(0, 14))

        # Log
        tk.Label(body, text="LOG", bg=BG, fg=MUTED, font=(FONT_FAMILY, 9, "bold")).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(
            body, height=8, state="disabled", bg=CARD_BG, fg=TEXT,
            font=("Consolas", 9), relief="solid", bd=1,
        )
        self.log.pack(fill="both", expand=True, pady=(4, 0))

    # -------------------------------------------------------------------
    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _apply_input_file(self, path):
        self.input_path.set(path)
        if not self.lyrics_row.path.get():
            self.lyrics_row.path.set(_default_output_path(path, "Lyrics"))
        if not self.chords_row.path.get():
            self.chords_row.path.set(_default_output_path(path, "Chords"))

    def on_drop(self, event):
        path = _parse_dnd_path(event.data)
        if not path:
            return
        if not os.path.isfile(path):
            messagebox.showerror("Invalid drop", "That doesn't look like a file:\n" + path)
            return
        self.input_path.set(path)
        self.lyrics_row.path.set(_default_output_path(path, "Lyrics"))
        self.chords_row.path.set(_default_output_path(path, "Chords"))

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="Select ChordPro file",
            filetypes=[
                ("ChordPro files", "*.cho *.chopro *.crd *.pro"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._apply_input_file(path)

    def do_convert(self):
        in_path = self.input_path.get().strip()

        if not in_path:
            messagebox.showerror("Missing input", "Please choose a ChordPro file to convert.")
            return
        if not os.path.isfile(in_path):
            messagebox.showerror("File not found", "The selected ChordPro file does not exist:\n" + in_path)
            return

        jobs = []  # (mode, out_path)
        if self.lyrics_row.enabled.get():
            out_path = self.lyrics_row.path.get().strip() or _default_output_path(in_path, "Lyrics")
            self.lyrics_row.path.set(out_path)
            jobs.append(("lyrics", out_path))
        if self.chords_row.enabled.get():
            out_path = self.chords_row.path.get().strip() or _default_output_path(in_path, "Chords")
            self.chords_row.path.set(out_path)
            jobs.append(("chords", out_path))

        if not jobs:
            messagebox.showinfo("Nothing to do", "Tick at least one of Lyrics file / Chords file.")
            return

        created = []
        for mode, out_path in jobs:
            if os.path.exists(out_path):
                if not messagebox.askyesno(
                    "File already exists",
                    "This file already exists:\n{}\n\nOverwrite it?".format(out_path),
                ):
                    self.log_msg("Skipped (exists): " + out_path)
                    continue
            try:
                convert_file(in_path, out_path, mode=mode)
            except Exception as exc:
                self.log_msg("ERROR ({}): {}".format(mode, exc))
                messagebox.showerror("Conversion failed", str(exc))
                continue
            self.log_msg("Created ({}):  {}".format(mode, out_path))
            created.append(out_path)

        if created:
            messagebox.showinfo("Done", "Created:\n" + "\n".join(created))


def main():
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = App(initial_file=initial_file)
    app.mainloop()


if __name__ == "__main__":
    main()
