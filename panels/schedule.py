import customtkinter as ctk
import tkinter as tk
from datetime import date, datetime, timedelta

# Color cycle: red → orange → green → blue → purple
EVENT_COLORS = ["#D0021B", "#F5A623", "#7ED321", "#4A90E2", "#9B59B6"]

HOUR_HEIGHT = 72   # canvas pixels per hour
START_HOUR  = 6
END_HOUR    = 24
LABEL_W     = 62   # pixel width of the time-label column


# ── Time helpers ─────────────────────────────────────────────────────────────

def time_to_y(t: str) -> float:
    h, m = map(int, t.split(":"))
    return (h - START_HOUR + m / 60) * HOUR_HEIGHT


def y_to_time(y: float, snap: int = 15) -> str:
    total_min = max(0.0, y) / HOUR_HEIGHT * 60
    snapped   = round(total_min / snap) * snap
    h = START_HOUR + int(snapped) // 60
    m = int(snapped) % 60
    h = max(START_HOUR, min(END_HOUR, h))
    m = 0 if h == END_HOUR else m
    return f"{h:02d}:{m:02d}"


def fmt_time(t: str) -> str:
    h, m = map(int, t.split(":"))
    suf = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suf}" if m else f"{h12} {suf}"


# ── Panel ─────────────────────────────────────────────────────────────────────

