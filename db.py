import sqlite3
import os
from datetime import date, timedelta, datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shabee.db")


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._migrate()
        self._startup_cleanup()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT    NOT NULL,
                start_time TEXT    NOT NULL,
                end_time   TEXT    NOT NULL,
                title      TEXT    DEFAULT '',
                color      TEXT    NOT NULL DEFAULT '#4A90E2',
                created_at TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS habits (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                color        TEXT    DEFAULT '#4A90E2',
                created_date TEXT    NOT NULL,
                archived     INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS habit_completions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                date     TEXT    NOT NULL,
                UNIQUE(habit_id, date),
                FOREIGN KEY(habit_id) REFERENCES habits(id)
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                title          TEXT    NOT NULL,
                note           TEXT    DEFAULT '',
                due_date       TEXT,
                completed      INTEGER DEFAULT 0,
                completed_date TEXT,
                created_date   TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tags (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT    NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS reminder_tags (
                reminder_id INTEGER NOT NULL,
                tag_id      INTEGER NOT NULL,
                PRIMARY KEY (reminder_id, tag_id),
                FOREIGN KEY (reminder_id) REFERENCES reminders(id),
                FOREIGN KEY (tag_id)      REFERENCES tags(id)
            );
        """)
        self.conn.commit()

    def _migrate(self):
        # Add completed_date column to existing DBs that predate it
        try:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN completed_date TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    def _startup_cleanup(self):
        today = date.today().isoformat()
        # Delete schedule events older than 7 days
        cutoff = (date.today() - timedelta(days=7)).isoformat()
        self.conn.execute("DELETE FROM events WHERE date < ?", (cutoff,))
        # Delete completed reminders finished on a previous day
        self.conn.execute(
            "DELETE FROM reminders WHERE completed=1"
            " AND completed_date IS NOT NULL AND completed_date < ?",
            (today,),
        )
        self.conn.commit()

    # ── Events ───────────────────────────────────────────────────────────────

    def get_events(self, date_str: str) -> list:
        cur = self.conn.execute(
            "SELECT * FROM events WHERE date=? ORDER BY start_time", (date_str,)
        )
        return [dict(row) for row in cur.fetchall()]

    def add_event(self, date_str: str, start_time: str, end_time: str,
                  title: str, color: str) -> int:
        cur = self.conn.execute(
            """INSERT INTO events (date, start_time, end_time, title, color, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date_str, start_time, end_time, title, color, datetime.now().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_event(self, event_id: int):
        self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.conn.commit()

    def get_total_event_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    # ── Habits ───────────────────────────────────────────────────────────────

    def get_habits(self) -> list:
        cur = self.conn.execute("SELECT * FROM habits WHERE archived=0 ORDER BY id")
        return [dict(row) for row in cur.fetchall()]

    def add_habit(self, name: str, color: str = "#4A90E2") -> int:
        cur = self.conn.execute(
            "INSERT INTO habits (name, color, created_date) VALUES (?, ?, ?)",
            (name, color, date.today().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_habit(self, habit_id: int):
        self.conn.execute("DELETE FROM habit_completions WHERE habit_id=?", (habit_id,))
        self.conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
        self.conn.commit()

    def is_habit_done(self, habit_id: int, date_str: str) -> bool:
        cur = self.conn.execute(
            "SELECT id FROM habit_completions WHERE habit_id=? AND date=?",
            (habit_id, date_str),
        )
        return cur.fetchone() is not None

    def toggle_habit(self, habit_id: int, date_str: str):
        if self.is_habit_done(habit_id, date_str):
            self.conn.execute(
                "DELETE FROM habit_completions WHERE habit_id=? AND date=?",
                (habit_id, date_str),
            )
        else:
            self.conn.execute(
                "INSERT OR IGNORE INTO habit_completions (habit_id, date) VALUES (?, ?)",
                (habit_id, date_str),
            )
        self.conn.commit()

    def get_habit_status(self, habit_id: int) -> dict:
        """
        Returns:
          streak          – length of the relevant consecutive run
          status          – "active" | "restarting" | "grace" | "lost" | "none"
          restart_progress – days done in the current restart attempt (0-2)
          days_left       – grace days remaining (0-3)

        States
        ──────
        active     : consecutive run ends today or yesterday; no recent gap ≤ 3 days,
                     OR a gap of 1-3 days existed but 3 consecutive restart days were done.
        grace      : missed ≥ 1 day; no restart started yet; still within 3-day window.
        restarting : missed 1-3 days ago; currently doing consecutive days again (< 3 done).
        lost       : grace window (3 days) expired without completing a restart.
        none       : never done this habit.
        """
        today = date.today()
        cur = self.conn.execute(
            "SELECT date FROM habit_completions WHERE habit_id=? ORDER BY date DESC",
            (habit_id,),
        )
        done = {date.fromisoformat(row[0]) for row in cur.fetchall()}

        if not done:
            return dict(streak=0, status="none", restart_progress=0, days_left=0)

        def count_back(from_d: date) -> int:
            n, d = 0, from_d
            while d in done:
                n += 1
                d -= timedelta(days=1)
            return n

        # ── Find current run end (today or yesterday counts as active) ────────
        yesterday = today - timedelta(days=1)
        run_end = today if today in done else (yesterday if yesterday in done else None)

        if run_end is not None:
            run_len   = count_back(run_end)
            run_start = run_end - timedelta(days=run_len - 1)
            prev_done = max((d for d in done if d < run_start), default=None)

            if prev_done is None:
                # Fresh run with no prior history
                return dict(streak=run_len, status="active",
                            restart_progress=0, days_left=0)

            gap = (run_start - prev_done).days - 1  # missed days before this run

            if gap > 3 or run_len >= 3:
                # Gap too old to care about, OR restart just completed (≥3 in a row)
                return dict(streak=run_len, status="active",
                            restart_progress=0, days_left=0)

            # Grace window: restart underway but not yet complete
            original        = count_back(prev_done)
            break_date      = prev_done + timedelta(days=1)
            days_since_break = (today - break_date).days
            days_left        = max(0, 3 - days_since_break)
            return dict(streak=original, status="restarting",
                        restart_progress=run_len, days_left=days_left)

        # ── Neither today nor yesterday is done ───────────────────────────────
        last_done        = max(done)
        original         = count_back(last_done)
        break_date       = last_done + timedelta(days=1)
        days_since_break = (today - break_date).days

        if days_since_break > 3:
            return dict(streak=0, status="lost", restart_progress=0, days_left=0)

        days_left = max(0, 3 - days_since_break)
        return dict(streak=original, status="grace",
                    restart_progress=0, days_left=days_left)

    # ── Reminders ────────────────────────────────────────────────────────────

    def get_reminders(self) -> list:
        cur = self.conn.execute(
            """SELECT * FROM reminders
               ORDER BY completed ASC, due_date ASC NULLS LAST, created_date ASC"""
        )
        return [dict(row) for row in cur.fetchall()]

    def add_reminder(self, title: str, note: str = "", due_date: str = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO reminders (title, note, due_date, created_date) VALUES (?, ?, ?, ?)",
            (title, note, due_date, date.today().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def toggle_reminder(self, reminder_id: int):
        cur = self.conn.execute(
            "SELECT completed FROM reminders WHERE id=?", (reminder_id,)
        )
        currently = bool(cur.fetchone()[0])
        if currently:
            self.conn.execute(
                "UPDATE reminders SET completed=0, completed_date=NULL WHERE id=?",
                (reminder_id,),
            )
        else:
            self.conn.execute(
                "UPDATE reminders SET completed=1, completed_date=? WHERE id=?",
                (date.today().isoformat(), reminder_id),
            )
        self.conn.commit()

    def delete_reminder(self, reminder_id: int):
        self.conn.execute("DELETE FROM reminder_tags WHERE reminder_id=?", (reminder_id,))
        self.conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
        self.conn.commit()

    # ── Tags ─────────────────────────────────────────────────────────────────

    def get_all_tags(self) -> list:
        cur = self.conn.execute("SELECT * FROM tags ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def get_or_create_tag(self, name: str):
        name = name.strip().lower()
        if not name:
            return None
        cur = self.conn.execute("SELECT id FROM tags WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur = self.conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        self.conn.commit()
        return cur.lastrowid

    def get_reminder_tags(self, reminder_id: int) -> list:
        cur = self.conn.execute(
            """SELECT t.* FROM tags t
               JOIN reminder_tags rt ON t.id = rt.tag_id
               WHERE rt.reminder_id=? ORDER BY t.name""",
            (reminder_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def set_reminder_tags(self, reminder_id: int, tag_ids: list):
        self.conn.execute(
            "DELETE FROM reminder_tags WHERE reminder_id=?", (reminder_id,)
        )
        for tag_id in tag_ids:
            if tag_id:
                self.conn.execute(
                    "INSERT OR IGNORE INTO reminder_tags (reminder_id, tag_id) VALUES (?, ?)",
                    (reminder_id, tag_id),
                )
        self.conn.commit()

    def close(self):
        self.conn.close()
