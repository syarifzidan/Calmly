import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import pytesseract
from PIL import Image, ImageGrab, ImageTk
import pyautogui
import time

from llm import extract_events, extract_events_from_image
from gcal import add_event
from time_logic import update_duration

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── Palette ──────────────────────────────────────────────────────────────────
BG = "#0f0f0f"
SURFACE = "#1a1a1a"
BORDER = "#2a2a2a"
ACCENT = "#4ade80"  # green
ACCENT2 = "#22c55e"
TEXT = "#f0f0f0"
MUTED = "#6b7280"
DANGER = "#ef4444"
FONT_UI = ("Consolas", 11)
FONT_LG = ("Consolas", 13, "bold")
FONT_SM = ("Consolas", 9)


def styled_btn(parent, text, command, color=ACCENT, fg=BG, **kwargs):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg=fg,
        activebackground=ACCENT2,
        activeforeground=BG,
        font=FONT_UI,
        relief="flat",
        cursor="hand2",
        padx=14,
        pady=8,
        bd=0,
        **kwargs,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT2))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn


def styled_entry(parent, **kwargs):
    return tk.Entry(
        parent,
        bg=SURFACE,
        fg=TEXT,
        insertbackground=ACCENT,
        relief="flat",
        font=FONT_UI,
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        **kwargs,
    )


def styled_label(parent, text, size=11, muted=False, **kwargs):
    return tk.Label(
        parent,
        text=text,
        bg=BG,
        fg=MUTED if muted else TEXT,
        font=("Consolas", size),
        **kwargs,
    )


