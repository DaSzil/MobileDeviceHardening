import uuid
import plistlib


def _new_uuid():
    return str(uuid.uuid4())


PASSCODE_RULE_MAP = {
    "2.4.1": ("allowSimple", False), # Fara parole simple
    "2.4.3": ("minLength", 6), # Lungime minima de 6
    "2.4.4": ("maxInactivity", 2), # Blocare automata dupa 2 minute
    "2.4.5": ("maxGracePeriod", 0), # Se cere parola instant dupa inchederea ecranului
    "2.4.6": ("maxFailedAttempts", 6), # Stergerea informatiilor dupa 6 incercari esuate
}

INST_PASSCODE_RULE_MAP = {
    # Doar pentru device-uri din institutii
    "3.4.1": ("allowSimple", False),
    "3.4.3": ("minLength", 6),
    "3.4.4": ("maxInactivity", 2),
    "3.4.5": ("maxGracePeriod", 0),
    "3.4.6": ("maxFailedAttempts", 6),
}

RESTRICTION_RULE_MAP = {
    "2.2.1.1": ("allowAssistantWhileLocked", False), # Siri pe lock screen
    "2.2.1.2": ("allowManagedAppsCloudSync", False), # Sync iCloud pentru aplicatile utilizate
    "2.2.1.3": ("forceEncryptedBackup", True), # Backup-uri criptate
    "2.2.1.5": ("allowUntrustedTLSPrompt", False), # Neacceptare TLS
    "2.2.1.7": ("allowOpenFromManagedToUnmanaged", False), #Posibilitatea de a scrie valori din aplicatii securizate in cele nesecurizate
    "2.2.1.8": ("allowOpenFromUnmanagedToManaged", False), #Posibilitatea de a scrie valori din aplicatii nesecurizate in cele securizate
    "2.2.1.9": ("airdropUnmanaged", True), # Setare AirDrop ca nesecurizat
    "2.2.1.10": ("allowActivityContinuation", False), # Continuare utilizare aplicatie pe alt dispozitiv Apple
    "2.2.1.12": ("forceWatchWristDetection", True), # Detectie pe incheietura pt Apple Watch
    "2.2.1.13": ("allowControlCenter", False), # Utilizare Control Center pe lock screen
    "2.2.1.14": ("allowNotificationCenter", False), # Utilizare Notification Center pe lock screen
    "2.2.2.1": ("safariAllowFraudWarning", True), # Avertizare Safari de frauda
    "2.2.2.2": ("safariCookiePolicy", 2), # Cookie-uri Safari doar pt site-ul curent
    "2.9.1": ("allowIntelligenceExtensions", False), # Extensii Externe AI
    "2.9.2": ("allowIntelligenceNotesSummarization", False), # Rezumat Notes
    "2.9.3": ("allowIntelligenceMailSummarization", False), # Rezumat Mail
    "2.9.4": ("allowIntelligenceWritingTools", False), # Instrumente de Scriere
}

