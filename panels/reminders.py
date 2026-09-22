import customtkinter as ctk
import tkinter as tk
from datetime import date, timedelta

TAG_PALETTE = [
    "#4A90E2", "#7ED321", "#F5A623", "#BD10E0",
    "#D0021B", "#50E3C2", "#FF6B6B", "#9B59B6",
]


def _tag_color(name: str) -> str:
    return TAG_PALETTE[abs(hash(name)) % len(TAG_PALETTE)]


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
    return d.strftime("%b") + " " + str(d.day)


class RemindersPanel(ctk.CTkFrame):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._build()

    def _build(self):
        self.configure(fg_color=("gray92", "gray12"))

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(header, text="Reminders",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Add", width=70, height=28,
                      command=self._add_dialog).pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._load_reminders()

    # ── List ─────────────────────────────────────────────────────────────────

    def _load_reminders(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        reminders = self.db.get_reminders()
        if not reminders:
            ctk.CTkLabel(self.scroll, text="All clear — no reminders!",
                         text_color=("gray55", "gray50"),
                         font=ctk.CTkFont(size=12)).pack(pady=24)
            return
        for r in reminders:
            self._make_row(r)

    def _make_row(self, r: dict):
        done    = bool(r["completed"])
        today   = date.today().isoformat()
        overdue = r["due_date"] and r["due_date"] < today and not done
        tags    = self.db.get_reminder_tags(r["id"])

        row = ctk.CTkFrame(self.scroll, corner_radius=8, fg_color=("gray88", "gray17"))
        row.pack(fill="x", pady=2)

        # Top line: stripe + checkbox + title + due-date + delete
        top = ctk.CTkFrame(row, fg_color="transparent", height=46)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkFrame(top, width=4, height=32, corner_radius=2,
                     fg_color="#D0021B" if overdue else ("gray80", "gray25")
                     ).pack(side="left", padx=(8, 6), pady=7)

        var = ctk.BooleanVar(value=done)
        ctk.CTkCheckBox(top, text="", variable=var, width=24, height=24,
                        checkmark_color="white",
                        command=lambda rid=r["id"]: self._toggle(rid)
                        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(top, text="✕", width=26, height=26,
                      fg_color="transparent", hover_color=("gray75", "gray28"),
                      text_color=("gray55", "gray55"), font=ctk.CTkFont(size=11),
                      command=lambda rid=r["id"]: self._delete(rid)
                      ).pack(side="right", padx=(0, 6))

        if r["due_date"]:
            bc = "#D0021B" if overdue else ("gray50", "gray55")
            ctk.CTkLabel(top, text=_fmt_due(r["due_date"]),
                         font=ctk.CTkFont(size=10), text_color=bc
                         ).pack(side="right", padx=(0, 4))

        ctk.CTkLabel(top, text=r["title"], anchor="w",
                     font=ctk.CTkFont(size=13, overstrike=done),
                     text_color=("gray60", "gray55") if done else
                                ("#D0021B" if overdue else ("gray10", "gray90"))
                     ).pack(side="left", fill="x", expand=True)

        # Tag chips row (only if there are tags)
        if tags:
            chip_row = ctk.CTkFrame(row, fg_color="transparent")
            chip_row.pack(anchor="w", padx=20, pady=(0, 8))
            for t in tags:
                self._tag_chip(chip_row, t["name"])

    def _tag_chip(self, parent, name: str):
        color = _tag_color(name)
        f = ctk.CTkFrame(parent, corner_radius=10, fg_color=color)
        f.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(f, text=name, font=ctk.CTkFont(size=10),
                     text_color="white").pack(padx=7, pady=2)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _toggle(self, rid: int):
        self.db.toggle_reminder(rid)
        self._load_reminders()

    def _delete(self, rid: int):
        self.db.delete_reminder(rid)
        self._load_reminders()

    # ── Add dialog ───────────────────────────────────────────────────────────

    def _add_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("New Reminder")
        win.geometry("390x340")
        win.resizable(False, False)
        win.grab_set()

        # ── Title ────────────────────────────────────────────────────────────
        ctk.CTkLabel(win, text="Title",
                     font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(padx=20, pady=(20, 4), anchor="w")
        title_e = ctk.CTkEntry(win, width=350, placeholder_text="e.g. Call dentist")
        title_e.pack(padx=20)
        title_e.focus()

        # ── Due date ─────────────────────────────────────────────────────────
        ctk.CTkLabel(win, text="Due date (optional)",
                     font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(padx=20, pady=(12, 4), anchor="w")
        date_e = ctk.CTkEntry(win, width=350, placeholder_text="YYYY-MM-DD")
        date_e.pack(padx=20)

        # ── Tags ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(win, text="Tags — type and press Enter (auto-creates new ones)",
                     font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(padx=20, pady=(12, 4), anchor="w")

        added_tags: list[str] = []

        chip_frame = ctk.CTkFrame(win, fg_color="transparent", height=24)
        chip_frame.pack(padx=20, anchor="w", fill="x")

        tag_e = ctk.CTkEntry(win, width=350, placeholder_text="e.g. work, urgent…")
        tag_e.pack(padx=20, pady=(4, 0))

        # Autocomplete listbox (placed absolutely when needed)
        is_dark = ctk.get_appearance_mode() == "Dark"
        lb = tk.Listbox(
            win,
            height=4,
            bg="#2b2b2b" if is_dark else "#ffffff",
            fg="#ebebeb" if is_dark else "#1c1c1e",
            selectbackground="#4A90E2",
            relief="flat", highlightthickness=1,
            highlightbackground="#4A90E2",
            font=("", 11), borderwidth=0,
        )

        def _refresh_chips():
            for w in chip_frame.winfo_children():
                w.destroy()
            for tname in added_tags:
                color = _tag_color(tname)
                tw = max(60, len(tname) * 9 + 32)
                ctk.CTkButton(
                    chip_frame,
                    text=f"{tname}  ✕",
                    width=tw, height=22,
                    corner_radius=11,
                    fg_color=color, hover_color=color,
                    text_color="white",
                    font=ctk.CTkFont(size=10),
                    command=lambda n=tname: _remove(n),
                ).pack(side="left", padx=(0, 4))

        def _remove(name: str):
            if name in added_tags:
                added_tags.remove(name)
                _refresh_chips()

        def _add_tag(name: str):
            name = name.strip().lower()
            if name and name not in added_tags:
                added_tags.append(name)
            tag_e.delete(0, "end")
            lb.place_forget()
            _refresh_chips()

        def _show_autocomplete():
            typed   = tag_e.get().strip().lower()
            all_t   = self.db.get_all_tags()
            matches = [t["name"] for t in all_t
                       if typed and typed in t["name"] and t["name"] not in added_tags]
            lb.delete(0, "end")
            if not matches:
                lb.place_forget()
                return
            for m in matches:
                lb.insert("end", m)
            win.update_idletasks()
            rx = tag_e.winfo_rootx() - win.winfo_rootx()
            ry = tag_e.winfo_rooty() - win.winfo_rooty() + tag_e.winfo_height() + 2
            lb.place(x=rx, y=ry, width=tag_e.winfo_width(),
                     height=min(len(matches), 4) * 22 + 4)
            lb.lift()

        def _on_tag_key(event):
            if event.keysym in ("Return", "Tab"):
                sel = lb.curselection()
                _add_tag(lb.get(sel[0]) if sel else tag_e.get())
                return "break"
            if event.keysym == "Down":
                lb.focus_set()
                lb.selection_set(0)
                return "break"
            win.after(10, _show_autocomplete)

        def _on_lb_select(_event):
            sel = lb.curselection()
            if sel:
                _add_tag(lb.get(sel[0]))
                tag_e.focus()

        tag_e.bind("<KeyRelease>", _on_tag_key)
        lb.bind("<ButtonRelease-1>", _on_lb_select)
        lb.bind("<Return>", _on_lb_select)

        # ── Save ─────────────────────────────────────────────────────────────
        def _save():
            title = title_e.get().strip()
            if not title:
                return
            # flush any text still in tag entry
            if tag_e.get().strip():
                _add_tag(tag_e.get())
            raw_date = date_e.get().strip() or None
            if raw_date:
                try:
                    date.fromisoformat(raw_date)
                except ValueError:
                    raw_date = None
            rid     = self.db.add_reminder(title, due_date=raw_date)
            tag_ids = [self.db.get_or_create_tag(t) for t in added_tags]
            self.db.set_reminder_tags(rid, [x for x in tag_ids if x])
            win.destroy()
            self._load_reminders()

        title_e.bind("<Return>", lambda _e: _save())

        ctk.CTkButton(win, text="Add Reminder", width=160, command=_save
                      ).pack(pady=16)
