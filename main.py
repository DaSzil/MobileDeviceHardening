from flask import Flask, jsonify, render_template, request
import subprocess
import json
import threading

IDEVICEINFO_PATH = r"C:\Users\somog\Desktop\Faculta\AN IV\Sem II\Licenta\libimobiledevice\ideviceinfo.exe"

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
                  capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return "ios"
    except Exception:
        pass

    return None


def check_device_connected():
    """
    Returneaza True daca orice dispozitiv (Android sau iOS) este conectat.
    """
    return detect_platform() is not None


def get_device_info(platform):
    """
    Preia informatiile dispozitivului conectat in functie de platforma detectata.
    """
    if platform == "android":
        def prop(key):
            try:
                result = subprocess.run(
                    ["adb", "shell", "getprop", key],
                    capture_output=True, text=True, timeout=5
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
                    errors='replace'
                )
                return result.stdout.strip() or "Unknown"
            except Exception:
                return "Unknown"

        return {
            "platform": "iOS",
            "manufacturer": "Apple",
            "model": iprop("HardwareModel"),  # D37AP — the hardware identifier
            "android": iprop("ProductVersion"),  # 18.4
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
            results = engine.audit_ios()  # de implementat

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
        with audit_lock:
            audit_state["status"]  = "error"
            audit_state["results"] = [{"id": "ERR", "status": "FAIL", "found": str(e)}]


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)