INST_RESTRICTION_RULE_MAP = {
    # Doar pentru device-uri din institutii
    "3.1.1": ("PayloadRemovalDisallowed", True), # Prevenire eliminare cont
    "3.2.1.2": ("allowAssistantWhileLocked", False), # Siri pe lock screen
    "3.2.1.3": ("allowCloudBackup", False), # Backup iCloud
    "3.2.1.4": ("allowCloudDocumentSync", False), # Documente & date iCloud
    "3.2.1.5": ("allowCloudKeychainSync", False), # Breloc iCloud
    "3.2.1.6": ("allowManagedAppsCloudSync", False), # iCloud sync pt applicatii securizate
    "3.2.1.7": ("allowUSBDriveFileSystemAccess", False), # Drive USB in applicatia Files
    "3.2.1.8": ("allowNetworkDriveFileSystemAccess", False), # Drive Network in aplicatia Files
    "3.2.1.9": ("forceEncryptedBackup", True), # Criptare fortata backup-uri
    "3.2.1.11": ("allowEraseContentAndSettings", False), # Stergere intreg continutul si setarile
    "3.2.1.12": ("allowUntrustedTLSPrompt", False), # Neacceptare TLS
    "3.2.1.14": ("allowProfileInstallation", False), # Instalare Profile de Configuratie
    "3.2.1.15": ("allowVPNCreation", False), # Adaugare configuratii VPN
    "3.2.1.17": ("allowCellularPlanModification", False), # Modificare setari de date celulare
    "3.2.1.18": ("allowUSBRestrictedMode", False), # Accesorii USB cat timp telefonul e inchis
    "3.2.1.19": ("allowHostPairing", False), # Asociere cu gazda non-Configurator
    "3.2.1.20": ("allowOpenFromManagedToUnmanaged", False),  #Posibilitatea de a scrie valori din aplicatii securizate in cele nesecurizate
    "3.2.1.21": ("allowOpenFromUnmanagedToManaged", False),  #Posibilitatea de a scrie valori din aplicatii nesecurizate in cele securizate
    "3.2.1.22": ("airdropUnmanaged", True), # Setare AirDrop ca nesecurizat
    "3.2.1.23": ("allowActivityContinuation", False), # Continuare utilizare aplicatie pe alt dispozitiv Apple
    "3.2.1.25": ("allowAutoFillPasswordAndCreditCard", False), # Require Face ID/Touch ID before AutoFill
    "3.2.1.26": ("forceWatchWristDetection", True), # Detectie pe incheietura pt Apple Watch
    "3.2.1.27": ("allowDeviceNameModification", False), # Configurarea de noi dispozitive din apropiere — cheie proxy
    "3.2.1.28": ("allowPasswordProximityRequests", False), # Partajarea parolei de proximitate
    "3.2.1.30": ("allowControlCenter", False), # Utilizare Control Center pe lock screen
    "3.2.1.31": ("allowNotificationCenter", False), # Utilizare Notification Center pe lock screen
    "3.2.2.1":  ("safariAllowFraudWarning", True), # Avertizare Safari de frauda
    "3.2.2.2": ("safariCookiePolicy", 2), # Cookie-uri Safari doar pt site-ul curent
    "3.10.1": ("allowIntelligenceExtensions", False), # Extensii Externe AI
    "3.10.2": ("allowIntelligenceNotesSummarization", False), # Rezumat Notes
    "3.10.3": ("allowIntelligenceMailSummarization", False), # Rezumat Notes
    "3.10.4": ("allowIntelligenceWritingTools", False), # Instrumente de Scriere
}

MAIL_RULE_MAP = {
    "2.7.1": ("PreventMove", True), # Interzicere mutarea mesajelor intre conturi
    "2.7.2": ("allowMailDrop", False),  # Dezactivare Mail Drop
}

INST_MAIL_RULE_MAP = {
    "3.7.1": ("PreventMove", True),  # Interzicere mutarea mesajelor intre conturi
    "3.7.2": ("allowMailDrop", False),  # Dezactivare Mail Drop
}

# Reguli manuale din lista
MANUAL_RULES = {
    "2.1.2": "Controls when profile can be removed",
    "2.2.1.4": "Personalized ads, cannot verify post-install",
    "2.2.1.6": "Force automatic date and time, manual in benchmark",
    "2.2.1.11": "Diagnostic submission, manual in benchmark",
    "2.3.1": "Managed Safari Web Domains, organisation specific configuration",
    "2.4.2": "Require alphanumeric value, manual in benchmark",
    "2.5.1": "MAC Randomization per-network setting",
    "2.6.1": "VPN,organisaton specific configuration",
    "2.8.1": "Notification Settings, per-app configuration",

    # Optionale
    "4.1.1": "Review Manage Sharing & Access: Settings > Privacy & Security",
    "4.1.2": "Review Emergency Reset: Settings > Face ID & Passcode > Safety Check",
    "4.1.3": "Review Lockdown Mode: Settings > Privacy & Security > Lockdown Mode",
    "4.1.4": "Ensure App Privacy Report enabled — Settings > Privacy & Security > App Privacy Report",
    "4.1.5": "Review AirPrint: Apple Configurator supervised only",
    "4.2": "Check device not jailbroken: look for Cydia, Sileo, checkra1n in Spotlight",
    "4.3": "Enable automatic iOS updates: Settings > General > Software Update > Automatic Updates",
    "4.4": "Ensure software is up to date: Settings > General > Software Update",
    "4.5": "Review iCloud Private Relay: Settings > [Name] > iCloud > Private Relay",
    "4.6": "Review Mail Privacy Protection: Settings > Mail > Privacy Protection",
    "4.7": "Enable automatic app updates: Settings > App Store > App Updates",
    "4.8": "Ensure Find My iPhone is enabled: Settings > [Name] > Find My > Find My iPhone",
    "4.9": "Use latest iOS device architecture: hardware replacement required",
    "4.10": "Verify iPhone Mirroring: Settings > General > AirPlay & Continuity",
    "4.11": "Enable RCS Messaging: Settings > Apps > Messages > RCS Messaging",
}

