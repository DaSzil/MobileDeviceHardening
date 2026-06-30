from flask import Flask, jsonify, render_template, request, send_file
import subprocess
import json
import threading
import time
import os
import traceback
import socket
from core.profile_gen import generate_cis_profile, get_all_profile_rules
from core.android_handler import AndroidHandler
from core.process import HardeningProcess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "profiles")
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXE_FOLDER = os.path.join(BASE_DIR, "executables")

IDEVICEINFO_PATH = os.path.join(EXE_FOLDER, "ideviceinfo.exe")
IDEVICEPAIR_PATH = os.path.join(EXE_FOLDER, "idevicepair.exe")
IDEVICE_ID_PATH = os.path.join(EXE_FOLDER, "idevice_id.exe")
IDEVICENAME_PATH = os.path.join(EXE_FOLDER, "idevicename.exe")

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

def detect_all_devices():
    """
    Detecteaza toate dispozitivele detectate pt oricare sistem de operare
    Returneaza o lista de dict cu inf despre fiecare dispozitiv

    Format:
    [
        { "serial": "val-seriala-Android", "platform": "android", "name": "Redmi Note 11" },
        { "serial": "val-seriala-iOS",     "platform": "ios",     "name": "Szil's iPhone" },
    ]
    """
    devices = []
    seen_hw_ids = set()
    # Android
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or "List of devices attached" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]

                if "_adb-tls-connect._tcp" in serial:
                    continue
                try:
                    hw_id_result = subprocess.run(
                        ["adb", "-s", serial, "shell", "getprop", "ro.serialno"],
                        capture_output=True, text=True, timeout=5
                    )
                    hw_id = hw_id_result.stdout.strip() or serial
                except Exception:
                    hw_id = serial

                if hw_id in seen_hw_ids:
                    continue
                seen_hw_ids.add(hw_id)

                try:
                    name_result = subprocess.run(
                        ["adb", "-s", serial, "shell", "getprop", "ro.product.marketname"],
                        capture_output=True, text=True, timeout=5
                    )
                    name = name_result.stdout.strip()

                    if not name:
                        name_result = subprocess.run(
                            ["adb", "-s", serial, "shell", "getprop", "ro.product.model"],
                            capture_output=True, text=True, timeout=5
                        )
                        name = name_result.stdout.strip() or serial

                except Exception as e:
                    name = serial


                devices.append({
                    "serial": serial,
                    "platform": "android",
                    "name": name
                })
    except Exception:
        pass

    # iOS
    try:
        result = subprocess.run(
            [IDEVICE_ID_PATH, "-l"],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace'
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                udid = line.strip()
                if not udid:
                    continue

                name_result = subprocess.run(
                    [IDEVICENAME_PATH],
                    capture_output=True, text=True, timeout=5,
                    encoding='utf-8', errors='replace'
                )
                name = name_result.stdout.strip() or udid

                devices.append({
                    "serial":   udid,
                    "platform": "ios",
                    "name":     name
                })
    except Exception:
        pass

    return devices




def detect_platform():
    """
    Detecteaza ce tip de dispozitiv este conectat.
    Returneaza "android", "ios", sau None daca nu este nimic conectat.
    """
    # Verificam Android prin ADB
    devices = detect_all_devices()
    if not devices:
        return None
    return devices[0]["platform"]




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
    return len(detect_all_devices()) > 0




def get_device_info(platform, serial=None):
    if platform == "android":
        def prop(key):
            try:
                cmd = ["adb"]
                if serial:
                    cmd += ["-s", serial]

                cmd += ["shell", "getprop", key]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.stdout.strip() or "Unknown"
            except Exception:
                return "Unknown"

        marketname = prop("ro.product.marketname")
        model = marketname if marketname and marketname != "Unknown" else prop("ro.product.model")

        return {
            "platform": "Android",
            "manufacturer": prop("ro.product.manufacturer"),
            "model": model,
            "android": prop("ro.build.version.release"),
            "patch": prop("ro.build.version.security_patch"),
            "serial": prop("ro.serialno"),
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




def pair_android_wireless(ip, pairing_port, pairing_code, connect_port):
    result = subprocess.run(
        ["adb", "pair", f"{ip}:{pairing_port}", pairing_code],
        capture_output=True,
        text=True,
        timeout=15
    )
    if "Successfully paired" not in result.stdout:
        return False, None, result.stdout + result.stderr

    # Use the explicit connect port the user provided
    connect = subprocess.run(
        ["adb", "connect", f"{ip}:{connect_port}"],
        capture_output=True,
        text=True,
        timeout=10
    )
    if "connected" in connect.stdout.lower() and "unable" not in connect.stdout.lower():
        devices = subprocess.run(["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in devices.stdout.splitlines():
            if ip in line and "device" in line:
                serial = line.split()[0]
                return True, serial, connect.stdout

    return False, None, f"Paired but could not connect: {connect.stdout}"



def run_audit_task():
    """
    Functia principala a auditului, rulata intr-un thread secundar.
    """
    with audit_lock:
        audit_state["status"] = "running"
        audit_state["results"] = []
        audit_state["device"] = {}
        audit_state["score"] = None
        audit_state["platform"] = None

    try:
        # Detectam platforma
        serial = audit_state.get("serial")
        platform = None
        for dev in detect_all_devices():
            if dev["serial"] == serial:
                platform = dev["platform"]
                break

        if platform is None:
            with audit_lock:
                audit_state["status"]  = "error"
                audit_state["results"] = []
            return

        device = get_device_info(platform, serial=audit_state.get("serial"))

        with open("policies.json") as f:
            policies = json.load(f)

        hardening = HardeningProcess(policies, serial=audit_state.get("serial"))

        if platform == "android":
            results = hardening.audit_android()

        elif platform == "ios":
            paired = pair_ios_device()
            if not paired:
                with audit_lock:
                    audit_state["status"] = "error"
                return
            results = hardening.audit_ios()
        else:
            print(f"[ERR] Could not determine platform for serial: {serial}")
            with audit_lock:
                audit_state["status"] = "error"
                audit_state["results"] = [{
                    "id": "ERR",
                    "status": "FAIL",
                    "found": "Device disconnected or platform could not be determined before audit could start."
                }]
            return

        # Calcularea scorului
        excluded    = ["MANUAL", "N/A"]
        automatable = [r for r in results if r["status"] not in excluded]

        def weight(r):
            return 2 if str(r.get("level")) == "1" else 1

        total_weight = sum(weight(r) for r in automatable)
        passed_weight = sum(weight(r) for r in automatable if r["status"] == "PASS")
        score = round((passed_weight / total_weight) * 100) if total_weight > 0 else 0

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

# Preluare IP curent pentru certificat https
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# Routing for Flask
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/run", methods=["POST"])
def run_audit():
    data = request.json or {}
    with audit_lock:
        audit_state["serial"] = data.get("serial")
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
    devices = detect_all_devices()
    return jsonify({
        "connected": len(devices) > 0,
        "devices": devices,
        "platform": devices[0]["platform"] if devices else None # Partea veche a codului
    })



@app.route('/api/remediate', methods=['POST'])
def remediate():
    data = request.json
    rule_id = data.get('id')
    serial = data.get('serial')

    if not rule_id:
        return jsonify({"status": "error", "message": "Missing rule id"}), 400

    handler = AndroidHandler(serial=serial)
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




@app.route("/api/android/wireless_pair", methods=["POST"])
def android_wireless_pair():
    data = request.json or {}
    ip           = data.get("ip")
    pairing_port = data.get("pairing_port")
    pairing_code = data.get("pairing_code")
    connect_port = data.get("connect_port")

    if not all([ip, pairing_port, pairing_code, connect_port]):
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    success, serial, output = pair_android_wireless(ip, pairing_port, pairing_code, connect_port)
    if success:
        return jsonify({"status": "success", "serial": serial})
    return jsonify({"status": "error", "message": output}), 500




@app.route("/api/ios/push_profile", methods=["POST"])
def push_ios_profile():
    try:
        import asyncio
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.mobile_config import MobileConfigService

        profile_path = os.path.join(OUTPUT_DIR, "cis_hardening.mobileconfig")

        if not os.path.exists(profile_path):
            return jsonify({"status": "error", "message": "Profile not found. Generate it first."}), 404

        with open(profile_path, "rb") as f:
            profile_data = f.read()
            async def do_push():
                lockdown = await create_using_usbmux()
                async with MobileConfigService(lockdown) as svc:
                    await svc.install_profile(profile_data)

            asyncio.run(do_push())

            return jsonify({"status": "success", "message": "Profile pushed to device."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/unpair/android", methods=["POST"])
def unpair_android():
    data   = request.json or {}
    serial = data.get("serial", "").strip()
    if not serial:
        return jsonify({"status": "error", "message": "Serial required"}), 400
    try:
        result = subprocess.run(
            ["adb", "disconnect", serial],
            capture_output=True,
            text=True,
            timeout=10
        )
        return jsonify({"status": "success", "message": result.stdout.strip()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/unpair/ios", methods=["POST"])
def unpair_ios():
    data = request.json or {}
    udid = data.get("serial", "").strip()
    if not udid:
        return jsonify({"status": "error", "message": "UDID required"}), 400
    try:
        result = subprocess.run(
            [IDEVICEPAIR_PATH, "unpair"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "Device unpaired."})
        else:
            return jsonify({"status": "error", "message": result.stdout + result.stderr}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)