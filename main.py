from flask import Flask, jsonify, render_template, request, send_file
import subprocess
import json
import threading
import time
import os
import traceback
from core.profile_gen import generate_cis_profile, get_all_profile_rules

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "profiles")
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXE_FOLDER = os.path.join(BASE_DIR, "executables")

IDEVICEINFO_PATH = os.path.join(EXE_FOLDER, "ideviceinfo.exe")
IDEVICEPAIR_PATH   = os.path.join(EXE_FOLDER, "idevicepair.exe")


from core.android_handler import AndroidHandler
from core.process import HardeningProcess

app = Flask(__name__)

# Starea initiala a auditului
audit_state = {
    "status":   "idle",
    "results":  [],
    "device":   {},
    "score":    None,
    "platform": None,  # "android", "ios", or None
}

audit_lock = threading.Lock()


def detect_platform():
    """
    Detecteaza ce tip de dispozitiv este conectat.
    Returneaza "android", "ios", sau None daca nu este nimic conectat.
    """
    # Verificam Android prin ADB
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        lines = []
        for l in result.stdout.splitlines():
            if l.strip() and "List of devices" not in l:
                lines.append(l.strip())
        if len(lines) > 0:
            return "android"
    except Exception:
        pass

    # Verificam iOS prin libimobiledevice
    try:
        result = subprocess.run(
        [IDEVICEINFO_PATH, "-k", "ProductType"],
              capture_output=True,
              text=True,
              timeout=5,
              encoding='utf-8',
              errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip():
            return "ios"
    except Exception:
        pass

    return None

def pair_ios_device():
    """
    Incearca sa conecteze dispozitivul iOS conectat.

      1. Prima incercare: esueaza daca dispozitivul nu a acceptat inca increderea
      2. Daca se detecteaza dialogul de incredere: se asteapta ca utilizatorul sa accepte pe telefon
      3. Se reincearca la fiecare 3 secunde, timp de maxim 30 de secunde
      4. A doua incercare: ar trebui sa reuseasca dupa acceptarea increderii

    Returneaza True daca asocierea a reusit, False altfel.
    """
    def attempt_pair():
        result = subprocess.run(
            [IDEVICEPAIR_PATH, "pair"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout + result.stderr

    # Prima incercare
    success, output = attempt_pair()

    if success:
        print("[iOS] Paired successfully.")
        return True

    # Dialogul de incredere nu a fost acceptat inca
    if "trust dialog" in output.lower() or "accept" in output.lower():
        print("[iOS] Trust dialog detected. Waiting for user to accept on device...")

        # Anuntam frontend-ul sa afiseze un mesaj utilizatorului
        with audit_lock:
            audit_state["status"] = "awaiting-trust"

        # Asteptam maxim 30 de secunde, verificand la fiecare 3 secunde
        for attempt in range(10):
            time.sleep(3)
            print(f"[iOS] Retry attempt {attempt + 1}/10...")
            success, output = attempt_pair()
            if success:
                print("[iOS] Paired successfully after trust.")
                return True

        print("[iOS] Pairing timed out.")
        return False

    print(f"[iOS] Pairing failed: {output.strip()}")
    return False


def check_device_connected():
    return detect_platform() is not None


def get_device_info(platform):
    if platform == "android":
        def prop(key):
            try:
                result = subprocess.run(
                    ["adb", "shell", "getprop", key],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.stdout.strip() or "Unknown"
            except Exception:
                return "Unknown"

        return {
            "platform":     "Android",
            "manufacturer": prop("ro.product.manufacturer"),
            "model":        prop("ro.product.model"),
            "android":      prop("ro.build.version.release"),
            "patch":        prop("ro.build.version.security_patch"),
            "serial":       prop("ro.serialno"),
        }

    elif platform == "ios":
        def iprop(key):
            try:
                result = subprocess.run(
                    [IDEVICEINFO_PATH, "-k", key],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='utf-8',
                    errors='replace',
                    cwd = EXE_FOLDER,
                    shell = True
                )
                return result.stdout.strip() or "Unknown"
            except Exception:
                return "Unknown"

        return {
            "platform": "iOS",
            "manufacturer": "Apple",
            "model": iprop("HardwareModel"),
            "android": iprop("ProductVersion"),
            "patch": "N/A",
            "serial": iprop("SerialNumber"),
        }

    return {}


def run_audit_task():
    """
    Functia principala a auditului, rulata intr-un thread secundar.
    """
    with audit_lock:
        audit_state["status"]   = "running"
        audit_state["results"]  = []
        audit_state["device"]   = {}
        audit_state["score"]    = None
        audit_state["platform"] = None

    try:
        # Detectam platforma
        platform = detect_platform()

        if platform is None:
            with audit_lock:
                audit_state["status"]  = "error"
                audit_state["results"] = []
            return

        device = get_device_info(platform)

        with open("policies.json") as f:
            policies = json.load(f)

        engine = HardeningProcess(policies)

        if platform == "android":
            results = engine.audit_android()

        elif platform == "ios":
            paired = pair_ios_device()
            if not paired:
                with audit_lock:
                    audit_state["status"] = "error"
                return
            results = engine.audit_ios()


        # Calcularea scorului
        excluded    = ["MANUAL", "N/A"]
        automatable = [r for r in results if r["status"] not in excluded]
        passed      = [r for r in automatable if r["status"] == "PASS"]
        score       = round((len(passed) / len(automatable)) * 100) if automatable else 0

        with audit_lock:
            audit_state["status"]   = "done"
            audit_state["results"]  = results
            audit_state["device"]   = device
            audit_state["score"]    = str(score)
            audit_state["platform"] = platform


    except Exception as e:
        traceback.print_exc()
        with audit_lock:
            audit_state["status"] = "error"
            audit_state["results"] = [{
                                        "id": "ERR",
                                        "status": "FAIL",
                                        "found": str(e)
                                     }]


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/run", methods=["POST"])
def run_audit():
    if audit_state["status"] == "running":
        return jsonify({"message": "Audit already running"}), 409
    thread = threading.Thread(target=run_audit_task)
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Audit started"})


@app.route("/api/status")
def get_status():
    with audit_lock:
        return jsonify(audit_state)


@app.route("/api/reset", methods=["POST"])
def reset_audit():
    with audit_lock:
        audit_state["status"]   = "idle"
        audit_state["results"]  = []
        audit_state["device"]   = {}
        audit_state["score"]    = None
        audit_state["platform"] = None
    return jsonify({"message": "Reset"})


@app.route("/api/ping_device")
def ping_device():
    platform = detect_platform()
    return jsonify({
        "connected": platform is not None,
        "platform":  platform
    })


@app.route('/api/remediate', methods=['POST'])
def remediate():
    data    = request.json
    rule_id = data.get('id')

    if not rule_id:
        return jsonify({"status": "error", "message": "Missing rule id"}), 400

    handler = AndroidHandler()
    success = handler.modify_values(rule_id)

    if success:
        return jsonify({"status": "success", "message": f"Rule {rule_id} remediated successfully."}), 200
    else:
        return jsonify({"status": "error", "message": f"Rule {rule_id} cannot be auto-remediated."}), 400

@app.route("/api/ios/profile_rules")
def ios_profile_rules():
    institutional = request.args.get("institutional", "false").lower() == "true"
    return jsonify(get_all_profile_rules(institutional= institutional))


@app.route("/api/ios/generate_profile", methods=["POST"])
def generate_ios_profile():
    try:
        data = request.json or {}
        selected = data.get("selected", None)
        institutional = data.get("institutional", False)

        path = generate_cis_profile(
            selected_rule_ids=selected if selected else None,
            output_path=os.path.join(OUTPUT_DIR, "cis_hardening.mobileconfig"),
            institutional = institutional
        )
        return send_file(
            path,
            mimetype="application/x-apple-aspen-config",
            as_attachment=True,
            download_name="cis_hardening.mobileconfig",
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)