# Doar pentru device-uri din institutii
INST_MANUAL_RULES = {
    "3.1.2": "Controls when profile can be removed",
    "3.2.1.1": "Allow screenshots and screen recording, manual in benchmark",
    "3.2.1.4": "Personalized ads, cannot verify post-install",
    "3.2.1.6": "Force automatic date and time, manual in benchmark",
    "3.2.1.10": "Personalized ads, cannot verify post-install",
    "3.2.1.11": "Diagnostic submission, manual in benchmark",
    "3.2.1.16": "Force automatic date and time, manual in benchmark",
    "3.2.1.24": "Diagnostic submission, manual in benchmark",
    "3.2.1.29": "Allow password sharing (supervised only), manual in benchmark",
    "3.3.1": "Managed Safari Web Domains, organisation specific configuration",
    "3.4.2": "Require alphanumeric value, manual in benchmark",
    "3.5.1": "MAC Randomization per-network setting",
    "3.6.1": "VPN,organisaton specific configuration",
    "3.8.1": "Notification Settings, per-app configuration",
    "3.9.1": "\"If Lost, Return to...\" Message, organisation specific configuration",
}

def generate_cis_profile(selected_rule_ids=None, output_path="cis_hardening.mobileconfig", institutional=False):

    if institutional:
        passcode_map = INST_PASSCODE_RULE_MAP
        restriction_map = INST_RESTRICTION_RULE_MAP
        mail_map = INST_MAIL_RULE_MAP
        default_ids = (
                list(INST_PASSCODE_RULE_MAP.keys()) +
                list(INST_RESTRICTION_RULE_MAP.keys()) +
                list(INST_MAIL_RULE_MAP.keys()) +
                ["3.1.1"]
        )
    else:
        passcode_map = PASSCODE_RULE_MAP
        restriction_map = RESTRICTION_RULE_MAP
        mail_map = MAIL_RULE_MAP
        default_ids = (
                list(PASSCODE_RULE_MAP.keys()) +
                list(RESTRICTION_RULE_MAP.keys()) +
                list(MAIL_RULE_MAP.keys()) +
                ["2.1.1"]
        )

    if selected_rule_ids is None:
        selected_rule_ids = default_ids


    payloads = []


    selected_passcode = {
        k: v for k, v in passcode_map.items()
        if k in selected_rule_ids
    }

    if selected_passcode:
        passcode_payload = {
            "PayloadType": "com.apple.mobiledevice.passwordpolicy",
            "PayloadIdentifier": "com.audit.cis.ios26.passcode",
            "PayloadUUID": _new_uuid(),
            "PayloadVersion": 1,
            "PayloadDisplayName": "Passcode Policy",
            "PayloadDescription": "CIS iOS 26 Passcode rules",
            "forcePIN": True,
        }
        for rule_id, (key, value) in selected_passcode.items():
            passcode_payload[key] = value
        payloads.append(passcode_payload)


    selected_restrictions = {
        k: v for k, v in restriction_map.items()
        if k in selected_rule_ids
    }

    if selected_restrictions:
        restriction_payload = {
            "PayloadType": "com.apple.applicationaccess",
            "PayloadIdentifier": "com.audit.cis.ios26.restrictions",
            "PayloadUUID": _new_uuid(),
            "PayloadVersion": 1,
            "PayloadDisplayName": "Security Restrictions",
            "PayloadDescription": "CIS iOS 26; Application access restrictions",
        }
        for rule_id, (key, value) in selected_restrictions.items():
            restriction_payload[key] = value
        payloads.append(restriction_payload)


    selected_mail = {
        k: v for k, v in mail_map.items()
        if k in selected_rule_ids
    }

    if selected_mail:
        mail_payload = {
            "PayloadType": "com.apple.mail.managed",
            "PayloadIdentifier": "com.audit.cis.ios26.mail",
            "PayloadUUID": _new_uuid(),
            "PayloadVersion": 1,
            "PayloadDisplayName": "Mail Restrictions",
            "PayloadDescription": "CIS iOS 26; Mail rules",
            "EmailAccountDescription": "CIS Hardening Policy",
            "EmailAccountType": "EmailTypeIMAP",
            "EmailAccountName": "CIS Hardening Policy",
            "EmailAddress": "audit@localhost",
            "IncomingMailServerAuthentication": "EmailAuthPassword",
            "IncomingMailServerHostName": "localhost",
            "IncomingMailServerPortNumber": 993,
            "IncomingMailServerUseSSL": True,
            "IncomingMailServerUsername": "audit",
            "OutgoingMailServerAuthentication": "EmailAuthPassword",
            "OutgoingMailServerHostName": "localhost",
            "OutgoingMailServerPortNumber": 587,
            "OutgoingMailServerUseSSL": True,
            "OutgoingMailServerUsername": "audit",
        }
        for rule_id, (key, value) in selected_mail.items():
            mail_payload[key] = value
        payloads.append(mail_payload)

    if not payloads:
        payloads.append({
            "PayloadType": "com.apple.applicationaccess",
            "PayloadIdentifier": "com.audit.cis.ios26.restrictions.base",
            "PayloadUUID": _new_uuid(),
            "PayloadVersion": 1,
            "PayloadDisplayName": "Base Restrictions",
            "PayloadDescription": "Required placeholder payload",
        })

    profile = {
        "PayloadDisplayName":
            ("CIS iOS 26 Institutional Profile" if institutional
             else "CIS iOS 26 Hardening Profile"
        ),

        "PayloadDescription": (
            f"Custom CIS Apple iOS 26 Benchmark profile "
            f"{len(selected_rule_ids)} rule(s) selected."
        ),

        "PayloadIdentifier": "com.audit.cis.ios26",
        "PayloadOrganization": "Device Hardening Audit",
        "PayloadType": "Configuration",
        "PayloadUUID": _new_uuid(),
        "PayloadVersion": 1,
        "PayloadRemovalDisallowed": institutional,
        "PayloadContent": payloads,
    }


    if "2.1.1" in selected_rule_ids:
        profile["ConsentText"] = {
            "default": (
                "This configuration profile enforces security settings "
                "recommended by the CIS Apple iOS 26 Benchmark v1.0.0. "
                "By installing this profile you acknowledge that certain "
                "device settings will be managed and restricted. "
                "You may remove this profile at any time via "
                "Settings > General > VPN & Device Management."
            )
        }

    if "3.1.1" in selected_rule_ids and institutional:
        profile["PayloadRemovalDisallowed"] = True

    with open(output_path, "wb") as f:
        plistlib.dump(profile, f, fmt=plistlib.FMT_XML)

    print(f"[iOS] Profile generated: {output_path}")
    print(f"[iOS] Type: {'Institutional' if institutional else 'End-user'}")
    print(f"[iOS] Rules included: {len(selected_rule_ids)}")

    return output_path