class SchedulePanel(ctk.CTkFrame):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db           = db
        self.current_date = date.today()
        self._drag_start  = None   # canvas-y where drag began
        self._drag_rect   = None   # canvas item id of drag preview
        self._resize_job  = None
        self._ev_items    = {}     # canvas item id → event db id
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        self.configure(fg_color=("gray92", "gray14"))

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16, 6))

        self.date_label = ctk.CTkLabel(
            hdr, text="", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.date_label.pack(side="left", expand=True, fill="x")

        nav = ctk.CTkFrame(hdr, fg_color="transparent")
        nav.pack(side="right")
        btn_kw = dict(height=28, fg_color=("gray80", "gray30"),
                      hover_color=("gray70", "gray40"), text_color=("gray10", "gray90"))
        ctk.CTkButton(nav, text="‹", width=30, font=ctk.CTkFont(size=16),
                      command=self._prev_day, **btn_kw).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="›", width=30, font=ctk.CTkFont(size=16),
                      command=self._next_day, **btn_kw).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="Today", width=60,
                      command=self._go_today, **btn_kw).pack(side="left", padx=2)

        # Hint label
        ctk.CTkLabel(self, text="Drag to create  •  Double-click to delete",
                     font=ctk.CTkFont(size=10),
                     text_color=("gray55", "gray50")).pack(anchor="w", padx=16, pady=(0, 4))

        # Canvas wrapper
        is_dark = ctk.get_appearance_mode() == "Dark"
        wrap_bg = "#1c1c1e" if is_dark else "#f2f2f7"
        wrap = tk.Frame(self, bg=wrap_bg)
        wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        vbar = ctk.CTkScrollbar(wrap)
        vbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(
            wrap, bg=wrap_bg, highlightthickness=0, yscrollcommand=vbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        vbar.configure(command=self.canvas.yview)

        total_h = (END_HOUR - START_HOUR) * HOUR_HEIGHT
        self.canvas.configure(scrollregion=(0, 0, 4000, total_h))

        self.canvas.bind("<Configure>",       self._on_resize)
        self.canvas.bind("<Button-1>",        self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        # Mac trackpad / mouse wheel scroll
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(int(-e.delta / 40), "units"))

        self._update_date_label()
        self.after(80, self._initial_draw)

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _initial_draw(self):
        self._redraw()
        self._scroll_to_now()

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        if w < 20:
            self.after(80, self._redraw)
            return

        is_dark  = ctk.get_appearance_mode() == "Dark"
        bg       = "#1c1c1e" if is_dark else "#f2f2f7"
        grid_c   = "#2c2c2e" if is_dark else "#d1d1d6"
        tick_c   = "#232325" if is_dark else "#e5e5ea"
        lbl_c    = "#636366" if is_dark else "#8e8e93"
        total_h  = (END_HOUR - START_HOUR) * HOUR_HEIGHT

        c.configure(bg=bg)
        self._ev_items = {}

        # Grid lines & labels
        for h in range(START_HOUR, END_HOUR + 1):
            y = (h - START_HOUR) * HOUR_HEIGHT
            c.create_line(LABEL_W, y, w, y, fill=grid_c, width=1)
            if h < END_HOUR:
                c.create_text(LABEL_W - 6, y + 3, text=fmt_time(f"{h:02d}:00"),
                              anchor="ne", fill=lbl_c, font=("", 10))
                for q in (1, 2, 3):
                    qy = y + q * HOUR_HEIGHT // 4
                    c.create_line(LABEL_W, qy, w, qy, fill=tick_c, width=1)

        # Events
        for ev in self.db.get_events(self.current_date.isoformat()):
            self._draw_event(ev, w, is_dark)

        # Current-time indicator
        if self.current_date == date.today():
            now = datetime.now()
            y   = (now.hour - START_HOUR + now.minute / 60) * HOUR_HEIGHT
            if 0 <= y <= total_h:
                c.create_oval(LABEL_W - 5, y - 5, LABEL_W + 5, y + 5,
                              fill="#ff3b30", outline="")
                c.create_line(LABEL_W, y, w, y, fill="#ff3b30", width=2)

    def _draw_event(self, ev: dict, w: int, is_dark: bool):
        y1 = time_to_y(ev["start_time"])
        y2 = time_to_y(ev["end_time"])
        if y2 - y1 < HOUR_HEIGHT // 8:
            y2 = y1 + HOUR_HEIGHT // 8

        color  = ev["color"]
        ev_tag = f"ev_{ev['id']}"
        pad    = 3

        rid = self.canvas.create_rectangle(
            LABEL_W + pad, y1 + 1, w - pad, y2 - 1,
            fill=color, outline="", tags=ev_tag
        )
        span  = y2 - y1
        label = ev["title"] or "Untitled"
        if span > 30:
            label += f"\n{fmt_time(ev['start_time'])} – {fmt_time(ev['end_time'])}"
        tid = self.canvas.create_text(
            LABEL_W + pad + 8, (y1 + y2) / 2,
            text=label, anchor="w",
            fill="white", font=("", 11, "bold"), tags=ev_tag
        )

        for item in (rid, tid):
            self._ev_items[item] = ev["id"]

        self.canvas.tag_bind(
            ev_tag, "<Double-Button-1>",
            lambda e, eid=ev["id"]: self._show_event_popup(eid, e.x_root, e.y_root)
        )

    # ── Mouse: drag-to-create ────────────────────────────────────────────────

    def _on_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        hits = self.canvas.find_overlapping(cx - 2, cy - 2, cx + 2, cy + 2)
        for h in hits:
            if h in self._ev_items:
                return  # clicking an existing event — double-click handles it
        self._drag_start = cy

    def _on_drag(self, event):
        if self._drag_start is None:
            return
        cy = self.canvas.canvasy(event.y)
        w  = self.canvas.winfo_width()
        y1 = min(self._drag_start, cy)
        y2 = max(self._drag_start, cy)
        if self._drag_rect is None and abs(cy - self._drag_start) > 6:
            self._drag_rect = self.canvas.create_rectangle(
                LABEL_W + 3, y1, w - 3, y2,
                fill="#4A90E2", outline="#6baee8", tags="drag"
            )
        elif self._drag_rect:
            self.canvas.coords(self._drag_rect, LABEL_W + 3, y1, w - 3, y2)

    def _on_release(self, event):
        if self._drag_start is None:
            return
        cy = self.canvas.canvasy(event.y)
        if self._drag_rect:
            self.canvas.delete("drag")
            y1    = min(self._drag_start, cy)
            y2    = max(self._drag_start, cy)
            start = y_to_time(y1)
            end   = y_to_time(y2)
            if start != end:
                self._create_event_dialog(start, end)
        self._drag_start = None
        self._drag_rect  = None

    def _create_event_dialog(self, start: str, end: str):
        color = EVENT_COLORS[self.db.get_total_event_count() % len(EVENT_COLORS)]
        dlg   = ctk.CTkInputDialog(
            text=f"Name this event\n{fmt_time(start)} → {fmt_time(end)}",
            title="New Event",
        )
        name = dlg.get_input()
        if name is not None:
            self.db.add_event(
                self.current_date.isoformat(), start, end, name.strip(), color
            )
            self._redraw()

    def _show_event_popup(self, event_id: int, rx: int, ry: int):
        events = self.db.get_events(self.current_date.isoformat())
        ev     = next((e for e in events if e["id"] == event_id), None)
        if not ev:
            return
        win = ctk.CTkToplevel(self)
        win.title("")
        win.geometry(f"210x110+{rx + 8}+{ry}")
        win.resizable(False, False)
        win.grab_set()
        ctk.CTkLabel(win, text=ev["title"] or "Untitled",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(padx=12, pady=(14, 2))
        ctk.CTkLabel(win,
                     text=f"{fmt_time(ev['start_time'])} – {fmt_time(ev['end_time'])}",
                     font=ctk.CTkFont(size=11),
                     text_color=("gray50", "gray55")).pack()
        ctk.CTkButton(win, text="Delete", fg_color="#D0021B",
                      hover_color="#a80000", width=100, height=28,
                      command=lambda: [win.destroy(),
                                       self._delete_event(event_id)]).pack(pady=12)

    def _delete_event(self, event_id: int):
        self.db.delete_event(event_id)
        self._redraw()

    # ── Navigation ───────────────────────────────────────────────────────────

    def _on_resize(self, _event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._redraw)

    def _prev_day(self):
        self.current_date -= timedelta(days=1)
        self._update_date_label()
        self._redraw()

    def _next_day(self):
        self.current_date += timedelta(days=1)
        self._update_date_label()
        self._redraw()

    def _go_today(self):
        self.current_date = date.today()
        self._update_date_label()
        self._redraw()
        self._scroll_to_now()

    def _scroll_to_now(self):
        if self.current_date == date.today():
            now     = datetime.now()
            y       = (now.hour - START_HOUR + now.minute / 60) * HOUR_HEIGHT
            total_h = (END_HOUR - START_HOUR) * HOUR_HEIGHT
            self.canvas.yview_moveto(max(0.0, (y - 120) / total_h))

    def _update_date_label(self):
        today = date.today()
        if self.current_date == today:
            prefix = "Today"
        elif self.current_date == today + timedelta(days=1):
            prefix = "Tomorrow"
        elif self.current_date == today - timedelta(days=1):
            prefix = "Yesterday"
        else:
            prefix = self.current_date.strftime("%A")
        self.date_label.configure(
            text=f"{prefix}, {self.current_date.strftime('%B')} {self.current_date.day}"
        )
