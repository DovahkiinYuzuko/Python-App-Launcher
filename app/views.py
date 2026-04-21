import customtkinter as ctk
import tkinter as tk
import psutil
from typing import List, Dict, Any, Optional
from .config import ConfigManager
from .font_loader import FontLoader

# --- Theme Colors ---
COLOR_BG = "#0F1115"
COLOR_SURFACE = "#1A1D23"
COLOR_TEXT = "#F8FAFC"
COLOR_TEXT_MUTED = "#475569" # スレートグレー (No blue)
COLOR_BORDER = "#2D333B"
COLOR_ACCENT = "#475569"
COLOR_GRAPH_GRID = "#2D333B"
COLOR_GRAPH_LINE = "#475569" # スレートグレー
COLOR_SUCCESS = "#162D24"    # 深いフォレストグリーン
COLOR_DANGER = "#3F1D1D"

class RealTimeGraph(ctk.CTkCanvas):
    """
    リアルタイムに流れる波形グラフを描画するカスタムキャンバス。
    """
    def __init__(self, master, width=300, height=100, max_value=100, **kwargs):
        super().__init__(master, width=width, height=height, bg=COLOR_SURFACE, highlightthickness=0, **kwargs)
        self.max_value = max_value
        self.data: List[float] = [0.0] * 50 # 50ポイント保持
        self.update_speed = 1000 # ms
        
        self.draw_grid()

    def draw_grid(self):
        """グリッド線を描画。"""
        self.delete("grid")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = 300
        if h <= 1:
            h = 100
        
        # 横線
        for i in range(1, 4):
            y = h * (i / 4)
            self.create_line(0, y, w, y, fill=COLOR_GRAPH_GRID, tags="grid")

    def update_data(self, new_val: float):
        """新しいデータを追加して再描画。"""
        self.data.pop(0)
        self.data.append(new_val)
        self.redraw()

    def redraw(self):
        self.delete("line")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = 300
        if h <= 1:
            h = 100
        
        points = []
        step = w / (len(self.data) - 1)
        
        for i, val in enumerate(self.data):
            x = i * step
            # 値を高さに変換 (上下反転)
            y = h - (val / self.max_value * h)
            points.extend([x, y])
            
        if len(points) >= 4:
            self.create_line(points, fill=COLOR_GRAPH_LINE, width=2, smooth=True, tags="line")

class StatCard(ctk.CTkFrame):
    """統計情報を表示するためのカードウィジェット。"""
    def __init__(self, master, title: str, subtitle: str, **kwargs):
        super().__init__(master, fg_color=COLOR_SURFACE, corner_radius=12, border_width=1, border_color=COLOR_BORDER, **kwargs)
        
        # ヘッダーContainer
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=(15, 5))
        
        self.title_label = ctk.CTkLabel(self.header, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_GRAPH_LINE)
        self.title_label.pack(side="left")
        
        self.subtitle_label = ctk.CTkLabel(self.header, text=f" | {subtitle}", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED)
        self.subtitle_label.pack(side="left", padx=5)

        self.val_label = ctk.CTkLabel(self, text="0%", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_TEXT)
        self.val_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.graph = RealTimeGraph(self, height=100)
        self.graph.pack(fill="x", padx=15, pady=(0, 15))