def get_all_profile_rules(institutional=False):
    if not institutional:
        return [
            # General
            {
                "id": "2.1.1",
                "title": "Show consent message at install",
                "group": "General"
             },
            {
                "id": "2.2.1.12",
                "title": "Force Apple Watch wrist detection",
                "group": "General"
             },

            # Lock Screen
            {
                "id": "2.2.1.1",
                "title": "Disable Siri on lock screen",
                "group": "Lock Screen"
             },
            {
                "id": "2.2.1.13",
                "title": "Disable Control Center on lock screen",
                "group": "Lock Screen"
             },
            {
                "id": "2.2.1.14",
                "title": "Disable Notification Center on lock screen",
                "group": "Lock Screen"
             },

            # Passcode
            {
                "id": "2.4.1",
                "title": "Disallow simple passcodes",
                "group": "Passcode"
             },
            {
                "id": "2.4.3",
                "title": "Minimum passcode length of 6",
                "group": "Passcode"
             },
            {
                "id": "2.4.4",
                "title": "Auto-lock after 2 minutes",
                "group": "Passcode"
             },
            {
                "id": "2.4.5",
                "title": "Require passcode immediately on lock",
                "group": "Passcode"
             },
            {
                "id": "2.4.6",
                "title": "Wipe device after 6 failed attempts",
                "group": "Passcode"
             },

            # iCloud
            {
                "id": "2.2.1.2",
                "title": "Prevent managed apps syncing to iCloud",
                "group": "iCloud"
             },
            {
                "id": "2.2.1.3",
                "title": "Force encrypted backups",
                "group": "iCloud"
             },

            # Network
            {
                "id": "2.2.1.5",
                "title": "Prevent accepting untrusted TLS certificates",
                "group": "Network"
             },

            # Data Transfer
            {
                "id": "2.2.1.7",
                "title": "Allow managed to unmanaged document transfer",
                "group": "Data Transfer"
             },
            {
                "id": "2.2.1.8",
                "title": "Allow unmanaged to managed document transfer",
                "group": "Data Transfer"
             },
            {
                "id": "2.2.1.9",
                "title": "Treat AirDrop as unmanaged destination",
                "group": "Data Transfer"
             },
            {
                "id": "2.2.1.10",
                "title": "Disable Handoff",
                "group": "Data Transfer"
             },

            # Safari
            {
                "id": "2.2.2.1",
                "title": "Force Safari fraud warning",
                "group": "Safari"
             },
            {
                "id": "2.2.2.2",
                "title": "Safari cookies from visited sites only",
                "group": "Safari"
             },

            # Mail
            {
                "id": "2.7.1",
                "title": "Prevent moving messages between accounts",
                "group": "Mail"
             },
            {
                "id": "2.7.2",
                "title": "Disable Mail Drop",
                "group": "Mail"
             },

            # Apple Intelligence
            {
                "id": "2.9.1",
                "title": "Disable external AI extensions",
                "group": "Apple Intelligence"
             },
            {
                "id": "2.9.2",
                "title": "Disable Notes summarization",
                "group": "Apple Intelligence"
             },
            {
                "id": "2.9.3",
                "title": "Disable Mail summarization",
                "group": "Apple Intelligence"
             },
            {
                "id": "2.9.4",
                "title": "Disable Writing Tools",
                "group": "Apple Intelligence"
             },
        ]
    else:
        # Institutional
        return [
            {
                "id": "3.1.1",
                "title": "Prevent profile removal (set to Never)",
                "group": "General"
            },
            {
                "id": "3.2.1.26",
                "title": "Force Apple Watch wrist detection",
                "group": "General"
            },
            {
                "id": "3.2.1.2",
                "title": "Disable Siri on lock screen",
                "group": "Lock Screen"
            },
            {
                "id": "3.2.1.30",
                "title": "Disable Control Center on lock screen",
                "group": "Lock Screen"
            },
            {
                "id": "3.2.1.31",
                "title": "Disable Notification Center on lock screen",
                "group": "Lock Screen"
            },
            {
                "id": "3.4.1",
                "title": "Disallow simple passcodes",
                "group": "Passcode"
            },
            {
                "id": "3.4.3",
                "title": "Minimum passcode length of 6",
                "group": "Passcode"
            },
            {
                "id": "3.4.4",
                "title": "Auto-lock after 2 minutes",
                "group": "Passcode"
            },
            {
                "id": "3.4.5",
                "title": "Require passcode immediately on lock",
                "group": "Passcode"
            },
            {
                "id": "3.4.6",
                "title": "Wipe device after 6 failed attempts",
                "group": "Passcode"
             },
            {
                "id": "3.2.1.3",
                "title": "Disable iCloud backup",
                "group": "iCloud"
            },
            {
                "id": "3.2.1.4",
                "title": "Disable iCloud documents and data",
                "group": "iCloud"
            },
            {
                "id": "3.2.1.5",
                "title": "Disable iCloud Keychain sync",
                "group": "iCloud"
            },
            {
                "id": "3.2.1.6",
                 "title": "Prevent managed apps syncing to iCloud",
                 "group": "iCloud"
             },
            {
                "id": "3.2.1.9",
                "title": "Force encrypted backups",
                "group": "iCloud"
            },
            {
                "id": "3.2.1.7",
                "title": "Disable USB drive access in Files app",
                "group": "Storage"
            },
            {
                "id": "3.2.1.8",
                "title": "Disable network drive access in Files app",
                "group": "Storage"
            },
            {
                "id": "3.2.1.12",
                "title": "Prevent accepting untrusted TLS certificates",
                "group": "Network"
            },
            {
                "id": "3.2.1.15",
                "title": "Disable adding VPN configurations",
                "group": "Network"
            },
            {
                "id": "3.2.1.17",
                "title": "Disable modifying cellular data settings",
                "group": "Network"
            },
            {
                "id": "3.2.1.18",
                "title": "Disable USB accessories while locked",
                "group": "Network"
            },
            {
                "id": "3.2.1.19",
                "title": "Disable pairing with non-Configurator hosts",
                "group": "Network"
            },
            {
                "id": "3.2.1.11",
                "title": "Disable Erase All Content and Settings",
                "group": "Security"
            },
            {
                "id": "3.2.1.14",
                "title": "Disable installing configuration profiles",
                "group": "Security"
            },
            {
                "id": "3.2.1.25",
                "title": "Require Face ID/Touch ID before AutoFill",
                "group": "Security"
            },
            {
                "id": "3.2.1.27",
                "title": "Disable setting up new nearby devices",
                "group": "Security"
            },
            {
                "id": "3.2.1.28",
                "title": "Disable proximity password sharing requests",
                "group": "Security"
            },
            {
                "id": "3.2.1.20",
                "title": "Block managed to unmanaged document transfer",
                "group": "Data Transfer"
            },
            {
                "id": "3.2.1.21",
                "title": "Block unmanaged to managed document transfer",
                "group": "Data Transfer"
            },
            {
                "id": "3.2.1.22",
                "title": "Treat AirDrop as unmanaged destination",
                "group": "Data Transfer"
            },
            {
                "id": "3.2.1.23",
                "title": "Disable Handoff",
                "group": "Data Transfer"
            },
            {
                "id": "3.2.2.1",
                "title": "Force Safari fraud warning",
                "group": "Safari"
            },
            {
                "id": "3.2.2.2",
                "title": "Safari cookies from visited sites only",
                "group": "Safari"
            },
            {
                "id": "3.7.1",
                "title": "Prevent moving messages between accounts",
                "group": "Mail"
            },
            {
                "id": "3.7.2",
                "title": "Disable Mail Drop",
                "group": "Mail"
            },
            {
                "id": "3.10.1",
                "title": "Disable external AI extensions",
                "group": "Apple Intelligence"
            },
            {
                "id": "3.10.2",
                "title": "Disable Notes summarization",
                "group": "Apple Intelligence"
            },
            {
                "id": "3.10.3",
                "title": "Disable Mail summarization",
                "group": "Apple Intelligence"
            },
            {
                "id": "3.10.4",
                "title": "Disable Writing Tools",
                "group": "Apple Intelligence"
            }
        ]


def get_profile_rule_ids(institutional=False):
    return [r["id"] for r in get_all_profile_rules(institutional = institutional)]


def get_manual_rule_ids(institutional=False):
    if institutional:
        return list(INST_MANUAL_RULES.keys())
    return list(MANUAL_RULES.keys())
