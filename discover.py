from core.android_handler import AndroidHandler

class StatusDiscovery:
    def __init__(self):
        self.handler = AndroidHandler()
        self.namespaces = ["global", "secure", "system"]

    def _get_snapshot(self):
        snapshot = {}
        for ns in self.namespaces:
            raw_data = self.handler.execute(f"settings list {ns}")
            settings = {}
            for line in raw_data.splitlines():
                if "=" in line:
                    key, val = line.split("=", 1)
                    settings[key] = val
            snapshot[ns] = settings
        return snapshot

    def execute_session(self):
        print("\n=== ANDROID STATUS VERIFICATION ===")

        # Capturing modified variables
        print("[*] Recording current settings. Please wait...")
        before = self._get_snapshot()

        # Testare
        print("\n[!] Discovering changes:")
        print("    1. Locate any security or privacy setting.")
        print("    2. Change the setting to a new value.")
        input("\n[*] Press Enter when finished.")

        # Capture after changing values
        print("\n[*] Recording TARGET state...")
        after = self._get_snapshot()

        # Verifying differences found
        print("\n[!] Detected changes: ")
        found_diffs = 0

        for ns in self.namespaces:
            all_keys = set(before[ns].keys()) | set(after[ns].keys())
            for key in all_keys:
                v_before = before[ns].get(key, "NULL (Key Missing)")
                v_after = after[ns].get(key, "NULL (Key Missing)")

                if v_before != v_after:
                    found_diffs += 1
                    print(f"\n[{found_diffs}] NAMESPACE: {ns.upper()}")
                    print(f"    Key:           {key}")
                    print(f"    Transition:    {v_before} -> {v_after}")
                    print(f"    Policy Export: \"namespace\": \"{ns}\", \"key\": \"{key}\"")

        if found_diffs == 0:
            print("[-] No variance detected. Check dumpsys.")
        else:
            print(f"\n[*] Session complete. {found_diffs} state changes identified.")






if __name__ == "__main__":
    StatusDiscovery().execute_session()
