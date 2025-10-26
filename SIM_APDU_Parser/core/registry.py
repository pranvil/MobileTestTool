
from typing import Dict, Type
from SIM_APDU_Parser.core.models import MsgType

_REGISTRY: Dict[tuple, Type] = {}

def register(msg_type: MsgType, key: str):
    def deco(cls):
        _REGISTRY[(msg_type, key.upper())] = cls
        return cls
    return deco

def resolve(msg_type: MsgType, key: str):
    return _REGISTRY.get((msg_type, key.upper()))
