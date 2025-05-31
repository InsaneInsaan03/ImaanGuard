import os
import subprocess
import sys
import platform

def build_exe():
    """
    Compile ImaanGuard project into a single EXE using PyInstaller.
    """
    print("Starting build process for ImaanGuard...")

    # Define paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    main_script = os.path.join(project_root, "src", "main.py")
    data_dir = os.path.join(project_root, "data")

    # PyInstaller options
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",            # Single EXE
        "--noconsole",         # No console window
        f"--add-data={data_dir}{os.pathsep}data",  # Bundle data/ folder
        "--hidden-import=pynput",  # Ensure pynput is included
        "--hidden-import=psutil",  # Ensure psutil is included
        "--hidden-import=shutil",  # Ensure shutil is included
        "--name=ImaanGuard",    # EXE name
        main_script             # Entry point
    ]

    # Run PyInstaller
    try:
        print(f"Running PyInstaller: {' '.join(pyinstaller_cmd)}")
        subprocess.run(pyinstaller_cmd, check=True)
        print(f"Build successful! EXE located at: dist/ImaanGuard.exe")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe()