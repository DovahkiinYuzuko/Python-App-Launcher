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
    print("--- Python App Launcher Installer for Linux ---")

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

    create_desktop = input("\nCreate Desktop Entry? [y/N]: ").strip().lower()
    if create_desktop == 'y':
        try:
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            script_path = os.path.abspath("main.py")
            python_path = os.path.abspath(os.path.join(".venv", "bin", "python"))
            icon_path = os.path.abspath(os.path.join("assets", "logo.png"))
            
            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Python App Launcher
Comment=Manage your Python applications
Exec={python_path} {script_path}
Icon={icon_path}
Terminal=false
Categories=Development;
"""
            entry_path = os.path.join(desktop, "python-app-launcher.desktop")
            with open(entry_path, "w") as f:
                f.write(desktop_content)
            
            run_command(f"chmod +x {entry_path}")
            print(f"Desktop entry created: {entry_path}")
        except Exception as e:
            print(f"Failed to create desktop entry: {e}")

if __name__ == "__main__":
    main()
