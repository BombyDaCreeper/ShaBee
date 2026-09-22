import customtkinter as ctk
from datetime import date

COLORS = [
    "#4A90E2",  # blue
    "#7ED321",  # green
    "#F5A623",  # orange
    "#BD10E0",  # purple
    "#D0021B",  # red
    "#50E3C2",  # teal
    "#FF6B6B",  # coral
    "#9B59B6",  # violet
]


class HabitsPanel(ctk.CTkFrame):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self.today = date.today().isoformat()
        self._build()

    def _build(self):
        self.configure(fg_color=("gray96", "gray13"))

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            header, text="Habits", font=ctk.CTkFont(size=17, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Add Habit", width=90, height=28,
            command=self._add_habit_dialog
        ).pack(side="right")

        ctk.CTkLabel(
            self,
            text=date.today().strftime("%A, %B %-d"),
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
        ).pack(anchor="w", padx=16, pady=(0, 6))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._load_habits()

    def _load_habits(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        habits = self.db.get_habits()
        if not habits:
            ctk.CTkLabel(
                self.scroll,
                text="No habits yet — add one to start tracking!",
                text_color=("gray55", "gray50"),
                font=ctk.CTkFont(size=12),
            ).pack(pady=24)
            return

        for habit in habits:
            self._make_habit_row(habit)

    def _make_habit_row(self, habit: dict):
        done   = self.db.is_habit_done(habit["id"], self.today)
        status = self.db.get_habit_status(habit["id"])
        state  = status["status"]

        has_sublabel = state in ("grace", "restarting")
        row_h = 62 if has_sublabel else 46

        row = ctk.CTkFrame(self.scroll, height=row_h, corner_radius=8,
                           fg_color=("gray88", "gray17"))
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        # Colored left stripe
        ctk.CTkFrame(
            row, width=4, height=32, corner_radius=2, fg_color=habit["color"]
        ).pack(side="left", padx=(8, 6), pady=7)

        # Checkbox
        var = ctk.BooleanVar(value=done)
        ctk.CTkCheckBox(
            row, text="", variable=var, width=24, height=24,
            checkmark_color="white",
            command=lambda hid=habit["id"]: self._toggle(hid),
        ).pack(side="left", padx=(0, 6))

        # Right side: streak badge + delete
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=(0, 4))

        ctk.CTkButton(
            right, text="✕", width=26, height=26,
            fg_color="transparent",
            hover_color=("gray75", "gray28"),
            text_color=("gray55", "gray55"),
            font=ctk.CTkFont(size=11),
            command=lambda hid=habit["id"]: self._delete(hid),
        ).pack(side="right", padx=(0, 2))

        # Streak/status badge
        if state == "active" and status["streak"] > 0:
            ctk.CTkLabel(
                right,
                text=f"🔥 {status['streak']}",
                font=ctk.CTkFont(size=11),
                text_color="#F5A623",
            ).pack(side="right", padx=(0, 4))

        elif state == "grace":
            badge = ctk.CTkFrame(right, fg_color="transparent")
            badge.pack(side="right", padx=(0, 4))
            ctk.CTkLabel(
                badge,
                text=f"🔥 {status['streak']}",
                font=ctk.CTkFont(size=11),
                text_color=("gray55", "gray50"),
            ).pack()
            ctk.CTkLabel(
                badge,
                text=f"{status['days_left']}d to restart",
                font=ctk.CTkFont(size=9),
                text_color=("gray55", "gray50"),
            ).pack()

        elif state == "restarting":
            badge = ctk.CTkFrame(right, fg_color="transparent")
            badge.pack(side="right", padx=(0, 4))
            ctk.CTkLabel(
                badge,
                text=f"🔥 {status['restart_progress']}/3",
                font=ctk.CTkFont(size=11),
                text_color=("gray55", "gray50"),
            ).pack()
            ctk.CTkLabel(
                badge,
                text=f"{status['days_left']}d left",
                font=ctk.CTkFont(size=9),
                text_color=("gray55", "gray50"),
            ).pack()

        # Habit name (center, fills remaining space)
        ctk.CTkLabel(
            row, text=habit["name"], anchor="w",
            font=ctk.CTkFont(size=13, overstrike=done),
            text_color=("gray60", "gray55") if done else ("gray10", "gray90"),
        ).pack(side="left", fill="x", expand=True)

    # ── Actions ─────────────────────────────────────────────────────────────

    def _toggle(self, habit_id: int):
        self.db.toggle_habit(habit_id, self.today)
        self._load_habits()

    def _delete(self, habit_id: int):
        self.db.delete_habit(habit_id)
        self._load_habits()

    def _add_habit_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter habit name:", title="New Habit")
        name = dialog.get_input()
        if name and name.strip():
            existing = self.db.get_habits()
            color = COLORS[len(existing) % len(COLORS)]
            self.db.add_habit(name.strip(), color)
            self._load_habits()
