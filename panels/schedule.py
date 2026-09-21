import customtkinter as ctk
from datetime import date, datetime, timedelta

HOURS = list(range(6, 24))  # 6 AM → 11 PM

HOUR_LABELS = {
    0: "12 AM", 1: "1 AM",  2: "2 AM",  3: "3 AM",
    4: "4 AM",  5: "5 AM",  6: "6 AM",  7: "7 AM",
    8: "8 AM",  9: "9 AM",  10: "10 AM", 11: "11 AM",
    12: "12 PM", 13: "1 PM", 14: "2 PM", 15: "3 PM",
    16: "4 PM", 17: "5 PM", 18: "6 PM", 19: "7 PM",
    20: "8 PM", 21: "9 PM", 22: "10 PM", 23: "11 PM",
}


class SchedulePanel(ctk.CTkFrame):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self.current_date = date.today()
        self._build()

    def _build(self):
        self.configure(fg_color=("gray92", "gray14"))

        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 6))

        nav_left = ctk.CTkFrame(header, fg_color="transparent")
        nav_left.pack(side="left")

        self.date_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.date_label.pack(side="left", expand=True, fill="x")

        nav_right = ctk.CTkFrame(header, fg_color="transparent")
        nav_right.pack(side="right")

        ctk.CTkButton(
            nav_right, text="Today", width=60, height=28,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("gray10", "gray90"),
            command=self._go_today
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            nav_right, text="›", width=30, height=28,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("gray10", "gray90"), font=ctk.CTkFont(size=16),
            command=self._next_day
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            nav_right, text="‹", width=30, height=28,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("gray10", "gray90"), font=ctk.CTkFont(size=16),
            command=self._prev_day
        ).pack(side="right", padx=2)

        # ── Scrollable time blocks ───────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.scroll.columnconfigure(0, weight=1)

        self.block_entries: dict[int, ctk.CTkEntry] = {}
        for i, hour in enumerate(HOURS):
            self._make_block(hour, i)

        self._update_date_label()
        self._load_blocks()

    def _make_block(self, hour: int, index: int):
        is_current = date.today() == self.current_date and hour == datetime.now().hour

        row = ctk.CTkFrame(
            self.scroll,
            height=50,
            corner_radius=8,
            fg_color=("gray85", "gray18") if index % 2 == 0 else ("gray90", "gray16"),
            border_width=2 if is_current else 0,
            border_color=("#4A90E2", "#4A90E2"),
        )
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        ctk.CTkLabel(
            row,
            text=HOUR_LABELS[hour],
            width=58,
            anchor="e",
            font=ctk.CTkFont(size=11),
            text_color=("#4A90E2" if is_current else ("gray40", "gray60")),
        ).pack(side="left", padx=(10, 4))

        ctk.CTkFrame(
            row, width=2, height=28, corner_radius=1,
            fg_color=("gray70", "gray40")
        ).pack(side="left", padx=(0, 6))

        entry = ctk.CTkEntry(
            row,
            placeholder_text="Add a plan…",
            border_width=0,
            fg_color="transparent",
            font=ctk.CTkFont(size=13),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        entry.bind("<FocusOut>", lambda _e, h=hour: self._save_block(h))
        entry.bind("<Return>", lambda _e, h=hour: self._save_block(h))

        self.block_entries[hour] = entry

    # ── Data ────────────────────────────────────────────────────────────────

    def _save_block(self, hour: int):
        title = self.block_entries[hour].get().strip()
        self.db.upsert_time_block(self.current_date.isoformat(), hour, title)

    def _save_all(self):
        for hour in HOURS:
            self._save_block(hour)

    def _load_blocks(self):
        blocks = self.db.get_time_blocks(self.current_date.isoformat())
        for hour, entry in self.block_entries.items():
            entry.delete(0, "end")
            if hour in blocks and blocks[hour]["title"]:
                entry.insert(0, blocks[hour]["title"])

    # ── Navigation ──────────────────────────────────────────────────────────

    def _prev_day(self):
        self._save_all()
        self.current_date -= timedelta(days=1)
        self._update_date_label()
        self._load_blocks()

    def _next_day(self):
        self._save_all()
        self.current_date += timedelta(days=1)
        self._update_date_label()
        self._load_blocks()

    def _go_today(self):
        self._save_all()
        self.current_date = date.today()
        self._update_date_label()
        self._load_blocks()

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
        month = self.current_date.strftime("%B")
        day = self.current_date.day
        self.date_label.configure(text=f"{prefix}, {month} {day}")
