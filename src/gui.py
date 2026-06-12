import json
import logging
import threading
import time
import tkinter as tk
import ctypes
import sys
from pathlib import Path
from tkinter import messagebox, ttk

from .config import BASE_URL, GUI_SETTINGS_PATH, PASSWORD, USERNAME
from .selenium_bot import GladiatusBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, command, *, bg_color, track_color, thumb_color, thumb_hover_color, width=18):
        super().__init__(
            parent,
            width=width,
            highlightthickness=0,
            bd=0,
            bg=bg_color,
            relief="flat",
            cursor="hand2",
        )
        self.command = command
        self.track_color = track_color
        self.thumb_color = thumb_color
        self.thumb_hover_color = thumb_hover_color
        self._first = 0.0
        self._last = 1.0
        self._drag_offset = None
        self._hovering = False

        self.bind("<Configure>", self._redraw)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set(self, first, last):
        self._first = max(0.0, min(1.0, float(first)))
        self._last = max(self._first, min(1.0, float(last)))
        self._redraw()

    def _thumb_geometry(self):
        height = max(1, self.winfo_height())
        width = max(1, self.winfo_width())
        pad_y = 10
        track_height = max(1, height - (pad_y * 2))
        visible_fraction = max(0.0, min(1.0, self._last - self._first))
        thumb_height = max(36, track_height * visible_fraction)
        max_top = pad_y + max(0, track_height - thumb_height)
        thumb_top = pad_y + ((track_height - thumb_height) * self._first)
        thumb_top = max(pad_y, min(max_top, thumb_top))
        thumb_bottom = thumb_top + thumb_height
        center_x = width / 2
        return center_x, thumb_top, thumb_bottom, track_height, pad_y

    def _redraw(self, _event=None):
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        center_x, thumb_top, thumb_bottom, _track_height, pad_y = self._thumb_geometry()

        self.create_line(
            center_x,
            pad_y,
            center_x,
            height - pad_y,
            fill=self.track_color,
            width=4,
            capstyle=tk.ROUND,
        )

        if self._last - self._first >= 0.999:
            return

        thumb_color = self.thumb_hover_color if self._hovering else self.thumb_color
        self.create_line(
            center_x,
            thumb_top + 2,
            center_x,
            thumb_bottom - 2,
            fill=thumb_color,
            width=7,
            capstyle=tk.ROUND,
            tags=("thumb",),
        )

    def _on_press(self, event):
        center_x, thumb_top, thumb_bottom, track_height, pad_y = self._thumb_geometry()
        if thumb_top <= event.y <= thumb_bottom:
            self._drag_offset = event.y - thumb_top
            return

        thumb_height = thumb_bottom - thumb_top
        new_top = max(pad_y, min((self.winfo_height() - pad_y) - thumb_height, event.y - (thumb_height / 2)))
        fraction = 0.0 if track_height <= thumb_height else (new_top - pad_y) / (track_height - thumb_height)
        self.command("moveto", str(fraction))

    def _on_drag(self, event):
        if self._drag_offset is None:
            return

        center_x, thumb_top, thumb_bottom, track_height, pad_y = self._thumb_geometry()
        thumb_height = thumb_bottom - thumb_top
        new_top = event.y - self._drag_offset
        new_top = max(pad_y, min((self.winfo_height() - pad_y) - thumb_height, new_top))
        fraction = 0.0 if track_height <= thumb_height else (new_top - pad_y) / (track_height - thumb_height)
        self.command("moveto", str(fraction))

    def _on_release(self, _event):
        self._drag_offset = None

    def _on_enter(self, _event):
        self._hovering = True
        self._redraw()

    def _on_leave(self, _event):
        self._hovering = False
        self._redraw()


