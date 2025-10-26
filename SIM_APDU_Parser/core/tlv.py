from dataclasses import dataclass
from typing import List
from asn1crypto import parser

@dataclass
class Tlv:
    tag: str
    length: int
    value_hex: str

def parse_ber_tlvs(hexstr: str) -> List[Tlv]:
    hs = hexstr.replace(" ", "").replace("\n", "")
    if len(hs) == 0:
        return []
    if len(hs) % 2 != 0:
        # odd nibble: treat as malformed and ignore the last nibble to be forgiving
        hs = hs[:-1]
    data = bytes.fromhex(hs)

    out: List[Tlv] = []
    off = 0
    total = len(data)
    while off < total:
        try:
            info, consumed_end = parser._parse(data, total, pointer=off, lengths_only=False, depth=0)
        except Exception:
            # Incomplete/garbage tail – stop parsing and return tokens we already got
            break
        cls, constructed, tag_no, header, value, trailer = info

        # Extract tag bytes from header
        i = 1
        if (header[0] & 0x1F) == 0x1F:
            while i < len(header) and (header[i] & 0x80):
                i += 1
            if i < len(header):
                i += 1
        tag_bytes = header[:i] if i <= len(header) else header

        out.append(Tlv(tag=tag_bytes.hex().upper(),
                       length=len(value),
                       value_hex=value.hex().upper()))
        if consumed_end <= off:
            # safety: avoid infinite loop on bad input
            break
        off = consumed_end
    return out
