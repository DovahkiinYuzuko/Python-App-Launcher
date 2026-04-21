import subprocess
import threading
import uuid
import sys
import os
try:
    import psutil
except ImportError:
    psutil = None
try:
    import cpuinfo
except ImportError:
    cpuinfo = None
try:
    import GPUtil
except ImportError:
    GPUtil = None
try:
    from plyer import notification
except ImportError:
    notification = None
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from app.config import ConfigManager

class AppManager:
    """アプリの検知、起動、停止、状態管理を担当するクラス。"""

    def __init__(self):
        self.apps: List[Dict] = []
        self.groups: List[Dict] = ConfigManager.get_groups()
        self.processes: Dict[str, subprocess.Popen] = {}  # file_id: process
        self.log_callbacks: Dict[str, Callable[[str], None]] = {} # file_id: callback
        self.manual_stops: set = set()  # 手動停止した file_id を記録
        self._cpu_name = None

    def add_group(self, name: str, icon: str, project_ids: List[str] = None) -> Dict:
        """新しいグループを追加し、指定されたプロジェクトを所属させる。"""
        group = {
            "id": str(uuid.uuid4()),
            "name": name,
            "icon": icon,
            "project_ids": project_ids or []
        }
        self.groups.append(group)
        
        # プロジェクト側の group_id も更新
        if project_ids:
            for pid in project_ids:
                for app in self.apps:
                    if app["id"] == pid:
                        app["group_id"] = group["id"]
                        break
        return group

    def update_group(self, group_id: str, name: str, icon: str, project_ids: List[str]):
        """グループ情報を更新し、メンバーを入れ替える。"""
        group = next((g for g in self.groups if g["id"] == group_id), None)
        if not group:
            return
        
        group["name"] = name
        group["icon"] = icon
        
        # 旧メンバーの解除 (このグループに所属していたものだけ)
        for app in self.apps:
            if app.get("group_id") == group_id:
                app["group_id"] = None
        
        # 新メンバーの登録
        group["project_ids"] = project_ids
        for pid in project_ids:
            for app in self.apps:
                if app["id"] == pid:
                    app["group_id"] = group_id
                    break

    def remove_group(self, group_id: str):
        """グループを削除し、所属していたプロジェクトを解除する。"""
        # 削除対象のグループを取得
        group_to_remove = next((g for g in self.groups if g["id"] == group_id), None)
        if not group_to_remove:
            return

        # 所属プロジェクトの group_id を None に戻す
        for project_id in group_to_remove.get("project_ids", []):
            for app in self.apps:
                if app["id"] == project_id:
                    app["group_id"] = None
                    break
        
        # 安全のため、全アプリをチェックして一致する group_id をリセット
        for app in self.apps:
            if app.get("group_id") == group_id:
                app["group_id"] = None

        # リストから削除
        self.groups = [g for g in self.groups if g["id"] != group_id]

    def move_project_to_group(self, project_id: str, group_id: Optional[str]):
        """プロジェクトを別のグループに移動する。"""
        # 既存のグループから削除
        for group in self.groups:
            if project_id in group["project_ids"]:
                group["project_ids"].remove(project_id)
        
        # プロジェクトの group_id を更新
        for app in self.apps:
            if app["id"] == project_id:
                app["group_id"] = group_id
                break
        
        # 新しいグループに追加
        if group_id:
            for group in self.groups:
                if group["id"] == group_id:
                    if project_id not in group["project_ids"]:
                        group["project_ids"].append(project_id)
                    break

    def _get_cpu_name(self) -> str:
        """CPUのブランド名を取得する（キャッシュ付き）。"""
        if self._cpu_name:
            return self._cpu_name
        
        if cpuinfo:
            try:
                info = cpuinfo.get_cpu_info()
                self._cpu_name = info.get('brand_raw', "Unknown CPU")
            except Exception:
                self._cpu_name = "Unknown CPU"
        else:
            self._cpu_name = "CPU Info Not Available"
        return self._cpu_name

    def _get_gpu_stats(self) -> List[Dict]:
        """GPUの統計情報を取得する。NVIDIAとその他のGPU（オンボード含む）を両方取得。"""
        gpu_list = []
        gpu_names = set()
        
        # 1. NVIDIA GPU (GPUtil)
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                for gpu in gpus:
                    name = gpu.name
                    gpu_list.append({
                        "name": name,
                        "load": round(gpu.load * 100, 1),
                        "memory_used": round(gpu.memoryUsed, 1),
                        "memory_total": round(gpu.memoryTotal, 1)
                    })
                    gpu_names.add(name.lower())
            except Exception:
                pass
        
        # 2. フォールバック/追加検出 (Windows wmic)
        if sys.platform == "win32":
            try:
                # wmic でビデオカード名とRAM容量を取得
                output = subprocess.check_output(
                    "wmic path win32_VideoController get name,AdapterRAM", 
                    shell=True, text=True
                ).strip().split('\n')
                
                if len(output) > 1:
                    name_idx = -1
                    ram_idx = -1
                    if "Name" in output[0]: name_idx = output[0].find("Name")
                    if "AdapterRAM" in output[0]: ram_idx = output[0].find("AdapterRAM")

                    for line in output[1:]:
                        if not line.strip(): continue
                        try:
                            # 位置ベースで取得を試みる
                            if ram_idx != -1 and name_idx != -1:
                                if ram_idx > name_idx:
                                    name = line[name_idx:ram_idx].strip()
                                    ram_str = line[ram_idx:].strip().split()[0]
                                else:
                                    name = line[name_idx:].strip()
                                    ram_str = line[ram_idx:name_idx].strip().split()[0]
                                ram_mb = round(int(ram_str) / (1024**2), 1)
                            else:
                                parts = line.split()
                                name = " ".join(parts[:-1])
                                ram_mb = 0.0
                        except:
                            continue
                        
                        if name and name.lower() not in gpu_names:
                            gpu_list.append({
                                "name": name,
                                "load": 0.0,
                                "memory_used": 0.0,
                                "memory_total": ram_mb
                            })
                            gpu_names.add(name.lower())
            except Exception:
                pass
        
        return gpu_list

    def scan_directory(self, root_dir: str) -> List[Dict]:
        """指定されたディレクトリをスキャンしてプロジェクトを登録する。"""
        root = Path(root_dir)
        new_projects_map = {}
        
        ignore_dirs = {".venv", "venv", "__pycache__", ".git", ".history", "dist", "build"}
        ignore_files = {"setup.py", "build_exe.py", "installer_win.py"}

        def process_dir(dirpath: Path, filenames: List[str]):
            if any(part in ignore_dirs for part in dirpath.parts):
                return

            py_files = [f for f in filenames if f.endswith(".py") and f not in ignore_files]
            if not py_files:
                return

            dir_str = str(dirpath)
            if dir_str not in new_projects_map:
                existing_proj = next((p for p in self.apps if p["path"] == dir_str), None)
                if existing_proj:
                    project = existing_proj
                else:
                    display_name = dirpath.name
                    venv_path = dirpath / ".venv"
                    if not venv_path.exists():
                        venv_path = dirpath / "venv"
                        if not venv_path.exists():
                            venv_path = root / ".venv"

                    project = {
                        "id": str(uuid.uuid4()),
                        "name": display_name,
                        "path": dir_str,
                        "venv": str(venv_path) if venv_path.exists() else None,
                        "group_id": None,
                        "collapsed": True,
                        "favorite": False,
                        "files": []
                    }
                new_projects_map[dir_str] = project

            project = new_projects_map[dir_str]
            for filename in py_files:
                if any(f["filename"] == filename for f in project["files"]):
                    continue
                
                project["files"].append({
                    "id": str(uuid.uuid4()),
                    "filename": filename,
                    "arguments": "",
                    "status": "stopped",
                    "in_console": False,
                    "use_venv": False,
                    "auto_start": False,
                    "schedule": "",
                    "bulk_target": False,
                    "auto_restart": False,
                    "custom_python": None
                })

        try:
            for dirpath, dirnames, filenames in root.walk():
                dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
                process_dir(dirpath, filenames)
        except AttributeError:
            for root_str, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                process_dir(Path(root_str), files)
        
        for dir_str, project in new_projects_map.items():
            if project not in self.apps:
                self.apps.append(project)
        
        return self.apps

    def get_system_stats(self) -> dict:
        """システム全体の統計情報を取得する。"""
        if psutil is None:
            return {
                "cpu": {"percent": 0.0, "name": "Unknown"},
                "ram": {"percent": 0.0, "total": 0.0, "used": 0.0},
                "gpus": []
            }
        
        vm = psutil.virtual_memory()
        return {
            "cpu": {"percent": psutil.cpu_percent(), "name": self._get_cpu_name()},
            "ram": {
                "percent": vm.percent,
                "total": round(vm.total / (1024**3), 2),
                "used": round(vm.used / (1024**3), 2)
            },
            "gpus": self._get_gpu_stats()
        }

    def scan_python_executables(self) -> List[str]:
        """システム内の python.exe を自動スキャンして返す。"""
        paths = [sys.executable]
        search_dirs = []
        
        if sys.platform == "win32":
            search_dirs = [
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                os.path.expanduser("~\\AppData\\Local\\Programs\\Python")
            ]
        elif sys.platform == "darwin":
            search_dirs = ["/usr/local/bin", "/usr/bin", "/Library/Frameworks/Python.framework/Versions"]
        
        for d in search_dirs:
            p = Path(d)
            if not p.exists(): continue
            try:
                pattern = "python.exe" if sys.platform == "win32" else "python[0-9]*"
                for exe in p.rglob(pattern):
                    if exe.is_file() and str(exe) not in paths:
                        paths.append(str(exe))
            except Exception: continue
        
        unique_paths = sorted(list(set(paths)))
        results = []
        for path in unique_paths:
            try:
                proc = subprocess.run([path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1.0)
                version_output = proc.stdout.strip()
                if version_output.startswith("Python"):
                    results.append(f"{version_output} ({path})")
                else:
                    results.append(f"Python Unknown ({path})")
            except Exception:
                results.append(f"Python Error ({path})")
        return results

    def _notify(self, title: str, message: str):
        """OS標準の通知を送る。"""
        if notification:
            try:
                notification.notify(title=title, message=message, app_name="Python App Launcher", timeout=5)
            except Exception: pass

    def _find_file_by_id(self, file_id: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        for project in self.apps:
            for file in project.get("files", []):
                if file["id"] == file_id:
                    return project, file
        return None, None

    def get_python_executable(self, project: Dict, use_venv: bool = False) -> str:
        if use_venv and project.get("venv"):
            venv_path = Path(project["venv"])
            if sys.platform == "win32":
                python_exe = venv_path / "Scripts" / "python.exe"
            else:
                python_exe = venv_path / "bin" / "python"
            if python_exe.exists():
                return str(python_exe)
        return sys.executable

    def start_app(self, file_id: str, log_callback: Optional[Callable[[str], None]] = None, 
                  in_console: bool = False, use_venv: bool = False, custom_python: Optional[str] = None) -> bool:
        """アプリ（ファイル）を起動する。"""
        project, file = self._find_file_by_id(file_id)
        if not file or file_id in self.processes:
            return False

        python_exe = custom_python or self.get_python_executable(project, use_venv=use_venv)
        
        if python_exe and " (" in python_exe and python_exe.endswith(")"):
            parts = python_exe.split(" (", 1)
            if len(parts) > 1 and parts[0].startswith("Python"):
                python_exe = parts[1].rsplit(")", 1)[0]

        entry_script = Path(project["path"]) / file["filename"]
        args = [python_exe, str(entry_script)]
        if file.get("arguments"):
            args.extend(file["arguments"].split())

        try:
            creation_flags = 0
            if in_console:
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NEW_CONSOLE
                    args = ["cmd.exe", "/k"] + args
                elif sys.platform == "darwin":
                    cmd_str = " ".join([f'"{arg}"' for arg in args])
                    args = ["osascript", "-e", f'tell application "Terminal" to do script "{cmd_str}"']
                else:
                    args = ["x-terminal-emulator", "-e"] + args
            else:
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                args, stdout=None if in_console else subprocess.PIPE,
                stderr=None if in_console else subprocess.STDOUT,
                stdin=None if in_console else subprocess.PIPE,
                text=True, bufsize=1, cwd=project["path"], creationflags=creation_flags
            )
            self.processes[file_id] = process
            file["status"] = "running"
            self._notify("App Started", f"{file['filename']} is now running.")
            
            if not in_console and log_callback:
                self.log_callbacks[file_id] = log_callback
                thread = threading.Thread(target=self._read_logs, args=(file_id, process), daemon=True)
                thread.start()
            return True
        except Exception as e:
            if log_callback: log_callback(f"Error: {e}\n")
            return False

    def stop_app(self, file_id: str, manual: bool = True) -> bool:
        if manual: self.manual_stops.add(file_id)
        process = self.processes.get(file_id)
        if process:
            if psutil:
                try:
                    parent = psutil.Process(process.pid)
                    for child in parent.children(recursive=True): child.terminate()
                    parent.terminate()
                    psutil.wait_procs(parent.children() + [parent], timeout=3)
                except: process.terminate()
            else: process.terminate()
            if file_id in self.processes: del self.processes[file_id]
            _, file = self._find_file_by_id(file_id)
            if file: file["status"] = "stopped"
            return True
        return False

    def get_status(self, file_id: str) -> str:
        _, file = self._find_file_by_id(file_id)
        return file["status"] if file else "stopped"

    def get_process_resources(self, file_id: str) -> dict:
        if psutil is None: return {"cpu": 0.0, "memory": 0.0}
        process = self.processes.get(file_id)
        if not process: return {"cpu": 0.0, "memory": 0.0}
        try:
            p = psutil.Process(process.pid)
            total_cpu = p.cpu_percent(interval=None)
            total_memory = p.memory_info().rss
            for child in p.children(recursive=True):
                try:
                    total_cpu += child.cpu_percent(interval=None)
                    total_memory += child.memory_info().rss
                except: continue
            return {"cpu": round(total_cpu, 1), "memory": round(total_memory / (1024**2), 1)}
        except: return {"cpu": 0.0, "memory": 0.0}

    def _read_logs(self, file_id: str, process: subprocess.Popen):
        callback = self.log_callbacks.get(file_id)
        if not callback: return
        for line in iter(process.stdout.readline, ""): callback(line)
        process.stdout.close()
        exit_code = process.wait()
        is_manual = file_id in self.manual_stops
        if file_id in self.processes: del self.processes[file_id]
        _, file = self._find_file_by_id(file_id)
        if file: file["status"] = "stopped"
        if is_manual:
            self.manual_stops.remove(file_id)
        else:
            if exit_code != 0:
                app_name = file["filename"] if file else "Unknown"
                if file and file.get("auto_restart"):
                    self._notify("App Crashed - Restarting", f"{app_name} failed. Restarting now...")
                    def _re(): self.start_app(file_id, log_callback=callback, in_console=file.get("in_console"), use_venv=file.get("use_venv"), custom_python=file.get("custom_python"))
                    threading.Timer(2.0, _re).start()
                else:
                    self._notify("App Crashed", f"{app_name} failed (Code: {exit_code}).")
        callback("\n--- App Process Terminated ---\n")

    def setup_venv(self, project_id: str, log_callback: Optional[Callable[[str], None]] = None):
        project = next((p for p in self.apps if p["id"] == project_id), None)
        if not project: return
        def _run_setup():
            if log_callback: log_callback("--- Starting Venv Setup ---\n")
            app_path = Path(project["path"])
            venv_path = app_path / ".venv"
            try:
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
                project["venv"] = str(venv_path)
                req_file = app_path / "requirements.txt"
                if req_file.exists():
                    python_exe = self.get_python_executable(project, use_venv=True)
                    subprocess.run([python_exe, "-m", "pip", "install", "-r", str(req_file)], check=True)
                if log_callback: log_callback("--- Venv Setup Completed ---\n")
            except Exception as e:
                if log_callback: log_callback(f"Error: {e}\n")
        threading.Thread(target=_run_setup, daemon=True).start()

    def update_dependencies(self, project_id: str, log_callback: Optional[Callable[[str], None]] = None):
        project = next((p for p in self.apps if p["id"] == project_id), None)
        if not project or not project.get("venv"): return
        def _run_update():
            if log_callback: log_callback("--- Starting Dependency Update ---\n")
            python_exe = self.get_python_executable(project, use_venv=True)
            req_file = Path(project["path"]) / "requirements.txt"
            try:
                subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True, capture_output=True)
                process = subprocess.Popen([python_exe, "-m", "pip", "install", "--upgrade", "-r", str(req_file)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=project["path"])
                if log_callback:
                    for line in iter(process.stdout.readline, ""): log_callback(line)
                process.stdout.close()
                if process.wait() == 0:
                    if log_callback: log_callback("--- Update Completed ---\n")
            except Exception as e:
                if log_callback: log_callback(f"Error: {e}\n")
        threading.Thread(target=_run_update, daemon=True).start()

    def open_in_file_manager(self, project_id: str):
        project = next((p for p in self.apps if p["id"] == project_id), None)
        if not project: return
        path = project["path"]
        if sys.platform == "win32": subprocess.Popen(["explorer.exe", path])
        elif sys.platform == "darwin": subprocess.Popen(["open", path])
        else: subprocess.Popen(["xdg-open", path])

    def open_in_terminal(self, project_id: str):
        project = next((p for p in self.apps if p["id"] == project_id), None)
        if not project: return
        path = project["path"]
        if sys.platform == "win32": subprocess.Popen(f'start cmd /k "cd /d \"{path}\""', shell=True)
        elif sys.platform == "darwin": subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "cd \"{path}\""'])
        else: subprocess.Popen(["x-terminal-emulator"], cwd=path)

    def clone_repository(self, url: str, dest_path: str, log_callback: Optional[Callable[[str], None]] = None):
        def _run_clone():
            if log_callback: log_callback(f"--- Starting Clone: {url} ---\n")
            try:
                repo_name = url.split("/")[-1].replace(".git", "")
                full_dest = Path(dest_path) / repo_name
                process = subprocess.Popen(["git", "clone", url], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=dest_path)
                if log_callback:
                    for line in iter(process.stdout.readline, ""): log_callback(line)
                process.stdout.close()
                if process.wait() == 0:
                    if log_callback: log_callback(f"--- Clone Completed: {repo_name} ---\n")
                    self.scan_directory(str(full_dest))
            except Exception as e:
                if log_callback: log_callback(f"Error: {e}\n")
        threading.Thread(target=_run_clone, daemon=True).start()