# ── Screenshot region selector ────────────────────────────────────────────────
class RegionSelector(tk.Toplevel):
    """Full-screen overlay; user drags to select a region."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.start_x = self.start_y = 0
        self.rect = None

        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.25)
        self.attributes("-topmost", True)
        self.configure(bg="black", cursor="crosshair")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        label = self.canvas.create_text(
            self.winfo_screenwidth() // 2,
            40,
            text="Drag to select the area to capture  •  ESC to cancel",
            fill="white",
            font=("Consolas", 14),
        )

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_press(self, e):
        self.start_x, self.start_y = e.x, e.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline=ACCENT, width=2, fill=""
        )

    def on_drag(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_release(self, e):
        x1 = min(self.start_x, e.x)
        y1 = min(self.start_y, e.y)
        x2 = max(self.start_x, e.x)
        y2 = max(self.start_y, e.y)
        self.destroy()
        if x2 - x1 > 10 and y2 - y1 > 10:
            time.sleep(0.1)  # let overlay fully disappear before grab
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            self.callback(screenshot)


# ── Edit / confirm window ─────────────────────────────────────────────────────
class EditWindow(tk.Toplevel):
    def __init__(self, parent, events, raw_text):
        super().__init__(parent)
        self.title("Review Event")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()  # modal

        self.events = events
        self.fields = {}

        pad = dict(padx=20, pady=6)

        styled_label(self, "REVIEW & EDIT EVENT", size=13).pack(pady=(24, 4))
        styled_label(
            self, f'from: "{raw_text}"', muted=True, size=9, wraplength=380
        ).pack(padx=20, pady=(0, 16))

        for label, key in [
            ("Title", "title"),
            ("Date (YYYY-MM-DD)", "date"),
            ("Start time (HH:MM)", "start_time"),
            ("End time (HH:MM)", "end_time"),
        ]:
            row = tk.Frame(self, bg=BG)
            row.pack(fill="x", **pad)
            styled_label(row, label, muted=True, size=9).pack(anchor="w")
            entry = styled_entry(row, width=36)
            entry.insert(0, str(events.get(key, "")))
            entry.pack(fill="x", pady=(2, 0), ipady=6)
            self.fields[key] = entry

        dur = events.get("duration", "?")
        self.dur_label = styled_label(self, f"Duration: {dur} min", muted=True, size=9)
        self.dur_label.pack(anchor="w", padx=20, pady=(0, 16))
        self.fields["end_time"].bind("<FocusOut>", self._refresh_duration)
        self.fields["start_time"].bind("<FocusOut>", self._refresh_duration)

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 24))
        styled_btn(btn_row, "Add to Calendar", self._submit).pack(side="left")
        styled_btn(btn_row, "Cancel", self.destroy, color=SURFACE, fg=TEXT).pack(
            side="left", padx=(10, 0)
        )

    def _refresh_duration(self, _=None):
        try:
            update_duration(
                {
                    "start_time": self.fields["start_time"].get(),
                    "end_time": self.fields["end_time"].get(),
                    "duration": 0,
                }
            )
            from time_logic import get_time_dif

            mins = get_time_dif(
                self.fields["start_time"].get(), self.fields["end_time"].get()
            )
            self.dur_label.config(text=f"Duration: {mins} min")
        except Exception:
            pass

    def _submit(self):
        ev = {k: f.get().strip() for k, f in self.fields.items()}
        try:
            update_duration(ev)
        except Exception as e:
            messagebox.showerror("Time error", str(e))
            return

        self.destroy()

        def run():
            try:
                created = add_event(
                    ev["title"], ev["date"], ev["start_time"], ev["duration"]
                )
                link = created.execute().get("htmlLink")
                messagebox.showinfo(
                    "Event created! 🎉", f"Added to Google Calendar:\n{link}"
                )
            except Exception as e:
                messagebox.showerror("Calendar error", str(e))

        threading.Thread(target=run, daemon=True).start()


# ── Main window ───────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoScheduler")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(28, 0))
        tk.Label(
            header, text="AUTO", bg=BG, fg=ACCENT, font=("Consolas", 22, "bold")
        ).pack(side="left")
        tk.Label(
            header, text="SCHEDULER", bg=BG, fg=TEXT, font=("Consolas", 22, "bold")
        ).pack(side="left")
        styled_label(header, "  v2.0", muted=True, size=10).pack(
            side="left", pady=(6, 0)
        )

        styled_label(self, "text → google calendar", muted=True, size=9).pack(
            anchor="w", padx=28, pady=(2, 20)
        )

        # Text input section
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=28)
        styled_label(self, "PASTE EVENT TEXT", muted=True, size=8).pack(
            anchor="w", padx=28, pady=(14, 4)
        )

        self.text_input = tk.Text(
            self,
            height=5,
            width=46,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=FONT_UI,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            padx=10,
            pady=8,
            wrap="word",
        )
        self.text_input.pack(padx=28)

        styled_btn(self, "Extract from text →", self._handle_text).pack(
            anchor="w", padx=28, pady=(10, 20)
        )

        # Screenshot section
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=28)
        styled_label(self, "OR CAPTURE A SCREENSHOT", muted=True, size=8).pack(
            anchor="w", padx=28, pady=(14, 4)
        )

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=28, pady=(0, 10))
        styled_btn(btn_row, "📷  Select region", self._take_screenshot).pack(
            side="left"
        )
        styled_btn(
            btn_row, "📁  Upload image", self._upload_image, color=SURFACE, fg=TEXT
        ).pack(side="left", padx=(10, 0))

        # Status bar
        self.status_var = tk.StringVar(value="ready.")
        tk.Label(
            self,
            textvariable=self.status_var,
            bg=BG,
            fg=MUTED,
            font=FONT_SM,
            anchor="w",
        ).pack(fill="x", padx=28, pady=(14, 20))

        self.geometry("")  # auto-size

    def _set_status(self, msg):
        self.status_var.set(msg)
        self.update_idletasks()

    def _process_text(self, text, label="text"):
        self._set_status(f"extracting event from {label}...")

        def run():
            try:
                events = extract_events(text)
                if not events:
                    self._set_status("couldn't extract event. try again.")
                    return
                self._set_status("ready.")
                self.after(0, lambda: EditWindow(self, events, text[:60]))
            except Exception as e:
                self._set_status(f"error: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _handle_text(self):
        text = self.text_input.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Empty", "Please enter some event text.")
            return
        self._process_text(text)

    def _take_screenshot(self):
        self.withdraw()
        time.sleep(0.3)

        def on_capture(img):
            self.deiconify()
            self._process_image(img)

        RegionSelector(on_capture)

    def _upload_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        if path:
            img = Image.open(path)
            self._process_image(img)

    def _process_image(self, img):
        self._set_status("running OCR...")

        def run():
            try:
                text = pytesseract.image_to_string(img, lang="ind+eng")
                print(f"OCR result:\n{text}")
                if not text.strip():
                    self._set_status("OCR found no text. try a clearer image.")
                    return
                self._process_text(text, label="screenshot")
            except Exception as e:
                self._set_status(f"OCR error: {e}")

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