class ThemedDropdown(tk.Frame):
    def __init__(
        self,
        parent,
        variable,
        values,
        *,
        bg_color,
        panel_color,
        border_color,
        text_color,
        muted_color,
        accent_color,
        width=220,
    ):
        super().__init__(parent, bg=border_color)
        self.variable = variable
        self.values = list(values)
        self.bg_color = bg_color
        self.panel_color = panel_color
        self.border_color = border_color
        self.text_color = text_color
        self.muted_color = muted_color
        self.accent_color = accent_color
        self.width = width
        self.height = 56
        self.popup = None
        self.popup_inner = None
        self.popup_canvas = None

        self.face = tk.Frame(self, bg=panel_color, padx=0, pady=0, cursor="hand2")
        self.face.pack(fill="both", expand=True, padx=1, pady=1)

        self.value_label = tk.Label(
            self.face,
            textvariable=self.variable,
            bg=panel_color,
            fg=text_color,
            font=("Segoe UI Semibold", 10),
            anchor="w",
        )
        self.value_label.place(x=14, rely=0.5, anchor="w")

        self.chevron = tk.Label(
            self.face,
            text="v",
            bg=panel_color,
            fg=accent_color,
            font=("Segoe UI Semibold", 11),
            cursor="hand2",
        )
        self.chevron.place(relx=1.0, x=-14, rely=0.5, anchor="e")

        self.face.configure(width=width - 2, height=self.height - 2)
        self.face.pack_propagate(False)
        self.configure(width=width, height=self.height)
        self.pack_propagate(False)
        self.grid_propagate(False)

        for widget in (self, self.face, self.value_label, self.chevron):
            widget.bind("<Button-1>", self._toggle_popup)

        self.variable.trace_add("write", self._sync_label)
        self._sync_label()

    def _sync_label(self, *_args):
        current = self.variable.get().strip()
        if not current and self.values:
            self.variable.set(self.values[0])

    def _toggle_popup(self, _event=None):
        if self.popup and self.popup.winfo_exists():
            self._close_popup()
        else:
            root = self.winfo_toplevel()
            if hasattr(root, "_close_all_dropdowns"):
                root._close_all_dropdowns()
            self._open_popup()

    def _open_popup(self):
        if self.popup and self.popup.winfo_exists():
            return

        root = self.winfo_toplevel()
        root_x = root.winfo_rootx()
        root_y = root.winfo_rooty()
        x = self.winfo_rootx() - root_x
        y = self.winfo_rooty() - root_y + self.winfo_height() + 6
        width = max(self.width, self.winfo_width())

        self.popup = tk.Frame(root, bg=self.border_color)
        self.popup._dropdown_owner = self
        self.popup.place(x=x, y=y, width=width)
        self.popup.lift()

        inner = tk.Frame(self.popup, bg=self.panel_color)
        inner._dropdown_owner = self
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.popup_inner = inner

        list_frame = tk.Frame(inner, bg=self.panel_color)
        list_frame._dropdown_owner = self
        list_frame.pack(fill="both", expand=True)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        visible_rows = min(max(len(self.values), 1), 8)
        popup_height = (visible_rows * 39) + 2

        canvas = tk.Canvas(
            list_frame,
            bg=self.panel_color,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        canvas._dropdown_owner = self
        canvas.grid(row=0, column=0, sticky="nsew")
        self.popup_canvas = canvas

        scroll_host = tk.Frame(list_frame, bg=self.panel_color, width=18)
        scroll_host._dropdown_owner = self
        scroll_host.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        scroll_host.grid_propagate(False)

        option_stack = tk.Frame(canvas, bg=self.panel_color)
        option_stack._dropdown_owner = self
        canvas_window = canvas.create_window((0, 0), window=option_stack, anchor="nw")

        scrollbar = ModernScrollbar(
            scroll_host,
            canvas.yview,
            bg_color=self.panel_color,
            track_color=self.border_color,
            thumb_color=self.accent_color,
            thumb_hover_color=self.accent_color,
            width=18,
        )
        scrollbar._dropdown_owner = self
        scrollbar.pack(fill="y", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _sync_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        option_stack.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_width)

        for idx, option in enumerate(self.values):
            row = tk.Label(
                option_stack,
                text=option,
                bg=self.panel_color,
                fg=self.text_color,
                font=("Segoe UI", 10),
                anchor="w",
                padx=12,
                pady=9,
                cursor="hand2",
            )
            row._dropdown_owner = self
            row.pack(fill="x")
            if option == self.variable.get():
                row.configure(bg="#162131", fg=self.accent_color)
            row.bind("<Enter>", lambda _e, item=row: item.configure(bg="#162131", fg=self.accent_color))
            row.bind("<Leave>", lambda _e, item=row, value=option: item.configure(
                bg="#162131" if value == self.variable.get() else self.panel_color,
                fg=self.accent_color if value == self.variable.get() else self.text_color,
            ))
            row.bind("<Button-1>", lambda _e, value=option: self._select_option(value))

            if idx < len(self.values) - 1:
                separator = tk.Frame(option_stack, bg=self.border_color, height=1)
                separator._dropdown_owner = self
                separator.pack(fill="x")

        def _on_mousewheel(event):
            delta = -1 * int(event.delta / 120)
            canvas.yview_scroll(delta, "units")
            return "break"

        for widget in (self.popup, inner, list_frame, canvas, option_stack, scroll_host):
            widget.bind("<MouseWheel>", _on_mousewheel)

        if self.variable.get() in self.values:
            current_index = self.values.index(self.variable.get())
            canvas.yview_moveto(min(1.0, max(0.0, current_index / max(1, len(self.values)))))

        self.popup.configure(height=popup_height)

    def _select_option(self, value):
        self.variable.set(value)
        self._close_popup()

    def _scroll_popup(self, delta_units):
        if self.popup_canvas and self.popup_canvas.winfo_exists():
            self.popup_canvas.yview_scroll(delta_units, "units")
            return True
        return False

    def _close_popup(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.place_forget()
            self.popup.destroy()
        self.popup = None
        self.popup_inner = None
        self.popup_canvas = None


class ThemedButton(tk.Frame):
    def __init__(self, parent, text, command, *, variant, width=180):
        palette = {
            "primary": {"bg": "#59e3b2", "fg": "#06110c", "hover": "#93f0cf", "disabled_bg": "#3b4655", "disabled_fg": "#90a0b5"},
            "secondary": {"bg": "#141a24", "fg": "#f5f7fb", "hover": "#1b2431", "disabled_bg": "#141a24", "disabled_fg": "#5f7087"},
            "danger": {"bg": "#2a141d", "fg": "#ff9ab1", "hover": "#3a1824", "disabled_bg": "#1a1014", "disabled_fg": "#6e5861"},
        }
        self.colors = palette[variant]
        super().__init__(parent, bg=self.colors["bg"], cursor="hand2")
        self.command = command
        self.state = "normal"
        self.text = text
        self.width = width
        self.height = 44
        self.label = tk.Label(self, text=text, bg=self.colors["bg"], fg=self.colors["fg"], font=("Segoe UI Semibold", 10), padx=16, pady=10, cursor="hand2")
        self.label.pack(fill="both", expand=True, padx=1, pady=1)
        super().configure(width=width, height=self.height)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.bind("<Button-1>", self._on_click)
        self.label.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.label.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.label.bind("<Leave>", self._on_leave)

    def _on_click(self, _event=None):
        if self.state != "disabled" and self.command:
            self.command()

    def _on_enter(self, _event=None):
        if self.state != "disabled":
            self.label.configure(bg=self.colors["hover"])

    def _on_leave(self, _event=None):
        self._refresh()

    def _refresh(self):
        if self.state == "disabled":
            super().configure(bg=self.colors["disabled_bg"], cursor="arrow")
            self.label.configure(bg=self.colors["disabled_bg"], fg=self.colors["disabled_fg"], cursor="arrow")
        else:
            super().configure(bg=self.colors["bg"], cursor="hand2")
            self.label.configure(bg=self.colors["bg"], fg=self.colors["fg"], cursor="hand2")

    def config(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
            self.label.configure(text=self.text)
        if "state" in kwargs:
            self.state = kwargs["state"]
        if "command" in kwargs:
            self.command = kwargs["command"]
        self._refresh()

    configure = config


class ThemedCheckbox(tk.Frame):
    def __init__(self, parent, text, variable, *, bg_color, text_color, muted_color, accent_color, command=None):
        super().__init__(parent, bg=bg_color, cursor="hand2")
        self.variable = variable
        self.command = command
        self.bg_color = bg_color
        self.text_color = text_color
        self.muted_color = muted_color
        self.accent_color = accent_color
        self.state = "normal"

        self.box = tk.Canvas(self, width=16, height=16, bg=bg_color, highlightthickness=0, bd=0, cursor="hand2")
        self.box.grid(row=0, column=0, sticky="w")
        self.label = tk.Label(self, text=text, bg=bg_color, fg=text_color, font=("Segoe UI Semibold", 10), cursor="hand2")
        self.label.grid(row=0, column=1, sticky="w", padx=(8, 0))

        for widget in (self, self.box, self.label):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        self.variable.trace_add("write", self._sync)
        self._sync()

    def _draw(self, hover=False):
        self.box.delete("all")
        border = self.accent_color if hover and self.state != "disabled" else self.muted_color
        fill = self.accent_color if self.variable.get() else self.bg_color
        if self.state == "disabled":
            border = "#44505f"
            fill = "#10151d" if not self.variable.get() else "#2a6352"
        self.box.create_rectangle(1, 1, 15, 15, outline=border, fill=fill, width=1)
        if self.variable.get():
            self.box.create_line(4, 8, 7, 11, 12, 4, fill="#06110c", width=2, capstyle=tk.ROUND, joinstyle=tk.ROUND)

    def _sync(self, *_args):
        self._draw()

    def _toggle(self, _event=None):
        if self.state == "disabled":
            return
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _on_enter(self, _event=None):
        self._draw(hover=True)
        if self.state != "disabled":
            self.label.configure(fg=self.accent_color)

    def _on_leave(self, _event=None):
        self._draw(hover=False)
        self.label.configure(fg=self.text_color if self.state != "disabled" else self.muted_color)

    def config(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]
        self._draw()
        self.label.configure(fg=self.text_color if self.state != "disabled" else self.muted_color)

    configure = config


class GladiatusGUI:
    BG = "#050608"
    PANEL = "#0a0d12"
    PANEL_ALT = "#10151d"
    PANEL_SOFT = "#080b10"
    INPUT_BG = "#06080c"
    BORDER = "#18212d"
    TEXT = "#f5f7fb"
    MUTED = "#90a0b5"
    ACCENT = "#59e3b2"
    ACCENT_SOFT = "#93f0cf"
    INFO = "#78a8ff"
    SUCCESS = "#3ee0aa"
    WARNING = "#ffb86b"
    DANGER = "#ff6f91"

    EXPEDITION_LOCATIONS = [
        ("Grimwood", "0"),
        ("Pirate Harbour", "1"),
        ("Misty Mountains", "2"),
        ("Wolf Cave", "3"),
        ("Ancient Temple", "4"),
        ("Barbarian Village", "5"),
        ("Bandit Camp", "6"),
        ("Voodoo Temple", "0"),
        ("Bridge", "1"),
        ("Blood Cave", "2"),
        ("Lost Harbour", "3"),
        ("Umpokta Tribe", "4"),
        ("Caravan", "5"),
        ("Mesoai-Oasis", "6"),
    ]
    DUNGEON_LOCATIONS = [label for label, _ in EXPEDITION_LOCATIONS]
    DUNGEON_DIFFICULTIES = ["Normal", "Advanced"]

    def __init__(self, root):
        self.root = root
        self.root.title("Gladiatus Command Suite")
        self.root.geometry("1320x860")
        self.root.minsize(1140, 760)
        self.root.configure(bg=self.BG)
        self.root.overrideredirect(True)
        self._chrome_initialized = False
        self._drag_origin = None
        self._is_maximized = False
        self._restore_geometry = None
        self._was_maximized_before_minimize = False
        self._window_transition = None
        self._transition_overlay = None
        self._transition_shell = None
        self._drag_window_offset = None
        self._drag_started_maximized = False
        self._top_snap_armed = False

        self.bot = None
        self.login_thread = None
        self.play_thread = None
        self.playing = False
        self.captcha_detected = False
        self.captcha_solved = False

        self.status_var = tk.StringVar(value="Standby")
        self.hp_var = tk.StringVar(value="HP: --")
        self.hp_refill_count_var = tk.StringVar(value="Refill pots: --")
        self.session_var = tk.StringVar(value="Awaiting secure login")
        self.combat_profile_var = tk.StringVar(value="Expedition / Dungeon / Circus")
        self.sustain_profile_var = tk.StringVar(value="Manual sustain")

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
            {"issue_number": "36", "issue_title": "Fix taskbar visibility for custom window chrome", "summary": "Windows taskbar gorunurlugu dogru HWND uzerine tasindi; startup'taki withdraw/deiconify dongusu kaldirildi ve custom chrome acik kalirken ikonun gorunmesi hedeflendi."},
            {"issue_number": "34", "issue_title": "Expand expedition and dungeon locations", "summary": "Expedition ve dungeon secimleri eski lokasyonlar korunarak yeni submenu lokasyonlariyla genisletildi; dropdown listesi kaydirilabilir hale getirildi, Hermit ve Rise of the Forgotten dropdown'lara dahil edilmedi."},
            {"issue_number": "32", "issue_title": "Handle Daily Bonus overlay", "summary": "Login sonrası Daily Bonus popup'i close_overlays akishina eklendi; Collect Bonus dialogu botu kilitlemeden kapatiliyor."},
            {"issue_number": "30", "issue_title": "Fix collapsed controls regression in premium GUI", "summary": "Custom button ve dropdown wrapper'larinin coktugu regress duzeltildi; login/CAPTCHA ile play/stop butonlari geri geldi, lokasyon dropdown'lari yeniden gorunur oldu, acik dropdown'lar scroll sirasinda kapanir hale getirildi ve sag kolon hizasi toparlandi."},
            {"issue_number": "25", "issue_title": "Premium GUI refresh", "summary": "Arayuz daha elit bir control suite hissi verecek sekilde yeniden tasarlandi; vitrin alani, durum kartlari, daha guclu tipografi ve premium panel hiyerarsisi eklendi."},
            {"issue_number": "21", "issue_title": "Remove main tab and use a single page", "summary": "Main tab kaldirildi; ana body scrollable yapildi, ekran 50/50 iki paneye bolundu, Activity Log ve Neler degisti sag panele ayni sutunda tasindi, Neler degisti kutusu Activity Log stiliyle ust baslikli hale getirildi ve scroll eklendi, login alanlari ve butonlar kompakt hale getirildi, Mekanikler kutusunun dis cizgisi kaldirildi, Dungeon location Expedition altina alindi ve bolumler cizgilerle ayrildi."},
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
        self._registered_dropdowns = []

        self._settings_suspended = True
        self._configure_styles()
        self._build_layout()
        self.root._close_all_dropdowns = self._close_all_dropdowns
        self._load_settings()
        self._bind_settings_watchers()
        self._settings_suspended = False
        self._refresh_overview()
        self._bind_focus_dismissal()
        self.root.bind("<Map>", self._on_window_map, add="+")
        self.root.after(30, self._enable_custom_window_chrome)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=self.BG, foreground=self.TEXT)
        style.configure("App.TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("PanelAlt.TFrame", background=self.PANEL_ALT)
        style.configure("CardTitle.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI Semibold", 13))
        style.configure("Muted.TLabel", background=self.PANEL, foreground=self.MUTED, font=("Segoe UI", 10))
        style.configure("Value.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI Semibold", 16))
        style.configure("Status.TLabel", background=self.PANEL_ALT, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Section.TLabelframe", background=self.PANEL, foreground=self.TEXT)
        style.configure("Section.TLabelframe.Label", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Modern.TCheckbutton", background=self.PANEL_ALT, foreground=self.TEXT, font=("Segoe UI Semibold", 10), padding=(0, 2))
        style.map("Modern.TCheckbutton", background=[("active", self.PANEL_ALT)], foreground=[("active", self.ACCENT_SOFT)])
        style.configure(
            "Premium.TCombobox",
            fieldbackground=self.INPUT_BG,
            background=self.PANEL_ALT,
            foreground=self.TEXT,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            arrowsize=16,
            padding=6,
        )
        style.map(
            "Premium.TCombobox",
            fieldbackground=[("readonly", self.INPUT_BG)],
            foreground=[("readonly", self.TEXT)],
            selectforeground=[("readonly", self.TEXT)],
            selectbackground=[("readonly", self.INPUT_BG)],
            background=[("readonly", self.PANEL_ALT)],
        )
        style.configure(
            "Primary.TButton",
            background=self.ACCENT,
            foreground="#07111b",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI Semibold", 10),
            padding=(16, 10),
        )
        style.map("Primary.TButton", background=[("active", self.ACCENT_SOFT), ("disabled", "#475569")], foreground=[("disabled", "#cbd5e1")])
        style.configure(
            "Danger.TButton",
            background=self.DANGER,
            foreground="white",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI Semibold", 10),
            padding=(16, 10),
        )
        style.map("Danger.TButton", background=[("active", "#f87171"), ("disabled", "#475569")], foreground=[("disabled", "#cbd5e1")])
        style.configure(
            "Secondary.TButton",
            background=self.PANEL_ALT,
            foreground=self.TEXT,
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI Semibold", 10),
            padding=(16, 10),
        )
        style.map("Secondary.TButton", background=[("active", "#1c2947"), ("disabled", "#475569")], foreground=[("disabled", "#94a3b8")])

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = ttk.Frame(self.root, style="App.TFrame", padding=0)
        shell.grid(sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)

        header_border = tk.Frame(shell, bg=self.BORDER)
        header_border.grid(row=0, column=0, columnspan=2, sticky="ew")
        header = tk.Frame(header_border, bg=self.PANEL_ALT)
        header.pack(fill="both", expand=True, padx=1, pady=1)
        header.columnconfigure(0, weight=1)

        hero = tk.Frame(header, bg=self.PANEL_ALT, padx=28, pady=20)
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=1)

        top_rail = tk.Frame(hero, bg=self.PANEL_ALT)
        top_rail.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        top_rail.columnconfigure(1, weight=1)

        brand = tk.Frame(top_rail, bg=self.PANEL_ALT)
        brand.grid(row=0, column=0, sticky="w")
        gla_mark = tk.Label(brand, text="GLA", bg=self.ACCENT, fg="#06110c", font=("Bahnschrift SemiBold", 10), padx=9, pady=5)
        gla_mark.grid(row=0, column=0, sticky="w")
        title_label = tk.Label(brand, text="Gladiatus Command Suite", bg=self.PANEL_ALT, fg=self.TEXT, font=("Bahnschrift SemiBold", 12))
        title_label.grid(row=0, column=1, sticky="w", padx=(12, 0))

        nav = tk.Frame(top_rail, bg=self.PANEL_ALT)
        nav.grid(row=0, column=1, sticky="w", padx=(28, 0))
        nav_labels = []
        for idx, (label, color) in enumerate((("Automation", self.ACCENT_SOFT), ("Recovery", self.TEXT), ("Routing", self.MUTED), ("Logs", self.MUTED))):
            nav_label = tk.Label(nav, text=label.upper(), bg=self.PANEL_ALT, fg=color, font=("Bahnschrift SemiBold", 10), padx=10, pady=5)
            nav_label.grid(row=0, column=idx, sticky="w")
            nav_labels.append(nav_label)

        right_tools = tk.Frame(top_rail, bg=self.PANEL_ALT)
        right_tools.grid(row=0, column=2, sticky="e")
        self.status_badge = tk.Label(
            right_tools,
            textvariable=self.status_var,
            bg=self.PANEL_SOFT,
            fg=self.ACCENT_SOFT,
            font=("Bahnschrift SemiBold", 10),
            padx=14,
            pady=8,
        )
        self.status_badge.grid(row=0, column=0, sticky="e")
        self.minimize_btn = self._create_window_control(right_tools, "minimize")
        self.minimize_btn.grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.maximize_btn = self._create_window_control(right_tools, "maximize")
        self.maximize_btn.grid(row=0, column=2, sticky="e", padx=(4, 0))
        self.close_btn = self._create_window_control(right_tools, "close")
        self.close_btn.grid(row=0, column=3, sticky="e", padx=(4, 0))
        for widget in (header_border, header, hero, top_rail, brand, gla_mark, title_label, nav, right_tools, self.status_badge, *nav_labels):
            self._bind_window_drag(widget)

        left_hero = tk.Frame(hero, bg=self.PANEL_ALT)
        left_hero.grid(row=1, column=0, sticky="nw")
        tk.Label(left_hero, text="Automation", bg=self.PANEL_ALT, fg=self.TEXT, font=("Bahnschrift SemiBold", 26)).grid(row=0, column=0, sticky="w")
        tk.Label(
            left_hero,
            text="Battle.net gibi tek parca bir operasyon yuzeyi: entegre shell, koyu chrome ve temaya ait componentler.",
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        badge_row = tk.Frame(left_hero, bg=self.PANEL_ALT)
        badge_row.grid(row=2, column=0, sticky="w", pady=(16, 0))
        for idx, label in enumerate(("Live Routing", "Recovery Guard", "Session Intelligence")):
            tk.Label(
                badge_row,
                text=label,
                bg=self.PANEL_SOFT,
                fg=self.ACCENT_SOFT if idx == 0 else self.INFO,
                font=("Segoe UI Semibold", 9),
                padx=12,
                pady=6,
            ).grid(row=0, column=idx, sticky="w", padx=(0, 10))

        overview = tk.Frame(hero, bg=self.PANEL_ALT)
        overview.grid(row=1, column=1, sticky="e")
        for col in range(3):
            overview.columnconfigure(col, weight=1)
        self._create_overview_tile(overview, 0, "SESSION", self.session_var, self.INFO)
        self._create_overview_tile(overview, 1, "COMBAT PROFILE", self.combat_profile_var, self.ACCENT_SOFT)
        self._create_overview_tile(overview, 2, "SUSTAIN", self.sustain_profile_var, self.SUCCESS)

        body = ttk.Frame(shell, style="App.TFrame")
        body.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=24, pady=(18, 24))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        canvas = tk.Canvas(body, bg=self.BG, highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        body_scroll = ModernScrollbar(
            body,
            canvas.yview,
            bg_color=self.BG,
            track_color="#10161e",
            thumb_color=self.ACCENT,
            thumb_hover_color=self.ACCENT_SOFT,
        )
        body_scroll.grid(row=0, column=1, sticky="ns", padx=(12, 0), pady=6)
        canvas.configure(yscrollcommand=body_scroll.set)

        scroll_frame = ttk.Frame(canvas, style="App.TFrame")
        scroll_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _sync_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_width(event):
            canvas.itemconfigure(scroll_window, width=event.width)

        scroll_frame.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_width)

        left = ttk.Frame(scroll_frame, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=0)
        left.rowconfigure(1, weight=0)
        left.rowconfigure(2, weight=0)
        left.rowconfigure(3, weight=1)

        right = ttk.Frame(scroll_frame, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        scroll_frame.columnconfigure(0, weight=1)
        scroll_frame.columnconfigure(1, weight=1)

        right_stack = ttk.Frame(right, style="App.TFrame")
        right_stack.grid(row=0, column=0, sticky="nsew")
        right_stack.columnconfigure(0, weight=1)
        right_stack.rowconfigure(0, weight=0)
        right_stack.rowconfigure(1, weight=0)

        top_row = ttk.Frame(left, style="App.TFrame")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_row.columnconfigure(0, weight=1)
        top_row.columnconfigure(1, weight=1)

        self._build_credentials_panel(top_row)
        self._build_status_panel(top_row)
        self._build_controls_panel(left)
        self._build_mechanics_panel(left)
        self._build_log_panel(right_stack)
        self._build_notes_panel(right_stack)

        self._bind_mousewheel(canvas)
        self._refresh_overview()

    def _create_overview_tile(self, parent, column, eyebrow, value_var, accent_color):
        tile_border = tk.Frame(parent, bg=self.BORDER)
        tile_border.grid(row=0, column=column, sticky="ew", padx=(0, 14 if column < 2 else 0))
        tile = tk.Frame(tile_border, bg=self.PANEL_SOFT, padx=16, pady=14)
        tile.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            tile,
            text=eyebrow,
            bg=self.PANEL_SOFT,
            fg=self.MUTED,
            font=("Bahnschrift SemiBold", 9),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            tile,
            textvariable=value_var,
            bg=self.PANEL_SOFT,
            fg=accent_color,
            font=("Segoe UI Semibold", 11),
            wraplength=280,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def _create_card(self, parent, row, column, *, columnspan=1, padx=(0, 0), pady=(0, 0), padding=20, bg=None):
        border = tk.Frame(parent, bg=self.BORDER)
        border.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=padx, pady=pady)
        card = tk.Frame(border, bg=bg or self.PANEL, padx=padding, pady=padding)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        return card

    def _create_subcard(self, parent, *, bg=None, padx=16, pady=16):
        border = tk.Frame(parent, bg=self.BORDER)
        card = tk.Frame(border, bg=bg or self.PANEL_ALT, padx=padx, pady=pady)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        return border, card

    def _style_input(self, widget):
        widget.configure(
            bg=self.INPUT_BG,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT,
            font=("Segoe UI", 11),
        )

    def _style_numeric_input(self, widget):
        self._style_input(widget)
        widget.configure(
            justify="center",
            font=("Segoe UI Semibold", 11),
            width=6,
        )

    def _style_text_panel(self, widget):
        widget.configure(
            bg=self.PANEL_SOFT,
            fg="#dbe7ff",
            insertbackground="#dbe7ff",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )

    def _bind_focus_dismissal(self):
        self.root.bind_all("<Button-1>", self._handle_global_click, add="+")

    def _handle_global_click(self, event):
        widget = event.widget
        keep_focus_classes = {"Entry", "Text", "TCombobox", "Combobox", "Spinbox"}
        if widget.winfo_class() in keep_focus_classes or self._has_ancestor(widget, ThemedDropdown) or hasattr(widget, "_dropdown_owner"):
            return
        self._close_all_dropdowns()
        self.root.after_idle(self.root.focus_set)

    def _has_ancestor(self, widget, widget_type):
        current = widget
        while current is not None:
            if isinstance(current, widget_type):
                return True
            parent_name = current.winfo_parent()
            if not parent_name:
                break
            try:
                current = current.nametowidget(parent_name)
            except Exception:
                break
        return False

    def _register_dropdown(self, dropdown):
        self._registered_dropdowns.append(dropdown)
        return dropdown

    def _create_window_control(self, parent, kind):
        frame = tk.Frame(parent, bg=self.PANEL_ALT, width=30, height=26, cursor="hand2")
        frame.grid_propagate(False)
        canvas = tk.Canvas(frame, width=30, height=26, bg=self.PANEL_ALT, highlightthickness=0, bd=0, cursor="hand2")
        canvas.pack(fill="both", expand=True)
        frame._kind = kind
        frame._canvas = canvas

        if kind == "minimize":
            command = self._minimize_window
            hover_bg = self.PANEL_SOFT
            hover_fg = self.TEXT
        elif kind == "maximize":
            command = self._toggle_maximize_restore
            hover_bg = self.PANEL_SOFT
            hover_fg = self.TEXT
        else:
            command = self._on_close
            hover_bg = "#35151d"
            hover_fg = self.TEXT

        for widget in (frame, canvas):
            widget.bind("<Button-1>", lambda _e, cb=command: cb())
            widget.bind("<Enter>", lambda _e, fr=frame, bg=hover_bg, fg=hover_fg: self._paint_window_control(fr, bg, fg))
            widget.bind("<Leave>", lambda _e, fr=frame: self._paint_window_control(fr, self.PANEL_ALT, self.MUTED))

        self._paint_window_control(frame, self.PANEL_ALT, self.MUTED)
        return frame

    def _paint_window_control(self, control, bg_color, fg_color):
        control.configure(bg=bg_color)
        canvas = control._canvas
        canvas.configure(bg=bg_color)
        canvas.delete("all")
        kind = control._kind

        if kind == "minimize":
            canvas.create_line(9, 15, 21, 15, fill=fg_color, width=2, capstyle=tk.ROUND)
        elif kind == "maximize":
            if self._is_maximized:
                canvas.create_rectangle(9, 8, 18, 17, outline=fg_color, width=1)
                canvas.create_rectangle(12, 5, 21, 14, outline=fg_color, width=1)
            else:
                canvas.create_rectangle(9, 7, 21, 19, outline=fg_color, width=1)
                canvas.create_line(9, 10, 21, 10, fill=fg_color, width=1)
        else:
            canvas.create_line(10, 8, 20, 18, fill=fg_color, width=2, capstyle=tk.ROUND)
            canvas.create_line(20, 8, 10, 18, fill=fg_color, width=2, capstyle=tk.ROUND)

    def _close_all_dropdowns(self):
        for dropdown in self._registered_dropdowns:
            try:
                dropdown._close_popup()
            except Exception:
                pass

    def _enable_custom_window_chrome(self):
        if self._chrome_initialized:
            self.root.overrideredirect(True)
            return

        if not sys.platform.startswith("win"):
            self._chrome_initialized = True
            self.root.overrideredirect(True)
            return

        try:
            self.root.update_idletasks()
            hwnd = self.root.winfo_id()
            parent_hwnd = ctypes.windll.user32.GetParent(hwnd)
            if parent_hwnd:
                hwnd = parent_hwnd
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            SW_HIDE = 0
            SW_SHOW = 5

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
            ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
            self.root.overrideredirect(True)
            self.root.lift()
            self._chrome_initialized = True
        except Exception:
            self.root.overrideredirect(False)

    def _bind_window_drag(self, widget):
        widget.bind("<ButtonPress-1>", self._start_window_drag, add="+")
        widget.bind("<B1-Motion>", self._perform_window_drag, add="+")
        widget.bind("<ButtonRelease-1>", self._stop_window_drag, add="+")
        widget.bind("<Double-Button-1>", self._toggle_maximize_restore, add="+")

    def _start_window_drag(self, event):
        try:
            if self._window_transition is not None:
                self.root.after_cancel(self._window_transition)
                self._window_transition = None
        except Exception:
            self._window_transition = None
        self._drag_window_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )
        self._drag_started_maximized = self._is_maximized
        self._top_snap_armed = False
        self._drag_origin = (event.x_root, event.y_root)

    def _perform_window_drag(self, event):
        if not self._drag_origin:
            return
        work_x, work_y, work_width, work_height = self._get_work_area_geometry()

        if self._is_maximized and self._drag_started_maximized:
            if event.y_root <= self._drag_origin[1] + 8:
                return

            if self._restore_geometry:
                _, _, restore_width, restore_height = self._parse_geometry(self._restore_geometry)
            else:
                restore_width = max(self.root.winfo_width() - 220, self.root.winfo_width() // 2)
                restore_height = max(self.root.winfo_height() - 160, self.root.winfo_height() // 2)

            current_width = max(1, self.root.winfo_width())
            pointer_offset_x = (self._drag_window_offset or (current_width // 2, 18))[0]
            pointer_ratio = min(max(pointer_offset_x / current_width, 0.18), 0.82)
            new_x = int(event.x_root - (restore_width * pointer_ratio))
            new_y = int(event.y_root - min(24, max(12, (self._drag_window_offset or (0, 18))[1])))
            max_x = work_x + max(0, work_width - restore_width)
            max_y = work_y + max(0, work_height - restore_height)
            new_x = max(work_x, min(new_x, max_x))
            new_y = max(work_y, min(new_y, max_y))

            self.root.geometry(f"{restore_width}x{restore_height}+{new_x}+{new_y}")
            self.root.update_idletasks()
            self._is_maximized = False
            self._drag_started_maximized = False
            self._paint_window_control(self.maximize_btn, self.PANEL_ALT, self.MUTED)
            self._drag_origin = (event.x_root, event.y_root)
            self._drag_window_offset = (
                event.x_root - self.root.winfo_x(),
                event.y_root - self.root.winfo_y(),
            )
            return

        dx = event.x_root - self._drag_origin[0]
        dy = event.y_root - self._drag_origin[1]
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")
        self._drag_origin = (event.x_root, event.y_root)
        self._drag_window_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )
        self._top_snap_armed = event.y_root <= work_y + 2

    def _stop_window_drag(self, _event):
        should_snap_top = bool(self._drag_origin and self._top_snap_armed and not self._is_maximized)
        self._drag_origin = None
        self._drag_window_offset = None
        self._drag_started_maximized = False
        self._top_snap_armed = False
        if should_snap_top:
            self._maximize_window()

    def _minimize_window(self):
        if not self._restore_geometry or not self._is_maximized:
            self._restore_geometry = self.root.geometry()
        self._was_maximized_before_minimize = self._is_maximized
        self.root.overrideredirect(False)
        self.root.iconify()

    def _on_window_map(self, _event=None):
        if str(self.root.state()) == "normal":
            self.root.after(20, self._restore_after_map)

    def _restore_after_map(self):
        self._enable_custom_window_chrome()
        if self._was_maximized_before_minimize:
            self.root.after(20, self._reapply_maximized_geometry)
        self._was_maximized_before_minimize = False

    def _toggle_maximize_restore(self, _event=None):
        self._drag_origin = None
        if self._is_maximized:
            self._restore_window()
        else:
            self._maximize_window()
        return "break"

    def _maximize_window(self):
        try:
            if not self._is_maximized:
                self._restore_geometry = self.root.geometry()
            self.root.update_idletasks()
            x, y, width, height = self._get_work_area_geometry()
            self._animate_to_geometry((x, y, width, height))
            self._is_maximized = True
            self._paint_window_control(self.maximize_btn, self.PANEL_ALT, self.MUTED)
        except Exception:
            pass

    def _restore_window(self):
        try:
            if self._restore_geometry:
                self._animate_to_geometry(self._parse_geometry(self._restore_geometry))
            self._is_maximized = False
            self._paint_window_control(self.maximize_btn, self.PANEL_ALT, self.MUTED)
        except Exception:
            pass

    def _reapply_maximized_geometry(self):
        try:
            x, y, width, height = self._get_work_area_geometry()
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            self._is_maximized = True
            self._paint_window_control(self.maximize_btn, self.PANEL_ALT, self.MUTED)
        except Exception:
            pass

    def _parse_geometry(self, geometry):
        size, position = geometry.split("+", 1)
        width, height = size.split("x", 1)
        x_pos, y_pos = position.split("+", 1)
        return int(x_pos), int(y_pos), int(width), int(height)

    def _current_geometry_tuple(self):
        self.root.update_idletasks()
        return self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()

    def _animate_to_geometry(self, target):
        try:
            if self._window_transition is not None:
                self.root.after_cancel(self._window_transition)
                self._window_transition = None
        except Exception:
            self._window_transition = None
        self._destroy_transition_overlay()

        start = self._current_geometry_tuple()
        end_x, end_y, end_w, end_h = target
        end = (end_x, end_y, end_w, end_h)

        if start == end or not sys.platform.startswith("win"):
            self.root.geometry(f"{end_w}x{end_h}+{end_x}+{end_y}")
            self._animate_window_settle()
            return

        try:
            self._run_shell_transition(start, end)
        except Exception:
            self._destroy_transition_overlay()
            self.root.geometry(f"{end_w}x{end_h}+{end_x}+{end_y}")
            self._animate_window_settle()

    def _animate_window_settle(self):
        try:
            self.root.attributes("-alpha", 0.985)
        except Exception:
            return

        steps = 2
        duration = 45

        def _step(index):
            alpha = 0.985 + ((1.0 - 0.985) * (index / steps))
            try:
                self.root.attributes("-alpha", alpha)
            except Exception:
                self._window_transition = None
                return

            if index < steps:
                self._window_transition = self.root.after(duration // steps, lambda: _step(index + 1))
            else:
                try:
                    self.root.attributes("-alpha", 1.0)
                except Exception:
                    pass
                self._window_transition = None

        _step(1)

    def _ensure_transition_overlay(self):
        if self._transition_overlay and self._transition_overlay.winfo_exists():
            return

        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="#ff00ff")
        try:
            overlay.attributes("-transparentcolor", "#ff00ff")
        except Exception:
            pass

        shell = tk.Frame(
            overlay,
            bg=self.BORDER,
            bd=0,
            highlightthickness=0,
        )
        shell.pack(fill="both", expand=True)

        inner = tk.Frame(
            shell,
            bg=self.PANEL_ALT,
            bd=0,
            highlightthickness=0,
        )
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        silhouette_top = tk.Frame(
            inner,
            bg=self.PANEL,
            height=44,
            bd=0,
            highlightthickness=0,
        )
        silhouette_top.pack(fill="x", side="top")

        silhouette_body = tk.Frame(
            inner,
            bg=self.BG,
            bd=0,
            highlightthickness=0,
        )
        silhouette_body.pack(fill="both", expand=True)

        self._transition_overlay = overlay
        self._transition_shell = shell

    def _destroy_transition_overlay(self):
        try:
            if self._transition_overlay and self._transition_overlay.winfo_exists():
                self._transition_overlay.destroy()
        except Exception:
            pass
        self._transition_overlay = None
        self._transition_shell = None

    def _run_shell_transition(self, start, end):
        self._ensure_transition_overlay()
        steps = 6
        duration = 96

        if self._transition_overlay and self._transition_overlay.winfo_exists():
            self._transition_overlay.geometry(f"{start[2]}x{start[3]}+{start[0]}+{start[1]}")
            try:
                self._transition_overlay.update_idletasks()
            except Exception:
                pass

        def _step(index):
            t = index / steps
            eased = 1 - ((1 - t) ** 3)
            x = round(start[0] + ((end[0] - start[0]) * eased))
            y = round(start[1] + ((end[1] - start[1]) * eased))
            width = round(start[2] + ((end[2] - start[2]) * eased))
            height = round(start[3] + ((end[3] - start[3]) * eased))

            if self._transition_overlay and self._transition_overlay.winfo_exists():
                self._transition_overlay.geometry(f"{width}x{height}+{x}+{y}")

            if index < steps:
                self._window_transition = self.root.after(duration // steps, lambda: _step(index + 1))
            else:
                try:
                    self.root.attributes("-alpha", 0.985)
                except Exception:
                    pass
                self.root.geometry(f"{end[2]}x{end[3]}+{end[0]}+{end[1]}")
                self.root.update_idletasks()
                self._destroy_transition_overlay()
                self._window_transition = None
                self._animate_window_settle()

        _step(1)

    def _get_work_area_geometry(self):
        if sys.platform.startswith("win"):
            try:
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

                rect = RECT()
                SPI_GETWORKAREA = 0x0030
                ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
            except Exception:
                pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _refresh_overview(self):
        if self.playing:
            self.session_var.set("Automation active")
        elif self.bot:
            self.session_var.set("Browser attached and ready")
        else:
            self.session_var.set("Awaiting secure login")

        enabled_modes = []
        if self.expedition_var.get():
            enabled_modes.append("Expedition")
        if self.dungeon_var.get():
            enabled_modes.append("Dungeon")
        if self.circus_var.get():
            enabled_modes.append("Circus")
        self.combat_profile_var.set(" / ".join(enabled_modes) if enabled_modes else "No mechanics selected")

        sustain_rules = []
        if self.refill_hp_var.get():
            sustain_rules.append(f"HP refill < {self.get_min_hp_percent()}%")
        if self.recovery_buy_refill_var.get():
            sustain_rules.append(f"Buy pots < {self.get_recovery_threshold()}")
        self.sustain_profile_var.set(" | ".join(sustain_rules) if sustain_rules else "Manual sustain")

    def _build_credentials_panel(self, parent):
        panel = self._create_card(parent, 0, 0, pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=0)

        title_box = tk.Frame(panel, bg=self.PANEL)
        title_box.grid(row=0, column=0, sticky="ew")
        tk.Label(title_box, text="Account Vault", bg=self.PANEL, fg=self.TEXT, font=("Bahnschrift SemiBold", 16)).grid(row=0, column=0, sticky="w")
        tk.Label(
            title_box,
            text="Tek oturum uzerinden login ol, sonra tum mekanikleri ayni browser instance'i ile cevir.",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            wraplength=430,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Label(
            panel,
            text="SECURE",
            bg=self.PANEL_SOFT,
            fg=self.ACCENT_SOFT,
            font=("Bahnschrift SemiBold", 9),
            padx=12,
            pady=7,
        ).grid(row=0, column=1, sticky="ne")

        tk.Label(panel, text="Email", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=1, column=0, sticky="w", pady=(20, 6))
        self.email_entry = tk.Entry(panel)
        self._style_input(self.email_entry)
        self.email_entry.grid(row=2, column=0, columnspan=2, sticky="ew", ipady=9)
        if USERNAME:
            self.email_entry.insert(0, USERNAME)

        tk.Label(panel, text="Password", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=3, column=0, sticky="w", pady=(14, 6))
        self.password_entry = tk.Entry(panel, show="*")
        self._style_input(self.password_entry)
        self.password_entry.grid(row=4, column=0, columnspan=2, sticky="ew", ipady=9)
        if PASSWORD:
            self.password_entry.insert(0, PASSWORD)

        buttons_row = tk.Frame(panel, bg=self.PANEL)
        buttons_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        buttons_row.columnconfigure(0, weight=1)
        buttons_row.columnconfigure(1, weight=1)

        self.login_btn = ThemedButton(buttons_row, "Launch Session", self.start_login, variant="primary")
        self.login_btn.grid(row=0, column=0, sticky="ew")

        self.captcha_btn = ThemedButton(buttons_row, "Continue After CAPTCHA", self.captcha_solved_callback, variant="secondary")
        self.captcha_btn.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        self.captcha_btn.config(state="disabled")

        tk.Label(
            panel,
            text="Kayitli `.env` bilgileri otomatik dolar. Login sonrasi pencere premium kontrol paneli gibi canli kalir.",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
            wraplength=520,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def _build_controls_panel(self, parent):
        panel = self._create_card(parent, 1, 0, pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        tk.Label(panel, text="Control Deck", bg=self.PANEL, fg=self.TEXT, font=("Bahnschrift SemiBold", 16)).grid(row=0, column=0, sticky="w")
        tk.Label(
            panel,
            text="Operasyon dongusu 60 saniyelik pulse ile secili mekanikleri dener. Baslat, izole et, durdur.",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 16))

        self.play_btn = ThemedButton(panel, "Start Automation", self.toggle_play, variant="primary")
        self.play_btn.grid(row=2, column=0, sticky="ew")

        self.stop_btn = ThemedButton(panel, "Stop Loop", self.stop_play, variant="danger")
        self.stop_btn.grid(row=2, column=1, sticky="ew", padx=(12, 0))
        self.stop_btn.config(state="disabled")

        pulse_border, pulse = self._create_subcard(panel, bg=self.PANEL_SOFT, padx=14, pady=14)
        pulse_border.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        for idx, (title, value, color) in enumerate(
            (
                ("Cycle", "60s pulse", self.ACCENT_SOFT),
                ("CAPTCHA", "Manual handoff ready", self.INFO),
                ("Session", "Single browser context", self.SUCCESS),
            )
        ):
            block = tk.Frame(pulse, bg=self.PANEL_SOFT)
            block.grid(row=0, column=idx, sticky="ew", padx=(0, 14 if idx < 2 else 0))
            pulse.columnconfigure(idx, weight=1)
            tk.Label(block, text=title.upper(), bg=self.PANEL_SOFT, fg=self.MUTED, font=("Bahnschrift SemiBold", 8)).grid(row=0, column=0, sticky="w")
            tk.Label(block, text=value, bg=self.PANEL_SOFT, fg=color, font=("Segoe UI Semibold", 10)).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_mechanics_panel(self, parent):
        panel = self._create_card(parent, 2, 0, pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        tk.Label(panel, text="Mechanic Studio", bg=self.PANEL, fg=self.TEXT, font=("Bahnschrift SemiBold", 16)).grid(row=0, column=0, sticky="w")
        tk.Label(
            panel,
            text="Saldiri ve recovery akisini profesyonel bir operasyon ekranindaymis gibi tek yerden yonet.",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            wraplength=620,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 18))

        attack_grid = tk.Frame(panel, bg=self.PANEL)
        attack_grid.grid(row=2, column=0, columnspan=2, sticky="ew")
        for col in range(3):
            attack_grid.columnconfigure(col, weight=1)
        attack_cards = [
            ("Expedition", self.expedition_var, "Lokasyon + mob hedefi ile kontrollu farm."),
            ("Dungeon", self.dungeon_var, "Sehir haritasi uzerinden secili bolgeye akilli dalis."),
            ("Circus Turma", self.circus_var, "Hazir oldugunda arena denemelerini otomatik yokla."),
        ]
        for idx, (title, variable, description) in enumerate(attack_cards):
            border, card = self._create_subcard(attack_grid)
            border.grid(row=0, column=idx, sticky="nsew", padx=(0, 14 if idx < 2 else 0))
            ThemedCheckbox(card, title, variable, bg_color=self.PANEL_ALT, text_color=self.TEXT, muted_color=self.MUTED, accent_color=self.ACCENT_SOFT).grid(row=0, column=0, sticky="w")
            tk.Label(card, text=description, bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 9), wraplength=220, justify="left").grid(row=1, column=0, sticky="w", pady=(8, 0))

        expedition_border, expedition = self._create_subcard(panel, padx=18, pady=18)
        expedition_border.grid(row=3, column=0, sticky="nsew", pady=(18, 0), padx=(0, 9))
        expedition.columnconfigure(0, weight=1)
        tk.Label(expedition, text="Expedition Routing", bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
        tk.Label(
            expedition,
            text="Country map uzerinden lokasyon sec, sonra hedef mob slotunu kilitle.",
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        expedition_location_row = tk.Frame(expedition, bg=self.PANEL_ALT)
        expedition_location_row.grid(row=2, column=0, sticky="ew")
        expedition_location_row.columnconfigure(1, weight=1)
        tk.Label(expedition_location_row, text="Lokasyon", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.location_combo = self._register_dropdown(ThemedDropdown(
            expedition_location_row,
            self.expedition_location_var,
            [label for label, _ in self.EXPEDITION_LOCATIONS],
            bg_color=self.PANEL_ALT,
            panel_color=self.INPUT_BG,
            border_color=self.BORDER,
            text_color=self.TEXT,
            muted_color=self.MUTED,
            accent_color=self.ACCENT_SOFT,
            width=250,
        ))
        self.location_combo.grid(row=0, column=1, sticky="ew")

        choice_box = tk.Frame(expedition, bg=self.PANEL_ALT)
        choice_box.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        choice_box.columnconfigure(0, weight=1)
        choice_box.columnconfigure(1, weight=1)

        options = [
            ("1", "1. mob", "Ilk kutudaki hedef"),
            ("2", "2. mob", "Ikinci kutudaki hedef"),
            ("3", "3. mob", "Ucuncu kutudaki hedef"),
            ("4", "4. mob", "Dorduncu kutudaki hedef"),
        ]
        for idx, (value, label, description) in enumerate(options):
            row = idx // 2
            col = idx % 2
            option_border, option_card = self._create_subcard(choice_box, bg=self.PANEL_SOFT, padx=12, pady=12)
            option_border.grid(row=row, column=col, sticky="ew", padx=(0, 12 if col == 0 else 0), pady=(0, 12))
            tk.Radiobutton(
                option_card,
                text=label,
                value=value,
                variable=self.expedition_target_var,
                bg=self.PANEL_SOFT,
                fg=self.TEXT,
                activebackground=self.PANEL_SOFT,
                activeforeground=self.TEXT,
                selectcolor=self.INPUT_BG,
                font=("Segoe UI Semibold", 10),
            ).grid(row=0, column=0, sticky="w")
            tk.Label(option_card, text=description, bg=self.PANEL_SOFT, fg=self.MUTED, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=(24, 0), pady=(4, 0))

        dungeon_border, dungeon = self._create_subcard(panel, padx=18, pady=18)
        dungeon_border.grid(row=3, column=1, sticky="nsew", pady=(18, 0), padx=(9, 0))
        dungeon.columnconfigure(0, weight=1)
        tk.Label(dungeon, text="Dungeon Routing", bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
        tk.Label(
            dungeon,
            text="Expedition ile ayni lokasyon mantigini kullan; zorlugu sec, sonra random hedefe gir.",
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            font=("Segoe UI", 9),
            wraplength=320,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        dungeon_row = tk.Frame(dungeon, bg=self.PANEL_ALT)
        dungeon_row.grid(row=2, column=0, sticky="ew")
        dungeon_row.columnconfigure(1, weight=1)
        tk.Label(dungeon_row, text="Lokasyon", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.dungeon_combo = self._register_dropdown(ThemedDropdown(
            dungeon_row,
            self.dungeon_location_var,
            self.DUNGEON_LOCATIONS,
            bg_color=self.PANEL_ALT,
            panel_color=self.INPUT_BG,
            border_color=self.BORDER,
            text_color=self.TEXT,
            muted_color=self.MUTED,
            accent_color=self.ACCENT_SOFT,
            width=250,
        ))
        self.dungeon_combo.grid(row=0, column=1, sticky="ew")

        difficulty_box = tk.Frame(dungeon, bg=self.PANEL_ALT)
        difficulty_box.grid(row=3, column=0, sticky="w", pady=(16, 0))
        tk.Label(difficulty_box, text="Difficulty", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w", padx=(0, 12))
        for idx, label in enumerate(self.DUNGEON_DIFFICULTIES):
            tk.Radiobutton(
                difficulty_box,
                text=label,
                value=label,
                variable=self.dungeon_difficulty_var,
                bg=self.PANEL_ALT,
                fg=self.TEXT,
                activebackground=self.PANEL_ALT,
                activeforeground=self.TEXT,
                selectcolor=self.INPUT_BG,
                font=("Segoe UI Semibold", 10),
            ).grid(row=0, column=idx + 1, sticky="w", padx=(0, 12))

        recovery_header = tk.Frame(panel, bg=self.PANEL)
        recovery_header.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(22, 10))
        tk.Label(recovery_header, text="Recovery Automation", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
        tk.Label(
            recovery_header,
            text="HP dususunu ve refill pot stokunu ayni anda koru.",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        recovery_left_border, recovery_left = self._create_subcard(panel, bg=self.PANEL_ALT, padx=16, pady=16)
        recovery_left_border.grid(row=5, column=0, sticky="ew", padx=(0, 9))
        recovery_left.columnconfigure(1, weight=1)
        ThemedCheckbox(
            recovery_left,
            "Buy refill pots when stock drops",
            self.recovery_buy_refill_var,
            bg_color=self.PANEL_ALT,
            text_color=self.TEXT,
            muted_color=self.MUTED,
            accent_color=self.ACCENT_SOFT,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(recovery_left, text="Threshold", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=1, column=0, sticky="w", pady=(14, 6))
        self.recovery_threshold_entry = tk.Entry(
            recovery_left,
            width=8,
            textvariable=self.recovery_threshold_var,
        )
        self._style_numeric_input(self.recovery_threshold_entry)
        self.recovery_threshold_entry.grid(row=1, column=1, sticky="w", pady=(14, 6), ipady=6)

        recovery_right_border, recovery_right = self._create_subcard(panel, bg=self.PANEL_ALT, padx=16, pady=16)
        recovery_right_border.grid(row=5, column=1, sticky="ew", padx=(9, 0))
        recovery_right.columnconfigure(1, weight=1)
        ThemedCheckbox(
            recovery_right,
            "Refill HP automatically",
            self.refill_hp_var,
            bg_color=self.PANEL_ALT,
            text_color=self.TEXT,
            muted_color=self.MUTED,
            accent_color=self.ACCENT_SOFT,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(recovery_right, text="Min HP %", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 10)).grid(row=1, column=0, sticky="w", pady=(14, 6))
        self.hp_entry = tk.Entry(
            recovery_right,
            width=8,
            textvariable=self.hp_min_var,
        )
        self._style_numeric_input(self.hp_entry)
        self.hp_entry.grid(row=1, column=1, sticky="w", pady=(14, 6), ipady=6)

    def _build_expedition_panel(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Expedition Location", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text="Hermit ve Rise of the Forgotten haric country map uzerindeki eski ve yeni lokasyonlardan birini sec.",
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
        panel = self._create_card(parent, 0, 0, pady=(0, 12), padding=25)
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=0)

        tk.Label(panel, text="Activity Feed", bg=self.PANEL, fg=self.TEXT, font=("Bahnschrift SemiBold", 16)).grid(row=0, column=0, sticky="w")
        tk.Label(panel, text="LIVE", bg=self.PANEL_SOFT, fg=self.INFO, font=("Bahnschrift SemiBold", 9), padx=12, pady=7).grid(row=0, column=1, sticky="e")
        tk.Label(panel, text="Tum login, attack ve recovery denemeleri zaman damgasi ile buraya akar.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 10))
        self.log_text = tk.Text(
            panel,
            height=14,
            wrap="word",
            font=("Consolas", 10),
            padx=12,
            pady=8,
        )
        self._style_text_panel(self.log_text)
        self.log_text.grid(row=2, column=0, sticky="nsew")
        log_scroll = ModernScrollbar(
            panel,
            self.log_text.yview,
            bg_color=self.PANEL,
            track_color="#10161e",
            thumb_color=self.ACCENT,
            thumb_hover_color=self.ACCENT_SOFT,
        )
        log_scroll.grid(row=2, column=1, sticky="ns", padx=(12, 0), pady=2)
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _build_status_panel(self, parent):
        panel = self._create_card(parent, 0, 1, padx=(12, 0), pady=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)
        tk.Label(panel, text="Live Status", bg=self.PANEL, fg=self.TEXT, font=("Bahnschrift SemiBold", 16)).grid(row=0, column=0, sticky="w")
        tk.Label(panel, text="MONITOR", bg=self.PANEL_SOFT, fg=self.ACCENT_SOFT, font=("Bahnschrift SemiBold", 9), padx=12, pady=7).grid(row=0, column=1, sticky="e")

        hp_border, hp_spotlight = self._create_subcard(panel, bg=self.PANEL_SOFT, padx=16, pady=16)
        hp_border.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.hp_value = tk.Label(hp_spotlight, textvariable=self.hp_var, bg=self.PANEL_SOFT, fg=self.SUCCESS, font=("Bahnschrift SemiBold", 24))
        self.hp_value.grid(row=0, column=0, sticky="w")

        self.hp_refill_value = tk.Label(
            hp_spotlight,
            textvariable=self.hp_refill_count_var,
            bg=self.PANEL_SOFT,
            fg=self.INFO,
            font=("Segoe UI Semibold", 11),
        )
        self.hp_refill_value.grid(row=1, column=0, sticky="w", pady=(6, 0))

        mode_border, mode_card = self._create_subcard(panel, bg=self.PANEL_ALT, padx=16, pady=16)
        mode_border.grid(row=2, column=0, sticky="ew", pady=(16, 0), padx=(0, 8))
        tk.Label(mode_card, text="MODE", bg=self.PANEL_ALT, fg=self.MUTED, font=("Bahnschrift SemiBold", 9)).grid(row=0, column=0, sticky="w")
        self.mode_value = tk.Label(mode_card, text="Idle", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 11))
        self.mode_value.grid(row=1, column=0, sticky="w", pady=(8, 0))

        loop_border, loop_card = self._create_subcard(panel, bg=self.PANEL_ALT, padx=16, pady=16)
        loop_border.grid(row=2, column=1, sticky="ew", pady=(16, 0), padx=(8, 0))
        tk.Label(loop_card, text="LOOP", bg=self.PANEL_ALT, fg=self.MUTED, font=("Bahnschrift SemiBold", 9)).grid(row=0, column=0, sticky="w")
        self.loop_value = tk.Label(loop_card, text="Dongu bekliyor", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI Semibold", 11))
        self.loop_value.grid(row=1, column=0, sticky="w", pady=(8, 0))

    def _build_notes_panel(self, parent):
        panel = self._create_card(parent, 1, 0, pady=(11, 0), padding=18)
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=0)

        tk.Label(panel, text="Release Notes", bg=self.PANEL, fg=self.TEXT, font=("Bahnschrift SemiBold", 16)).grid(row=0, column=0, sticky="w")
        tk.Label(panel, text="LATEST 10", bg=self.PANEL_SOFT, fg=self.ACCENT_SOFT, font=("Bahnschrift SemiBold", 9), padx=12, pady=7).grid(row=0, column=1, sticky="e")
        tk.Label(panel, text="Son dokunuslar ve issue baglantili degisiklikler burada tutulur.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 12))

        self.change_notes_text = tk.Text(
            panel,
            height=12,
            wrap="word",
            padx=12,
            pady=10,
            font=("Segoe UI", 10),
        )
        self._style_text_panel(self.change_notes_text)
        self.change_notes_text.grid(row=2, column=0, sticky="nsew")
        notes_scroll = ModernScrollbar(
            panel,
            self.change_notes_text.yview,
            bg_color=self.PANEL,
            track_color="#10161e",
            thumb_color=self.ACCENT,
            thumb_hover_color=self.ACCENT_SOFT,
        )
        notes_scroll.grid(row=2, column=1, sticky="ns", padx=(12, 0), pady=2)
        self.change_notes_text.configure(yscrollcommand=notes_scroll.set)
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
                    prefix = f"- #{issue_number} " if issue_number else "- "
                    prefix_start = self.change_notes_text.index("end-1c")
                    self.change_notes_text.insert("end", prefix)
                    prefix_end = self.change_notes_text.index("end-1c")
                    title_start = self.change_notes_text.index("end-1c")
                    self.change_notes_text.insert("end", f"{issue_title}\n")
                    title_end = self.change_notes_text.index("end-1c")
                    if issue_number:
                        self.change_notes_text.tag_add("issue_prefix", prefix_start, prefix_end)
                    if issue_title:
                        self.change_notes_text.tag_add("issue_title", title_start, title_end)
                    if summary:
                        summary_start = self.change_notes_text.index("end-1c")
                        self.change_notes_text.insert("end", f"{summary}\n")
                        summary_end = self.change_notes_text.index("end-1c")
                        self.change_notes_text.tag_add("issue_summary", summary_start, summary_end)
                    self.change_notes_text.insert("end", "\n")
                else:
                    self.change_notes_text.insert("end", f"- {note}\n\n")
            self.change_notes_text.tag_configure("issue_prefix", foreground=self.ACCENT_SOFT, font=("Bahnschrift SemiBold", 10))
            self.change_notes_text.tag_configure("issue_title", foreground=self.TEXT, font=("Segoe UI Semibold", 10))
            self.change_notes_text.tag_configure("issue_summary", foreground=self.MUTED, spacing1=2, spacing3=6)
            self.change_notes_text.configure(state="disabled")
        except Exception:
            pass

    def _bind_mousewheel(self, canvas):
        def _on_mousewheel(event):
            widget = event.widget
            dropdown_owner = getattr(widget, "_dropdown_owner", None)
            if dropdown_owner and dropdown_owner._scroll_popup(-1 * int(event.delta / 120)):
                return "break"
            if not (self._has_ancestor(widget, ThemedDropdown) or hasattr(widget, "_dropdown_owner")):
                self._close_all_dropdowns()
            delta = -1 * int(event.delta / 120)
            canvas.yview_scroll(delta, "units")
            return "break"

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

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
        self._refresh_overview()
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
        self._refresh_overview()

    def _set_login_widgets_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.login_btn.config(state=state)
        self.email_entry.config(state=state)
        self.password_entry.config(state=state)

    def _set_captcha_enabled(self, enabled):
        self.captcha_btn.config(state="normal" if enabled else "disabled")

    def _set_play_state(self, playing):
        if playing:
            self.play_btn.config(text="Automation Running", state="disabled")
            self.stop_btn.config(state="normal")
            self.mode_value.config(text="Auto mode active", fg=self.SUCCESS)
            self.loop_value.config(text="Pulse is live", fg=self.ACCENT_SOFT)
        else:
            self.play_btn.config(text="Start Automation", state="normal")
            self.stop_btn.config(state="disabled")
            self.mode_value.config(text="Idle", fg=self.MUTED)
            self.loop_value.config(text="Dongu bekliyor", fg=self.MUTED)
        self._refresh_overview()

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
                try:
                    self.bot.quit()
                except Exception:
                    pass
                self.bot = None
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
                    try:
                        self.bot.quit()
                    except Exception:
                        pass
                    self.bot = None
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
            self._ui(self._refresh_overview)
        except Exception as exc:
            logger.error("Login worker error: %s", exc)
            try:
                if self.bot:
                    self.bot.quit()
            except Exception:
                pass
            self.bot = None
            self.update_status(f"Error: {str(exc)[:40]}", self.DANGER)
            self.append_log(f"Login error: {exc}")
            self._ui(lambda: self._set_login_widgets_enabled(True))
            self._ui(lambda: self._set_captcha_enabled(False))
            self._ui(self._refresh_overview)

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
