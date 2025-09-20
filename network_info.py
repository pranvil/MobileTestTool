#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, re, time, argparse
from datetime import datetime

MAXINT = 2147483647

# ----------------- helpers -----------------
def run_adb(cmd):
    out = subprocess.check_output(["adb", "shell"] + cmd, stderr=subprocess.STDOUT)
    return out.decode("utf-8", errors="ignore")

def to_int(v):
    if v is None: return None
    try:
        iv = int(v)
        return None if iv == MAXINT else iv
    except:
        return None

def val_ok(v):  # 非 None 且不是 MAXINT
    return v is not None

# ----------------- anchors & regex -----------------
SIG_BLOCK_RE = re.compile(r"mSignalStrength=SignalStrength:\{", re.DOTALL)
PRIMARY_RE   = re.compile(r"primary=(?P<primary>\w+)")

LTE_SIG_RE = re.compile(
    r"CellSignalStrengthLte:.*?rssi=(?P<rssi>-?\d+|%d).*?rsrp=(?P<rsrp>-?\d+|%d).*?rsrq=(?P<rsrq>-?\d+|%d).*?rssnr=(?P<rssnr>-?\d+|%d).*?ta=(?P<ta>-?\d+|%d).*?level=(?P<level>-?\d+)"
    % (MAXINT, MAXINT, MAXINT, MAXINT, MAXINT),
    re.DOTALL,
)
NR_SIG_RE  = re.compile(
    r"CellSignalStrengthNr:\{.*?ssRsrp\s*=\s*(?P<ssrsrp>-?\d+|%d).*?ssRsrq\s*=\s*(?P<ssrsrq>-?\d+|%d).*?ssSinr\s*=\s*(?P<sssinr>-?\d+|%d).*?level\s*=\s*(?P<level>-?\d+)"
    % (MAXINT, MAXINT, MAXINT),
    re.DOTALL,
)

LTE_ID_RE = re.compile(
    r"CellIdentityLte:\{.*?mPci=(?P<pci>\d+).*?mTac=(?P<tac>\d+).*?mEarfcn=(?P<earfcn>\d+).*?mBands=\[(?P<bands>[^\]]*)\].*?mMcc=(?P<mcc>\d+).*?mMnc=(?P<mnc>\d+)",
    re.DOTALL,
)
NR_ID_RE = re.compile(
    r"CellIdentityNr:\{.*?mPci\s*=\s*(?P<pci>\d+).*?mTac\s*=\s*(?P<tac>\d+).*?mNrArfcn\s*=\s*(?P<nrarfcn>\d+).*?mBands\s*=\s*\[(?P<bands>[^\]]*)\].*?mMcc\s*=\s*(?P<mcc>null|\d+).*?mMnc\s*=\s*(?P<mnc>null|\d+).*?mNci\s*=\s*(?P<nci>\d+)",
    re.DOTALL,
)
REG_FLAG_RE = re.compile(r"mRegistered=(?P<yesno>YES|NO)")

# PhysicalChannelConfigs: 两种样式：列表或单对象
PCC_LIST_RE = re.compile(r"mPhysicalChannelConfigs=\[(?P<body>.*?)\]", re.DOTALL)
PCC_OBJ_RE  = re.compile(r"PhysicalChannelConfig\{(?P<obj>.*?)\}", re.DOTALL)
# 字段抓取
PCC_KV = {
    "connection": re.compile(r"(?:mConnectionStatus|connectionStatus)=([^,}]+)"),
    "rat":        re.compile(r"(?:mNetworkType|rat)=([^,}]+)", re.IGNORECASE),
    "band":       re.compile(r"(?:mBand|band)=([^,}]+)"),
    "pci":        re.compile(r"(?:mPhysicalCellId|pci)=(\-?\d+)"),
    "dl_ch":      re.compile(r"(?:mDownlinkChannelNumber|channelNumber|earfcn|nrarfcn)=(\-?\d+)"),
    "ul_ch":      re.compile(r"(?:mUplinkChannelNumber)=(\-?\d+)"),
    "dl_freq":    re.compile(r"(?:mDownlinkFrequency)=(\-?\d+)"),
    "ul_freq":    re.compile(r"(?:mUplinkFrequency)=(\-?\d+)"),
    "dl_bw_khz":  re.compile(r"(?:mCellBandwidthDownlinkKhz|downlinkBandwidthKhz)=(\-?\d+)"),
    "ul_bw_khz":  re.compile(r"(?:mCellBandwidthUplinkKhz|uplinkBandwidthKhz)=(\-?\d+)"),
}

