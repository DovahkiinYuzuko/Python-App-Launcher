import os
import subprocess
import sys
import customtkinter
from pathlib import Path

def get_customtkinter_path():
    """customtkinter の場所を取得する。"""
    return os.path.dirname(customtkinter.__file__)

def main():
    print("--- Python App Launcher Universal Builder ---")
    
    # 1. 必要なパスの準備
    ctk_path = get_customtkinter_path()
    assets_path = os.path.abspath("assets")
    app_module_path = os.path.abspath("app")
    
    # OS ごとの区切り文字 (Windows は ; , 他は :)
    sep = ";" if os.name == "nt" else ":"
    
    # 2. PyInstaller コマンドの構築
    # 直接 'pyinstaller' を呼ぶとパスの問題が起きる場合があるため、python -m を使用
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",       # コンソールウィンドウを表示しない
        "--onefile",         # 単一の実行ファイルにまとめる
        f"--add-data={ctk_path}{sep}customtkinter", # CTK のアセットを含める
        f"--add-data={assets_path}{sep}assets",        # 自前のアセットを含める
        f"--add-data={app_module_path}{sep}app",      # app モジュールを含める
    ]
    
    # OS 別のアイコン設定
    if sys.platform == "win32":
        icon_path = os.path.join(assets_path, "icon.ico")
        if os.path.exists(icon_path):
            cmd.append(f"--icon={icon_path}")
    elif sys.platform == "darwin":
        icon_path = os.path.join(assets_path, "icon.icns")
        if os.path.exists(icon_path):
            cmd.append(f"--icon={icon_path}")
        cmd.append("--windowed") # Mac ではこれが必要
    
    # 3. ターゲットの指定
    cmd.extend([
        "--name=PythonAppLauncher",
        "main.py"
    ])
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        # PyInstaller を実行
        subprocess.check_call(cmd)
        print("\n--- Build Successful! ---")
        print(f"The executable can be found in the 'dist' folder.")
    except subprocess.CalledProcessError:
        print("\n--- Build Failed! ---")
        print("Make sure PyInstaller is installed: pip install pyinstaller")
        sys.exit(1)
    except FileNotFoundError:
        print("\n--- Error: PyInstaller not found! ---")
        print("Please install it using: pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    main()
