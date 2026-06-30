import subprocess


class AndroidHandler:
    def __init__(self, serial=None):
        self.serial = serial
        self.supported = [
            "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.14a", "1.14b", "1.15",
            "1.17", "1.18", "1.19", "1.20", "1.21", "1.23", "1.24", "1.26", "1.27",
            "2.1", "2.10", "2.11", "3.2"
        ]

    # Ruleaza o comanda prin adb si salveaza rezultatea ca pe un string
    # Prin command intelegem commanda de tip adb de rulat pe dispozitivul testat
    # Comenzile utile ar fi getprop, settings get, si dumpsys
    # Returneaza un string care este ori gol, in cazul in care avem o eroare, ori este returnat in intregime
    # valoarea cautata/necesara
    def execute(self, command: str) -> str:

        try:
            # Transmite intreaga comanda ca un singur string catre adb, a.i
            # caracterele specifice sa fie interpretate corect de catre powershell,
            # in loc sa fie impartite in argumente separate

            cmd = ["adb"]
            if self.serial:
                cmd += ["-s", self.serial]

            cmd += ["shell"] + command.split()
            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,            # Preia si stdout, dar si stderr
                text=True,                      # Transforma octetii in string automat
                timeout=10,                     # Daca dupa 10s nu se pot prelua informatiile, comanda se va opri
                encoding = 'utf-8',             # Folosim UTF-8 pentru decodare
                errors = 'replace'              # Daca nu se pot deocoda octeti, vor fi setati ca si ?, pentru a nu
            )                                   # bloca programul

            # Afiseaza erori legate de adb daca valoarea este diferita de 0
            if result.returncode != 0 and result.stderr:
                print(f"[ERR] {result.stderr.strip()}")

            # Eliminam spatiile din jurul string-ului inainte de a-l returna
            return result.stdout.strip()

        except FileNotFoundError:
            # Daca nu avem adb instalat, nu vom putea configura/testa nimic
            print("[ERR] adb not found")
            return ""
        except subprocess.TimeoutExpired:
            # Mentionata in momentul in care procesul nu raspunde in timpul limita setat anterior
            print(f"[ERR] Command timed out: {command}")
            return ""
        except Exception as e:
            # Orice alta eroare/exceptie intra aici
            print(f"[ERR] Unexpected error: {e}")
            return ""

    def modify_values(self, rule_id):
        if rule_id not in self.supported:
            print(f"[!] Rule {rule_id} cannot be modified, as its variables cannot be modified within ADB.")
            return False

        print(f"[*] Executing Modifications for Rule {rule_id}")

        writes = []

        # Namespace : Global
        if rule_id == "1.9":
            self.execute("settings put global development_settings_enabled 0")
            writes.append(("global", "development_settings_enabled", "0"))
        elif rule_id == "1.14a":
            self.execute("settings put global auto_time 1")
            writes.append(("global", "auto_time", "1"))
        elif rule_id == "1.14b":
            self.execute("settings put global auto_time_zone 1")
            writes.append(("global", "auto_time_zone", "1"))
        elif rule_id == "1.21":
            self.execute("settings put global network_recommendations_enabled 0")
            writes.append(("global", "network_recommendations_enabled", "0"))
        elif rule_id == "1.23":
            self.execute("settings put global add_users_when_locked 0")
            writes.append(("global", "add_users_when_locked", "0"))
        elif rule_id == "1.24":
            self.execute("settings put global guest_user_enabled 0")
            writes.append(("global", "guest_user_enabled", "0"))
        elif rule_id == "1.26":
            self.execute("svc bluetooth disable")
        elif rule_id == "2.10":
            self.execute("settings put global wifi_scan_always_enabled 0")
            writes.append(("global", "wifi_scan_always_enabled", "0"))
        elif rule_id == "2.11":
            self.execute("settings put global ble_scan_always_enabled 0")
            writes.append(("global", "ble_scan_always_enabled", "0"))

        # Namespace: Secure
        elif rule_id == "1.3":
            self.execute("settings put secure lock_pattern_visible_pattern 0")
            writes.append(("secure", "lock_pattern_visible_pattern", "0"))
        elif rule_id == "1.4":
            self.execute("settings put secure lock_screen_lock_after_timeout 0")
            writes.append(("secure", "lock_screen_lock_after_timeout", "0"))
        elif rule_id == "1.5":
            self.execute("settings put secure power_button_instantly_locks 1")
            writes.append(("secure", "power_button_instantly_locks", "1"))
        elif rule_id == "1.6":
            self.execute("settings put secure lock_screen_owner_info_enabled 1")
            writes.append(("secure", "lock_screen_owner_info_enabled", "1"))
        elif rule_id == "1.15":
            self.execute("settings put secure location_mode 3")
            writes.append(("secure", "location_mode", "3"))
        elif rule_id == "1.17":
            # App protection requires writing to multiple keys
            self.execute("settings put secure appprotection_permission_function_agree_or_disagree 1")
            self.execute("settings put secure appprotection_permission_function_usage 1")
            writes.append(("secure", "appprotection_permission_function_agree_or_disagree", "1"))
            writes.append(("secure", "appprotection_permission_function_usage", "1"))
        elif rule_id == "1.18":
            self.execute("settings put secure upload_apk_enable 1")
            writes.append(("secure", "upload_apk_enable", "1"))
        elif rule_id == "1.27":
            # Forces the default AOSP/Google keyboard back as the primary input method
            forced_ime = (
                "com.google.android.googlequicksearchbox/com.google.android.voicesearch.ime.VoiceInputMethodService:"
                "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME")
            self.execute(f"settings put secure enabled_input_methods {forced_ime}")
            writes.append(("secure", "enabled_input_methods", forced_ime))
        elif rule_id == "2.1":
            self.execute("settings put secure lock_screen_show_notifications 0")
            writes.append(("secure", "lock_screen_show_notifications", "0"))
        elif rule_id == "3.2":
            self.execute("settings put secure location_mode 3")
            writes.append(("secure", "location_mode", "3"))


        # Namespace: System
        elif rule_id == "1.8":
            self.execute("settings put system show_password 0")
            writes.append(("system", "show_password", "0"))
        elif rule_id == "1.19":
            self.execute("settings put system lock_to_app_exit_locked 1")
            writes.append(("system", "lock_to_app_exit_locked", "1"))
        elif rule_id == "1.20":
            self.execute("settings put system screen_off_timeout 120000")
            writes.append(("system", "screen_off_timeout", "120000"))


        # Namespace: Other
        elif rule_id == "1.7":
            self.execute("svc wifi disable")

        for namespace, key, desired in writes:
            current = self.execute(f"settings get {namespace} {key}").strip()
            if current != desired:
                print(f"[!] Verification failed for {rule_id}: expected '{desired}', got '{current}'")
                return False



        return True