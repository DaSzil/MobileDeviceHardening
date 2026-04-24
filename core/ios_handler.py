import subprocess
import os

BIN_PATH = r"C:\Users\somog\Desktop\Faculta\AN IV\Sem II\Licenta\libimobiledevice"


def run_ios_audit():
    # Use the absolute path to the executable
    exe_path = os.path.join(BIN_PATH, "ideviceinfo.exe")

    try:
        result = subprocess.run(
            [exe_path, "-k", "PasswordProtected"],
            capture_output=True,
            text=True,
            cwd=BIN_PATH,  # This ensures the .exe can see its required .dll files
            shell=True  # Required on some Windows setups to resolve the path correctly
        )

        # Log exactly what the hardware said to the Python console
        print(f"Hardware Response: {result.stdout.strip()}")

        return result.stdout.strip()
    except Exception as e:
        print(f"Execution Error: {e}")
        return None