# ----------------- segment & slicing -----------------
def split_segments(raw):
    """按每个 mSignalStrength 起点分段。"""
    starts = [m.start() for m in SIG_BLOCK_RE.finditer(raw)]
    if not starts:
        return []
    bounds = []
    for i, s in enumerate(starts):
        e = starts[i+1] if i+1 < len(starts) else len(raw)
        bounds.append(raw[s:e])
    return bounds  # 每个就是一个 SIM 段的大文本

def find_first(regex, text):
    m = regex.search(text)
    return m

def parse_signal_from_segment(seg):
    """从段内解析 mSignalStrength 的 LTE/NR 数值 + primary。"""
    primary = None
    mpri = PRIMARY_RE.search(seg)
    if mpri: primary = mpri.group("primary")

    lte = nr = None
    ml = LTE_SIG_RE.search(seg)
    if ml:
        lte = {k: to_int(ml.group(k)) for k in ("rssi","rsrp","rsrq","rssnr","ta","level")}
        if not any(val_ok(v) for v in lte.values()): lte = None

    mn = NR_SIG_RE.search(seg)
    if mn:
        nr = { "ssRsrp": to_int(mn.group("ssrsrp")),
               "ssRsrq": to_int(mn.group("ssrsrq")),
               "ssSinr": to_int(mn.group("sssinr")),
               "level":  to_int(mn.group("level")) }
        if not any(val_ok(v) for v in (nr["ssRsrp"], nr["ssRsrq"], nr["ssSinr"])): nr = None

    return {"primary": primary, "lte": lte, "nr": nr}

def iter_cellinfo_chunks(seg, kind="NR"):
    """粗切片：从 'CellInfoNr:{' 或 'CellInfoLte:{' 到下一个 CellInfo/Signal/Carrier 标记。"""
    start_tag = "CellInfoNr:{" if kind == "NR" else "CellInfoLte:{"
    i = 0
    while True:
        s = seg.find(start_tag, i)
        if s < 0: break
        # 下一个边界
        nexts = []
        for tag in ("CellInfoNr:{", "CellInfoLte:{", "mCarrierRoaming", "mSignalStrength=", "mPhysicalChannelConfigs="):
            p = seg.find(tag, s+1)
            if p != -1:
                nexts.append(p)
        e = min(nexts) if nexts else len(seg)
        yield seg[s:e]
        i = s + 1

def parse_cellinfo_from_segment(seg):
    """返回 (best_nr, best_lte)，优先 registered=YES；否则按 RSRP 最大。"""
    nrs, ltes = [], []

    for chunk in iter_cellinfo_chunks(seg, "NR"):
        reg = REG_FLAG_RE.search(chunk)
        idm = NR_ID_RE.search(chunk)
        sgm = NR_SIG_RE.search(chunk)
        entry = {
            "type": "NR",
            "registered": (reg and reg.group("yesno")=="YES"),
            "pci":  to_int(idm.group("pci")) if idm else None,
            "tac":  to_int(idm.group("tac")) if idm else None,
            "nrarfcn": to_int(idm.group("nrarfcn")) if idm else None,
            "bands": [b.strip() for b in (idm.group("bands") if idm else "").split(",")] if idm else [],
            "mcc": None if not idm or idm.group("mcc") in (None,"null") else idm.group("mcc"),
            "mnc": None if not idm or idm.group("mnc") in (None,"null") else idm.group("mnc"),
            "nci":  to_int(idm.group("nci")) if idm else None,
            "ssRsrp": to_int(sgm.group("ssrsrp")) if sgm else None,
            "ssRsrq": to_int(sgm.group("ssrsrq")) if sgm else None,
            "ssSinr": to_int(sgm.group("sssinr")) if sgm else None,
            "level":  to_int(sgm.group("level")) if sgm else None,
        }
        if any(val_ok(entry[k]) for k in ("ssRsrp","ssRsrq","ssSinr")):
            nrs.append(entry)

    for chunk in iter_cellinfo_chunks(seg, "LTE"):
        reg = REG_FLAG_RE.search(chunk)
        idm = LTE_ID_RE.search(chunk)
        sgm = LTE_SIG_RE.search(chunk)
        entry = {
            "type": "LTE",
            "registered": (reg and reg.group("yesno")=="YES"),
            "pci":  to_int(idm.group("pci")) if idm else None,
            "tac":  to_int(idm.group("tac")) if idm else None,
            "earfcn": to_int(idm.group("earfcn")) if idm else None,
            "bands": [b.strip() for b in (idm.group("bands") if idm else "").split(",")] if idm else [],
            "mcc": idm.group("mcc") if idm else None,
            "mnc": idm.group("mnc") if idm else None,
            "rssi":  to_int(sgm.group("rssi")) if sgm else None,
            "rsrp":  to_int(sgm.group("rsrp")) if sgm else None,
            "rsrq":  to_int(sgm.group("rsrq")) if sgm else None,
            "rssnr": to_int(sgm.group("rssnr")) if sgm else None,
            "ta":    to_int(sgm.group("ta")) if sgm else None,
            "level": to_int(sgm.group("level")) if sgm else None,
        }
        if any(val_ok(entry[k]) for k in ("rsrp","rsrq","rssnr","rssi")):
            ltes.append(entry)

    def pick_best(items, is_nr):
        regs = [x for x in items if x.get("registered")]
        if regs: return regs[0]
        key = (lambda x: x.get("ssRsrp")) if is_nr else (lambda x: x.get("rsrp"))
        cand = [x for x in items if val_ok(key(x))]
        if cand:
            return sorted(cand, key=key, reverse=True)[0]
        return items[0] if items else None

    return pick_best(nrs, True), pick_best(ltes, False)

