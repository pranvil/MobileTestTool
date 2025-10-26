
from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid, hex_to_utf8

def _parse_profile_owner(b7_hex: str) -> ParseNode:
    """解析profileOwner字段 (B7标签)"""
    prof_owner = ParseNode(name="Profile Owner (B7)")
    
    # 解析OperatorId SEQUENCE
    tlvs = parse_ber_tlvs(b7_hex)
    for t in tlvs:
        if t.tag == "80":  # mccMnc
            mcc_mnc = t.value_hex
            if len(mcc_mnc) == 6:
                mcc = mcc_mnc[:3]
                mnc = mcc_mnc[3:6]
                val = f"MCC: {mcc}, MNC: {mnc}"
            else:
                val = f"Raw: {mcc_mnc}"
            prof_owner.children.append(ParseNode(name="MCC&MNC (80)", value=val))
        elif t.tag == "81":  # gid1
            prof_owner.children.append(ParseNode(name="GID1 (81)", value=t.value_hex))
        elif t.tag == "82":  # gid2
            prof_owner.children.append(ParseNode(name="GID2 (82)", value=t.value_hex))
        else:
            prof_owner.children.append(ParseNode(name=f"Unknown field {t.tag}", value=t.value_hex))
    
    return prof_owner

def _build_profile_block(e3_hex: str) -> ParseNode:
    prof = ParseNode(name="Profile")
    for st in parse_ber_tlvs(e3_hex):
        name = st.tag
        val = st.value_hex
        if st.tag == "5A":
            name = "ICCID"; val = parse_iccid(val)
        elif st.tag == "4F":
            name = "ISD-P AID"
        elif st.tag == "9F70":
            name = "Profile state"; val = {"00":"Disabled","01":"Enabled"}.get(val, f"Unknown({val})")
        elif st.tag == "90":
            name = "Profile Nickname"; val = hex_to_utf8(val) or st.value_hex
        elif st.tag == "91":
            name = "Service provider name"; val = hex_to_utf8(val) or st.value_hex
        elif st.tag == "92":
            name = "Profile name"; val = hex_to_utf8(val) or st.value_hex
        elif st.tag == "95":
            name = "Profile Class"; val = {"00":"test","01":"provisioning","02":"operational"}.get(val, f"Unknown({val})")
        elif st.tag == "B7":
            # 解析profileOwner字段
            prof_owner_node = _parse_profile_owner(st.value_hex)
            prof.children.append(prof_owner_node)
            continue
        prof.children.append(ParseNode(name=name, value=val))
    return prof

def _try_response_profiles(hexv: str) -> ParseNode|None:
    # Look for profiles under E3, possibly wrapped by A0/A1 etc.
    # Depth 0
    tlvs = parse_ber_tlvs(hexv)
    e3_blocks = [t for t in tlvs if t.tag == "E3"]
    if e3_blocks:
        root = ParseNode(name="BF2D: Profile Info List")
        for i, t in enumerate(e3_blocks, 1):
            prof = _build_profile_block(t.value_hex)
            prof.name = f"Profile {i}"
            root.children.append(prof)
        return root
    # Depth 1 containers
    for t in tlvs:
        if t.tag in ("A0","A1","E0","E1","61","30"):
            inner = parse_ber_tlvs(t.value_hex)
            e3_blocks = [x for x in inner if x.tag == "E3"]
            if e3_blocks:
                root = ParseNode(name="BF2D: Profile Info List")
                for i, x in enumerate(e3_blocks, 1):
                    prof = _build_profile_block(x.value_hex)
                    prof.name = f"Profile {i}"
                    root.children.append(prof)
                return root
    return None

def _decode_taglist_hex(taglist_hex: str):
    s = taglist_hex.upper().replace(" ", "")
    idx = 0; n = len(s); out = []
    
    # Tag meaning mapping
    tag_meaning_map = {
        "5A": "ICCID",
        "4F": "ISD-P AID",
        "9F70": "Profile state",
        "90": "profileNickname", 
        "91": "serviceProviderName",
        "92": "profileName",
        "93": "iconType",
        "94": "icon",
        "95": "profileClass",
        "B6": "notificationConfigurationInfo",
        "B7": "profileOwner",
        "B8": "dpProprietaryData",
        "99": "profilePolicyRules",
        "BF22": "serviceSpecificData",
        "BA": "rpmConfiguration",
        "9B": "hriServerAddress",
        "BC": "lprConfiguration",
        "BD": "enterpriseConfiguration",
        "9F1F": "serviceDescription",
        "BF20": "deviceChangeConfiguration",
        "9F24": "enabledOnESimPort",
        "9F25": "profileSize",
        "BF76": "BF76 (unknown/vendor-specific)",
    }
    
    while idx < n:
        if idx+2>n: break
        t1 = s[idx:idx+2]; idx += 2
        if t1 in ("9F","BF","5F","7F") and idx+2<=n:
            t2 = s[idx:idx+2]; idx += 2
            tag = t1+t2
        else:
            tag = t1
        meaning = tag_meaning_map.get(tag, "Unknown")
        out.append((tag, meaning))
    return out

@register(MsgType.ESIM, "BF2D")
class BF2DParser:
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        # Try response style first (E3 profile blocks)
        resp = _try_response_profiles(payload_hex)
        if resp is not None:
            return resp

        # Request style: Tag List / searchCriteria
        root = ParseNode(name="BF2D: ProfileInfoListRequest")
        tlvs = parse_ber_tlvs(payload_hex)
        for t in tlvs:
            if t.tag == "A0":
                # searchCriteria [0] CHOICE
                search_criteria = ParseNode(name="Search Criteria (A0)")
                sub_tlvs = parse_ber_tlvs(t.value_hex)
                for sub_t in sub_tlvs:
                    if sub_t.tag == "4F":
                        search_criteria.children.append(ParseNode(name="ISD-P AID (4F)", value=sub_t.value_hex))
                    elif sub_t.tag == "5A":
                        search_criteria.children.append(ParseNode(name="ICCID (5A)", value=parse_iccid(sub_t.value_hex)))
                    elif sub_t.tag == "95":
                        profile_class = {"00":"test","01":"provisioning","02":"operational"}.get(sub_t.value_hex, f"Unknown({sub_t.value_hex})")
                        search_criteria.children.append(ParseNode(name="Profile Class (95)", value=profile_class))
                    else:
                        search_criteria.children.append(ParseNode(name=f"Unknown search criteria {sub_t.tag}", value=f"len={sub_t.length}", hint=sub_t.value_hex[:120]))
                root.children.append(search_criteria)
            elif t.tag == "5C":
                # tagList [APPLICATION 28]
                tag_pairs = _decode_taglist_hex(t.value_hex)
                tag_list = [f"{tag}({meaning})" for tag, meaning in tag_pairs]
                sub = ParseNode(name="Requested Tags (5C)", value=", ".join(tag_list))
                for tag, meaning in tag_pairs:
                    sub.children.append(ParseNode(name=f"Tag {tag}", value=meaning))
                root.children.append(sub)
            else:
                root.children.append(ParseNode(name=f"Unknown TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        if not tlvs and payload_hex == "00":
            root.hint = "Default request (BF2D 00)"
        return root
