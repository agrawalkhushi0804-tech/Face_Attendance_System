import os
import cv2
import pandas as pd
from datetime import datetime
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
 
# ── AI Engine ──────────────────────────────────────────────────────────────────
try:
    from deepface import DeepFace
    DEEPFACE_READY = True
except Exception as e:
    print(f"DeepFace Load Error: {e}")
    DEEPFACE_READY = False
 
# ── Config ─────────────────────────────────────────────────────────────────────
DB_PATH  = "database"
CSV_FILE = "attendance.csv"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)
 
# Fixed camera display size — never changes, kills jitter
CAM_W, CAM_H = 640, 420
 
# ── Palette ────────────────────────────────────────────────────────────────────
C = {
    "bg":          "#0D0D12",
    "sidebar":     "#111118",
    "card":        "#15151E",
    "input":       "#1C1C28",
    "border":      "#252535",
    "accent":      "#7C6FFB",
    "accent_dk":   "#5146C8",
    "green":       "#34D399",
    "red":         "#F87171",
    "amber":       "#FBBF24",
    "txt":         "#EEEDF8",
    "txt2":        "#7A798C",
    "txt3":        "#3E3D52",
    "nav_sel":     "#1A1A2E",
}
 
F = {
    "title":  ("Segoe UI",    24, "bold"),
    "head":   ("Segoe UI",    14, "bold"),
    "nav":    ("Segoe UI",    13),
    "body":   ("Segoe UI",    12),
    "small":  ("Segoe UI",    10),
    "tag":    ("Segoe UI",     9, "bold"),
    "mono":   ("Consolas",    12),
    "stat":   ("Segoe UI",    30, "bold"),
}
 
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def frm(parent, bg=None, **kw):
    return tk.Frame(parent, bg=bg or C["bg"], **kw)
 
def lbl(parent, text, font=None, fg=None, bg=None, **kw):
    return tk.Label(parent,
        text=text,
        font=font or F["body"],
        fg=fg or C["txt"],
        bg=bg or C["bg"],
        **kw)
 
def divider(parent, bg=None, padx=0, pady=0):
    tk.Frame(parent, bg=bg or C["border"], height=1).pack(
        fill="x", padx=padx, pady=pady)
 
def pill_btn(parent, text, bg, hover, cmd, fg=None, pady=9):
    """Flat pill button using a Label."""
    b = tk.Label(parent, text=text,
                 font=F["body"], fg=fg or C["txt"],
                 bg=bg, cursor="hand2",
                 pady=pady, padx=0, anchor="center")
    b.pack(fill="x")
    b.bind("<Button-1>", lambda e: cmd())
    b.bind("<Enter>",    lambda e: b.configure(bg=hover))
    b.bind("<Leave>",    lambda e: b.configure(bg=bg))
    return b
 
 
# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class AttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Presently  ·  AI Attendance")
        self.geometry("1180x720")
        self.minsize(1000, 660)
        self.configure(fg_color=C["bg"])
        self.resizable(True, True)
 
        self.cap        = cv2.VideoCapture(0)
        self.scanning   = False
        self.cur_page   = None
        self.pages      = {}
        self._last_imgtk = None   # keep reference alive
 
        self._build()
        self._go("register")
        self._cam_loop()
 
    # ── Shell ─────────────────────────────────────────────────────────────────
    def _build(self):
        # Sidebar — fixed 210px, no propagation
        self.sidebar = frm(self, bg=C["sidebar"], width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
 
        # 1-px border
        frm(self, bg=C["border"], width=1).pack(side="left", fill="y")
 
        # Content
        self.content = frm(self, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)
 
        self._build_sidebar()
        self._build_pages()
 
    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        s = self.sidebar
 
        lbl(s, "MENU", font=F["tag"], fg=C["txt3"],
            bg=C["sidebar"], anchor="w").pack(fill="x", padx=22, pady=(0,8))
 
        self._nav_btns = {}
        for key, icon, label, sub in [
            ("register", "◎", "Register Face",    "Enrol a new student"),
            ("scan",     "◉", "Mark Attendance",  "Live recognition"),
            ("logs",     "≡", "View Logs",         "All records"),
        ]:
            self._nav_btns[key] = self._nav_item(s, key, icon, label, sub)
 
        # Bottom status
        frm(s, bg=C["border"], height=1).pack(side="bottom", fill="x", padx=16)
 
        bot = frm(s, bg=C["sidebar"])
        bot.pack(side="bottom", fill="x", padx=20, pady=16)
 
        sc = C["green"] if DEEPFACE_READY else C["red"]
        st = "AI Engine Ready" if DEEPFACE_READY else "Engine Missing"
 
        row = frm(bot, bg=C["sidebar"])
        row.pack(fill="x")
        lbl(row, "●", font=("Segoe UI", 9), fg=sc, bg=C["sidebar"]).pack(side="left")
        lbl(row, f"  {st}", font=F["small"], fg=C["txt2"],
            bg=C["sidebar"]).pack(side="left")
 
        self._status_var = tk.StringVar(value="Idle")
        tk.Label(bot, textvariable=self._status_var,
                 font=F["small"], fg=C["txt3"],
                 bg=C["sidebar"], anchor="w").pack(fill="x", pady=(5,0))
 
    def _nav_item(self, parent, key, icon, label, sub):
        wrap = frm(parent, bg=C["sidebar"])
        wrap.pack(fill="x", padx=10, pady=2)
 
        inner = frm(wrap, bg=C["sidebar"])
        inner.pack(fill="x", ipady=8, ipadx=10)
 
        # Icon + label on same row
        row = frm(inner, bg=C["sidebar"])
        row.pack(fill="x", padx=8)
 
        icon_l = lbl(row, icon, font=("Segoe UI", 14),
                     fg=C["txt3"], bg=C["sidebar"])
        icon_l.pack(side="left")
 
        name_l = lbl(row, f"  {label}", font=F["nav"],
                     fg=C["txt2"], bg=C["sidebar"])
        name_l.pack(side="left")
 
        sub_l = lbl(inner, f"     {sub}", font=F["small"],
                    fg=C["txt3"], bg=C["sidebar"], anchor="w")
        sub_l.pack(fill="x", padx=8)
 
        widgets = [wrap, inner, row, icon_l, name_l, sub_l]
        for w in widgets:
            w.bind("<Button-1>", lambda e, k=key: self._go(k))
            w.bind("<Enter>",    lambda e, i=inner, il=icon_l, nl=name_l, sl=sub_l:
                   self._nav_hover(i, il, nl, sl, True))
            w.bind("<Leave>",    lambda e, i=inner, il=icon_l, nl=name_l, sl=sub_l, k=key:
                   self._nav_hover(i, il, nl, sl, False, k))
 
        return (inner, icon_l, name_l, sub_l)
 
    def _nav_hover(self, inner, icon_l, name_l, sub_l, on, key=None):
        if key and key == self.cur_page:
            return
        bg = C["nav_sel"] if on else C["sidebar"]
        fg = C["txt"]     if on else C["txt2"]
        inner.configure(bg=bg)
        icon_l.configure(bg=bg, fg=fg)
        name_l.configure(bg=bg, fg=fg)
        sub_l.configure(bg=bg)
 
    def _set_nav(self, active):
        for key, (inner, icon_l, name_l, sub_l) in self._nav_btns.items():
            if key == active:
                inner.configure(bg=C["nav_sel"])
                icon_l.configure(fg=C["accent"], bg=C["nav_sel"])
                name_l.configure(fg=C["accent"], bg=C["nav_sel"])
                sub_l.configure(bg=C["nav_sel"])
            else:
                inner.configure(bg=C["sidebar"])
                icon_l.configure(fg=C["txt3"], bg=C["sidebar"])
                name_l.configure(fg=C["txt2"], bg=C["sidebar"])
                sub_l.configure(bg=C["sidebar"])
 
    # ── Pages ─────────────────────────────────────────────────────────────────
    def _build_pages(self):
        self.pages["register"] = RegisterPage(self.content, self)
        self.pages["scan"]     = ScanPage(self.content, self)
        self.pages["logs"]     = LogsPage(self.content, self)
        for p in self.pages.values():
            p.place(relx=0, rely=0, relwidth=1, relheight=1)
 
    def _go(self, key):
        if self.cur_page and self.cur_page != key:
            old = self.pages.get(self.cur_page)
            if old and hasattr(old, "on_leave"):
                old.on_leave()
        self.cur_page = key
        self._set_nav(key)
        page = self.pages[key]
        page.lift()
        if hasattr(page, "on_enter"):
            page.on_enter()
 
    # ── Single camera loop — feeds whichever page is active ──────────────────
    def _cam_loop(self):
        ret, frame = self.cap.read()
        if ret:
            page = self.pages.get(self.cur_page)
            if page and hasattr(page, "feed_frame"):
                page.feed_frame(frame)
        self.after(33, self._cam_loop)   # ~30 fps, stable interval
 
    # ── Shared helpers ────────────────────────────────────────────────────────
    def mark_attendance(self, name):
        now      = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
 
        if not os.path.exists(CSV_FILE):
            pd.DataFrame(columns=["Name", "Date", "Time"]).to_csv(CSV_FILE, index=False)
 
        df = pd.read_csv(CSV_FILE)
        already = not df[(df["Name"] == name) & (df["Date"] == date_str)].empty
        if not already:
            new = pd.DataFrame([[name, date_str, time_str]], columns=["Name", "Date", "Time"])
            new.to_csv(CSV_FILE, mode="a", header=False, index=False)
            self.pages["scan"].add_entry(name, time_str)
            self._status_var.set(f"Marked: {name.replace('_',' ')}")
 
    def reset_camera(self):
        self.cap.release()
        self.cap = cv2.VideoCapture(0)
        self._status_var.set("Camera reset")
 
    def on_closing(self):
        self.cap.release()
        self.destroy()
 
 
# ══════════════════════════════════════════════════════════════════════════════
# REGISTER PAGE
# ══════════════════════════════════════════════════════════════════════════════
class RegisterPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()
 
    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = frm(self, bg=C["bg"])
        hdr.pack(fill="x", padx=36, pady=(28, 0))
        lbl(hdr, "Register Face", font=F["title"], bg=C["bg"]).pack(anchor="w")
        lbl(hdr, "Position student in frame, enter name, then capture.",
            font=F["body"], fg=C["txt2"], bg=C["bg"]).pack(anchor="w", pady=(3,0))
        divider(self, padx=36, pady=(16, 0))
 
        # ── Body: camera left, form right ─────────────────────────────────────
        body = frm(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=36, pady=16)
 
        # Camera — FIXED size container, no expand on the label
        cam_outer = frm(body, bg=C["card"])
        cam_outer.pack(side="left", fill="both", expand=True, padx=(0,16))
        cam_outer.configure(highlightbackground=C["border"], highlightthickness=1)
 
        # Fixed-size label: width/height in pixels via a containing frame trick
        self.cam_lbl = tk.Label(
            cam_outer,
            bg=C["card"],
            width=CAM_W, height=CAM_H,   # pixels when image is set; chars otherwise
            text="Initialising camera…",
            font=F["body"], fg=C["txt2"],
        )
        self.cam_lbl.pack(expand=True)   # centres in card, doesn't resize it
 
        # Form panel — fixed 280px
        right = frm(body, bg=C["bg"], width=280)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
 
        self._form(right)
 
    def _form(self, parent):
        # Card
        card = frm(parent, bg=C["card"])
        card.configure(highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))
 
        inner = frm(card, bg=C["card"])
        inner.pack(fill="x", padx=20, pady=20)
 
        lbl(inner, "Student Details", font=F["head"],
            bg=C["card"]).pack(anchor="w", pady=(0,16))
 
        lbl(inner, "FULL NAME", font=F["tag"], fg=C["txt3"],
            bg=C["card"]).pack(anchor="w")
 
        self._name_var = tk.StringVar()
        ent = tk.Entry(inner, textvariable=self._name_var,
                       font=F["body"],
                       bg=C["input"], fg=C["txt"],
                       insertbackground=C["accent"],
                       relief="flat", bd=0)
        ent.pack(fill="x", ipady=9, pady=(5,0))
        frm(inner, bg=C["border"], height=1).pack(fill="x")
 
        tk.Frame(inner, bg=C["card"], height=16).pack()  # spacer
 
        pill_btn(inner, "Capture & Register",
                 C["accent"], C["accent_dk"], self._do_register)
 
        tk.Frame(inner, bg=C["card"], height=8).pack()
 
        pill_btn(inner, "Reset Camera",
                 C["input"], C["border"],
                 self.app.reset_camera,
                 fg=C["txt2"])
 
        self._fb_var = tk.StringVar()
        self._fb_lbl = tk.Label(inner, textvariable=self._fb_var,
                                font=F["small"], fg=C["green"],
                                bg=C["card"], anchor="w", wraplength=240)
        self._fb_lbl.pack(fill="x", pady=(12,0))
 
        # Tips card
        tips_card = frm(parent, bg=C["card"])
        tips_card.configure(highlightbackground=C["border"], highlightthickness=1)
        tips_card.pack(fill="x")
        tips_i = frm(tips_card, bg=C["card"])
        tips_i.pack(fill="x", padx=20, pady=16)
 
        lbl(tips_i, "Tips for best results", font=F["head"],
            bg=C["card"]).pack(anchor="w", pady=(0,10))
        for t in ["◦  Face camera directly",
                  "◦  Good, even lighting",
                  "◦  Neutral expression",
                  "◦  Remove hats / glasses"]:
            lbl(tips_i, t, font=F["small"], fg=C["txt2"],
                bg=C["card"], anchor="w").pack(fill="x", pady=2)
 
    def _do_register(self):
        name = self._name_var.get().strip().replace(" ", "_")
        if not name:
            self._fb_var.set("⚠  Enter a name first.")
            self._fb_lbl.configure(fg=C["amber"])
            return
        ret, frame = self.app.cap.read()
        if ret:
            cv2.imwrite(os.path.join(DB_PATH, f"{name}.jpg"), frame)
            pkl = os.path.join(DB_PATH, "representations_vgg_face.pkl")
            if os.path.exists(pkl):
                os.remove(pkl)
            self._name_var.set("")
            self._fb_var.set(f"✓  Registered: {name.replace('_',' ')}")
            self._fb_lbl.configure(fg=C["green"])
            self.app._status_var.set(f"Registered {name}")
        else:
            self._fb_var.set("⚠  Camera error — try resetting.")
            self._fb_lbl.configure(fg=C["red"])
 
    # ── Camera feed ───────────────────────────────────────────────────────────
    def feed_frame(self, frame):
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb).resize((CAM_W, CAM_H), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.cam_lbl.configure(image=imgtk, text="")
        self.cam_lbl.imgtk = imgtk   # prevent GC
 
    def on_enter(self): pass
    def on_leave(self): pass
 
 
# ══════════════════════════════════════════════════════════════════════════════
# SCAN PAGE
# ══════════════════════════════════════════════════════════════════════════════
class ScanPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._log_count = 0
        self._build()
 
    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = frm(self, bg=C["bg"])
        hdr.pack(fill="x", padx=36, pady=(28, 0))
 
        left_h = frm(hdr, bg=C["bg"])
        left_h.pack(side="left", fill="x", expand=True)
        lbl(left_h, "Mark Attendance", font=F["title"], bg=C["bg"]).pack(anchor="w")
        lbl(left_h, "Recognised faces are logged automatically once per day.",
            font=F["body"], fg=C["txt2"], bg=C["bg"]).pack(anchor="w", pady=(3,0))
 
        self._scan_btn = tk.Label(
            hdr, text="  ▶  Start Scanning  ",
            font=("Segoe UI", 12, "bold"),
            fg=C["txt"], bg=C["accent"],
            cursor="hand2", pady=9, padx=2)
        self._scan_btn.pack(side="right", padx=(0, 2))
        self._scan_btn.bind("<Button-1>", lambda e: self._toggle())
 
        divider(self, padx=36, pady=(16, 0))
 
        # ── Body ──────────────────────────────────────────────────────────────
        body = frm(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=36, pady=16)
 
        # Camera — fixed size
        cam_outer = frm(body, bg=C["card"])
        cam_outer.pack(side="left", fill="both", expand=True, padx=(0, 16))
        cam_outer.configure(highlightbackground=C["border"], highlightthickness=1)
 
        self.cam_lbl = tk.Label(cam_outer, bg=C["card"],
                                width=CAM_W, height=CAM_H,
                                text="Camera…", font=F["body"], fg=C["txt2"])
        self.cam_lbl.pack(expand=True)
 
        # Status bar below camera
        self._status_var = tk.StringVar(value="")
        tk.Label(cam_outer, textvariable=self._status_var,
                 font=("Consolas", 11), fg=C["green"],
                 bg=C["card"], anchor="w").pack(fill="x", padx=12, pady=(0,8))
 
        # Log panel — fixed 290px
        right = frm(body, bg=C["bg"], width=290)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
 
        self._build_log(right)
 
    def _build_log(self, parent):
        card = frm(parent, bg=C["card"])
        card.configure(highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="both", expand=True)
 
        inner = frm(card, bg=C["card"])
        inner.pack(fill="both", expand=True, padx=16, pady=16)
 
        # Header row
        top = frm(inner, bg=C["card"])
        top.pack(fill="x", pady=(0,10))
        lbl(top, "Today's Log", font=F["head"], bg=C["card"]).pack(side="left")
        self._count_lbl = lbl(top, " 0 ", font=("Segoe UI", 10, "bold"),
                              fg=C["accent"], bg=C["input"])
        self._count_lbl.pack(side="right")
 
        # Column labels
        cols = frm(inner, bg=C["card"])
        cols.pack(fill="x", pady=(0,4))
        lbl(cols, "NAME", font=F["tag"], fg=C["txt3"],
            bg=C["card"], anchor="w").pack(side="left", fill="x", expand=True)
        lbl(cols, "TIME", font=F["tag"], fg=C["txt3"],
            bg=C["card"], anchor="e").pack(side="right")
 
        divider(inner, pady=(0,6))
 
        # Scrollable list via canvas
        c_wrap = frm(inner, bg=C["card"])
        c_wrap.pack(fill="both", expand=True)
 
        self._canvas = tk.Canvas(c_wrap, bg=C["card"],
                                 highlightthickness=0, bd=0)
        self._canvas.pack(side="left", fill="both", expand=True)
 
        sb = tk.Scrollbar(c_wrap, orient="vertical",
                          command=self._canvas.yview,
                          bg=C["card"], troughcolor=C["card"])
        sb.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=sb.set)
 
        self._log_frame = frm(self._canvas, bg=C["card"])
        self._canvas.create_window((0,0), window=self._log_frame, anchor="nw")
        self._log_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
 
    def add_entry(self, name, time_str):
        row = frm(self._log_frame, bg=C["card"])
        row.pack(fill="x", pady=3)
 
        lbl(row, "●", font=("Segoe UI", 8), fg=C["green"],
            bg=C["card"]).pack(side="left", padx=(0, 8))
        lbl(row, name.replace("_", " ")[:22],
            font=F["body"], bg=C["card"],
            anchor="w").pack(side="left", fill="x", expand=True)
        lbl(row, time_str, font=("Consolas", 11),
            fg=C["txt2"], bg=C["card"],
            anchor="e").pack(side="right")
 
        divider(self._log_frame, pady=(2,0))
 
        self._log_count += 1
        self._count_lbl.configure(text=f" {self._log_count} ")
        self._canvas.after(50, lambda: self._canvas.yview_moveto(1))
 
        # Flash status
        self._status_var.set(f"✓  Marked: {name.replace('_',' ')}")
        self.after(2500, lambda: self._status_var.set(""))
 
    def _toggle(self):
        if not DEEPFACE_READY:
            messagebox.showerror("AI Unavailable",
                "DeepFace is not installed properly.")
            return
        self.app.scanning = not self.app.scanning
        if self.app.scanning:
            self._scan_btn.configure(
                text="  ■  Stop Scanning  ", bg=C["red"])
            self._status_var.set("Scanning…")
            self.app._status_var.set("Scanning active")
        else:
            self._scan_btn.configure(
                text="  ▶  Start Scanning  ", bg=C["accent"])
            self._status_var.set("")
            self.app._status_var.set("Scanning paused")
 
    def feed_frame(self, frame):
        display = frame.copy()
 
        if self.app.scanning:
            try:
                results = DeepFace.find(
                    img_path=frame,
                    db_path=DB_PATH,
                    model_name="VGG-Face",
                    enforce_detection=False,
                    silent=True)
 
                if results and not results[0].empty:
                    r    = results[0]
                    name = os.path.splitext(os.path.basename(r["identity"][0]))[0]
                    x, y = int(r["source_x"][0]), int(r["source_y"][0])
                    w, h = int(r["source_w"][0]), int(r["source_h"][0])
 
                    cv2.rectangle(display, (x,y), (x+w, y+h), (124,111,251), 2)
                    cv2.putText(display, name.replace("_"," "),
                                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX,
                                0.65, (124,111,251), 2)
                    self.app.mark_attendance(name)
            except Exception as ex:
                print(f"Recognition: {ex}")
 
        rgb   = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb).resize((CAM_W, CAM_H), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.cam_lbl.configure(image=imgtk, text="")
        self.cam_lbl.imgtk = imgtk
 
    def on_enter(self): pass
    def on_leave(self): pass
 
 
# ══════════════════════════════════════════════════════════════════════════════
# LOGS PAGE
# ══════════════════════════════════════════════════════════════════════════════
class LogsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()
 
    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = frm(self, bg=C["bg"])
        hdr.pack(fill="x", padx=36, pady=(28, 0))
 
        left_h = frm(hdr, bg=C["bg"])
        left_h.pack(side="left", fill="x", expand=True)
        lbl(left_h, "Attendance Records", font=F["title"], bg=C["bg"]).pack(anchor="w")
        lbl(left_h, "Complete history of all logged entries.",
            font=F["body"], fg=C["txt2"], bg=C["bg"]).pack(anchor="w", pady=(3,0))
 
        rb = tk.Label(hdr, text="  ↻  Refresh  ",
                      font=("Segoe UI", 12, "bold"),
                      fg=C["txt"], bg=C["input"],
                      cursor="hand2", pady=9, padx=2)
        rb.pack(side="right")
        rb.bind("<Button-1>", lambda e: self.on_enter())
        rb.bind("<Enter>",    lambda e: rb.configure(bg=C["border"]))
        rb.bind("<Leave>",    lambda e: rb.configure(bg=C["input"]))
 
        divider(self, padx=36, pady=(16, 0))
 
        # ── Stats row ─────────────────────────────────────────────────────────
        stats = frm(self, bg=C["bg"])
        stats.pack(fill="x", padx=36, pady=(16, 0))
 
        self._s_total   = self._stat(stats, "Total Entries",   "—", C["accent"])
        self._s_today   = self._stat(stats, "Present Today",   "—", C["green"])
        self._s_unique  = self._stat(stats, "Unique Students", "—", C["amber"])
 
        divider(self, padx=36, pady=(16, 0))
 
        # ── Table ─────────────────────────────────────────────────────────────
        tbl_wrap = frm(self, bg=C["bg"])
        tbl_wrap.pack(fill="both", expand=True, padx=36, pady=16)
 
        tbl_card = frm(tbl_wrap, bg=C["card"])
        tbl_card.configure(highlightbackground=C["border"], highlightthickness=1)
        tbl_card.pack(fill="both", expand=True)
 
        # Column header
        col_hdr = frm(tbl_card, bg=C["input"])
        col_hdr.pack(fill="x")
        for txt, w, a in [("#", 4, "center"), ("Name", 28, "w"),
                          ("Date", 14, "w"), ("Time", 12, "w")]:
            tk.Label(col_hdr, text=txt,
                     font=F["tag"], fg=C["txt3"],
                     bg=C["input"],
                     width=w, anchor=a,
                     pady=10).pack(side="left", padx=(10,0))
 
        # Scrollable body
        c_wrap = frm(tbl_card, bg=C["card"])
        c_wrap.pack(fill="both", expand=True)
 
        self._tbl_canvas = tk.Canvas(c_wrap, bg=C["card"],
                                     highlightthickness=0, bd=0)
        self._tbl_canvas.pack(side="left", fill="both", expand=True)
 
        sb = tk.Scrollbar(c_wrap, orient="vertical",
                          command=self._tbl_canvas.yview,
                          bg=C["card"], troughcolor=C["card"])
        sb.pack(side="right", fill="y")
        self._tbl_canvas.configure(yscrollcommand=sb.set)
 
        self._tbl_rows = frm(self._tbl_canvas, bg=C["card"])
        self._tbl_canvas.create_window((0,0), window=self._tbl_rows, anchor="nw")
        self._tbl_rows.bind(
            "<Configure>",
            lambda e: self._tbl_canvas.configure(
                scrollregion=self._tbl_canvas.bbox("all")))
 
    def _stat(self, parent, label, value, accent):
        card = frm(parent, bg=C["card"])
        card.configure(highlightbackground=C["border"], highlightthickness=1)
        card.pack(side="left", padx=(0, 12), ipadx=16, ipady=10)
 
        # Accent bar at top
        frm(card, bg=accent, height=3).pack(fill="x")
 
        inner = frm(card, bg=C["card"])
        inner.pack(fill="x", padx=16, pady=(10, 14))
 
        lbl(inner, label, font=F["small"], fg=C["txt2"],
            bg=C["card"]).pack(anchor="w")
        val = lbl(inner, value, font=F["stat"], bg=C["card"])
        val.pack(anchor="w", pady=(2,0))
        return val
 
    def on_enter(self):
        self._load()
 
    def _load(self):
        for w in self._tbl_rows.winfo_children():
            w.destroy()
 
        if not os.path.exists(CSV_FILE):
            lbl(self._tbl_rows, "No records yet.",
                font=F["body"], fg=C["txt3"],
                bg=C["card"]).pack(pady=40)
            for s in [self._s_total, self._s_today, self._s_unique]:
                s.configure(text="0")
            return
 
        df    = pd.read_csv(CSV_FILE)
        today = datetime.now().strftime("%Y-%m-%d")
 
        self._s_total.configure(text=str(len(df)))
        self._s_today.configure(text=str(len(df[df["Date"] == today])))
        self._s_unique.configure(text=str(df["Name"].nunique()))
 
        for i, row in df.iloc[::-1].reset_index(drop=True).iterrows():
            is_today = row["Date"] == today
            bg   = C["card"] if i % 2 == 0 else C["input"]
            dot  = C["green"] if is_today else C["txt3"]
            namec= C["txt"]   if is_today else C["txt2"]
 
            r = frm(self._tbl_rows, bg=bg)
            r.pack(fill="x")
 
            # #
            lbl(r, str(len(df)-i), font=F["small"], fg=C["txt3"],
                bg=bg, width=4, anchor="center").pack(side="left", padx=(10,0), pady=7)
 
            # dot + name
            nf = frm(r, bg=bg)
            nf.pack(side="left")
            lbl(nf, "●", font=("Segoe UI",8), fg=dot, bg=bg).pack(side="left")
            lbl(nf, "  " + row["Name"].replace("_"," "),
                font=F["body"], fg=namec, bg=bg,
                width=26, anchor="w").pack(side="left")
 
            lbl(r, row["Date"], font=F["small"], fg=C["txt2"],
                bg=bg, width=14, anchor="w").pack(side="left")
            lbl(r, row["Time"], font=("Consolas",11), fg=C["accent"],
                bg=bg, width=12, anchor="w").pack(side="left")
 
            frm(self._tbl_rows, bg=C["border"], height=1).pack(fill="x")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ENTRY
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = AttendanceApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