# ----------------- PCC parsing -----------------
def parse_pcc_objects(text):
    """全局/段内都可用：解析任何出现的 PCC 对象。"""
    objs = []
    # 列表样式
    for m in PCC_LIST_RE.finditer(text):
        body = m.group("body")
        # 逐个 { ... }
        for jm in re.finditer(r"\{(.*?)\}", body, re.DOTALL):
            objs.append(jm.group(1))
    # 单对象样式
    for m in PCC_OBJ_RE.finditer(text):
        objs.append(m.group("obj"))

    parsed = []
    for obj in objs:
        item = {}
        for k, rx in PCC_KV.items():
            mm = rx.search(obj)
            if not mm: 
                item[k] = None
            else:
                val = mm.group(1)
                item[k] = to_int(val) if k in ("pci","dl_ch","ul_ch","dl_freq","ul_freq","dl_bw_khz","ul_bw_khz") else val
        parsed.append(item)
    return parsed

def pick_pcc_for_segment(seg_text, global_pcc, best_ci):
    """优先用段内 PCC；否则根据 PCI/频道/Band 从全局 PCC 匹配。"""
    seg_pcc = parse_pcc_objects(seg_text)
    if seg_pcc:
        return seg_pcc

    if not best_ci:
        return []

    want_rat = "NR" if best_ci["type"]=="NR" else "LTE"
    want_pci = best_ci.get("pci")
    want_ch  = best_ci.get("nrarfcn") if best_ci["type"]=="NR" else best_ci.get("earfcn")
    want_band = None
    if best_ci.get("bands"):
        # 取第一个 band 值（如 ["2"] / ["71"]）
        try:
            want_band = best_ci["bands"][0]
        except:
            pass

    cand = []
    for p in global_pcc:
        rat = (p.get("rat") or "").upper()
        if want_rat not in rat:
            continue
        ok = False
        if val_ok(want_pci) and val_ok(p.get("pci")) and want_pci == p["pci"]:
            ok = True
        if not ok and val_ok(want_ch) and val_ok(p.get("dl_ch")) and want_ch == p["dl_ch"]:
            ok = True
        if not ok and want_band and p.get("band") and want_band in str(p["band"]):
            ok = True
        if ok:
            cand.append(p)
    return cand

# ----------------- Wi-Fi -----------------
WIFI_BLOCK_RES = [
    re.compile(r"mWifiInfo\s*=\s*WifiInfo\{(?P<info>.*?)\}", re.DOTALL),
    re.compile(r"WifiInfo\{(?P<info>.*?)\}", re.DOTALL),
]
SSID_RE_LIST = [
    re.compile(r'SSID:\s*"(?P<ssid>[^"]*)"'),
    re.compile(r"SSID:\s*(?P<ssid><unknown ssid>|[^\s,}]+)"),
    re.compile(r"mSSID:\s*SSID\{(?P<ssid>[^}]*)\}"),
]
RSSI_RE_LIST = [re.compile(r"RSSI:\s*(?P<rssi>-?\d+)"), re.compile(r"mRssi=\s*(?P<rssi>-?\d+)")]
BSSID_RE   = re.compile(r"BSSID:\s*(?P<bssid>[0-9a-fA-F:]{11,})")
LINKSPD_RE = re.compile(r"LinkSpeed:\s*(?P<ls>\d+)\s*Mbps")
FREQ_RE    = re.compile(r"Frequency:\s*(?P<freq>\d+)")
SUPPL_RE   = re.compile(r"Supplicant state:\s*(?P<state>\w+)", re.IGNORECASE)

