import json
import logging
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .config import BASE_URL, GUI_SETTINGS_PATH, PASSWORD, USERNAME
from .selenium_bot import GladiatusBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GladiatusGUI:
    BG = "#0f172a"
    PANEL = "#111827"
    PANEL_ALT = "#1f2937"
    TEXT = "#e5e7eb"
    MUTED = "#94a3b8"
    ACCENT = "#38bdf8"
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"

    def __init__(self, root):
        self.root = root
        self.root.title("Gladiatus Bot Control")
        self.root.geometry("920x680")
        self.root.minsize(820, 620)
        self.root.configure(bg=self.BG)

        self.bot = None
        self.login_thread = None
        self.play_thread = None
        self.playing = False
        self.captcha_detected = False
        self.captcha_solved = False

        self.status_var = tk.StringVar(value="Ready")
        self.hp_var = tk.StringVar(value="HP: --")

        self.expedition_var = tk.BooleanVar(value=True)
        self.dungeon_var = tk.BooleanVar(value=True)
        self.circus_var = tk.BooleanVar(value=True)
        self.refill_hp_var = tk.BooleanVar(value=False)
        self.hp_min_var = tk.StringVar(value="25")

        self._settings_suspended = True
        self._configure_styles()
        self._build_layout()
        self._load_settings()
        self._bind_settings_watchers()
        self._settings_suspended = False
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=self.BG, foreground=self.TEXT)
        style.configure("App.TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("PanelAlt.TFrame", background=self.PANEL_ALT)
        style.configure("CardTitle.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI Semibold", 12))
        style.configure("Muted.TLabel", background=self.PANEL, foreground=self.MUTED, font=("Segoe UI", 10))
        style.configure("Value.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI Semibold", 16))
        style.configure("Status.TLabel", background=self.PANEL_ALT, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Section.TLabelframe", background=self.PANEL, foreground=self.TEXT)
        style.configure("Section.TLabelframe.Label", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Modern.TCheckbutton", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI", 10))
        style.map("Modern.TCheckbutton", background=[("active", self.PANEL)])
        style.configure(
            "Primary.TButton",
            background=self.ACCENT,
            foreground="#0f172a",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI Semibold", 10),
            padding=(12, 8),
        )
        style.map("Primary.TButton", background=[("active", "#7dd3fc"), ("disabled", "#475569")], foreground=[("disabled", "#cbd5e1")])
        style.configure(
            "Danger.TButton",
            background=self.DANGER,
            foreground="white",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI Semibold", 10),
            padding=(12, 8),
        )
        style.map("Danger.TButton", background=[("active", "#f87171"), ("disabled", "#475569")], foreground=[("disabled", "#cbd5e1")])

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = ttk.Frame(self.root, style="App.TFrame", padding=18)
        shell.grid(sticky="nsew")
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell, style="PanelAlt.TFrame", padding=18)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Gladiatus Bot",
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 22),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Daha temiz kontrol, daha guvenli mekanik gecisleri ve canli durum takibi.",
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.status_badge = tk.Label(
            header,
            textvariable=self.status_var,
            bg="#0b1220",
            fg=self.ACCENT,
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=6,
        )
        self.status_badge.grid(row=0, column=1, rowspan=2, sticky="e")

        left = ttk.Frame(shell, style="App.TFrame")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)

        right = ttk.Frame(shell, style="App.TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self._build_credentials_panel(left)
        self._build_controls_panel(left)
        self._build_mechanics_panel(left)
        self._build_log_panel(left)

        self._build_status_panel(right)
        self._build_notes_panel(right)

    def _build_credentials_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Hesap", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Giristen sonra ayni oturum uzerinden mekanikler doner.", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))

        tk.Label(panel, text="Email", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")
        tk.Label(panel, text="Password", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=2, column=1, sticky="w")

        self.email_entry = tk.Entry(
            panel,
            bg="#0b1220",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.email_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), ipady=8)
        if USERNAME:
            self.email_entry.insert(0, USERNAME)

        self.password_entry = tk.Entry(
            panel,
            show="*",
            bg="#0b1220",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.password_entry.grid(row=3, column=1, sticky="ew", ipady=8)
        if PASSWORD:
            self.password_entry.insert(0, PASSWORD)

        self.login_btn = ttk.Button(panel, text="Login", style="Primary.TButton", command=self.start_login)
        self.login_btn.grid(row=4, column=0, sticky="w", pady=(14, 0))

        self.captcha_btn = ttk.Button(
            panel,
            text="CAPTCHA Solved - Continue",
            style="Danger.TButton",
            command=self.captcha_solved_callback,
            state="disabled",
        )
        self.captcha_btn.grid(row=4, column=1, sticky="e", pady=(14, 0))

    def _build_controls_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Kontrol", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text="Play dongusu 60 saniyede bir secili mekanikleri sirayla dener.", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))

        self.play_btn = ttk.Button(panel, text="Play", style="Primary.TButton", command=self.toggle_play)
        self.play_btn.grid(row=2, column=0, sticky="ew", padx=(0, 8))

        self.stop_btn = ttk.Button(panel, text="Stop", style="Danger.TButton", command=self.stop_play)
        self.stop_btn.grid(row=2, column=1, sticky="ew")
        self.stop_btn.config(state="disabled")

    def _build_mechanics_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="Mekanikler", style="Section.TLabelframe", padding=16)
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        ttk.Checkbutton(panel, text="Expedition", variable=self.expedition_var, style="Modern.TCheckbutton").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Checkbutton(panel, text="Dungeon", variable=self.dungeon_var, style="Modern.TCheckbutton").grid(row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(panel, text="Circus Turma", variable=self.circus_var, style="Modern.TCheckbutton").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Checkbutton(panel, text="Refill HP", variable=self.refill_hp_var, style="Modern.TCheckbutton").grid(row=1, column=1, sticky="w", pady=4)

        hp_row = ttk.Frame(panel, style="Panel.TFrame")
        hp_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        tk.Label(hp_row, text="Min HP %", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).pack(side="left")
        self.hp_spinbox = tk.Spinbox(
            hp_row,
            from_=1,
            to=99,
            width=5,
            textvariable=self.hp_min_var,
            bg="#0b1220",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.hp_spinbox.pack(side="left", padx=(10, 0), ipady=4)

    def _build_log_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=3, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        ttk.Label(panel, text="Activity Log", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.log_text = tk.Text(
            panel,
            height=16,
            wrap="word",
            bg="#08111f",
            fg="#dbeafe",
            insertbackground="#dbeafe",
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        log_scroll = ttk.Scrollbar(panel, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _build_status_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Durum", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        self.hp_value = tk.Label(panel, textvariable=self.hp_var, bg=self.PANEL, fg=self.SUCCESS, font=("Segoe UI Semibold", 18))
        self.hp_value.grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 8))

        self.mode_value = tk.Label(panel, text="Idle", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 11))
        self.mode_value.grid(row=2, column=0, sticky="w")

        self.loop_value = tk.Label(panel, text="Dongu bekliyor", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 11))
        self.loop_value.grid(row=2, column=1, sticky="e")

    def _build_notes_panel(self, parent):
        panel = ttk.Frame(parent, style="PanelAlt.TFrame", padding=16)
        panel.grid(row=1, column=0, sticky="ew")
        tk.Label(panel, text="Neler degisti?", bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI Semibold", 12)).pack(anchor="w")
        tk.Label(
            panel,
            text=(
                "Mekanik gecisleri daha guvenli. Bot artik hedef sayfa acilmadan mob aramiyor "
                "ve aksiyonlardan sonra overviewe donerek bir sonraki adimi daha temiz baslatiyor."
            ),
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            justify="left",
            wraplength=280,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(8, 0))

    def _bind_settings_watchers(self):
        for variable in (self.expedition_var, self.dungeon_var, self.circus_var, self.refill_hp_var, self.hp_min_var):
            variable.trace_add("write", self._on_settings_changed)

    def _on_settings_changed(self, *args):
        if self._settings_suspended:
            return
        self._save_settings()

    def _collect_settings(self):
        return {
            "expedition": bool(self.expedition_var.get()),
            "dungeon": bool(self.dungeon_var.get()),
            "circus": bool(self.circus_var.get()),
            "refill_hp": bool(self.refill_hp_var.get()),
            "hp_min": self.hp_min_var.get().strip() or "25",
        }

    def _coerce_bool(self, value, default):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    def _load_settings(self):
        try:
            path = Path(GUI_SETTINGS_PATH)
            if not path.exists():
                return

            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            if not isinstance(data, dict):
                return

            self.expedition_var.set(self._coerce_bool(data.get("expedition"), True))
            self.dungeon_var.set(self._coerce_bool(data.get("dungeon"), True))
            self.circus_var.set(self._coerce_bool(data.get("circus"), True))
            self.refill_hp_var.set(self._coerce_bool(data.get("refill_hp"), False))

            hp_min = data.get("hp_min", "25")
            self.hp_min_var.set(str(hp_min))
        except Exception as exc:
            logger.warning("Could not load GUI settings: %s", exc)

    def _save_settings(self):
        try:
            path = Path(GUI_SETTINGS_PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(self._collect_settings(), handle, indent=2)
        except Exception as exc:
            logger.warning("Could not save GUI settings: %s", exc)

    def _on_close(self):
        self._save_settings()
        try:
            self.stop_play()
        except Exception:
            pass
        try:
            if self.bot:
                self.bot.quit()
        except Exception:
            pass
        self.root.destroy()

    def _ui(self, callback):
        self.root.after(0, callback)

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_badge.config(fg=color)

    def _set_login_widgets_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.login_btn.config(state=state)
        self.email_entry.config(state=state)
        self.password_entry.config(state=state)

    def _set_captcha_enabled(self, enabled):
        self.captcha_btn.config(state="normal" if enabled else "disabled")

    def _set_play_state(self, playing):
        if playing:
            self.play_btn.config(text="Playing", state="disabled")
            self.stop_btn.config(state="normal")
            self.mode_value.config(text="Auto mode active", fg=self.SUCCESS)
            self.loop_value.config(text="Dongu calisiyor", fg=self.ACCENT)
        else:
            self.play_btn.config(text="Play", state="normal")
            self.stop_btn.config(state="disabled")
            self.mode_value.config(text="Idle", fg=self.MUTED)
            self.loop_value.config(text="Dongu bekliyor", fg=self.MUTED)

    def start_login(self):
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()

        if not email or not password:
            messagebox.showerror("Error", "Please enter email and password")
            return

        self.captcha_solved = False
        self.captcha_detected = False
        self._set_login_widgets_enabled(False)
        self._set_captcha_enabled(False)
        self.update_status("Logging in...", self.ACCENT)
        self.append_log("Login started")

        self.login_thread = threading.Thread(target=self.login_worker, args=(email, password), daemon=True)
        self.login_thread.start()

    def login_worker(self, email, password):
        try:
            self.bot = GladiatusBot(headless=False)
            ok = self.bot.login(BASE_URL, email, password)

            if not ok:
                self.update_status("Login failed", self.DANGER)
                self.append_log("Login failed")
                self._ui(lambda: self._set_login_widgets_enabled(True))
                return

            self.update_status("Checking CAPTCHA...", self.ACCENT)

            captcha_found = False
            for _ in range(6):
                if self.detect_captcha():
                    captcha_found = True
                    break
                time.sleep(0.5)

            if captcha_found:
                self.captcha_detected = True
                self.update_status("CAPTCHA detected", self.WARNING)
                self.append_log("CAPTCHA detected; waiting for manual solve")
                self._ui(lambda: self._set_captcha_enabled(True))

                timeout = 300
                waited = 0
                while waited < timeout and not self.captcha_solved:
                    time.sleep(1)
                    waited += 1

                if not self.captcha_solved:
                    self.update_status("CAPTCHA timeout", self.DANGER)
                    self.append_log("CAPTCHA solve timed out")
                    self._ui(lambda: self._set_login_widgets_enabled(True))
                    self._ui(lambda: self._set_captcha_enabled(False))
                    return

                self.update_status("Continuing after CAPTCHA...", self.ACCENT)
                self.append_log("CAPTCHA confirmed by user")
            else:
                self.update_status("No CAPTCHA detected", self.SUCCESS)
                self.append_log("Login passed without CAPTCHA")

            self.bot.close_overlays()
            time.sleep(0.2)

            clicked = self.bot.click_last_played_button()
            if clicked:
                self.update_status("Bot ready", self.SUCCESS)
                self.append_log("Last Played opened successfully")
                self.refresh_hp_label()
            else:
                self.update_status("Last Played not found", self.WARNING)
                self.append_log("Last Played button not found")

            self._ui(lambda: self._set_login_widgets_enabled(True))
            self._ui(lambda: self._set_captcha_enabled(False))
        except Exception as exc:
            logger.error("Login worker error: %s", exc)
            self.update_status(f"Error: {str(exc)[:40]}", self.DANGER)
            self.append_log(f"Login error: {exc}")
            self._ui(lambda: self._set_login_widgets_enabled(True))
            self._ui(lambda: self._set_captcha_enabled(False))

    def detect_captcha(self):
        try:
            if not self.bot or not self.bot.driver:
                return False

            iframes = self.bot.driver.find_elements("tag name", "iframe")
            for iframe in iframes:
                src = (iframe.get_attribute("src") or "").lower()
                if "challenge" in src or "captcha" in src:
                    return True

            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            try:
                WebDriverWait(self.bot.driver, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-challenge-id]"))
                )
                return True
            except Exception:
                return False
        except Exception as exc:
            logger.error("CAPTCHA detection error: %s", exc)
            return False

    def captcha_solved_callback(self):
        self.captcha_solved = True
        self._set_captcha_enabled(False)

    def refresh_hp_label(self):
        try:
            if not self.bot:
                return
            hp = self.bot.get_hp_status()
            if hp and hp.get("current") is not None and hp.get("max") is not None:
                text = f"HP: {hp['current']} / {hp['max']} ({hp['percent']}%)"
            elif hp and hp.get("percent") is not None:
                text = f"HP: {hp['percent']}%"
            else:
                text = "HP: --"
            self._ui(lambda: self.hp_var.set(text))
        except Exception:
            pass

    def get_min_hp_percent(self):
        try:
            value = int(self.hp_min_var.get())
            return max(1, min(99, value))
        except (ValueError, tk.TclError):
            return 25

    def append_log(self, msg):
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            text = f"[{ts}] {msg}\n"
            self._ui(lambda: self._append_log_ui(text))
        except Exception:
            pass

    def _append_log_ui(self, text):
        self.log_text.insert("end", text)
        self.log_text.see("end")

    def toggle_play(self):
        if not self.bot:
            messagebox.showerror("Error", "Bot not running. Please login first.")
            return
        if not self.playing:
            self.playing = True
            self._set_play_state(True)
            self.update_status("Playing...", self.SUCCESS)
            self.append_log("Play started")
            self.play_thread = threading.Thread(target=self.play_loop, daemon=True)
            self.play_thread.start()
        else:
            self.stop_play()

    def stop_play(self):
        if self.playing:
            self.playing = False
            self.update_status("Stopped", self.WARNING)
            self.append_log("Play stopped by user")
        self._ui(lambda: self._set_play_state(False))

    def play_loop(self):
        while self.playing:
            try:
                if not self.bot:
                    self.append_log("Bot instance missing, stopping")
                    self.playing = False
                    break

                min_hp = self.get_min_hp_percent()

                if self.refill_hp_var.get():
                    try:
                        self.bot.attempt_refill_hp_if_needed(
                            min_hp_percent=min_hp, logger_callback=self.append_log
                        )
                    except Exception as exc:
                        self.append_log(f"Refill HP error: {exc}")

                hp_ready = self.bot.is_hp_above_threshold(min_hp)

                if self.expedition_var.get():
                    if hp_ready:
                        self.bot.attempt_expedition_if_ready(logger_callback=self.append_log)
                    else:
                        self.append_log(f"HP at or below {min_hp}%, skipping expedition")
                else:
                    self.append_log("Expedition mechanic disabled")

                if self.dungeon_var.get():
                    try:
                        self.bot.attempt_dungeon_if_ready(logger_callback=self.append_log)
                    except Exception as exc:
                        self.append_log(f"Dungeon attempt error: {exc}")
                else:
                    self.append_log("Dungeon mechanic disabled")

                if self.circus_var.get():
                    try:
                        self.bot.attempt_circus_if_ready(logger_callback=self.append_log)
                    except Exception as exc:
                        self.append_log(f"Circus Turma attempt error: {exc}")
                else:
                    self.append_log("Circus Turma mechanic disabled")

                self.refresh_hp_label()
            except Exception as exc:
                self.append_log(f"Error in play loop: {exc}")

            for remaining in range(60, 0, -1):
                if not self.playing:
                    break
                self._ui(lambda value=remaining: self.loop_value.config(text=f"Sonraki tur {value}s", fg=self.MUTED))
                time.sleep(1)

        self._ui(lambda: self._set_play_state(False))
        self.update_status("Ready", self.ACCENT)

    def update_status(self, text, color):
        self._ui(lambda: self._set_status(text, color))


def run_gui():
    root = tk.Tk()
    gui = GladiatusGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
