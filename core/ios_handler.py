import subprocess
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_PATH = os.path.join(BASE_DIR, "executables")

def run_ios_audit():
    # Use the absolute path to the executable
    exe_path = os.path.join(BASE_DIR, "ideviceinfo.exe")

    try:
        result = subprocess.run(
            [exe_path, "-k", "PasswordProtected"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            shell=True
        )

        # Log exactly what the hardware said to the Python console
        print(f"Hardware Response: {result.stdout.strip()}")

        return result.stdout.strip()
    except Exception as e:
        print(f"Execution Error: {e}")
        return None