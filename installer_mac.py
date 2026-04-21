import os
import subprocess
import sys

def run_command(command):
    print(f"Executing: {command}")
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing: {command}")
        sys.exit(1)

def main():
    print("--- Python App Launcher Installer for macOS ---")

    if not os.path.exists(".venv"):
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv .venv")
    else:
        print("Virtual environment already exists.")

    print("Installing dependencies...")
    pip_path = os.path.join(".venv", "bin", "pip")
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")

    print("\n--- Installation Complete! ---")
    print("To start the app, run: ./.venv/bin/python main.py")
    print("To build the app, run: ./.venv/bin/python -m PyInstaller --windowed --onefile --name=PythonAppLauncher main.py")

    create_alias = input("\nCreate Desktop Alias? [y/N]: ").strip().lower()
    if create_alias == 'y':
        try:
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            script_path = os.path.abspath("main.py")
            python_path = os.path.abspath(os.path.join(".venv", "bin", "python"))
            
            alias_script = f"""
tell application "Finder"
    make new alias file to POSIX file "{python_path}" at POSIX file "{desktop}"
    set name of result to "Python App Launcher"
end tell
"""
            # OSAScript でエイリアス作成は少し複雑なので、簡易的なシンボリックリンクまたはApp化を推奨
            # ここでは簡易的にシンボリックリンクを作成
            os.symlink(python_path, os.path.join(desktop, "Python App Launcher"))
            print(f"Alias created on Desktop (Symlink to Python). Note: You may need to pass main.py as argument.")
        except Exception as e:
            print(f"Failed to create alias: {e}")

if __name__ == "__main__":
    main()
