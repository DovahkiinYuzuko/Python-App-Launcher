import locale
from typing import Final

class I18nManager:
    """
    多言語対応を管理するクラス。
    日本語('jpn')と英語('en')をサポートします。
    """
    TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
        "jpn": {
            "title": "Python App Launcher",
            "search": "アプリを検索... (#タグ名 でタグ検索)",
            "scan": "スキャン",
            "settings": "設定",
            "start": "起動",
            "stop": "停止",
            "delete": "削除",
            "running": "起動中",
            "stopped": "停止中",
            "setup_venv": "Venv作成",
            "arguments": "引数",
            "console": "コンソール",
            "auto_start": "自動起動",
            "schedule": "スケジュール",
            "bulk": "一括対象",
            "help": "ヘルプ",
            "help_title": "Python App Launcher ユーザーガイド",
            "help_content": """【基本操作】
・「スキャン」ボタンで指定フォルダ内の .py ファイルを自動検知します。
・アコーディオン形式でプロジェクトごとにファイルをまとめて表示します。
・スイッチを「ON」にするとアプリが起動し、リアルタイムでログが表示されます。

【便利機能】
・タグ検索: 各プロジェクトにタグを付けて保存できます。検索バーに「#bot」のように入力すると、そのタグが含まれるプロジェクトのみが表示されます。
・一括対象 (Bulk): チェックを入れたアプリは、ヘッダーの「一括起動/停止」の対象になります。
・自動起動 (Auto): ランチャーを起動した際に、自動的にそのアプリも起動します。
・スケジュール (Schedule): 「HH:MM」形式で時間を入力すると、毎日その時間に自動で起動します。Cron形式 (* * * * *) にも対応しています。
・Venv: プロジェクト内の仮想環境（.venv）を使用して実行します。
・コンソール: ログをランチャー内ではなく、別ウィンドウのターミナルで表示します。
・.envエディタ: プロジェクト内の .env ファイルを直接編集できます。
・メモ (📝): プロジェクトごとの備忘録を残せます。

【管理機能】
・📂: プロジェクトフォルダをエクスプローラーで開きます。
・💻: プロジェクトパスでターミナルを開きます。
・Update Libs: 仮想環境のライブラリを一括でアップデートします。
・Backup / Restore: 設定や.env、メモを丸ごとバックアップ・復元します。
・お気に入り (★): よく使うプロジェクトをリストの一番上に固定します。""",
            "dotenv_editor": ".env エディタ",
            "start_all": "一括起動",
            "stop_all": "一括停止",
            "save": "保存",
            "cancel": "キャンセル",
            "update_libs": "ライブラリ更新",
            "create_new": "新規作成",
            "confirm_create": ".envファイルが見つかりません。新規作成しますか？",
            "memo_editor": "プロジェクト・メモ",
            "confirm_create_memo": "memo.txtが見つかりません。新規作成しますか？",
            "label_args": "Args:",
            "label_schedule": "Sched:",
            "label_python": "Python:",
            "label_restart": "自動再起動:",
            "label_exit_on_close": "閉じる時にアプリを終了する",
            "desc_exit_on_close": "ONにすると、右上の×ボタンでアプリをトレイに隠さずに完全に終了します。",
            "app_settings": "アプリ設定",
            "system_stats": "システム監視",
            "clone": "クローン",
            "clone_dialog_title": "GitHubリポジトリをクローン",
            "repo_url": "リポジトリURL",
            "dest_path": "保存先フォルダ",
            "cloning": "クローン中...",
            "clone_success": "クローンが完了しました",
            "clone_failed": "クローンに失敗しました",
            "select_folder": "フォルダを選択",
            "backup": "バックアップ",
            "restore": "復元",
            "backup_success": "バックアップが完了しました",
            "restore_success": "復元が完了しました。アプリを再起動してください。",
            "backup_failed": "バックアップに失敗しました",
            "restore_failed": "復元に失敗しました",
            # メニューバー
            "menu_file": "ファイル",
            "menu_tools": "ツール",
            "menu_view": "表示",
            "menu_help": "ヘルプ",
            "menu_exit": "終了",
            "menu_lang": "言語切替 (English)",
            # ツールチップ
            "tt_args": "実行時の引数を入力してください",
            "tt_console": "別窓のターミナルで実行して操作可能にします",
            "tt_venv": "仮想環境を使って依存関係を分離します",
            "tt_auto": "ランチャーを開いた時に自動で起動します",
            "tt_schedule": "毎日決まった時間に自動で起動します",
            "tt_bulk": "「一括起動/停止」の対象に含めます",
            "tt_python": "実行に使用する Python のバージョンを選択します",
            "tt_restart": "エラー終了時に自動的に再起動を試みます",
            "tt_log": "ログ画面を表示・非表示にします",
            "tt_fav": "リストの最上部にピン留めします",
            "tt_tags": "検索用のタグ（カンマ区切り）",
            "tt_setup_venv": "仮想環境を新しく作成します",
            "tt_update_libs": "pip install --upgrade を実行します",
            "tt_folder": "エクスプローラーでフォルダを開く",
            "tt_terminal": "この場所でターミナルを起動する",
            "tt_dotenv": ".env ファイルの編集",
            "tt_memo": "備忘録メモの編集",
            "tt_delete": "このプロジェクトをリストから消す",
            "tt_scan": "新しいアプリを探しに行く",
            "tt_help": "詳しい使い方を見る",
            "tt_lang": "UIの言語を切り替える",
            "tt_clone": "GitHubからプロジェクトをクローンします",
            "tt_backup": "全ての設定、.env、メモをバックアップします",
            "tt_restore": "バックアップファイルから復元します",
            "tt_log_filter": "ログを絞り込み... (大文字小文字無視)",
            # グループ管理
            "group_manager": "グループ管理",
            "add_group": "グループ追加",
            "edit_group": "グループ編集",
            "delete_group": "グループ削除",
            "group_name": "グループ名",
            "icon": "アイコン (1文字)",
            "members": "メンバー",
            "tt_add_group": "新しいグループを作成します",
            "project_list": "プロジェクト一覧",
            "ready": "準備完了",
            "venv_ok": "Venv 準備完了",
            "limit_reached": "上限に達しました",
            "max_apps_warning": "同時に起動できるアプリは最大 {max_apps} 個までです。",
            "auto": "自動",
            "bulk_label": "一括",
            "console_label": "窓",
            "venv_label": "Venv"
        },
        "en": {
            "title": "Python App Launcher",
            "search": "Search apps... (or #tagname)",
            "scan": "Scan",
            "settings": "Settings",
            "start": "Start",
            "stop": "Stop",
            "delete": "Delete",
            "running": "Running",
            "stopped": "Stopped",
            "setup_venv": "Setup Venv",
            "update_libs": "Update Libs",
            "arguments": "Args",
            "console": "Console",
            "auto_start": "Auto-start",
            "schedule": "Schedule",
            "bulk": "Bulk",
            "help": "Help",
            "help_title": "Python App Launcher User Guide",
            "help_content": """[Basic Operations]
- Click "Scan" to find .py files in a specific folder.
- Apps are grouped by project in a neat accordion list.
- Toggle "ON" to start an app and monitor logs in real-time.

[Key Features]
- Tag Search: Filter projects by tags using "#tagname" in search.
- Bulk: Apps with "Bulk" checked are targeted by the "Start/Stop All" buttons.
- Auto-start: Automatically start the app when the launcher opens.
- Schedule: Enter "HH:MM" or Cron format (* * * * *) to start at a specific time.
- Venv: Run scripts using the project's virtual environment.
- Console: Launch the app in a separate terminal window.
- .env Editor: Edit project environment variables directly.
- Memo (📝): Keep notes for each project.

[Management]
- 📂: Open project folder in File Explorer.
- 💻: Open terminal at the project path.
- Update Libs: Upgrade project dependencies easily.
- Backup / Restore: Securely backup and restore all your configs.
- Favorites (★): Pin your most-used projects to the top.""",
            "dotenv_editor": ".env Editor",
            "memo_editor": "Project Memo",
            "start_all": "Start All",
            "stop_all": "Stop All",
            "save": "Save",
            "cancel": "Cancel",
            "update_libs": "Update Libs",
            "create_new": "Create New",
            "confirm_create": ".env file not found. Create new one?",
            "confirm_create_memo": "memo.txt not found. Create new one?",
            "label_args": "Args:",
            "label_schedule": "Sched:",
            "label_python": "Python:",
            "label_restart": "Auto-Restart:",
            "label_exit_on_close": "Exit on close",
            "desc_exit_on_close": "If ON, clicking the X button will completely exit the app instead of hiding it in the tray.",
            "app_settings": "App Settings",
            "system_stats": "System Hardware Status",
            "label_close_to_tray": "Close to system tray",
            "clone": "Clone",
            "clone_dialog_title": "Clone GitHub Repository",
            "repo_url": "Repository URL",
            "dest_path": "Destination Folder",
            "cloning": "Cloning...",
            "clone_success": "Cloning completed successfully",
            "clone_failed": "Cloning failed",
            "select_folder": "Select Folder",
            "backup": "Backup",
            "restore": "Restore",
            "backup_success": "Backup completed successfully",
            "restore_success": "Restoration completed. Please restart the app.",
            "backup_failed": "Backup failed",
            "restore_failed": "Restoration failed",
            # Menu Bar
            "menu_file": "File",
            "menu_tools": "Tools",
            "menu_view": "View",
            "menu_help": "Help",
            "menu_exit": "Exit",
            "menu_lang": "Switch Language (日本語)",
            # Tooltips
            "tt_args": "Enter runtime arguments",
            "tt_console": "Run in an interactive terminal window",
            "tt_venv": "Use isolated virtual environment",
            "tt_auto": "Run automatically on launcher startup",
            "tt_schedule": "Set daily automatic execution time",
            "tt_bulk": "Include in 'Start/Stop All' operations",
            "tt_python": "Select the Python version to use",
            "tt_restart": "Automatically try to restart on error",
            "tt_log": "Toggle inline log view",
            "tt_fav": "Pin this project to the top",
            "tt_tags": "Categorize with tags (comma separated)",
            "tt_setup_venv": "Create a new virtual environment",
            "tt_update_libs": "Run pip install --upgrade",
            "tt_folder": "Open in File Explorer",
            "tt_terminal": "Launch terminal here",
            "tt_dotenv": "Edit .env file",
            "tt_memo": "Edit project notes",
            "tt_delete": "Remove from list",
            "tt_scan": "Scan directory for new apps",
            "tt_help": "Show documentation",
            "tt_lang": "Switch UI language",
            "tt_clone": "Clone project from GitHub",
            "tt_backup": "Backup all settings, .env, and memos",
            "tt_restore": "Restore settings from a backup file",
            "tt_log_filter": "Filter logs... (case-insensitive)",
            # Group Manager
            "group_manager": "Group Manager",
            "add_group": "Add Group",
            "edit_group": "Edit Group",
            "delete_group": "Delete Group",
            "confirm_delete_group": "Are you sure you want to delete this group? (Projects will be unassigned)",
            "group_name": "Group Name",
            "icon": "Icon (1 char)",
            "members": "Members",
            "bulk": "Bulk",
            "tt_add_group": "Create a new group",
            "project_list": "PROJECT LIST",
            "ready": "Ready",
            "venv_ok": "Venv OK",
            "limit_reached": "Limit Reached",
            "max_apps_warning": "Maximum {max_apps} apps can run simultaneously.",
            "auto": "Auto",
            "bulk_label": "Bulk",
            "console_label": "Console",
            "venv_label": "Venv"
        }
    }

    def __init__(self, lang: str | None = None) -> None:
        if lang is None:
            try:
                import locale
                lang_code, _ = locale.getlocale()
                lang = "jpn" if lang_code and (lang_code.startswith("Japanese") or lang_code == "ja_JP") else "en"
            except Exception:
                lang = "jpn"
        self.lang: str = lang

    def get(self, key: str) -> str:
        translations = self.TRANSLATIONS.get(self.lang, self.TRANSLATIONS["en"])
        return translations.get(key, key)
