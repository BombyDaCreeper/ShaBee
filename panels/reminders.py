import customtkinter as ctk
from datetime import date, timedelta


def _fmt_due(due_str: str) -> str:
    today = date.today()
    try:
        d = date.fromisoformat(due_str)
    except ValueError:
        return due_str
    if d == today:
        return "Today"
    elif d == today + timedelta(days=1):
        return "Tomorrow"
    elif d == today - timedelta(days=1):
        return "Yesterday"
    else:
        return d.strftime("%b %-d")


class RemindersPanel(ctk.CTkFrame):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._build()

    def _build(self):
        self.configure(fg_color=("gray92", "gray12"))

        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header, text="Reminders", font=ctk.CTkFont(size=17, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Add", width=70, height=28,
            command=self._add_dialog
        ).pack(side="right")

        # ── Scrollable reminders list ────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._load_reminders()

    def _load_reminders(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        reminders = self.db.get_reminders()
        if not reminders:
            ctk.CTkLabel(
                self.scroll,
                text="All clear — no reminders!",
                text_color=("gray55", "gray50"),
                font=ctk.CTkFont(size=12),
            ).pack(pady=24)
            return

        for r in reminders:
            self._make_row(r)

    def _make_row(self, r: dict):
        done = bool(r["completed"])
        today = date.today().isoformat()
        overdue = r["due_date"] and r["due_date"] < today and not done

        row = ctk.CTkFrame(self.scroll, height=46, corner_radius=8,
                           fg_color=("gray88", "gray17"))
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        # Left overdue stripe
        stripe_color = "#D0021B" if overdue else ("gray80", "gray25")
        ctk.CTkFrame(
            row, width=4, height=32, corner_radius=2, fg_color=stripe_color
        ).pack(side="left", padx=(8, 6), pady=7)

        # Checkbox
        var = ctk.BooleanVar(value=done)
        ctk.CTkCheckBox(
            row, text="", variable=var, width=24, height=24,
            checkmark_color="white",
            command=lambda rid=r["id"]: self._toggle(rid),
        ).pack(side="left", padx=(0, 6))

        # Title
        ctk.CTkLabel(
            row, text=r["title"], anchor="w",
            font=ctk.CTkFont(size=13, overstrike=done),
            text_color=("gray60", "gray55") if done else
                        ("#D0021B" if overdue else ("gray10", "gray90")),
        ).pack(side="left", fill="x", expand=True)

        # Due date badge
        if r["due_date"]:
            badge_color = "#D0021B" if overdue else ("gray50", "gray55")
            ctk.CTkLabel(
                row, text=_fmt_due(r["due_date"]),
                font=ctk.CTkFont(size=10),
                text_color=badge_color,
            ).pack(side="right", padx=(0, 4))

        # Delete button
        ctk.CTkButton(
            row, text="✕", width=26, height=26,
            fg_color="transparent",
            hover_color=("gray75", "gray28"),
            text_color=("gray55", "gray55"),
            font=ctk.CTkFont(size=11),
            command=lambda rid=r["id"]: self._delete(rid),
        ).pack(side="right", padx=(0, 6))

    # ── Actions ─────────────────────────────────────────────────────────────

    def _toggle(self, reminder_id: int):
        self.db.toggle_reminder(reminder_id)
        self._load_reminders()

    def _delete(self, reminder_id: int):
        self.db.delete_reminder(reminder_id)
        self._load_reminders()

    def _add_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("New Reminder")
        win.geometry("360x210")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="Title", font=ctk.CTkFont(size=13, weight="bold")).pack(
            padx=20, pady=(20, 4), anchor="w"
        )
        title_entry = ctk.CTkEntry(win, width=320, placeholder_text="e.g. Call dentist")
        title_entry.pack(padx=20)
        title_entry.focus()

        ctk.CTkLabel(win, text="Due date (optional)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            padx=20, pady=(14, 4), anchor="w"
        )
        date_entry = ctk.CTkEntry(win, width=320, placeholder_text="YYYY-MM-DD")
        date_entry.pack(padx=20)

        def save():
            title = title_entry.get().strip()
            if not title:
                return
            raw_date = date_entry.get().strip() or None
            # basic format validation
            if raw_date:
                try:
                    date.fromisoformat(raw_date)
                except ValueError:
                    raw_date = None
            self.db.add_reminder(title, due_date=raw_date)
            win.destroy()
            self._load_reminders()

        title_entry.bind("<Return>", lambda _e: save())
        date_entry.bind("<Return>", lambda _e: save())

        ctk.CTkButton(win, text="Add Reminder", width=160, command=save).pack(pady=18)
