from flask import Flask, jsonify, render_template, request
import subprocess
import json
import threading
import os

from android_handler import AndroidHandler
from core.process import HardeningProcess

BIN_PATH = r"C:\Users\somog\Desktop\Faculta\AN IV\Sem II\Licenta\libimobiledevice"

app = Flask(__name__)

# Status initial
audit_state = {
    "status": "idle", # Idle, Running, Done, Error
    "results": [], # O lista care include rezultatele functiei "HardeningProcess()", salvate ca si var de tip dict
    "device": {}, # Informatiile device-ului mobil care a fost conectat, preluate cu get_device_info()
    "score": None, # Scor creat prin adunarea criteriilor care au fost prevazute ca si corecte de catre benchmark,
                   # Pentru calcularea scorului se vor omite valorile de tip "Manual" si "N/A"
}


# Necesar pentru a evite operatiunile de scriere/citire simulatane care s-ar putea produce. Acest lucru se
# intampla din cauza thread-ului site-ului creat de Flask, si cel al functiei run_audit_task()
audit_lock = threading.Lock()


# Returneaza informatii despre device-ul conectat utilizand un o cmanda de tip ADB
# utilizand "adb getprop" vom putea afla detalii precum modelul telefonului, producatorul, si versiunea de android
# existenta, si alte date cautate.
# Daca nu se va putea afla vreo informatie din motive specifice (nu avem USB debugging activat), va returna "Unknown"
# pentru fiecare camp
def get_device_info():
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
        "model":        prop("ro.product.model"),
        "manufacturer": prop("ro.product.manufacturer"),
        "android":      prop("ro.build.version.release"),
        "patch":        prop("ro.build.version.security_patch"),
        "serial":       prop("ro.serialno"),
    }

# Verificam daca avem un device conectat prin USB la dispozitivul care da host dashboard-ului pentru verificare.
# Daca da, vom putea continua cu testarile, daca nu, butonul de testare nu va putea fi apasat, si va ramane asa pana la
# introducerea dispozitivului compatibil.
# Utilizand comanda "adb devices" vom avea o lista cu dispozitive care sunt conectate catre serverul adb rulat.
# Returnam True daca exista vreun dispozitiv in lista ADB, iar False daca nu este gasit vreun dispozitiv sau avem
# vreo alta eroare.
def check_device_connected():
    try:
        result = subprocess.run(["adb", "devices"],
                                capture_output=True,
                                text=True,
                                timeout=5)

        # Eliminam liniile goale si linia "List of devices attached"
        lines = []
        for l in result.stdout.splitlines():
            if l.strip() and "List of devices" not in l:
                lines.append(l.strip())

        return len(lines) > 0
    except Exception:
        return False

def detect_platform():
    # Debug: Check if the file actually exists
    ios_exe = os.path.join(BIN_PATH, "idevice_id.exe")
    print(f"Checking for iOS binary at: {ios_exe}")
    print(f"Exists? {os.path.exists(ios_exe)}")

    try:
        # We must use shell=True on Windows sometimes for path resolution
        # Or provide the full absolute path
        result = subprocess.run([ios_exe, "-l"], capture_output=True, text=True, timeout=5)
        udid = result.stdout.strip()
        print(f"iOS Detection Output: '{udid}'")

        if udid:
            return "IOS", udid
    except Exception as e:
        print(f"iOS Detection Error: {e}")







# Functia principala
# Se va folosi un thread secundar pentru a nu avea conflicte cu threadul principal al serverului Flask
#
# Etape:
# 1. Resetare valorile anterioare, schimbarea statusului din "idle" in "running"
# 2. Daca nu exista vreun telefon conectat, returnam o eroare
# 3. Daca da, vom prelua valorile telefonului, si le vom salva
# 4. Preluam din policies.json testele inscrise
# 5. Procesam aceste teste utilizand HardeningProcess
# 6. Calcularea scorului
# 7. Salvarea valorilor in audit_state si marcam procesul ca si finalizat (done)

