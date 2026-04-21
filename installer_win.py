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
    print("--- Python App Launcher Installer for Windows ---")

    if not os.path.exists(".venv"):
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv .venv")
    else:
        print("Virtual environment already exists.")

    print("Installing dependencies...")
    pip_path = os.path.join(".venv", "Scripts", "pip")
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")

    print("\n--- Installation Complete! ---")
    print("To start the app, run: .\\.venv\\Scripts\\python.exe main.py")
    print("To build the exe, run: .\\.venv\\Scripts\\python.exe build_exe.py")

    create_shortcut = input("\nCreate Desktop Shortcut? [y/N]: ").strip().lower()
    if create_shortcut == 'y':
        try:
            import tempfile
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            script_path = os.path.abspath("main.py")
            python_exe = os.path.abspath(os.path.join(".venv", "Scripts", "python.exe"))
            icon_path = os.path.abspath("main.py") # とりあえず
            
            vbs_content = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop}\\Python App Launcher.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{python_exe}"
oLink.Arguments = "{script_path}"
oLink.WorkingDirectory = "{os.path.abspath(".")}"
oLink.Description = "Python App Launcher"
oLink.Save
"""
            with tempfile.NamedTemporaryFile(suffix=".vbs", delete=False, mode="w") as f:
                f.write(vbs_content)
                vbs_file = f.name
            
            subprocess.check_call(f"cscript //nologo {vbs_file}", shell=True)
            os.remove(vbs_file)
            print(f"Shortcut created on Desktop: {desktop}\\Python App Launcher.lnk")
        except Exception as e:
            print(f"Failed to create shortcut: {e}")

if __name__ == "__main__":
    main()
