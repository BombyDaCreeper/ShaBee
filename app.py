import customtkinter as ctk
from db import Database
from panels.schedule import SchedulePanel
from panels.habits import HabitsPanel
from panels.reminders import RemindersPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ShaBeeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ShaBee")
        self.geometry("1240x820")
        self.minsize(900, 640)

        self.db = Database()

        # ── Root grid: left schedule | separator | right panels ──────────────
        self.grid_columnconfigure(0, weight=43, minsize=380)
        self.grid_columnconfigure(1, weight=0, minsize=1)
        self.grid_columnconfigure(2, weight=57, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        # Left: schedule
        self.schedule = SchedulePanel(self, self.db, corner_radius=0)
        self.schedule.grid(row=0, column=0, sticky="nsew")

        # Vertical separator
        ctk.CTkFrame(self, width=1, corner_radius=0,
                     fg_color=("gray78", "gray25")).grid(
            row=0, column=1, sticky="ns"
        )

        # Right container
        right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_rowconfigure(0, weight=55, minsize=260)
        right.grid_rowconfigure(1, weight=0, minsize=1)
        right.grid_rowconfigure(2, weight=45, minsize=200)
        right.grid_columnconfigure(0, weight=1)

        # Top-right: habits
        self.habits = HabitsPanel(right, self.db, corner_radius=0)
        self.habits.grid(row=0, column=0, sticky="nsew")

        # Horizontal separator
        ctk.CTkFrame(right, height=1, corner_radius=0,
                     fg_color=("gray78", "gray25")).grid(
            row=1, column=0, sticky="ew"
        )

        # Bottom-right: reminders
        self.reminders = RemindersPanel(right, self.db, corner_radius=0)
        self.reminders.grid(row=2, column=0, sticky="nsew")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.schedule._save_all()
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = ShaBeeApp()
    app.mainloop()