def parse_wifi(raw_wifi):
    txt = None
    for pat in WIFI_BLOCK_RES:
        m = pat.search(raw_wifi)
        if m: txt = m.group("info"); break
    if not txt: txt = raw_wifi

    def first_match(text, pats):
        for p in pats:
            m = p.search(text)
            if m: return m.groupdict()
        return {}

    ssid_m = first_match(txt, SSID_RE_LIST)
    rssi_m = first_match(txt, RSSI_RE_LIST)
    bssid_m= BSSID_RE.search(txt) or {}
    link_m = LINKSPD_RE.search(txt) or {}
    freq_m = FREQ_RE.search(txt) or {}
    supp_m = SUPPL_RE.search(txt) or {}

    ssid = (ssid_m.get("ssid") if ssid_m else None)
    if ssid == "<unknown ssid>": ssid = None

    wifi = {
        "ssid": ssid,
        "rssi": to_int((rssi_m.get("rssi") if rssi_m else None)),
        "bssid": (bssid_m.group("bssid") if hasattr(bssid_m,"group") else None),
        "linkMbps": to_int((link_m.group("ls") if hasattr(link_m,"group") else None)),
        "freqMHz": to_int((freq_m.group("freq") if hasattr(freq_m,"group") else None)),
        "state": (supp_m.group("state") if hasattr(supp_m,"group") else None),
    }
    band = None
    if wifi["freqMHz"]:
        f = wifi["freqMHz"]
        if 2400 <= f < 2500: band = "2.4GHz"
        elif 4900 <= f < 5900: band = "5GHz"
        elif 5925 <= f < 7125: band = "6GHz"
    wifi["band"] = band
    wifi["connected"] = (wifi["ssid"] is not None) and (wifi["rssi"] is not None)
    return wifi

# ----------------- pretty print -----------------
def render_plmn(mcc, mnc):
    if not mcc or not mnc: return None
    return f"{mcc}{mnc}"

def fmt_pcc(p):
    if not p: return "N/A"
    parts = []
    if p.get("rat"): parts.append(p["rat"])
    if p.get("band"): parts.append(f"Band={p['band']}")
    if val_ok(p.get("dl_bw_khz")): parts.append(f"DL_BW={p['dl_bw_khz']/1000:.0f}MHz")
    if val_ok(p.get("ul_bw_khz")): parts.append(f"UL_BW={p['ul_bw_khz']/1000:.0f}MHz")
    if val_ok(p.get("dl_ch")): parts.append(f"DL_CH={p['dl_ch']}")
    if val_ok(p.get("ul_ch")) and p['ul_ch']>0: parts.append(f"UL_CH={p['ul_ch']}")
    if val_ok(p.get("pci")): parts.append(f"PCI={p['pci']}")
    if val_ok(p.get("dl_freq")): parts.append(f"DL_Freq={p['dl_freq']}kHz")
    return ", ".join(parts) if parts else "N/A"

def print_cell(prefix, show, meta, pcc_list):
    print(f"{prefix}Source:", show.get("source","none"))
    if show.get("primary") is not None:
        print(f"{prefix}Primary:", show["primary"])

    def kv(title, kvd):
        if not kvd:
            print(f"{prefix}{title}: N/A"); return
        keys = ("rssi","rsrp","rsrq","rssnr","ta","level","ssRsrp","ssRsrq","ssSinr")
        pairs = [f"{k}={kvd[k]}" for k in keys if k in kvd and val_ok(kvd[k])]
        print(f"{prefix}{title}: " + (", ".join(pairs) if pairs else "N/A"))

    kv("LTE", show.get("lte"))
    kv("NR",  show.get("nr"))

    if meta:
        base = [f"type={meta['type']}"]
        if meta.get("registered") is not None:
            base.append("registered="+("YES" if meta["registered"] else "NO"))
        for k in ("pci","tac","earfcn","nrarfcn","mcc","mnc","nci"):
            if val_ok(meta.get(k)): base.append(f"{k}={meta[k]}")
        if meta.get("bands"): base.append("bands=[" + ",".join(meta["bands"]) + "]")
        plmn = render_plmn(meta.get("mcc"), meta.get("mnc"))
        if plmn: base.append(f"PLMN={plmn}")
        print(f"{prefix}CellInfo: " + ", ".join(base))

    if pcc_list:
        prim = [p for p in pcc_list if str(p.get("connection","")).lower().startswith("primary")]
        secs = [p for p in pcc_list if str(p.get("connection","")).lower().startswith("secondary")]
        if prim:
            print(f"{prefix}PhyChan Primary: {fmt_pcc(prim[0])}")
        if secs:
            print(f"{prefix}PhyChan CA     : " + " | ".join(fmt_pcc(s) for s in secs))

