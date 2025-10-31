
from parsers.general import encode_service_bitmap, decode_service_bitmap

service_mapping = [
    "Local Phone Book(n°1)", "Fixed Dialling Numbers (FDN)(n°2)", "Extension 2(n°3)", "Service Dialling Numbers (SDN)(n°4)",
    "Extension 3(n°5)", "Barred Dialling Numbers (BDN)(n°6)", "Extension 4(n°7)", "Outgoing Call Information (OCI and OCT)(n°8)",
    "Incoming Call Information (ICI and ICT)(n°9)", "Short Message Storage (SMS)(n°10)", "Short Message Status Reports (SMSR)(n°11)",
    "Short Message Service Parameters (SMSP)(n°12)", "Advice of Charge (AoC)(n°13)", "Capability Configuration Parameters 2 (CCP2)(n°14)",
    "Cell Broadcast Message Identifier(n°15)", "Cell Broadcast Message Identifier Ranges(n°16)", "Group Identifier Level 1(n°17)",
    "Group Identifier Level 2(n°18)", "Service Provider Name(n°19)", "User controlled PLMN selector with Access Technology(n°20)",
    "MSISDN(n°21)", "Image (IMG)(n°22)", "Support of Localised Service Areas (SoLSA)(n°23)", "Enhanced Multi Level Precedence and Pre emption Service(n°24)",
    "Automatic Answer for eMLPP(n°25)", "RFU(n°26)", "GSM Access(n°27)", "Data download via SMS PP(n°28)", "Data download via SMS CB(n°29)",
    "Call Control by USIM(n°30)", "MO SMS Control by USIM(n°31)", "RUN AT COMMAND command(n°32)", "shall be set to 1(n°33)",
    "Enabled Services Table(n°34)", "APN Control List (ACL)(n°35)", "Depersonalisation Control Keys(n°36)", "Co operative Network List(n°37)",
    "GSM security context(n°38)", "CPBCCH Information(n°39)", "Investigation Scan(n°40)", "MexE(n°41)",
    "Operator controlled PLMN selector with Access Technology(n°42)", "HPLMN selector with Access Technology(n°43)", "Extension 5(n°44)",
    "PLMN Network Name(n°45)", "Operator PLMN List(n°46)", "Mailbox Dialling Numbers(n°47)", "Message Waiting Indication Status(n°48)",
    "Call Forwarding Indication Status(n°49)", "Reserved and shall be ignored(n°50)", "Service Provider Display Information(n°51)",
    "Multimedia Messaging Service (MMS)(n°52)", "Extension 8(n°53)", "Call control on GPRS by USIM(n°54)", "MMS User Connectivity Parameters(n°55)",
    "Network's indication of alerting in the MS (NIA)(n°56)", "VGCS Group Identifier List (EFVGCS and EFVGCSS)(n°57)",
    "VBS Group Identifier List (EFVBS and EFVBSS)(n°58)", "Pseudonym(n°59)", "User Controlled PLMN selector for I-WLAN access(n°60)",
    "Operator Controlled PLMN selector for I-WLAN access(n°61)", "User controlled WSID list(n°62)", "Operator controlled WSID list(n°63)",
    "VGCS security(n°64)", "VBS security(n°65)", "WLAN Reauthentication Identity(n°66)", "Multimedia Messages Storage(n°67)",
    "Generic Bootstrapping Architecture (GBA)(n°68)", "MBMS security(n°69)", "Data download via USSD and USSD application mode(n°70)",
    "Equivalent HPLMN(n°71)", "Additional TERMINAL PROFILE after UICC activation(n°72)", "Equivalent HPLMN Presentation Indication(n°73)",
    "Last RPLMN Selection Indication(n°74)", "OMA BCAST Smart Card Profile(n°75)", "GBA-based Local Key Establishment Mechanism(n°76)",
    "Terminal Applications(n°77)", "Service Provider Name Icon(n°78)", "PLMN Network Name Icon(n°79)",
    "Connectivity Parameters for USIM IP connections(n°80)", "Home I-WLAN Specific Identifier List(n°81)", "I-WLAN Equivalent HPLMN Presentation Indication(n°82)",
    "I-WLAN HPLMN Priority Indication(n°83)", "I-WLAN Last Registered PLMN(n°84)", "EPS Mobility Management Information(n°85)",
    "Allowed CSG Lists and corresponding indications(n°86)", "Call control on EPS PDN connection by USIM(n°87)", "HPLMN Direct Access(n°88)",
    "eCall Data(n°89)", "Operator CSG Lists and corresponding indications(n°90)", "Support for SM-over-IP(n°91)",
    "Support of CSG Display Control(n°92)", "Communication Control for IMS by USIM(n°93)", "Extended Terminal Applications(n°94)",
    "Support of UICC access to IMS(n°95)", "Non-Access Stratum configuration by USIM(n°96)", "PWS configuration by USIM(n°97)",
    "RFU(n°98)", "URI support by UICC(n°99)", "Extended EARFCN support(n°100)", "ProSe(n°101)", "USAT Application Pairing(n°102)",
    "Media Type support(n°103)", "IMS call disconnection cause(n°104)", "URI support for MO SHORT MESSAGE CONTROL(n°105)",
    "ePDG configuration Information support(n°106)", "ePDG configuration Information configured(n°107)", "ACDC support(n°108)",
    "Mission Critical Services(n°109)", "ePDG configuration Information for Emergency Service support(n°110)",
    "ePDG configuration Information for Emergency Service configured(n°111)", "eCall Data over IMS(n°112)",
    "URI support for SMS-PP DOWNLOAD(n°113)", "From Preferred(n°114)", "IMS configuration data(n°115)", "TV configuration(n°116)",
    "3GPP PS Data Off(n°117)", "3GPP PS Data Off Service List(n°118)", "V2X(n°119)", "XCAP Configuration Data(n°120)",
    "EARFCN list for MTC/NB-IOT UEs(n°121)", "5GS Mobility Management Information(n°122)", "5G Security Parameters(n°123)",
    "Subscription identifier privacy support(n°124)", "SUCI calculation by the USIM(n°125)", "UAC Access Identities support(n°126)",
    "Control plane-based steering of UE in VPLMN(n°127)", "Call control on PDU Session by USIM(n°128)",
    "5GS Operator PLMN List(n°129)", "Support for SUPI of type NSI or GLI or GCI(n°130)",
    "3GPP PS Data Off separate Home and Roaming lists(n°131)", "Support for URSP by USIM(n°132)",
    "5G Security Parameters extended(n°133)", "MuD and MiD configuration data(n°134)",
    "Support for Trusted non-3GPP access networks by USIM(n°135)",
    "Support for multiple records of NAS security context storage (n°136)",
    "Pre-configured CAG information list(n°137)", "SOR-CMCI storage in USIM(n°138)", "5G ProSe(n°139)",
    "Storage of disaster roaming information in USIM(n°140)", "Pre-configured eDRX parameters(n°141)",
    "5G NSWO support(n°142)", "PWS configuration for SNPN in USIM(n°143)",
    "Multiplier Coefficient for Higher Priority PLMN search(n°144)", "KAUSF derivation configuration(n°145)",
    "Network Identifier for SNPN (NID)(n°146)", "5MBS UE pre-configuration(n°147)",
    "UE configured for using Operator controlled signal(n°148)", "A2X(n°149)", "IMS Data Channel Indication(n°150)"
]

def parse_data(raw_data: list) -> list:
    if not raw_data:
        return []
    hex_data = raw_data[0]
    return [decode_service_bitmap(hex_data, service_mapping)]

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    flags = [user_data.get(name, 'N') for name in service_mapping]
    return encode_service_bitmap(flags, ef_file_len_decimal)
