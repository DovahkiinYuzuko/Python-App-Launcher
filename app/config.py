import json
import zipfile
import shutil
from pathlib import Path
from typing import Any, Dict

class ConfigManager:
    """設定とアプリリストの永続化を管理するクラス。"""
    
    CACHE_FILE = Path("app_cache.json")
    DEFAULT_CONFIG = {
        "settings": {
            "language": "en",
            "theme": "dark",
            "font_family": "Segoe UI",
            "max_running_apps": 5,
            "exit_on_close": False
        },
        "apps": [],
        "groups": []
    }

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """キャッシュファイルからデータを読み込む。存在しない場合はデフォルト値を返す。"""
        if cls.CACHE_FILE.exists():
            try:
                with open(cls.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return cls.DEFAULT_CONFIG.copy()
        return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def save(cls, data: Dict[str, Any]) -> None:
        """データをキャッシュファイルに保存する。"""
        with open(cls.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """設定部分のみを取得する。"""
        data = cls.load()
        return data.get("settings", cls.DEFAULT_CONFIG["settings"])

    @classmethod
    def get_apps(cls) -> list:
        """アプリリストのみを取得する。"""
        data = cls.load()
        return data.get("apps", [])

    @classmethod
    def get_groups(cls) -> list:
        """グループリストを取得する。"""
        data = cls.load()
        return data.get("groups", [])

    @classmethod
    def create_backup(cls, save_path: str) -> None:
        """app_cache.json とプロジェクトごとの .env, memo.txt を ZIP にまとめる。"""
        data = cls.load()
        apps = data.get("apps", [])
        
        with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # メインのキャッシュファイルを保存
            if cls.CACHE_FILE.exists():
                zipf.write(cls.CACHE_FILE, cls.CACHE_FILE.name)
            
            # 各プロジェクトのファイルを保存
            for app in apps:
                app_path = Path(app.get("path", ""))
                app_id = app.get("id", "unknown")
                if not app_path.exists():
                    continue
                
                # .env
                env_file = app_path / ".env"
                if env_file.exists():
                    # ZIP内では projects/ID/.env として保存
                    zipf.write(env_file, f"projects/{app_id}/.env")
                
                # memo.txt
                memo_file = app_path / "memo.txt"
                if memo_file.exists():
                    zipf.write(memo_file, f"projects/{app_id}/memo.txt")

    @classmethod
    def restore_backup(cls, zip_path: str) -> None:
        """ZIPから設定とファイルを復元する。"""
        temp_dir = Path("temp_restore")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        try:
            with zipfile.ZipFile(zip_path, "r") as zipf:
                zipf.extractall(temp_dir)
            
            # 1. app_cache.json を復元
            cached_json = temp_dir / cls.CACHE_FILE.name
            if cached_json.exists():
                shutil.copy2(cached_json, cls.CACHE_FILE)
            
            # 2. プロジェクトごとのファイルを復元
            # 最新のパス情報を取得するために読み直す
            data = cls.load()
            apps = data.get("apps", [])
            
            for app in apps:
                app_id = app.get("id")
                app_path = Path(app.get("path", ""))
                if not app_id or not app_path.exists():
                    continue
                
                proj_restore_dir = temp_dir / "projects" / app_id
                if proj_restore_dir.exists():
                    # .env
                    env_src = proj_restore_dir / ".env"
                    if env_src.exists():
                        shutil.copy2(env_src, app_path / ".env")
                    
                    # memo.txt
                    memo_src = proj_restore_dir / "memo.txt"
                    if memo_src.exists():
                        shutil.copy2(memo_src, app_path / "memo.txt")
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