# ----------------- snapshot -----------------
def snapshot():
    tel = run_adb(["dumpsys", "telephony.registry"])
    wifi_raw = run_adb(["dumpsys", "wifi"])
    wifi = parse_wifi(wifi_raw)

    segments = split_segments(tel)
    global_pcc = parse_pcc_objects(tel)

    print("==== Telephony + Wi-Fi Snapshot ====")
    print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if not segments:
        print("No mSignalStrength found.")
    else:
        for i, seg in enumerate(segments, 1):
            sig = parse_signal_from_segment(seg)
            best_nr, best_lte = parse_cellinfo_from_segment(seg)

            used_source = "none"
            show = {"primary": sig.get("primary")}
            if sig.get("nr") and any(val_ok(sig["nr"].get(k)) for k in ("ssRsrp","ssRsrq","ssSinr")):
                show["nr"] = sig["nr"]; show["lte"] = sig.get("lte"); used_source = "mSignalStrength"
            elif sig.get("lte") and any(val_ok(sig["lte"].get(k)) for k in ("rsrp","rsrq","rssnr","rssi")):
                show["lte"] = sig["lte"]; show["nr"]  = sig.get("nr");  used_source = "mSignalStrength"
            elif best_nr or best_lte:
                # 回退到 CellInfo
                used_source = "mCellInfo"
                show["nr"]  = {"ssRsrp": best_nr.get("ssRsrp"), "ssRsrq": best_nr.get("ssRsrq"),
                               "ssSinr": best_nr.get("ssSinr"), "level": best_nr.get("level")} if best_nr else None
                show["lte"] = {"rssi":  best_lte.get("rssi"), "rsrp": best_lte.get("rsrp"),
                               "rsrq":  best_lte.get("rsrq"), "rssnr":best_lte.get("rssnr"),
                               "ta":    best_lte.get("ta"),   "level":best_lte.get("level")} if best_lte else None
            show["source"] = used_source

            # 选择 meta（优先 NR，否则 LTE）
            meta = best_nr if best_nr else best_lte

            # 选 PCC：段内优先；否则用全局 PCC 按 PCI/频点/带匹配
            pcc_list = pick_pcc_for_segment(seg, global_pcc, meta)

            print(f"\n-- SIM#{i} --")
            print_cell("  ", show, meta, pcc_list)

    print("\nWi-Fi:")
    if wifi.get("connected"):
        parts = []
        if wifi.get("ssid"):  parts.append(f'SSID="{wifi["ssid"]}"')
        if wifi.get("bssid"): parts.append(f'BSSID={wifi["bssid"]}')
        if val_ok(wifi.get("rssi")): parts.append(f'RSSI={wifi["rssi"]} dBm')
        if val_ok(wifi.get("linkMbps")): parts.append(f'Link={wifi["linkMbps"]} Mbps')
        if val_ok(wifi.get("freqMHz")):
            band = f' ({wifi["band"]})' if wifi.get("band") else ""
            parts.append(f'Freq={wifi["freqMHz"]} MHz{band}')
        if wifi.get("state"): parts.append(f'State={wifi["state"]}')
        print("  " + ", ".join(parts))
    else:
        state = wifi.get("state")
        print("  Not connected." + (f" State={state}" if state else ""))
    print("-----------------------------------")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Robust Multi-SIM LTE/NR + PLMN + Band/EARFCN/NRARFCN + PCI + PCC + Wi-Fi")
    ap.add_argument("-w","--watch", type=float, default=0.0, help="watch seconds, e.g. -w 2")
    args = ap.parse_args()
    if args.watch and args.watch > 0:
        try:
            while True:
                snapshot(); time.sleep(args.watch)
        except KeyboardInterrupt:
            pass
    else:
        snapshot()
