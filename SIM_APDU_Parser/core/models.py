
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class MsgType(str, Enum):
    CAT = "proactive"  # 保持向后兼容，内部仍使用"proactive"
    ESIM = "esim"
    NORMAL_SIM = "normal_sim"
    UNKNOWN = "unknown"

@dataclass
class Message:
    raw: str                     # hex string, no spaces, uppercase
    direction: str               # 'tx' or 'rx'
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Apdu:
    cla: Optional[int] = None
    ins: Optional[int] = None
    p1: Optional[int] = None
    p2: Optional[int] = None
    lc: Optional[int] = None
    le: Optional[int] = None
    data_hex: str = ""           # body without header if applicable

@dataclass
class ParseNode:
    name: str
    value: Optional[str] = None
    children: List["ParseNode"] = field(default_factory=list)
    hint: Optional[str] = None

@dataclass
class ParseResult:
    msg_type: MsgType
    message: Message
    apdu: Optional[Apdu]
    root: Optional[ParseNode]
    title: str                   # text for GUI list
    direction_hint: str          # 'UICC=>TERMINAL', ... for GUI coloring
    tag: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
