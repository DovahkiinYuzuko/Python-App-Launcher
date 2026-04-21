import sys
import os
from pathlib import Path
import tkinter.filedialog as filedialog

def resource_path(relative_path: str) -> Path:
    """ 
    リソースの絶対パスを取得する。 
    PyInstaller の一時フォルダ（sys._MEIPASS）と開発時のカレントディレクトリの両方に対応。
    """
    try:
        # PyInstaller が一時フォルダを作成した場合のベースパス
        base_path = Path(sys._MEIPASS)
    except Exception:
        # 開発時はカレントディレクトリ
        base_path = Path(os.path.abspath("."))

    return base_path / relative_path

def get_python_executable(venv_path: Path) -> Path:
    """
    仮想環境のPython実行ファイルのパスをOSに合わせて返します。

    Args:
        venv_path: 仮想環境のルートディレクトリ (.venv など)

    Returns:
        Python実行ファイルへのPathオブジェクト
    """
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"

def select_directory() -> str:
    """
    フォルダ選択ダイアログを表示し、選択されたパスを返します。
    """
    path = filedialog.askdirectory()
    return path

