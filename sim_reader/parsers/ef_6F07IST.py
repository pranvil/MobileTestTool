
from parsers.general import encode_service_bitmap, decode_service_bitmap

service_mapping = [
    "P-CSCF address(n°1)",
    "Generic Bootstrapping Architecture (GBA)(n°2)",
    "HTTP Digest(n°3)",
    "GBA-based Local Key Establishment Mechanism(n°4)",
    "Support of P-CSCF discovery(n°5)",
    "Short Message Storage (SMS)(n°6)",
    "Short Message Status Reports (SMSR)(n°7)",
    "Support SMS-PP over SM-over-IP (n°8)",
    "Communication Control for IMS by ISIM(n°9)",
    "Support of UICC access to IMS(n°10)",
    "URI support by UICC(n°11)",
    "Media Type support(n°12)",
    "IMS call disconnection cause(n°13)",
    "URI support for MO SHORT MESSAGE CONTROL(n°14)",
    "Mission Critical Services(n°15)",
    "URI support for SMS-PP DOWNLOAD(n°16)",
    "From Preferred(n°17)",
    "IMS configuration data(n°18)",
    "XCAP Configuration Data(n°19)",
    "WebRTC URI(n°20)",
    "MuD and MiD configuration data(n°21)"
]

def parse_data(raw_data: list) -> list:
    if not raw_data:
        return []
    hex_data = raw_data[0]
    return [decode_service_bitmap(hex_data, service_mapping)]

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    flags = [user_data.get(name, 'N') for name in service_mapping]
    return encode_service_bitmap(flags, ef_file_len_decimal)
