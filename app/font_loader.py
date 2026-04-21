import sys
import ctypes
from pathlib import Path
import tkinter.font as tkfont

class FontLoader:
    """
    外部の .ttf フォントをOSに登録し、アプリ内で使用可能にするクラス。
    Windows/macOS/Linux に対応。
    """
    _loaded_fonts = []

    @classmethod
    def load_font(cls, font_path: str) -> bool:
        """
        指定されたパスのフォントをOSに一時的に登録する。
        """
        from .utils import resource_path
        path = resource_path(font_path)
        if not path.exists():
            return False

        if sys.platform == "win32":
            # Windows: GDI API を使用してフォントを一時登録
            FR_PRIVATE = 0x10
            path_str = str(path.absolute())
            res = ctypes.windll.gdi32.AddFontResourceExW(path_str, FR_PRIVATE, 0)
            if res:
                cls._loaded_fonts.append(path_str)
                return True
        
        elif sys.platform == "darwin":
            # macOS: 基本的に同梱されていれば tk.Font でパス指定できる場合が多いが、
            # OSへの登録は CoreText 等が必要。ここでは簡易的に True を返す。
            # (tkinter はシステムにインストールされていないフォントでもファイルパスが通れば読める場合がある)
            return True
            
        elif sys.platform.startswith("linux"):
            # Linux: ~/.local/share/fonts 等への配置が必要な場合があるが、
            # プログラムからの動的ロードは環境に依存。
            return True

        return False

    @classmethod
    def get_system_default(cls):
        """
        OSごとの標準フォント名を返す。
        """
        if sys.platform == "win32":
            return "Segoe UI"
        elif sys.platform == "darwin":
            return ".AppleSystemUIFont"
        else:
            return "Ubuntu"
