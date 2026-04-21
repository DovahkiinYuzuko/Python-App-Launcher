import sys
import multiprocessing
from app.gui import AppGUI

def main():
    """
    アプリケーションのエントリーポイント。
    """
    # PyInstaller でビルドされたバイナリでのマルチプロセス対応
    multiprocessing.freeze_support()
    
    try:
        app = AppGUI()
        app.mainloop()
    except Exception as e:
        # 起動失敗時にエラーを表示（exe化してコンソールがない場合でもダイアログが出るように）
        import tkinter.messagebox as mb
        mb.showerror("Startup Error", f"Failed to start the application:\n\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
