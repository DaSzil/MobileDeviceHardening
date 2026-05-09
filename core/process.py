from .android_handler import AndroidHandler


# Procesul care va rula pentru testarea politciilor mentionate in fisierul policies.json.
# Exista verificare care trebuiesc verificate printr-o ramura separata, sau unele care vor
# fi testate doar prin preluarea informatiilor redate de catre comanda "adb getprop"

class HardeningProcess:
    def __init__(self, policy):

        # Policy => Se va prelua dict din policies.json, dar doar partea cu "Android"
        # Pe viitor, trb implementat partea pt iOS, care nu va putea folosi adb
        self.policy = policy
        self.handler = AndroidHandler()

    def audit_ios(self):
        print("\n[*] Commencing iOS Security Audit...")
        results = []
        ios_rules = self.policy.get('ios', [])

        for rule in ios_rules:
            # Placeholder — iOS audit not yet implemented
            results.append({
                "id": rule.get('id', '?'),
                "title": rule.get('title', ''),
                "status": "MANUAL",
                "found": "iOS audit not yet implemented.",
                "description": rule.get('description', ''),
                "rationale": rule.get('rationale', ''),
                "desired": rule.get('desired', ''),
                "steps": rule.get('steps', []),
                "fixable": False
            })

        return results




    def audit_android(self):

        # Verifica iteratie cu iteratie toate regulile prezente pe ramura "Android" din fisierul mentionat,
        # pentru a putea reda daca exista nereguli.
        # Functia va returna o lista cu dict-uri rezultat, unul pentru fiecare regula, in care vor aparea
        # campurile create (id, title, status) si vor fi mai tarziu afisate pe dashboard.

        print("\n[*] Commencing Android Security Audit...")
        results = []
        android_rules = self.policy.get('android', [])

        for rule in android_rules:

            # 1.2 Testarea tipului de lock screen utilizat (pattern/pin/pass)
            # Trebuie utilizat comanda dumpsys deoarece comand adb getprop nu are o variabila care sa ne
            # zica daca exista sau nu o parola pe lock screen
            if rule['id'] == "1.2":
                dump = self.handler.execute("dumpsys lock_settings")
                SECURE_TYPES = ["credentialtype: pin",
                                "credentialtype: password",
                                "credentialtype: pattern"]

                # Toate dintre cele mentionate mai sus sunt bune, deci daca exista aceste variabile (returneaza 1),
                # vom putea cataloga aceasta regula ca si indeplinita (PASS)
                is_compliant = any(ct in dump.lower() for ct in SECURE_TYPES)
                current = "Credential Found" if is_compliant else "None/Swipe Only"



            # 1.7 WI-FI Securizat
            # Regula mentioneaza faptul ca un telefon este neprotejat in momentul in care se va atasa unei retele
            # de tip WI-FI care nu are parola configurata. Deci, vom putea asigna urmatoarele valori pentru
            # urmatoarele situatii:
            #
            # 1. WI-Fi Oprit => PASS (Este mentionat faptul ca cea mai sigura optiune ar fi sa avem WI-FI-ul oprit daca nu este utilizat/necesar);
            # 2. WI-FI Pornit, neconectat la vreo retea => PASS
            # 3. WI-FI Pornit, conectat la o retea care necesita o parola => PASS
            # 4. WI-FI Pornit, conectat la o retea care nu are o parola configurata => FAIL
            elif rule['id'] == "1.7":
                wifi_on = self.handler.execute("settings get global wifi_on").strip()
                if wifi_on == "0":
                    is_compliant = True
                    current = "Wi-Fi Disabled"
                else:
                    wifi_info = self.handler.execute("dumpsys wifi")
                    primary_line = ""
                    for line in wifi_info.splitlines():
                        if "isprimary: 1" in line.lower():
                            primary_line = line
                            break
                    if not primary_line:
                        is_compliant = True
                        current = "Wi-Fi On - Not Connected"
                    else:
                        is_compliant = "security type: 0" not in primary_line.lower()
                        current = "Wi-Fi On - Secured" if is_compliant else "Wi-Fi On - Open Network"

            # 1.11 Telefon Rootat
            # A aplica un root asupra unui telefon person ridica riscuri mari dpdv al securitatii dispozitivului. Astfel vom testa daca exista sau nu
            # un acces superior asupra instalari, modificarii si eliminarii aplicatiilor sau fisierelor dorite.
            # Acest lucru duce la crearea mai multor probleme si vulnerabilitati, deci vom incerca sa vedem daca dispozitivul este rootat sau nu.
            #
            # Totusi, pentru a testa asta, vom avea nevoie de niste librarii secundare care sa poata testa acest lucru.
            # Testam cu 3 librarii specifice, fiecare redand un mesaj daca este sau nu dispozitivul modificat in acest mod.
            elif rule['id'] == "1.11":
                su_check = self.handler.execute("which su")
                debuggable = self.handler.execute("getprop ro.debuggable")
                secure_prop = self.handler.execute("getprop ro.secure")

                packages = self.handler.execute("pm list packages")

                # Librarii care pot detecta daca telefonul este rootat sau nu
                root_apps = ["com.topjohnwu.magisk", "io.github.tiann.kernelsu", "me.weishu.apatch"]

                found_app = any(app in packages for app in root_apps)

                is_rooted = (su_check != "" and "not found" not in su_check) or (debuggable == "1") or \
                            (secure_prop == "0") or found_app

                is_compliant = not is_rooted
                current = "Root Detected" if is_rooted else "Clean / Unrooted"

            # 1.28 3rd Party Keyboards
            # Putem vedea concret cate tastaturi are instalat fiecare telefon, dar trebuie sa vedem concret care sunt
            # de tipul 3rd party (adica care nu sunt dezvoltate de producatorii de dispozitive mobile, dar exista pe dispozitiv).
            # Rezultatele pe care le-am gasit m-a dus sa testez astfel: vad daca inceputul numelui aplicatiei contine
            # un producator de telefon/dezvoltator mobile. (Google/Android, Samsung).
            # Problema intalnita : Nu stiu cati sunt first party si cati sunt 3rd party, iar la unele firme e discutabil
            # Ex: swiftkey de exemplu este un program de tastatura creat de catre microsoft, care vine pe unele telefoane
            # din fabrica, si nu stiu cum sa-l cataloghez. Ca prefix pt package are
            elif rule['id'] == "1.27":
                ime_list = self.handler.execute("ime list -s").strip()
                trusted_vendors_kb = ["com.google.", "com.android.","com.samsung.", "com.sec."]

                is_compliant = True
                found_untrusted_kb = []
                all_installed_kb =[]

                for l in ime_list.splitlines():
                    if not l.strip():
                        continue

                    pkg_name = l.split('/')[0]
                    all_installed_kb.append(pkg_name)

                    if not any(pkg_name.startswith(vendor) for vendor in trusted_vendors_kb):
                        is_compliant = False
                        found_untrusted_kb.append(pkg_name)

                if is_compliant:
                    current = f"OK : ({len(all_installed_kb)} trusted KB)"
                else:
                    current = f"ERR : {', '.join(found_untrusted_kb).join(" is untrusted")}"

            # Teste generice
            # Daca nu exista cazuri specifice de mentionat, restul testelor vor fi regasite aici,
            # bazandu-ne pe comenzile adb getprop. Daca nu putem prelua informatiile necesare/nu putem vizualiza
            # optiunile care trebuiesc indeplinite, va trebui sa le mentionam ca valori manuale (MANUAL).
            # Daca variabilele nu exista pe un tip de dispozitiv, le vom nota ca si N/A (not available).
            else:

                # Daca nu exista variabila (key) corespunzatoare, le vom cataloga ca si teste manuale
                if rule.get('key') is None:
                    status = "MANUAL"
                    current = "Manual verification"
                    print(
                        f" [MANUAL] {rule['id']}: {rule['title']} - See: {rule.get('description', 'No existing description')}")

                    results.append({
                        "id": rule['id'],
                        "title": rule.get('title', ''),
                        "status": status,
                        "found": current,
                        "description": rule.get('description', ''),
                        "rationale": rule.get('rationale', ''),
                        "desired": rule.get('desired', ''),
                        "steps": rule.get('steps', []),
                        "fixable": (str(rule['id']) in self.handler.supported)
                    })
                    # Neavand vreo variabila de testat, vom putea sari la final, neputand da o nota de PASS sau FAIL
                    continue
                else:
                    # Cream comanda care trebuie creata dupa namespace (global, secure, system) si cheia/variabila utilizata
                    if rule.get('namespace') == 'getprop':
                        cmd = f"getprop {rule['key']}"
                    else:
                        cmd = f"settings get {rule['namespace']} {rule['key']}"
                    current = self.handler.execute(cmd).strip()



                    # Testare
                    if rule.get('namespace') != 'getprop':
                        listing = self.handler.execute(f"settings list {rule['namespace']}")
                        key_exists = any(
                            line.split("=")[0].strip() == rule['key']
                            for line in listing.splitlines() if "=" in line
                        )

                        if not key_exists:
                            # Key genuinely does not exist on this device/OEM
                            status = "N/A"
                            current = "Key absent on device."
                            print(f" [N/A]  {rule['id']}: {rule['title']} - Key not present on this device")

                            results.append({
                                "id": rule['id'],
                                "title": rule.get('title', ''),
                                "status": status,
                                "found": current,
                                "description": rule.get('description', ''),
                                "rationale": rule.get('rationale', ''),
                                "desired": rule.get('desired', ''),
                                "steps": rule.get('steps', []),
                                "fixable": (str(rule['id']) in self.handler.supported)
                            })

                            continue  # skip the PASS/FAIL evaluation at the bottom
                    # Testare


                    if current in ("null", "", "N/A") or current is None:
                        status = "N/A"
                        current = "Key present on device, but no value set."
                        print(f" [N/A]  {rule['id']}: {rule['title']} - Key present on device, but no value set")

                        results.append({"id": rule['id'],
                                        "title": rule.get('title', ''),
                                        "status": status,
                                        "found": current,
                                        "steps": rule.get('steps', []),
                                        })
                        continue


                    is_compliant = (current == str(rule['desired']).strip())


            # Rezultatul final
            # Blocurile de cod care nu au apelat "continue" vor ajunge aici
            # Asignarea statusului va putea duce la cresterea scorului de securitate, doar daca este o valoare PASS
            status = "PASS" if is_compliant else "FAIL"
            print(f" [{status}] {rule['id']}: {rule['title']} (Found: {current})")

            results.append({
                "id": rule['id'],
                "title": rule.get('title', ''),
                "status": status,
                "found": current,
                "description": rule.get('description', ''),
                "rationale": rule.get('rationale', ''),
                "desired": rule.get('desired', ''),
                "steps": rule.get('steps', []),
                "fixable": (str(rule['id']) in self.handler.supported)
            })
        return results