class StatsView(ctk.CTkScrollableFrame):
    """
    システムリソースの稼働状況を動的に表示するスクロール可能なビュー。
    """
    def __init__(self, master, app_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_manager = app_manager
        self.grid_columnconfigure(0, weight=1)
        self.font_family = FontLoader.get_system_default()
        
        self.title_label = ctk.CTkLabel(
            self, text=self.app_manager.i18n.get("system_stats") if hasattr(self.app_manager, "i18n") else "System Hardware Status", 
            font=ctk.CTkFont(family=self.font_family, size=24, weight="bold"), 
            text_color=COLOR_TEXT
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(10, 30), sticky="w")
        
        # 初期ステータスを取得
        stats = self.app_manager.get_system_stats()
        self.cards: Dict[str, StatCard] = {}

    def update_texts(self, i18n):
        self.title_label.configure(text=i18n.get("system_stats"))

        # 1. CPU Card
        self.cards['cpu'] = StatCard(self, "CPU", stats['cpu']['name'])
        self.cards['cpu'].grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # 2. RAM Card
        ram_subtitle = f"{stats['ram']['total']} GB Total"
        self.cards['ram'] = StatCard(self, "RAM", ram_subtitle)
        self.cards['ram'].grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        # 3. GPU Cards
        for i, gpu in enumerate(stats['gpus']):
            key = f"gpu_{i}"
            self.cards[key] = StatCard(self, f"GPU {i}", gpu['name'])
            self.cards[key].grid(row=2 + i, column=0, sticky="ew", padx=10, pady=10)

        self._update_loop()

    def _update_loop(self):
        stats = self.app_manager.get_system_stats()

        # CPU
        cpu_val = stats['cpu']['percent']
        self.cards['cpu'].val_label.configure(text=f"{cpu_val:.1f}%")
        self.cards['cpu'].graph.update_data(cpu_val)

        # RAM
        ram_val = stats['ram']['percent']
        ram_used = stats['ram']['used']
        ram_total = stats['ram']['total']
        self.cards['ram'].val_label.configure(text=f"{ram_val:.1f}% ({ram_used:.1f} / {ram_total:.1f} GB)")
        self.cards['ram'].graph.update_data(ram_val)

        # GPUs
        for i, gpu in enumerate(stats['gpus']):
            key = f"gpu_{i}"
            if key in self.cards:
                gpu_val = gpu['load']
                vram_used = gpu['memory_used']
                vram_total = gpu['memory_total']
                if vram_total > 100: # MB 単位
                    vram_used_gb = vram_used / 1024
                    vram_total_gb = vram_total / 1024
                    self.cards[key].val_label.configure(text=f"{gpu_val:.1f}% ({vram_used_gb:.1f} / {vram_total_gb:.1f} GB)")
                else: # GB 単位
                    self.cards[key].val_label.configure(text=f"{gpu_val:.1f}% ({vram_used:.1f} / {vram_total:.1f} GB)")
                self.cards[key].graph.update_data(gpu_val)

        self.after(2000, self._update_loop)

class SettingsView(ctk.CTkFrame):
    """
    アプリ全体の詳細設定を行うビュー。
    """
    def __init__(self, master, i18n, save_config_callback, settings, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.i18n = i18n
        self.save_config_callback = save_config_callback
        self.settings = settings # Use shared settings object
        
        self.grid_columnconfigure(0, weight=1)
        self.font_family = FontLoader.get_system_default()
        
        # タイトル
        self.title_label = ctk.CTkLabel(self, text=self.i18n.get("app_settings"), font=ctk.CTkFont(family=self.font_family, size=24, weight="bold"), text_color=COLOR_TEXT)
        self.title_label.grid(row=0, column=0, padx=20, pady=(10, 30), sticky="w")
        
        # 1. 終了時の挙動設定
        self.behavior_f = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        self.behavior_f.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.behavior_f.grid_columnconfigure(0, weight=1)
        
        # トレイ設定 (論理反転: exit_on_close)
        # 以前の close_to_tray から移行しつつ、デフォルトは False (終了しない=トレイに隠す)
        init_val = self.settings.get("exit_on_close", not self.settings.get("close_to_tray", True))
        self.tray_var = ctk.BooleanVar(value=init_val)
        
        self.tray_switch = ctk.CTkSwitch(
            self.behavior_f, text=self.i18n.get("label_exit_on_close"), 
            variable=self.tray_var, command=self._on_setting_change,
            font=ctk.CTkFont(family=self.font_family, size=14),
            progress_color=COLOR_ACCENT
        )
        self.tray_switch.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.tray_desc = ctk.CTkLabel(
            self.behavior_f, text=self.i18n.get("desc_exit_on_close"),
            font=ctk.CTkFont(family=self.font_family, size=12),
            text_color=COLOR_TEXT_MUTED
        )
        self.tray_desc.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

    def update_texts(self):
        self.title_label.configure(text=self.i18n.get("app_settings"))
        self.tray_switch.configure(text=self.i18n.get("label_exit_on_close"))
        self.tray_desc.configure(text=self.i18n.get("desc_exit_on_close"))

    def _on_setting_change(self):
        # 親（AppGUI）の設定オブジェクトを直接更新 (論理: exit_on_close)
        val = self.tray_var.get()
        self.settings["exit_on_close"] = val
        # 古いキーを念のため削除
        if "close_to_tray" in self.settings:
            del self.settings["close_to_tray"]
        # 設定を保存
        self.save_config_callback()