def run_audit_task():
    # 1.
    with audit_lock:
        audit_state["status"] = "running"
        audit_state["results"] = []
        audit_state["device"] = {}
        audit_state["score"] = None

    try:
        # 2.
        if not check_device_connected():
            with audit_lock:
                audit_state["status"] = "error"
                audit_state["results"] = []
            return

        # 3.
        device = get_device_info()

        # 4.
        with open("policies.json") as f:
            policies = json.load(f)

        # 5.
        engine = HardeningProcess(policies)
        results = engine.audit_android()

        # 6.
        excluded = ["Manual", "MANUAL", "N/A"]

        automatable = []
        for r in results:
            if r["status"] not in excluded:
                automatable.append(r)

        passed = []
        for r in automatable:
            if r["status"] == "PASS":
                passed.append(r)

        if automatable:
            score = round((len(passed) / len(automatable)) * 100)
        else:
            score = 0

        # 7.
        with audit_lock:
            audit_state["status"] = "done"
            audit_state["results"] = results
            audit_state["device"] = device
            audit_state["score"] = str(score)

    except Exception as e:
        with audit_lock:
            audit_state["status"] = "error"
            audit_state["results"] = [{"id": "ERR",
                                       "status": "FAIL",
                                       "found": str(e)}]


# Pagina principala a site-ului
@app.route("/")
def index():
    return render_template("dashboard.html")

# Creeaza o noua testare intr-un thread din background
# Returneaza o eroare cu codul 409 daca exista un proces care deja deruleaza.
# Error Code 409 - "indicates a request conflict with the current state of the target resource."
@app.route("/api/run", methods=["POST"])
def run_audit():
    if audit_state["status"] == "running":
        return jsonify({"message": "Audit already running"}), 409
    thread = threading.Thread(target=run_audit_task)
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Audit started"})


# Returneaza varianta curenta a variabilei audit_state ca JSON
# Verificat de frontend in fiecare secunda pentru a verifica finalizarea
# si a prelua rezultatele odată ce testarea se termină
@app.route("/api/status")
def get_status():
    with audit_lock:
        return jsonify(audit_state)


# Reseteaza audit_state la valoarea sa initiala (idle)
# Apelat de frontend inainte de a reincepe testarea pentru
# a stii ca valorile anterioare sunt eliminate/golite
@app.route("/api/reset", methods=["POST"])
def reset_audit():
    with audit_lock:
        audit_state["status"] = "idle"
        audit_state["results"] = []
        audit_state["device"] = {}
        audit_state["score"] = None
    return jsonify({"message": "Reset"})



# Metoda pt testarea/verificarea conectivitatii prin adb
# Utilizat pt afisarea faptului ca avem un dispozitiv conectat prin USB, fara ca sa trebuiasca sa testam
# benchmark-urile propuse.
@app.route("/api/ping_device")
def ping_device():
    is_connected = check_device_connected()
    return jsonify({"connected": is_connected})

@app.route('/api/remediate', methods=['POST'])
def remediate():
    data = request.json
    rule_id = data.get('id')

    if not rule_id:
        return jsonify({"status": "error", "message": "Missing rule id"}), 400

    handler = AndroidHandler()
    success = handler.modify_values(rule_id)

    if success:
        return jsonify({"status": "success", "message": f"Rule {rule_id} modified successfully."}), 200
    else:
        return jsonify({"status": "error", "message": f"Rule {rule_id} cannot be modified."}), 400






# Procesul principal pt rularea serverului flask
# debug=true => Ne lasa sa interactionam la nivel de debugger (nu e nevoie momentan)
# port=5000 alegerea portului a fost aleatorie, dar va putea fi mentionat faptul ca vom alege
# un port care nu este de obicei utilizat de alte dispozitive/conexiuni
if __name__ == "__main__":
    app.run(debug=True, port=5000)