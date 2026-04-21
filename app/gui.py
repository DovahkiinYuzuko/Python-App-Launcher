import customtkinter as ctk
from typing import Dict, List, Optional, Callable, Tuple, Any, cast
from .app_manager import AppManager
from .i18n import I18nManager
from .config import ConfigManager
from .font_loader import FontLoader
from .views import StatsView, SettingsView
import sys
from pathlib import Path
import pystray
from pystray import MenuItem as item
from PIL import Image
import threading
import tkinter as tk
import datetime

# --- 2026 Ultimate Modern Theme Colors ---
COLOR_BG = "#0F1115"
COLOR_SURFACE = "#1A1D23"
COLOR_INNER_BG = "#090B0F"
COLOR_ACCENT = "#475569"
COLOR_SUCCESS = "#162D24"
COLOR_DANGER = "#3F1D1D"
COLOR_TEXT = "#F8FAFC"
COLOR_TEXT_MUTED = "#475569"
COLOR_BORDER = "#2D333B"

class NavButton(ctk.CTkButton):
    """インジケーター付きのサイドバー用ボタン。"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.indicator: Optional[ctk.CTkFrame] = None

class Tooltip:
    """ウィジェットにマウスオーバーした際にヒントを表示するクラス。"""
    def __init__(self, widget, i18n, key=None, text=None):
        self.widget = widget
        self.i18n = i18n
        self.key = key
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window:
            return
        
        display_text = self.text
        if self.key:
            display_text = self.i18n.get(self.key)
            
        if not display_text:
            return
            
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        font_family = FontLoader.get_system_default()
        tk.Label(
            tw, text=display_text, justify='left', 
            background="#1E293B", foreground="#F1F5F9", 
            relief='flat', borderwidth=0, 
            font=(font_family, 10), padx=8, pady=4
        ).pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class FileItemFrame(ctk.CTkFrame):
    """個別の .py ファイルを表示・操作するフレーム。"""
    def __init__(self, master, file_data, project_data, app_manager, i18n, save_callback, gui_root, python_list, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.file_data = file_data
        self.project_data = project_data
        self.app_manager = app_manager
        self.i18n = i18n
        self.save_callback = save_callback
        self.gui_root = gui_root
        self.python_list = python_list
        self.log_expanded = False
        self.font_family = FontLoader.get_system_default()
        
        # Python パス表示用のマッピング作成
        self.py_map = {} # display_str -> full_str
        self.py_display_list = []
        for py_full in self.python_list:
            display = self._format_py_path(py_full)
            self.py_map[display] = py_full
            self.py_display_list.append(display)

        self.grid_columnconfigure(1, weight=1)
        
        # --- 1段目 ---
        self.main_row = ctk.CTkFrame(self, fg_color="transparent")
        self.main_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5)
        self.main_row.grid_columnconfigure(2, weight=1)
        
        self.status_canvas = ctk.CTkCanvas(self.main_row, width=12, height=12, bg=COLOR_INNER_BG, highlightthickness=0)
        self.status_canvas.grid(row=0, column=0, padx=(10, 5), pady=10)
        self.status_oval = self.status_canvas.create_oval(1, 1, 11, 11, fill="#475569")
        
        self.name_label = ctk.CTkLabel(
            self.main_row, text=file_data.get("filename", "unknown.py"), 
            text_color=COLOR_TEXT, font=ctk.CTkFont(family=self.font_family, size=13, weight="bold")
        )
        self.name_label.grid(row=0, column=1, padx=5, sticky="w")
        
        self.resource_label = ctk.CTkLabel(self.main_row, text="", text_color=COLOR_ACCENT, font=("Consolas", 13, "bold"), width=160)
        self.resource_label.grid(row=0, column=2, padx=20, sticky="w")

        self.switch_var = ctk.StringVar(value="off")
        self.toggle_switch = ctk.CTkSwitch(
            self.main_row, text="", command=self._on_toggle, 
            variable=self.switch_var, onvalue="on", offvalue="off", progress_color=COLOR_SUCCESS
        )
        self.toggle_switch.grid(row=0, column=3, padx=10)
        
        self.log_button = ctk.CTkButton(
            self.main_row, text="▼ Log", width=60, height=28, 
            fg_color="#334155", hover_color="#475569", 
            command=self._toggle_log, font=ctk.CTkFont(family=self.font_family, size=11)
        )
        self.log_button.grid(row=0, column=4, padx=(5, 10))
        Tooltip(self.log_button, self.i18n, "tt_log")
        
        # --- 2段目 ---
        self.details_row = ctk.CTkFrame(self, fg_color=COLOR_INNER_BG, corner_radius=6)
        self.details_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(30, 10), pady=(0, 5))
        
        self.py_label = ctk.CTkLabel(self.details_row, text=self.i18n.get("label_python"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family, size=10))
        self.py_label.grid(row=0, column=0, padx=(10, 2), pady=5)
        
        current_py = file_data.get("custom_python") or sys.executable
        if current_py and not str(current_py).startswith("Python "):
            for py_str in self.python_list:
                if f"({str(current_py).lower()})" in py_str.lower():
                    current_py = py_str
                    break
        
        # 表示名に変換
        display_init = self._format_py_path(current_py)
        self.py_var = ctk.StringVar(value=display_init)
        self.py_dropdown = ctk.CTkOptionMenu(
            self.details_row, values=self.py_display_list, variable=self.py_var, 
            width=140, height=24, fg_color=COLOR_BG, button_color="#334155", 
            button_hover_color="#475569", dropdown_fg_color=COLOR_SURFACE, 
            font=ctk.CTkFont(family=self.font_family, size=10), command=self._save_args
        )
        self.py_dropdown.grid(row=0, column=1, padx=2, pady=5)
        Tooltip(self.py_dropdown, self.i18n, "tt_python")

        self.restart_var = ctk.BooleanVar(value=file_data.get("auto_restart", False))
        self.restart_switch = ctk.CTkSwitch(
            self.details_row, text=self.i18n.get("label_restart"), 
            variable=self.restart_var, command=self._save_args, 
            width=40, font=ctk.CTkFont(family=self.font_family, size=10), 
            text_color=COLOR_TEXT_MUTED, progress_color=COLOR_ACCENT
        )
        self.restart_switch.grid(row=0, column=2, padx=10, pady=5)
        Tooltip(self.restart_switch, self.i18n, "tt_restart")

        self.args_label = ctk.CTkLabel(self.details_row, text=self.i18n.get("label_args"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family, size=10))
        self.args_label.grid(row=0, column=3, padx=(10, 2), pady=5)
        self.args_entry = ctk.CTkEntry(self.details_row, placeholder_text=self.i18n.get("arguments"), width=120, height=24, border_color=COLOR_BORDER, fg_color=COLOR_BG, font=ctk.CTkFont(family=self.font_family, size=11))
        self.args_entry.insert(0, file_data.get("arguments", ""))
        self.args_entry.grid(row=0, column=4, padx=2, pady=5)
        self.args_entry.bind("<FocusOut>", self._save_args)
        Tooltip(self.args_entry, self.i18n, "tt_args")

        self.sched_label = ctk.CTkLabel(self.details_row, text=self.i18n.get("label_schedule"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family, size=10))
        self.sched_label.grid(row=0, column=5, padx=(10, 2), pady=5)
        self.schedule_entry = ctk.CTkEntry(self.details_row, placeholder_text="HH:MM", width=60, height=24, border_color=COLOR_BORDER, fg_color=COLOR_BG, font=ctk.CTkFont(family=self.font_family, size=11))
        self.schedule_entry.insert(0, file_data.get("schedule", ""))
        self.schedule_entry.grid(row=0, column=6, padx=2, pady=5)
        self.schedule_entry.bind("<FocusOut>", self._save_args)
        Tooltip(self.schedule_entry, self.i18n, "tt_schedule")

        self.flags_f = ctk.CTkFrame(self.details_row, fg_color="transparent")
        self.flags_f.grid(row=0, column=7, padx=15)
        
        self.auto_var = ctk.BooleanVar(value=file_data.get("auto_start", False))
        self.auto_checkbox = ctk.CTkCheckBox(self.flags_f, text=self.i18n.get("auto"), variable=self.auto_var, command=self._save_args, width=18, font=ctk.CTkFont(family=self.font_family, size=10), border_color=COLOR_BORDER)
        self.auto_checkbox.grid(row=0, column=0, padx=5)
        Tooltip(self.auto_checkbox, self.i18n, "tt_auto")
        
        self.venv_var = ctk.BooleanVar(value=file_data.get("use_venv", False))
        self.venv_checkbox = ctk.CTkCheckBox(self.flags_f, text=self.i18n.get("venv_label"), variable=self.venv_var, command=self._save_args, width=18, font=ctk.CTkFont(family=self.font_family, size=10), border_color=COLOR_BORDER)
        self.venv_checkbox.grid(row=0, column=1, padx=5)
        if not self.project_data.get("venv"):
            self.venv_checkbox.configure(state="disabled")
        Tooltip(self.venv_checkbox, self.i18n, "tt_venv")
            
        self.console_var = ctk.BooleanVar(value=file_data.get("in_console", False))
        self.console_checkbox = ctk.CTkCheckBox(self.flags_f, text=self.i18n.get("console_label"), variable=self.console_var, command=self._save_args, width=18, font=ctk.CTkFont(family=self.font_family, size=10), border_color=COLOR_BORDER)
        self.console_checkbox.grid(row=0, column=2, padx=5)
        Tooltip(self.console_checkbox, self.i18n, "tt_console")
        
        self.bulk_var = ctk.BooleanVar(value=file_data.get("bulk_target", False))
        self.bulk_checkbox = ctk.CTkCheckBox(self.flags_f, text=self.i18n.get("bulk_label"), variable=self.bulk_var, command=self._save_args, width=18, font=ctk.CTkFont(family=self.font_family, size=10), border_color=COLOR_BORDER)
        self.bulk_checkbox.grid(row=0, column=3, padx=5)
        Tooltip(self.bulk_checkbox, self.i18n, "tt_bulk")

        self.log_filter_entry = ctk.CTkEntry(self, placeholder_text=self.i18n.get("tt_log_filter"), width=120, height=22, font=ctk.CTkFont(family=self.font_family, size=10), border_color=COLOR_BORDER, fg_color=COLOR_BG)
        self.log_textbox = ctk.CTkTextbox(self, height=150, font=("Consolas", 12), fg_color=COLOR_INNER_BG, text_color="#E2E8F0", border_width=1, border_color=COLOR_BORDER)
        self.log_textbox.tag_config("error", foreground="#FB7185")
        self.log_textbox.tag_config("warning", foreground="#FBBF24")
        self.log_textbox.tag_config("success", foreground="#34D399")
        self.log_textbox.tag_config("info", foreground="#475569")
        self.log_textbox.configure(state="disabled")
        
        for w in [self.main_row, self.name_label]:
            w.bind("<Button-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_motion)
            w.bind("<ButtonRelease-1>", self._on_drag_release)
            
        self._update_status_ui()

    def _format_py_path(self, path_str: str, max_len: int = 40) -> str:
        """Python パス文字列を短縮フォーマットする。"""
        if not path_str:
            return "Unknown"
        if len(path_str) <= max_len:
            return path_str
        # 'Python 3.10.0 (C:\...)' 形式を想定
        if " (" in path_str and path_str.endswith(")"):
            prefix, path = path_str.split(" (", 1)
            path = path[:-1] # 末尾の ')' を除去
            available_for_path = max_len - len(prefix) - 5
            if available_for_path > 10:
                return f"{prefix} (...{path[-available_for_path:]})"
        return path_str[:max_len-3] + "..."

    def update_texts(self):
        self.args_label.configure(text=self.i18n.get("label_args"))
        self.args_entry.configure(placeholder_text=self.i18n.get("arguments"))
        self.sched_label.configure(text=self.i18n.get("label_schedule"))
        if self.log_expanded:
            self.log_button.configure(text="▲ Log")
        else:
            self.log_button.configure(text="▼ Log")
        self.auto_checkbox.configure(text="Auto")
        self.bulk_checkbox.configure(text=self.i18n.get("bulk"))
        self.log_filter_entry.configure(placeholder_text=self.i18n.get("tt_log_filter"))

    def _update_status_ui(self):
        status = self.app_manager.get_status(self.file_data["id"])
        if status == "running":
            color = "#10B981"
            self.switch_var.set("on")
            self._update_resources()
        else:
            color = "#475569"
            self.switch_var.set("off")
            self.resource_label.configure(text="")
        self.status_canvas.itemconfig(self.status_oval, fill=color)

    def _update_resources(self):
        if self.app_manager.get_status(self.file_data["id"]) != "running":
            return
        interval = 2000 if self.gui_root.winfo_viewable() != 0 else 10000
        res = self.app_manager.get_process_resources(self.file_data["id"])
        self.resource_label.configure(text=f"CPU:{res['cpu']}% RAM:{res['memory']}MB")
        self.after(interval, self._update_resources)

    def _save_args(self, event=None):
        self.file_data["arguments"] = self.args_entry.get()
        self.file_data["in_console"] = self.console_var.get()
        self.file_data["use_venv"] = self.venv_var.get()
        self.file_data["auto_start"] = self.auto_var.get()
        self.file_data["schedule"] = self.schedule_entry.get()
        self.file_data["bulk_target"] = self.bulk_var.get()
        
        # 表示名から元のフルパスに復元
        display_val = self.py_var.get()
        self.file_data["custom_python"] = self.py_map.get(display_val, display_val)
        
        self.save_callback()

    def _on_toggle(self):
        if self.switch_var.get() == "on":
            self._save_args()
            max_apps = ConfigManager.get_settings().get("max_running_apps", 5)
            if len(self.app_manager.processes) >= max_apps:
                from tkinter import messagebox
                messagebox.showwarning(self.i18n.get("limit_reached"), self.i18n.get("max_apps_warning").format(max_apps=max_apps))
                self.switch_var.set("off")
                return
            
            # 実行時もマッピングからフルパスを取得
            py_full = self.py_map.get(self.py_var.get(), self.py_var.get())
            success = self.app_manager.start_app(
                self.file_data["id"], 
                log_callback=self._append_log, 
                in_console=self.console_var.get(), 
                use_venv=self.venv_var.get(),
                custom_python=py_full
            )
            if not success:
                self.switch_var.set("off")
        else:
            self.app_manager.stop_app(self.file_data["id"])
        self._update_status_ui()

    def _append_log(self, text: str):
        f_val = self.log_filter_entry.get().lower()
        if f_val and f_val not in text.lower():
            return
        self.log_textbox.configure(state="normal")
        s_idx = self.log_textbox.index("end-1c")
        self.log_textbox.insert("end", text)
        e_idx = self.log_textbox.index("end-1c")
        u_text = text.upper()
        if any(kw in u_text for kw in ["ERROR", "EXCEPTION", "CRITICAL"]):
            self.log_textbox.tag_add("error", s_idx, e_idx)
        elif any(kw in u_text for kw in ["WARNING", "WARN"]):
            self.log_textbox.tag_add("warning", s_idx, e_idx)
        elif any(kw in u_text for kw in ["SUCCESS", "READY", "STARTED"]):
            self.log_textbox.tag_add("success", s_idx, e_idx)
        elif "INFO" in u_text:
            self.log_textbox.tag_add("info", s_idx, e_idx)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        if not self.log_expanded:
            self._toggle_log()
        if "--- App Process Terminated ---" in text:
            self.after(100, self._update_status_ui)

    def _toggle_log(self):
        if self.log_expanded:
            self.log_filter_entry.grid_forget()
            self.log_textbox.grid_forget()
            self.log_button.configure(text="▼ Log")
        else:
            self.log_filter_entry.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 5), sticky="w")
            self.log_textbox.grid(row=3, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="nsew")
            self.log_button.configure(text="▲ Log")
        self.log_expanded = not self.log_expanded

    def _on_drag_start(self, event):
        self.gui_root.configure(cursor="fleur")
    def _on_drag_motion(self, event): pass
    def _on_drag_release(self, event):
        self.gui_root.configure(cursor="")
        self.gui_root._handle_project_drop(self.project_data["id"], event.x_root, event.y_root)

class ProjectFrame(ctk.CTkFrame):
    """プロジェクトごとの枠を表示し、ファイルを管理するフレーム。"""
    def __init__(self, master, project_data, app_manager, i18n, delete_callback, save_callback, refresh_callback, gui_root, python_list, **kwargs):
        super().__init__(master, fg_color=COLOR_SURFACE, corner_radius=10, border_width=1, border_color=COLOR_BORDER, **kwargs)
        self.project_data = project_data
        self.app_manager = app_manager
        self.i18n = i18n
        self.delete_callback = delete_callback
        self.save_callback = save_callback
        self.refresh_callback = refresh_callback
        self.gui_root = gui_root
        self.python_list = python_list
        self.font_family = FontLoader.get_system_default()
        self.grid_columnconfigure(0, weight=1)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        self.header.grid_columnconfigure(1, weight=1)
        
        self.fav_var = ctk.StringVar(value="★" if project_data.get("favorite", False) else "☆")
        self.fav_btn = ctk.CTkButton(self.header, textvariable=self.fav_var, width=30, fg_color="transparent", text_color="#FACC15", font=ctk.CTkFont(family=self.font_family, size=20), command=self._toggle_favorite)
        self.fav_btn.grid(row=0, column=0, padx=(0, 5))
        Tooltip(self.fav_btn, self.i18n, "tt_fav")
        
        self.name_btn = ctk.CTkButton(self.header, text=f"📁 {project_data['name']}", anchor="w", fg_color="transparent", text_color=COLOR_TEXT, hover_color="#2D333B", font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"), command=self._toggle_collapse)
        self.name_btn.grid(row=0, column=1, sticky="ew")
        
        for w in [self.header, self.name_btn]:
            w.bind("<Button-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_motion)
            w.bind("<ButtonRelease-1>", self._on_drag_release)

        self.act_f = ctk.CTkFrame(self.header, fg_color="transparent")
        self.act_f.grid(row=0, column=2, sticky="e")
        
        self.tags_entry = ctk.CTkEntry(self.act_f, placeholder_text="Tag1, Tag2", width=120, height=26, border_color=COLOR_BORDER, fg_color=COLOR_INNER_BG, font=ctk.CTkFont(family=self.font_family, size=11))
        self.tags_entry.insert(0, ",".join(project_data.get("tags", [])))
        self.tags_entry.grid(row=0, column=0, padx=5)
        self.tags_entry.bind("<FocusOut>", self._save_tags)
        Tooltip(self.tags_entry, self.i18n, "tt_tags")
        
        has_v = project_data.get("venv")
        self.setup_btn = ctk.CTkButton(self.act_f, text=self.i18n.get("venv_ok") if has_v else self.i18n.get("setup_venv"), width=80, height=26, fg_color="#334155", state="disabled" if has_v else "normal", command=self._on_setup_venv, font=ctk.CTkFont(family=self.font_family, size=11))
        self.setup_btn.grid(row=0, column=1, padx=3)
        Tooltip(self.setup_btn, self.i18n, "tt_setup_venv")
        
        self.up_btn = ctk.CTkButton(self.act_f, text=self.i18n.get("update_libs"), width=80, height=26, fg_color="#334155", state="normal" if has_v else "disabled", command=self._on_update_libs, font=ctk.CTkFont(family=self.font_family, size=11))
        self.up_btn.grid(row=0, column=2, padx=3)
        Tooltip(self.up_btn, self.i18n, "tt_update_libs")
        
        self.folder_btn = ctk.CTkButton(self.act_f, text="📁", width=30, height=26, fg_color="transparent", hover_color="#2D333B", command=lambda: self.app_manager.open_in_file_manager(self.project_data["id"]))
        self.folder_btn.grid(row=0, column=3, padx=1)
        Tooltip(self.folder_btn, self.i18n, "tt_folder")

        self.term_btn = ctk.CTkButton(self.act_f, text="💻", width=30, height=26, fg_color="transparent", hover_color="#2D333B", command=lambda: self.app_manager.open_in_terminal(self.project_data["id"]))
        self.term_btn.grid(row=0, column=4, padx=1)
        Tooltip(self.term_btn, self.i18n, "tt_terminal")
        
        self.del_btn = ctk.CTkButton(self.act_f, text=self.i18n.get("delete"), width=60, height=26, fg_color=COLOR_DANGER, hover_color="#5D2626", command=self._on_delete, font=ctk.CTkFont(family=self.font_family, size=11))
        self.del_btn.grid(row=0, column=5, padx=5)
        Tooltip(self.del_btn, self.i18n, "tt_delete")
        
        self.files_c = ctk.CTkFrame(self, fg_color="#111827", corner_radius=0)
        self.files_c.grid(row=1, column=0, sticky="ew", padx=1, pady=(0, 1))
        self.files_c.grid_columnconfigure(0, weight=1)
        self.file_frames = {}
        self.collapsed = project_data.get("collapsed", True)
        if self.collapsed:
            self.files_c.grid_remove()
        else:
            self.files_c.grid()
            self._refresh_files()

    def update_texts(self):
        has_v = self.project_data.get("venv")
        self.setup_btn.configure(text=self.i18n.get("venv_ok") if has_v else self.i18n.get("setup_venv"))
        self.up_btn.configure(text=self.i18n.get("update_libs"))
        self.del_btn.configure(text=self.i18n.get("delete"))
        for ff in self.file_frames.values():
            ff.update_texts()

    def _toggle_favorite(self):
        self.project_data["favorite"] = not self.project_data.get("favorite", False)
        self.fav_var.set("★" if self.project_data["favorite"] else "☆")
        self.save_callback()
        self.refresh_callback()

    def _save_tags(self, event=None):
        tags = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
        if self.project_data.get("tags") != tags:
            self.project_data["tags"] = tags
            self.save_callback()
            self.refresh_callback()

    def _refresh_files(self):
        c_ids = [f["id"] for f in self.project_data.get("files", [])]
        for fid in list(self.file_frames.keys()):
            if fid not in c_ids:
                self.file_frames[fid].destroy()
                del self.file_frames[fid]
        for i, f in enumerate(self.project_data.get("files", [])):
            if f["id"] not in self.file_frames:
                self.file_frames[f["id"]] = FileItemFrame(self.files_c, f, self.project_data, self.app_manager, self.i18n, self.save_callback, self.gui_root, self.python_list)
            ff = self.file_frames[f["id"]]
            if ff.grid_info().get("row") != str(i):
                ff.grid(row=i, column=0, sticky="ew", pady=2)

    def _toggle_collapse(self):
        if self.collapsed:
            self._refresh_files()
            self.files_c.grid()
        else:
            self.files_c.grid_remove()
        self.collapsed = not self.collapsed
        self.project_data["collapsed"] = self.collapsed
        self.save_callback()

    def _on_setup_venv(self):
        self.setup_btn.configure(state="disabled", text="...")
        self.app_manager.setup_venv(self.project_data["id"], log_callback=self._on_setup_log)
    def _on_setup_log(self, text):
        if not self.file_frames:
            self._refresh_files()
            self.files_c.grid()
            self.collapsed = False
            self.save_callback()
        if self.file_frames:
            next(iter(self.file_frames.values()))._append_log(text)
        if "--- Venv Setup Completed Successfully" in text:
            self.after(100, lambda: [self.setup_btn.configure(text=self.i18n.get("venv_ok"), state="disabled"), self.up_btn.configure(state="normal"), self.save_callback()])
    def _on_update_libs(self):
        self.up_btn.configure(state="disabled", text="...")
        self.app_manager.update_dependencies(self.project_data["id"], log_callback=self._on_update_log)
    def _on_update_log(self, text):
        if not self.file_frames:
            self._refresh_files()
            self.files_c.grid()
            self.collapsed = False
            self.save_callback()
        if self.file_frames:
            next(iter(self.file_frames.values()))._append_log(text)
        if "--- Dependency Update Completed Successfully" in text:
            self.after(100, lambda: self.up_btn.configure(text=self.i18n.get("update_libs"), state="normal"))
    def _on_delete(self): self.delete_callback(self.project_data["id"])
    def _on_drag_start(self, e): self.gui_root.configure(cursor="fleur")
    def _on_drag_motion(self, e): pass
    def _on_drag_release(self, e):
        self.gui_root.configure(cursor="")
        self.gui_root._handle_project_drop(self.project_data["id"], e.x_root, e.y_root)

class GroupEditDialog(ctk.CTkToplevel):
    def __init__(self, master: 'AppGUI', app_manager, i18n, group_id=None, **kwargs):
        super().__init__(master, **kwargs)
        self.gui = master
        self.app_manager = app_manager
        self.i18n = i18n
        self.group_id = group_id
        self.group_data = None
        if self.group_id:
            for g in self.app_manager.groups:
                if g["id"] == self.group_id:
                    self.group_data = g
                    break
        self.title(self.i18n.get("edit_group" if self.group_id else "add_group"))
        self.geometry("500x650")
        self.configure(fg_color=COLOR_BG)
        self.attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        self.font_family = FontLoader.get_system_default()
        ctk.CTkLabel(self, text=self.i18n.get("group_name"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family)).grid(row=0, column=0, padx=20, pady=(20, 0), sticky="w")
        self.name_entry = ctk.CTkEntry(self, width=400, border_color=COLOR_BORDER, font=ctk.CTkFont(family=self.font_family))
        self.name_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        if self.group_data:
            self.name_entry.insert(0, self.group_data["name"])
        ctk.CTkLabel(self, text=self.i18n.get("icon"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family)).grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.icon_entry = ctk.CTkEntry(self, width=100, border_color=COLOR_BORDER, font=ctk.CTkFont(family=self.font_family))
        self.icon_entry.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.icon_entry.insert(0, self.group_data.get("icon", "📁") if self.group_data else "📁")
        ctk.CTkLabel(self, text=self.i18n.get("members"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family)).grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")
        self.projects_frame = ctk.CTkScrollableFrame(self, fg_color=COLOR_SURFACE, border_width=1, border_color=COLOR_BORDER)
        self.projects_frame.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")
        self.projects_frame.grid_columnconfigure(0, weight=1)
        self.project_vars = {}
        m_ids = [p["id"] for p in self.app_manager.apps if p.get("group_id") == self.group_id] if self.group_id else []
        for i, p in enumerate(self.app_manager.apps):
            v = tk.BooleanVar(value=p["id"] in m_ids)
            c = ctk.CTkCheckBox(self.projects_frame, text=p["name"], variable=v, font=ctk.CTkFont(family=self.font_family))
            c.grid(row=i, column=0, padx=10, pady=5, sticky="w")
            self.project_vars[p["id"]] = v
        self.act_f = ctk.CTkFrame(self, fg_color="transparent")
        self.act_f.grid(row=6, column=0, padx=20, pady=20, sticky="ew")
        self.act_f.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(self.act_f, text=self.i18n.get("save"), fg_color=COLOR_ACCENT, command=self._on_save, font=ctk.CTkFont(family=self.font_family, weight="bold")).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(self.act_f, text=self.i18n.get("cancel"), fg_color="#334155", command=self.destroy, font=ctk.CTkFont(family=self.font_family)).grid(row=0, column=1, padx=5, sticky="ew")
    def _on_save(self):
        n, i = self.name_entry.get().strip(), self.icon_entry.get().strip()
        if not n: return
        icon = i[0] if i else "📁"
        p_ids = [pid for pid, v in self.project_vars.items() if v.get()]
        if self.group_id:
            self.app_manager.update_group(self.group_id, n, icon, p_ids)
        else:
            self.app_manager.add_group(n, icon, p_ids)
        self.gui._save_config()
        self.gui._refresh_sidebar()
        self.gui._refresh_app_list(self.gui.search_entry.get())
        self.destroy()

class CloneDialog(ctk.CTkToplevel):
    def __init__(self, master: 'AppGUI', app_manager, i18n, refresh_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.gui = master
        self.app_manager = app_manager
        self.i18n = i18n
        self.refresh_callback = refresh_callback
        self.title(self.i18n.get("clone_dialog_title"))
        self.geometry("600x550")
        self.configure(fg_color=COLOR_BG)
        self.attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.font_family = FontLoader.get_system_default()
        ctk.CTkLabel(self, text=self.i18n.get("repo_url"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family)).grid(row=0, column=0, padx=20, pady=(20, 0), sticky="w")
        self.url_entry = ctk.CTkEntry(self, placeholder_text="https://github.com/user/repo", width=500, border_color=COLOR_BORDER, font=ctk.CTkFont(family=self.font_family))
        self.url_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        ctk.CTkLabel(self, text=self.i18n.get("dest_path"), text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family)).grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.dest_f = ctk.CTkFrame(self, fg_color="transparent")
        self.dest_f.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.dest_f.grid_columnconfigure(0, weight=1)
        self.d_p_v = tk.StringVar(value=str(Path.home() / "Documents"))
        self.d_e = ctk.CTkEntry(self.dest_f, textvariable=self.d_p_v, state="readonly", border_color=COLOR_BORDER, font=ctk.CTkFont(family=self.font_family))
        self.d_e.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        ctk.CTkButton(self.dest_f, text=self.i18n.get("select_folder"), fg_color="#334155", command=self._on_select_dest, font=ctk.CTkFont(family=self.font_family)).grid(row=0, column=1)
        self.log_t = ctk.CTkTextbox(self, height=150, font=("Consolas", 12), fg_color="#0F172A", border_width=1, border_color=COLOR_BORDER)
        self.log_t.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        self.log_t.configure(state="disabled")
        self.act_f = ctk.CTkFrame(self, fg_color="transparent")
        self.act_f.grid(row=5, column=0, padx=20, pady=20, sticky="ew")
        self.act_f.grid_columnconfigure((0, 1), weight=1)
        self.cl_b = ctk.CTkButton(self.act_f, text=self.i18n.get("clone"), fg_color=COLOR_ACCENT, command=self._on_clone, font=ctk.CTkFont(family=self.font_family, weight="bold"))
        self.cl_b.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(self.act_f, text=self.i18n.get("cancel"), fg_color="#334155", command=self.destroy, font=ctk.CTkFont(family=self.font_family)).grid(row=0, column=1, padx=5, sticky="ew")
    def _on_select_dest(self):
        from .utils import select_directory
        p = select_directory()
        if p:
            self.d_p_v.set(p)
    def _on_clone(self):
        u, d = self.url_entry.get().strip(), self.d_p_v.get()
        if not u:
            return
        self.cl_b.configure(state="disabled", text=self.i18n.get("cloning"))
        self.app_manager.clone_repository(u, d, log_callback=self._append_log)
    def _append_log(self, t: str):
        self.log_t.configure(state="normal")
        self.log_t.insert("end", t)
        self.log_t.see("end")
        self.log_t.configure(state="disabled")
        if "--- Clone Completed Successfully" in t:
            self.after(1000, self._on_success)
        elif "--- Clone Failed" in t:
            self.after(100, lambda: self.cl_b.configure(state="normal", text=self.i18n.get("clone")))
    def _on_success(self):
        self.refresh_callback()
        self.cl_b.configure(text=self.i18n.get("clone_success"))
        self.after(2000, self.destroy)

class DotenvEditor(ctk.CTkToplevel):
    def __init__(self, master, project_path, i18n, **kwargs):
        super().__init__(master, **kwargs)
        self.project_path = Path(project_path)
        self.dotenv_path = self.project_path / ".env"
        self.i18n = i18n
        self.title(f"{self.i18n.get('dotenv_editor')} - {self.project_path.name}")
        self.geometry("600x500")
        self.configure(fg_color=COLOR_BG)
        self.attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 14), fg_color=COLOR_SURFACE, text_color=COLOR_TEXT)
        self.textbox.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.btn_f = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_f.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.btn_f.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(self.btn_f, text=self.i18n.get("save"), fg_color=COLOR_ACCENT, command=self._on_save).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(self.btn_f, text=self.i18n.get("cancel"), fg_color="#334155", command=self.destroy).grid(row=0, column=1, padx=5, sticky="ew")
        self._load_dotenv()
    def _load_dotenv(self):
        if self.dotenv_path.exists():
            self.textbox.insert("0.0", self.dotenv_path.read_text(encoding="utf-8"))
        else:
            from tkinter import messagebox
            if messagebox.askyesno(self.i18n.get("create_new"), self.i18n.get("confirm_create")):
                try:
                    self.dotenv_path.touch()
                except:
                    pass
            else:
                self.destroy()
    def _on_save(self):
        try:
            self.dotenv_path.write_text(self.textbox.get("0.0", "end-1c"), encoding="utf-8")
            self.destroy()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"{e}")

class MemoEditor(ctk.CTkToplevel):
    def __init__(self, master, project_path, i18n, **kwargs):
        super().__init__(master, **kwargs)
        self.project_path = Path(project_path)
        self.memo_path = self.project_path / "memo.txt"
        self.i18n = i18n
        self.title(f"{self.i18n.get('memo_editor')} - {self.project_path.name}")
        self.geometry("600x500")
        self.configure(fg_color=COLOR_BG)
        self.attributes("-topmost", True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 14), fg_color=COLOR_SURFACE, text_color=COLOR_TEXT)
        self.textbox.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.btn_f = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_f.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.btn_f.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(self.btn_f, text=self.i18n.get("save"), fg_color=COLOR_ACCENT, command=self._on_save).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(self.btn_f, text=self.i18n.get("cancel"), fg_color="#334155", command=self.destroy).grid(row=0, column=1, padx=5, sticky="ew")
        self._load_memo()
    def _load_memo(self):
        if self.memo_path.exists():
            self.textbox.insert("0.0", self.memo_path.read_text(encoding="utf-8"))
        else:
            from tkinter import messagebox
            if messagebox.askyesno(self.i18n.get("create_new"), self.i18n.get("confirm_create_memo")):
                try:
                    self.memo_path.touch()
                except:
                    pass
            else:
                self.destroy()
    def _on_save(self):
        try:
            self.memo_path.write_text(self.textbox.get("0.0", "end-1c"), encoding="utf-8")
            self.destroy()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"{e}")

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = ConfigManager.get_settings()
        self.i18n = I18nManager(lang=self.settings.get("language", "en"))
        self.app_manager = AppManager()
        self._search_timer = None
        self.current_group_id = "all"
        self.available_pythons = self.app_manager.scan_python_executables()
        
        # resource_path をインポート
        from .utils import resource_path
        
        fp = resource_path("assets/fonts/MPLUS1Code-ExtraLight.ttf")
        self.title_font_name = "Segoe UI"
        if fp.exists() and FontLoader.load_font(str(fp)):
            self.title_font_name = "M PLUS 1 Code ExtraLight"
        self.font_family = FontLoader.get_system_default()
        
        self.title(self.i18n.get("title"))
        self.geometry("1500x900")
        self.configure(fg_color=COLOR_BG)
        self._setup_icon()
        self.tray_icon = None
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.grid_columnconfigure(0, weight=0, minsize=75)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=75, corner_radius=0, fg_color="#090B0F")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.nav_buttons: Dict[str, NavButton] = {}
        self._refresh_sidebar()
        
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.menu_bar = None
        self._setup_menu_bar()
        
        self.header_frame = ctk.CTkFrame(self.main_area, corner_radius=0, fg_color=COLOR_SURFACE, height=80)
        self.header_frame.grid(row=0, column=0, sticky="nsew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.title_canvas = tk.Canvas(self.header_frame, width=320, height=60, bg=COLOR_SURFACE, highlightthickness=0)
        self.title_canvas.grid(row=0, column=0, padx=20, pady=10)
        self._draw_glowing_title()
        
        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text=self.i18n.get("search"), width=350, height=35, border_color=COLOR_BORDER, fg_color=COLOR_INNER_BG, font=ctk.CTkFont(family=self.font_family))
        self.search_entry.grid(row=0, column=1, padx=10, pady=20, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        self.btn_f = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.btn_f.grid(row=0, column=2, padx=15)
        self.start_all_btn = ctk.CTkButton(self.btn_f, text=self.i18n.get("start_all"), width=100, height=35, fg_color=COLOR_SUCCESS, hover_color="#091812", command=self._start_all_visible, font=ctk.CTkFont(family=self.font_family, weight="bold"))
        self.start_all_btn.grid(row=0, column=0, padx=3)
        self.stop_all_btn = ctk.CTkButton(self.btn_f, text=self.i18n.get("stop_all"), width=100, height=35, fg_color=COLOR_DANGER, hover_color="#220E0E", command=self._stop_all_visible, font=ctk.CTkFont(family=self.font_family, weight="bold"))
        self.stop_all_btn.grid(row=0, column=1, padx=3)

        self.home_view = ctk.CTkScrollableFrame(self.main_area, label_text=self.i18n.get("project_list"), fg_color=COLOR_BG, label_fg_color=COLOR_BG, label_text_color=COLOR_TEXT_MUTED)
        self.home_view.grid_columnconfigure(0, weight=1)
        self.stats_view = StatsView(self.main_area, self.app_manager)
        self.settings_view = SettingsView(self.main_area, self.i18n, self._save_config, self.settings)
        self.project_frames: Dict[str, ProjectFrame] = {}
        
        self.status_bar = ctk.CTkLabel(self.main_area, text=self.i18n.get("ready"), height=25, fg_color=COLOR_SURFACE, text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=self.font_family, size=11), anchor="w")
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        
        self._load_cached_apps()
        self._start_automation()
        self._switch_view("all")

    def _refresh_sidebar(self):
        # Clear all existing widgets from sidebar
        for child in self.sidebar.winfo_children():
            child.destroy()
        
        self.nav_buttons = {}
        row = 0
        
        # --- Top Section (Fixed) ---
        self.top_sidebar = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.top_sidebar.grid(row=0, column=0, sticky="ew")
        self.top_sidebar.grid_columnconfigure(0, weight=1)
        
        self._create_nav_button("all", "🏠", 0, parent=self.top_sidebar)
        
        divider = ctk.CTkFrame(self.top_sidebar, height=2, fg_color=COLOR_BORDER)
        divider.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # --- Middle Section (Scrollable Groups) ---
        self.sidebar.rowconfigure(1, weight=1)
        self.groups_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent", corner_radius=0, 
            scrollbar_button_color=COLOR_BORDER, scrollbar_button_hover_color=COLOR_ACCENT
        )
        self.groups_scroll.grid(row=1, column=0, sticky="nsew")
        self.groups_scroll.grid_columnconfigure(0, weight=1)
        
        g_row = 0
        for g in self.app_manager.groups:
            self._create_nav_button(g["id"], g.get("icon", "📁"), g_row, parent=self.groups_scroll)
            self.nav_buttons[g["id"]].bind("<Button-3>", lambda e, gid=g["id"]: self._show_group_context_menu(e, gid))
            # Add Tooltip for groups
            Tooltip(self.nav_buttons[g["id"]], self.i18n, text=g["name"])
            g_row += 1
            
        # --- Bottom Section (Fixed System Icons) ---
        self.bottom_sidebar = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.bottom_sidebar.grid(row=2, column=0, sticky="ew", pady=(10, 20))
        self.bottom_sidebar.grid_columnconfigure(0, weight=1)
        
        font_emoji = "Segoe UI Emoji" if sys.platform == "win32" else "system-ui"
        
        # Add Group Button (Moved here)
        self.add_group_btn = ctk.CTkButton(
            self.bottom_sidebar, text="➕", width=45, height=45, 
            fg_color="transparent", hover_color=COLOR_SURFACE, 
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=font_emoji, size=18), 
            command=self._on_add_group_click
        )
        self.add_group_btn.grid(row=0, column=0, padx=7, pady=5)
        Tooltip(self.add_group_btn, self.i18n, "tt_add_group")
        
        self._create_nav_button("stats", "📊", 1, parent=self.bottom_sidebar)
        self._create_nav_button("settings", "⚙", 2, parent=self.bottom_sidebar)

    def _create_nav_button(self, name, icon, row, parent=None):
        target = parent if parent else self.sidebar
        font_fam = "Segoe UI Emoji" if sys.platform == "win32" else "system-ui"
        btn = NavButton(
            target, text=icon, width=45, height=45, 
            fg_color="transparent", hover_color=COLOR_SURFACE, 
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=font_fam, size=20), 
            command=lambda: self._switch_view(name)
        )
        btn.grid(row=row, column=0, padx=7, pady=5)
        self.nav_buttons[name] = btn
        
        indicator = ctk.CTkFrame(target, width=3, height=25, fg_color="transparent")
        indicator.grid(row=row, column=0, sticky="w", padx=0)
        btn.indicator = indicator

    def _switch_view(self, name):
        for b in self.nav_buttons.values():
            if b.indicator:
                b.indicator.configure(fg_color="transparent")
            b.configure(text_color=COLOR_TEXT_MUTED)
        self.home_view.grid_forget()
        self.stats_view.grid_forget()
        self.settings_view.grid_forget()
        if name == "stats":
            self.stats_view.grid(row=1, column=0, padx=25, pady=(5, 25), sticky="nsew")
        elif name == "settings":
            self.settings_view.grid(row=1, column=0, padx=25, pady=(5, 25), sticky="nsew")
        else:
            self.current_group_id = name
            self.home_view.grid(row=1, column=0, padx=25, pady=(5, 25), sticky="nsew")
            self._refresh_app_list(self.search_entry.get())
        if name in self.nav_buttons:
            btn = self.nav_buttons[name]
            btn.configure(text_color=COLOR_TEXT)
            if btn.indicator:
                btn.indicator.configure(fg_color=COLOR_TEXT)

    def _handle_project_drop(self, project_id, x_root, y_root):
        target_group_id = None
        for name, btn in self.nav_buttons.items():
            if name in ["stats", "settings"]:
                continue
            bx, by, bw, bh = btn.winfo_rootx(), btn.winfo_rooty(), btn.winfo_width(), btn.winfo_height()
            if bx <= x_root <= bx + bw and by <= y_root <= by + bh:
                target_group_id = name
                break
        if target_group_id:
            new_gid = None if target_group_id == "all" else target_group_id
            if self.app_manager.move_project_to_group(project_id, new_gid):
                self._flash_sidebar_button(target_group_id)
                self._save_config()
                self._refresh_sidebar()
                self._refresh_app_list(self.search_entry.get())

    def _flash_sidebar_button(self, name):
        if name not in self.nav_buttons:
            return
        btn = self.nav_buttons[name]
        orig = btn.cget("fg_color")
        btn.configure(fg_color=COLOR_SUCCESS)
        self.after(300, lambda: btn.configure(fg_color=orig))

    def _setup_menu_bar(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        f = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=self.i18n.get("menu_file"), menu=f)
        f.add_command(label=self.i18n.get("scan"), command=self._on_scan)
        f.add_separator()
        f.add_command(label=self.i18n.get("menu_exit"), command=self._exit_app)
        t = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=self.i18n.get("menu_tools"), menu=t)
        t.add_command(label=self.i18n.get("clone"), command=self._on_clone_click)
        t.add_separator()
        t.add_command(label=self.i18n.get("backup"), command=self._on_backup)
        t.add_command(label=self.i18n.get("restore"), command=self._on_restore)
        v = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=self.i18n.get("menu_view"), menu=v)
        v.add_command(label=self.i18n.get("menu_lang"), command=self._toggle_language)
        h = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=self.i18n.get("menu_help"), menu=h)
        h.add_command(label=self.i18n.get("help"), command=self._show_help)

    def _draw_glowing_title(self):
        text = "Python App Launcher"
        font = (self.title_font_name, 18)
        self.title_canvas.create_text(162, 32, text=text, fill="#475569", font=font)
        self.title_canvas.create_text(160, 30, text=text, fill=COLOR_TEXT, font=font)
    def _setup_icon(self):
        try:
            i_p, l_p = Path("assets/icon.ico"), Path("assets/logo.png")
            if sys.platform == "win32" and i_p.exists():
                self.iconbitmap(str(i_p))
            elif l_p.exists():
                self.iconphoto(False, tk.PhotoImage(file=str(l_p)))
        except:
            pass
    def _load_cached_apps(self):
        self.app_manager.apps = [a for a in ConfigManager.get_apps() if "files" in a]
        self._refresh_app_list()
        for p in self.app_manager.apps:
            for f in p.get("files", []):
                if f.get("auto_start"):
                    self.after(1000, lambda fid=f["id"]: self._auto_start_app(fid))
    def _auto_start_app(self, fid):
        p, f = self.app_manager._find_file_by_id(fid)
        if p and f and p["id"] in self.project_frames:
            pf = self.project_frames[p["id"]]
            if pf.collapsed:
                pf._toggle_collapse()
            if fid in pf.file_frames:
                ff = pf.file_frames[fid]
                ff.switch_var.set("on")
                ff._on_toggle()
    def _start_automation(self):
        self._check_schedule()
    def _check_schedule(self):
        now = datetime.datetime.now().strftime("%H:%M")
        for p in self.app_manager.apps:
            for f in p.get("files", []):
                if f.get("schedule") == now and self.app_manager.get_status(f["id"]) == "stopped":
                    self._auto_start_app(f["id"])
        self.after(60000, self._check_schedule)
    def _refresh_app_list(self, filter_text=""):
        s_t = filter_text.lower()
        is_tag = s_t.startswith("#")
        tag_q = s_t[1:] if is_tag else ""
        self.app_manager.apps.sort(key=lambda x: not x.get("favorite", False))
        c_ids = [p["id"] for p in self.app_manager.apps]
        for pid in list(self.project_frames.keys()):
            if pid not in c_ids:
                self.project_frames[pid].destroy()
                del self.project_frames[pid]
        target_p = []
        for p in self.app_manager.apps:
            if self.current_group_id != "all" and p.get("group_id") != self.current_group_id:
                if p["id"] in self.project_frames:
                    self.project_frames[p["id"]].grid_remove()
                continue
            match = any(tag_q in t.lower() for t in p.get("tags", [])) if is_tag else (s_t in p["name"].lower() or any(s_t in f.get("filename", "").lower() for f in p.get("files", [])))
            if match:
                target_p.append(p)
            elif p["id"] in self.project_frames:
                self.project_frames[p["id"]].grid_remove()
        self._render_index = 0
        self._target_projects = target_p
        self._render_step()
    def _render_step(self):
        if self._render_index >= len(self._target_projects):
            return
        for _ in range(min(3, len(self._target_projects) - self._render_index)):
            p = self._target_projects[self._render_index]
            if p["id"] not in self.project_frames:
                self.project_frames[p["id"]] = ProjectFrame(self.home_view, p, self.app_manager, self.i18n, self._delete_project, self._save_config, lambda: self._refresh_app_list(self.search_entry.get()), self, self.available_pythons)
            pf = self.project_frames[p["id"]]
            pf.project_data = p
            if pf.grid_info().get("row") != str(self._render_index):
                pf.grid(row=self._render_index, column=0, padx=10, pady=6, sticky="ew")
            if not pf.collapsed:
                pf._refresh_files()
            self._render_index += 1
        self.after(50, self._render_step)
    def _on_scan(self):
        from .utils import select_directory
        p = select_directory()
        if p:
            self.app_manager.scan_directory(p)
            self._save_config()
            self._refresh_app_list(self.search_entry.get())
    def _on_clone_click(self):
        CloneDialog(self, self.app_manager, self.i18n, lambda: self._refresh_app_list(self.search_entry.get()))
    def _on_search(self, e):
        if self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, lambda: self._refresh_app_list(self.search_entry.get()))
    def _show_help(self):
        hw = ctk.CTkToplevel(self)
        hw.title(self.i18n.get("help_title"))
        hw.geometry("700x600")
        hw.configure(fg_color=COLOR_BG)
        hw.attributes("-topmost", True)
        ctk.CTkLabel(hw, text=self.i18n.get("help_title"), text_color=COLOR_ACCENT, font=ctk.CTkFont(family=self.font_family, size=20, weight="bold")).pack(pady=25)
        content = ctk.CTkTextbox(hw, width=620, height=420, font=(self.font_family, 13), fg_color=COLOR_SURFACE, text_color=COLOR_TEXT)
        content.insert("0.0", self.i18n.get("help_content"))
        content.configure(state="disabled")
        content.pack(padx=30, pady=10)
        ctk.CTkButton(hw, text="Got it!", fg_color=COLOR_ACCENT, command=hw.destroy, font=ctk.CTkFont(family=self.font_family, weight="bold")).pack(pady=20)
    def _delete_project(self, pid):
        self.app_manager.apps = [p for p in self.app_manager.apps if p["id"] != pid]
        self._save_config()
        self._refresh_app_list(self.search_entry.get())
    def _save_config(self):
        data = ConfigManager.load()
        data["apps"] = self.app_manager.apps
        data["groups"] = self.app_manager.groups
        data["settings"] = self.settings
        data["settings"]["language"] = self.i18n.lang
        ConfigManager.save(data)
    def _toggle_language(self):
        self.i18n.lang = "en" if self.i18n.lang == "jpn" else "jpn"
        if self.menu_bar:
            self.menu_bar.delete(0, "end")
        self._setup_menu_bar()
        self.title(self.i18n.get("title"))
        self.title_canvas.delete("all")
        self._draw_glowing_title()
        self.search_entry.configure(placeholder_text=self.i18n.get("search"))
        self.start_all_btn.configure(text=self.i18n.get("start_all"))
        self.stop_all_btn.configure(text=self.i18n.get("stop_all"))
        
        # 各ビューを即座にリフレッシュ
        for pf in self.project_frames.values():
            pf.update_texts()
        self.settings_view.update_texts()
        self.stats_view.update_texts(self.i18n)
        self.home_view.configure(label_text=self.i18n.get("project_list"))
        self.status_bar.configure(text=self.i18n.get("ready"))
        
        self._save_config()
    def _on_backup(self):
        from tkinter import filedialog, messagebox
        f = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")], initialfile="launcher_backup.zip", title=self.i18n.get("backup"))
        if f:
            try:
                ConfigManager.create_backup(f)
                messagebox.showinfo("Success", self.i18n.get("backup_success"))
            except Exception as e:
                messagebox.showerror("Error", f"{e}")
    def _on_restore(self):
        from tkinter import filedialog, messagebox
        f = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")], title=self.i18n.get("restore"))
        if f:
            if messagebox.askyesno(self.i18n.get("restore"), self.i18n.get("restore_success")):
                try:
                    ConfigManager.restore_backup(f)
                    self.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"{e}")
    def _start_all_visible(self):
        for p in self._target_projects:
            for f in p.get("files", []):
                if f.get("bulk_target") and self.app_manager.get_status(f["id"]) == "stopped":
                    self._auto_start_app(f["id"])
    def _stop_all_visible(self):
        for p in self._target_projects:
            for f in p.get("files", []):
                if f.get("bulk_target") and self.app_manager.get_status(f["id"]) == "running":
                    self.app_manager.stop_app(f["id"])
                    if p["id"] in self.project_frames:
                        pf = self.project_frames[p["id"]]
                        if f["id"] in pf.file_frames:
                            ff = pf.file_frames[f["id"]]
                            ff.switch_var.set("off")
                            ff._update_status_ui()
    def _on_closing(self):
        # 新しい設定項目 exit_on_close を参照 (デフォルト False ＝ 終了せずにトレイへ)
        is_exit = self.settings.get("exit_on_close", False)
        if is_exit:
            self._exit_app()
        else:
            self.withdraw()
            self._setup_tray_icon()

    def _setup_tray_icon(self):
        if self.tray_icon:
            return
        i_p, l_p = Path("assets/icon.ico"), Path("assets/logo.png")
        img = None
        try:
            if i_p.exists():
                img = Image.open(i_p)
            elif l_p.exists():
                img = Image.open(l_p)
            else:
                img = Image.new('RGB', (64, 64), color=(30, 30, 30))
        except:
            img = Image.new('RGB', (64, 64), color=(30, 30, 30))
        
        m = (item('Show', self._show_window), item('Exit', self._exit_app))
        self.tray_icon = pystray.Icon("PythonAppLauncher", img, self.i18n.get("title"), m)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _show_window(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.deiconify)

    def _exit_app(self):
        # トレイアイコンが存在すれば確実に停止
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
            self.tray_icon = None
        self.after(0, self.destroy)
        # プロセスを物理的に終了させる
        sys.exit(0)

    def _on_add_group_click(self):
        GroupEditDialog(self, self.app_manager, self.i18n)
    def _on_edit_group(self, gid):
        GroupEditDialog(self, self.app_manager, self.i18n, group_id=gid)
    def _on_delete_group(self, gid):
        from tkinter import messagebox
        if messagebox.askyesno(self.i18n.get("delete_group"), self.i18n.get("confirm_delete_group")):
            self.app_manager.remove_group(gid)
            self._save_config()
            if self.current_group_id == gid:
                self._switch_view("all")
            self._refresh_sidebar()
            self._refresh_app_list(self.search_entry.get())
    def _show_group_context_menu(self, e, gid):
        m = tk.Menu(self, tearoff=0, bg=COLOR_SURFACE, fg=COLOR_TEXT, activebackground=COLOR_ACCENT)
        m.add_command(label=self.i18n.get("edit_group"), command=lambda: self._on_edit_group(gid))
        m.add_command(label=self.i18n.get("delete_group"), command=lambda: self._on_delete_group(gid))
        m.post(e.x_root, e.y_root)
