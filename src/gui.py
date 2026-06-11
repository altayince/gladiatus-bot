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

    EXPEDITION_LOCATIONS = [
        ("Grimwood", "0"),
        ("Pirate Harbour", "1"),
        ("Misty Mountains", "2"),
        ("Wolf Cave", "3"),
        ("Ancient Temple", "4"),
        ("Barbarian Village", "5"),
        ("Bandit Camp", "6"),
    ]
    DUNGEON_LOCATIONS = [label for label, _ in EXPEDITION_LOCATIONS]
    DUNGEON_DIFFICULTIES = ["Normal", "Advanced"]

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
        self.hp_refill_count_var = tk.StringVar(value="Refill pots: --")

        self.expedition_var = tk.BooleanVar(value=True)
        self.dungeon_var = tk.BooleanVar(value=True)
        self.circus_var = tk.BooleanVar(value=True)
        self.refill_hp_var = tk.BooleanVar(value=False)
        self.recovery_buy_refill_var = tk.BooleanVar(value=False)
        self.hp_min_var = tk.StringVar(value="25")
        self.recovery_threshold_var = tk.StringVar(value="10")
        self.expedition_location_var = tk.StringVar(value="Grimwood")
        self.expedition_target_var = tk.StringVar(value="1")
        self.dungeon_location_var = tk.StringVar(value="Grimwood")
        self.dungeon_difficulty_var = tk.StringVar(value="Normal")
        self.change_notes = [
            {"issue_number": "21", "issue_title": "Remove main tab and use a single page", "summary": "Main tab kaldirildi; login alanlari ve butonlar kompakt hale getirildi, Mekanikler kutusunun dis cizgisi kaldirildi, Dungeon location Expedition altina alindi ve bolumler cizgilerle ayrildi."},
            {"issue_number": "18", "issue_title": "Add recovery tab and refill pot purchasing", "summary": "Recovery akisi shop'tan refill pot satin alma ve sayi dogrulama ile calisiyor."},
            "Dungeon akisi lokasyon secimi ve zorluk secimi ile ayrildi.",
            "Expedition ayarlari kendi tabina tasindi ve mob secimi korunuyor.",
            "HP refill sayaci ana ekranda gorunuyor.",
            "HP refill akisi ilk envanter bagini ve avatar hedefini kullaniyor.",
            "Expedition country map uzerinden secili lokasyona gidiyor.",
            "Dungeon secilen country map lokasyonunu acip rastgele saldiriyor.",
            "Workflow issue-first, branch-per-task ve PR-only hale getirildi.",
            "Main branch'e direkt pushlar engellendi.",
            "PR'lar GLA project ve issue baglantisi ile takip ediliyor.",
        ]

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
        self.status_badge.grid(row=1, column=1, sticky="e", padx=(16, 0))

        left = ttk.Frame(shell, style="App.TFrame")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=0)
        left.rowconfigure(1, weight=0)
        left.rowconfigure(2, weight=0)
        left.rowconfigure(3, weight=1)

        right = ttk.Frame(shell, style="App.TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self._build_credentials_panel(left)
        self._build_controls_panel(left)
        self._build_mechanics_panel(left)
        self._build_log_panel(left)

        self._build_notes_panel(right)

    def _build_credentials_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=0)

        content = ttk.Frame(panel, style="Panel.TFrame")
        content.grid(row=0, column=0, sticky="ew")
        content.columnconfigure(0, weight=1)

        ttk.Label(content, text="Hesap", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(content, text="Giristen sonra ayni oturum uzerinden mekanikler doner.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 10))

        tk.Label(content, text="Email", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.email_entry = tk.Entry(
            content,
            bg="#0b1220",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#3b4a63",
            highlightcolor="#53b7ff",
            font=("Segoe UI", 11),
        )
        self.email_entry.grid(row=3, column=0, sticky="ew", ipady=8)
        if USERNAME:
            self.email_entry.insert(0, USERNAME)

        tk.Label(content, text="Password", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w", pady=(10, 6))
        self.password_entry = tk.Entry(
            content,
            show="*",
            bg="#0b1220",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#3b4a63",
            highlightcolor="#53b7ff",
            font=("Segoe UI", 11),
        )
        self.password_entry.grid(row=5, column=0, sticky="ew", ipady=8)
        if PASSWORD:
            self.password_entry.insert(0, PASSWORD)

        buttons_row = ttk.Frame(content, style="Panel.TFrame")
        buttons_row.grid(row=6, column=0, sticky="w", pady=(14, 0))

        self.login_btn = ttk.Button(buttons_row, text="Login", style="Primary.TButton", command=self.start_login, width=12)
        self.login_btn.grid(row=0, column=0, sticky="w")

        self.captcha_btn = ttk.Button(
            buttons_row,
            text="CAPTCHA Solved - Continue",
            style="Danger.TButton",
            command=self.captcha_solved_callback,
            state="disabled",
            width=18,
        )
        self.captcha_btn.grid(row=0, column=1, sticky="w", padx=(12, 0))

        self._build_status_panel(panel)

    def _build_controls_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Kontrol", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(panel, text="Play dongusu 60 saniyede bir secili mekanikleri sirayla dener.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 12))

        self.play_btn = ttk.Button(panel, text="Play", style="Primary.TButton", command=self.toggle_play, width=16)
        self.play_btn.grid(row=2, column=0, sticky="w")

        self.stop_btn = ttk.Button(panel, text="Stop", style="Danger.TButton", command=self.stop_play, width=16)
        self.stop_btn.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.stop_btn.config(state="disabled")

    def _build_mechanics_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Mekanikler", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text="Attacks ve Recovery ayarlari burada toplanir.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        attacks_box = ttk.Frame(panel, style="Panel.TFrame")
        attacks_box.grid(row=2, column=0, columnspan=2, sticky="ew")
        attacks_box.columnconfigure(0, weight=1)
        attacks_box.columnconfigure(1, weight=1)

        attack_toggles = ttk.Frame(attacks_box, style="Panel.TFrame")
        attack_toggles.grid(row=0, column=0, columnspan=2, sticky="ew")
        attack_toggles.columnconfigure(0, weight=1)

        ttk.Checkbutton(attack_toggles, text="Expedition", variable=self.expedition_var, style="Modern.TCheckbutton").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Checkbutton(attack_toggles, text="Dungeon", variable=self.dungeon_var, style="Modern.TCheckbutton").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Checkbutton(attack_toggles, text="Circus Turma", variable=self.circus_var, style="Modern.TCheckbutton").grid(row=2, column=0, sticky="w", pady=4)

        ttk.Separator(attacks_box, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 12))

        ttk.Label(attacks_box, text="Locations", style="CardTitle.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))

        locations_box = ttk.Frame(attacks_box, style="Panel.TFrame")
        locations_box.grid(row=3, column=0, columnspan=2, sticky="ew")
        locations_box.columnconfigure(0, weight=1)

        expedition_section = ttk.Frame(locations_box, style="Panel.TFrame")
        expedition_section.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        expedition_section.columnconfigure(1, weight=1)
        ttk.Label(expedition_section, text="Expedition Location", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            expedition_section,
            text="Country map uzerinden lokasyon secilir, sonra mob hedefi belirlenir.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        expedition_location_row = ttk.Frame(expedition_section, style="Panel.TFrame")
        expedition_location_row.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        expedition_location_row.columnconfigure(1, weight=1)
        tk.Label(expedition_location_row, text="Lokasyon", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.location_combo = ttk.Combobox(
            expedition_location_row,
            textvariable=self.expedition_location_var,
            values=[label for label, _ in self.EXPEDITION_LOCATIONS],
            state="readonly",
            width=24,
        )
        self.location_combo.grid(row=0, column=1, sticky="w")

        choice_box = ttk.Frame(expedition_section, style="Panel.TFrame")
        choice_box.grid(row=3, column=0, sticky="ew")
        choice_box.columnconfigure(0, weight=1)

        options = [
            ("1", "1. mob", "Ilk kutudaki hedef"),
            ("2", "2. mob", "Ikinci kutudaki hedef"),
            ("3", "3. mob", "Ucuncu kutudaki hedef"),
            ("4", "4. mob", "Dorduncu kutudaki hedef"),
        ]

        for idx, (value, label, description) in enumerate(options):
            row = idx // 2
            col = idx % 2
            option_frame = ttk.Frame(choice_box, style="Panel.TFrame")
            option_frame.grid(row=row, column=col, sticky="ew", padx=(0, 10 if col == 0 else 0), pady=(0, 10))
            option_frame.columnconfigure(1, weight=1)

            tk.Radiobutton(
                option_frame,
                text=label,
                value=value,
                variable=self.expedition_target_var,
                bg=self.PANEL,
                fg=self.TEXT,
                activebackground=self.PANEL,
                activeforeground=self.TEXT,
                selectcolor="#0b1220",
                font=("Segoe UI", 10),
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                option_frame,
                text=description,
                bg=self.PANEL,
                fg=self.MUTED,
                font=("Segoe UI", 9),
            ).grid(row=1, column=0, sticky="w", padx=(24, 0), pady=(2, 0))

        dungeon_section = ttk.Frame(locations_box, style="Panel.TFrame")
        dungeon_section.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        dungeon_section.columnconfigure(1, weight=1)
        ttk.Label(dungeon_section, text="Dungeon Location", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            dungeon_section,
            text="Dungeon, expedition ile ayni country map lokasyonlari kullanir.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        dungeon_row = ttk.Frame(dungeon_section, style="Panel.TFrame")
        dungeon_row.grid(row=2, column=0, sticky="ew")
        dungeon_row.columnconfigure(1, weight=1)
        tk.Label(dungeon_row, text="Lokasyon", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.dungeon_combo = ttk.Combobox(
            dungeon_row,
            textvariable=self.dungeon_location_var,
            values=self.DUNGEON_LOCATIONS,
            state="readonly",
            width=24,
        )
        self.dungeon_combo.grid(row=0, column=1, sticky="w")

        difficulty_row = ttk.Frame(dungeon_section, style="Panel.TFrame")
        difficulty_row.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        difficulty_row.columnconfigure(1, weight=1)
        tk.Label(difficulty_row, text="Difficulty", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10))

        difficulty_box = ttk.Frame(difficulty_row, style="Panel.TFrame")
        difficulty_box.grid(row=0, column=1, sticky="w")
        for idx, label in enumerate(self.DUNGEON_DIFFICULTIES):
            tk.Radiobutton(
                difficulty_box,
                text=label,
                value=label,
                variable=self.dungeon_difficulty_var,
                bg=self.PANEL,
                fg=self.TEXT,
                activebackground=self.PANEL,
                activeforeground=self.TEXT,
                selectcolor="#0b1220",
                font=("Segoe UI", 10),
            ).grid(row=0, column=idx, sticky="w", padx=(0, 12))

        ttk.Separator(panel, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 12))

        ttk.Label(panel, text="Recovery", style="CardTitle.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 6))

        recovery_box = ttk.Frame(panel, style="Panel.TFrame")
        recovery_box.grid(row=5, column=0, columnspan=2, sticky="ew")
        recovery_box.columnconfigure(0, weight=1)
        recovery_box.columnconfigure(1, weight=0)

        ttk.Checkbutton(
            recovery_box,
            text="Buy refill pots when refill pots are under",
            variable=self.recovery_buy_refill_var,
            style="Modern.TCheckbutton",
        ).grid(row=0, column=0, sticky="w", pady=4)

        threshold_box = ttk.Frame(recovery_box, style="Panel.TFrame")
        threshold_box.grid(row=0, column=1, sticky="e")
        tk.Label(threshold_box, text="Threshold", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        self.recovery_threshold_spinbox = tk.Spinbox(
            threshold_box,
            from_=0,
            to=999,
            width=6,
            textvariable=self.recovery_threshold_var,
            bg="#0b1220",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.recovery_threshold_spinbox.pack(side="left", ipady=4)

        hp_row = ttk.Frame(panel, style="Panel.TFrame")
        hp_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        hp_row.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            hp_row,
            text="Refill HP",
            variable=self.refill_hp_var,
            style="Modern.TCheckbutton",
        ).grid(row=0, column=0, sticky="w", pady=4)

        hp_box = ttk.Frame(hp_row, style="Panel.TFrame")
        hp_box.grid(row=0, column=1, sticky="e")
        tk.Label(hp_box, text="Min HP %", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        self.hp_spinbox = tk.Spinbox(
            hp_box,
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
        self.hp_spinbox.pack(side="left", ipady=4)

    def _build_expedition_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Expedition Location", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text="Hermit ve event haric country map uzerindeki lokasyonlardan birini sec.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        location_row = ttk.Frame(panel, style="Panel.TFrame")
        location_row.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        location_row.columnconfigure(1, weight=1)
        tk.Label(location_row, text="Lokasyon", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.location_combo = ttk.Combobox(
            location_row,
            textvariable=self.expedition_location_var,
            values=[label for label, _ in self.EXPEDITION_LOCATIONS],
            state="readonly",
            width=24,
        )
        self.location_combo.grid(row=0, column=1, sticky="w")

        choice_box = ttk.Frame(panel, style="Panel.TFrame")
        choice_box.grid(row=3, column=0, sticky="ew")
        choice_box.columnconfigure(0, weight=1)

        options = [
            ("1", "1. mob", "Ilk kutudaki hedef"),
            ("2", "2. mob", "Ikinci kutudaki hedef"),
            ("3", "3. mob", "Ucuncu kutudaki hedef"),
            ("4", "4. mob", "Dorduncu kutudaki hedef"),
        ]

        for idx, (value, label, description) in enumerate(options):
            row = idx // 2
            col = idx % 2
            option_frame = ttk.Frame(choice_box, style="Panel.TFrame")
            option_frame.grid(row=row, column=col, sticky="ew", padx=(0, 10 if col == 0 else 0), pady=(0, 10))
            option_frame.columnconfigure(1, weight=1)

            tk.Radiobutton(
                option_frame,
                text=label,
                value=value,
                variable=self.expedition_target_var,
                bg=self.PANEL,
                fg=self.TEXT,
                activebackground=self.PANEL,
                activeforeground=self.TEXT,
                selectcolor="#0b1220",
                font=("Segoe UI", 10),
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                option_frame,
                text=description,
                bg=self.PANEL,
                fg=self.MUTED,
                font=("Segoe UI", 9),
            ).grid(row=1, column=0, sticky="w", padx=(24, 0), pady=(2, 0))

    def _build_dungeon_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Dungeon Location", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text="Dungeon icin expedition ile ayni country map lokasyonlari kullanilir, moblar random dalinir.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        dungeon_row = ttk.Frame(panel, style="Panel.TFrame")
        dungeon_row.grid(row=2, column=0, sticky="ew")
        dungeon_row.columnconfigure(1, weight=1)
        tk.Label(dungeon_row, text="Lokasyon", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.dungeon_combo = ttk.Combobox(
            dungeon_row,
            textvariable=self.dungeon_location_var,
            values=self.DUNGEON_LOCATIONS,
            state="readonly",
            width=12,
        )
        self.dungeon_combo.grid(row=0, column=1, sticky="w")

        difficulty_row = ttk.Frame(panel, style="Panel.TFrame")
        difficulty_row.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        difficulty_row.columnconfigure(1, weight=1)
        tk.Label(difficulty_row, text="Difficulty", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10))

        difficulty_box = ttk.Frame(difficulty_row, style="Panel.TFrame")
        difficulty_box.grid(row=0, column=1, sticky="w")
        for idx, label in enumerate(self.DUNGEON_DIFFICULTIES):
            tk.Radiobutton(
                difficulty_box,
                text=label,
                value=label,
                variable=self.dungeon_difficulty_var,
                bg=self.PANEL,
                fg=self.TEXT,
                activebackground=self.PANEL,
                activeforeground=self.TEXT,
                selectcolor="#0b1220",
                font=("Segoe UI", 10),
            ).grid(row=0, column=idx, sticky="w", padx=(0, 12))

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
        panel.grid(row=2, column=1, sticky="ne", padx=(16, 0), pady=(2, 0))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Durum", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        self.hp_value = tk.Label(panel, textvariable=self.hp_var, bg=self.PANEL, fg=self.SUCCESS, font=("Segoe UI Semibold", 18))
        self.hp_value.grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 8))

        self.hp_refill_value = tk.Label(
            panel,
            textvariable=self.hp_refill_count_var,
            bg=self.PANEL,
            fg=self.ACCENT,
            font=("Segoe UI Semibold", 11),
        )
        self.hp_refill_value.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.mode_value = tk.Label(panel, text="Idle", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 11))
        self.mode_value.grid(row=3, column=0, sticky="w")

        self.loop_value = tk.Label(panel, text="Dongu bekliyor", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 11))
        self.loop_value.grid(row=3, column=1, sticky="e")

    def _build_notes_panel(self, parent):
        panel = ttk.Frame(parent, style="PanelAlt.TFrame", padding=16)
        panel.grid(row=1, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)

        tk.Label(panel, text="Neler degisti?", bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI Semibold", 12)).grid(
            row=0, column=0, sticky="w"
        )

        self.change_notes_text = tk.Text(
            panel,
            height=12,
            wrap="word",
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            padx=0,
            pady=0,
            font=("Segoe UI", 10),
        )
        self.change_notes_text.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.change_notes_text.configure(state="disabled")
        self._render_change_notes()

    def _render_change_notes(self):
        try:
            self.change_notes_text.configure(state="normal")
            self.change_notes_text.delete("1.0", "end")
            for note in self.change_notes[:10]:
                if isinstance(note, dict):
                    issue_number = str(note.get("issue_number", "")).strip()
                    issue_title = str(note.get("issue_title", "")).strip()
                    summary = str(note.get("summary", "")).strip()
                    self.change_notes_text.insert("end", f"- #{issue_number} " if issue_number else "- ")
                    title_start = self.change_notes_text.index("end-1c")
                    self.change_notes_text.insert("end", f"{issue_title}\n")
                    title_end = self.change_notes_text.index("end-1c")
                    if issue_title:
                        self.change_notes_text.tag_add("issue_title", title_start, title_end)
                    if summary:
                        self.change_notes_text.insert("end", f"{summary}\n")
                    self.change_notes_text.insert("end", "\n")
                else:
                    self.change_notes_text.insert("end", f"- {note}\n\n")
            self.change_notes_text.tag_configure("issue_title", font=("Segoe UI Semibold", 10))
            self.change_notes_text.configure(state="disabled")
        except Exception:
            pass

    def add_change_note(self, issue_number, issue_title, note):
        note = (note or "").strip()
        if not note:
            return
        issue_number = str(issue_number).strip()
        issue_title = (issue_title or "").strip()
        self.change_notes.insert(
            0,
            {
                "issue_number": issue_number,
                "issue_title": issue_title,
                "summary": note,
            },
        )
        self.change_notes = self.change_notes[:10]
        self._render_change_notes()

    def _bind_settings_watchers(self):
        for variable in (
            self.expedition_var,
            self.dungeon_var,
            self.circus_var,
            self.refill_hp_var,
            self.recovery_buy_refill_var,
            self.hp_min_var,
            self.recovery_threshold_var,
            self.expedition_location_var,
            self.expedition_target_var,
            self.dungeon_location_var,
            self.dungeon_difficulty_var,
        ):
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
            "recovery_buy_refill": bool(self.recovery_buy_refill_var.get()),
            "hp_min": self.hp_min_var.get().strip() or "25",
            "recovery_threshold": self.recovery_threshold_var.get().strip() or "10",
            "expedition_location": self.get_expedition_location(),
            "expedition_target": self.get_expedition_target(),
            "dungeon_location": self.get_dungeon_location(),
            "dungeon_difficulty": self.get_dungeon_difficulty(),
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
            self.recovery_buy_refill_var.set(self._coerce_bool(data.get("recovery_buy_refill"), False))

            hp_min = data.get("hp_min", "25")
            self.hp_min_var.set(str(hp_min))

            recovery_threshold = data.get("recovery_threshold", "10")
            self.recovery_threshold_var.set(str(recovery_threshold))

            expedition_location = data.get("expedition_location", "Grimwood")
            self.expedition_location_var.set(self._coerce_expedition_location(expedition_location))

            expedition_target = data.get("expedition_target", "1")
            self.expedition_target_var.set(str(self._coerce_expedition_target(expedition_target)))

            dungeon_location = data.get("dungeon_location", "Grimwood")
            self.dungeon_location_var.set(self._coerce_dungeon_location(dungeon_location))

            dungeon_difficulty = data.get("dungeon_difficulty", "Normal")
            self.dungeon_difficulty_var.set(self._coerce_dungeon_difficulty(dungeon_difficulty))
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
            self.refresh_hp_refill_count()
        except Exception:
            pass

    def refresh_hp_refill_count(self):
        try:
            if not self.bot:
                self.set_hp_refill_count(None)
                return

            count = self.bot.get_healing_item_count(logger_callback=None)
            self.set_hp_refill_count(count)
        except Exception:
            pass

    def set_hp_refill_count(self, count):
        text = f"Refill pots: {count}" if count is not None else "Refill pots: --"
        self._ui(lambda: self.hp_refill_count_var.set(text))

    def get_min_hp_percent(self):
        try:
            value = int(self.hp_min_var.get())
            return max(1, min(99, value))
        except (ValueError, tk.TclError):
            return 25

    def _coerce_expedition_target(self, value):
        try:
            target = int(value)
        except (TypeError, ValueError):
            target = 1
        return max(1, min(4, target))

    def _coerce_expedition_location(self, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            for label, _ in self.EXPEDITION_LOCATIONS:
                if normalized == label.lower():
                    return label
        return self.EXPEDITION_LOCATIONS[0][0]

    def get_expedition_location(self):
        return self._coerce_expedition_location(self.expedition_location_var.get())

    def get_expedition_target(self):
        return self._coerce_expedition_target(self.expedition_target_var.get())

    def _coerce_dungeon_location(self, value):
        value = str(value).strip()
        if value in self.DUNGEON_LOCATIONS:
            return value
        return self.DUNGEON_LOCATIONS[0]

    def get_dungeon_location(self):
        return self._coerce_dungeon_location(self.dungeon_location_var.get())

    def _coerce_dungeon_difficulty(self, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            for label in self.DUNGEON_DIFFICULTIES:
                if normalized == label.lower():
                    return label
        return self.DUNGEON_DIFFICULTIES[0]

    def get_dungeon_difficulty(self):
        return self._coerce_dungeon_difficulty(self.dungeon_difficulty_var.get())

    def get_recovery_threshold(self):
        try:
            value = int(self.recovery_threshold_var.get())
            return max(0, min(999, value))
        except (ValueError, tk.TclError):
            return 10

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

                if self.recovery_buy_refill_var.get():
                    try:
                        self.bot.attempt_buy_refill_pots_if_needed(
                            min_item_count=self.get_recovery_threshold(),
                            logger_callback=self.append_log,
                            count_update_callback=self.set_hp_refill_count,
                        )
                    except Exception as exc:
                        self.append_log(f"Recovery refill buy error: {exc}")

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
                        self.bot.attempt_expedition_if_ready(
                            expedition_location=self.get_expedition_location(),
                            expedition_target=self.get_expedition_target(),
                            logger_callback=self.append_log,
                        )
                    else:
                        self.append_log(f"HP at or below {min_hp}%, skipping expedition")
                else:
                    self.append_log("Expedition mechanic disabled")

                if self.dungeon_var.get():
                    try:
                        self.bot.attempt_dungeon_if_ready(
                            dungeon_location=self.get_dungeon_location(),
                            dungeon_difficulty=self.get_dungeon_difficulty(),
                            logger_callback=self.append_log,
                        )
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
                self.refresh_hp_refill_count()
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
