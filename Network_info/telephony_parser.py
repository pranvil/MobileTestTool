#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telephony解析器 - 纯解析模块
按照 min_parser_refactor.json 规范实现，≤220行
"""

import re
from typing import Dict, List, Optional, Any

# 列定义
COLS = [
    "SIM", "CC", "RAT", "BAND", "DL_ARFCN", "UL_ARFCN", "PCI", 
    "RSRP", "RSRQ", "SINR", "RSSI", "BW_DL", "BW_UL", "CA_ENDC", "CQI", "NOTE"
]

MAXINT = 2147483647

def _to_int(value: Any) -> Optional[int]:
    """转换为整数，处理MAXINT"""
    if value is None:
        return None
    try:
        iv = int(value)
        return None if iv == MAXINT else iv
    except:
        return None

def _extract_key_values(text: str) -> Dict[str, str]:
    """通用键值对提取器：(\\w+)=([^,}]+)"""
    pattern = r'(\w+)=([^,}]+)'
    matches = re.findall(pattern, text)
    return {k: v.strip() for k, v in matches}

def _segment_by_phone_or_physical(raw: str) -> List[str]:
    """分段：先Phone Id=，无则用最后一个非空PhysicalChannel块"""
    # 1) 尝试Phone Id分段
    phone_matches = list(re.finditer(r'Phone Id=(\d+)', raw))
    if phone_matches:
        sections = []
        for i, match in enumerate(phone_matches):
            start_pos = match.start()
            end_pos = phone_matches[i + 1].start() if i + 1 < len(phone_matches) else len(raw)
            sections.append(raw[start_pos:end_pos])
        return sections
    
    # 2) 备用方案：PhysicalChannel块分段
    blocks = []
    for m in re.finditer(r"mPhysicalChannelConfigs=\[(.*?)\]", raw, re.DOTALL):
        content = m.group(1).strip()
        if content:  # 只保留非空块
            blocks.append("mPhysicalChannelConfigs=[" + content + "]")
    
    # 取最后2个非空块作为SIM1/SIM2
    return blocks[-2:] if len(blocks) >= 2 else blocks[:1] if blocks else [raw]

def _parse_physical_channels(section: str) -> List[Dict]:
    """解析PhysicalChannel配置"""
    channels = []
    
    # 使用更强大的正则表达式匹配完整的PhysicalChannelConfigs块
    pattern = r"mPhysicalChannelConfigs=\[(.*?)\](?=\s*mLinkCapacityEstimateList|\s*mECBMReason|\s*$)"
    match = re.search(pattern, section, re.DOTALL)
    if not match:
        return channels
    
    content = match.group(1).strip()
    if not content:
        return channels
    
    # 手动解析配置块，处理嵌套的方括号
    start_pos = 0
    while True:
        start = content.find('{', start_pos)
        if start == -1:
            break
        
        # 找到匹配的结束位置
        depth = 0
        end_pos = start
        for i, char in enumerate(content[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > start:
            block = content[start:end_pos]
            start_pos = end_pos
            kv = _extract_key_values(block)
            if 'mNetworkType' in kv and 'mBand' in kv:
                channel = {
                    'connection_status': kv.get('mConnectionStatus', ''),
                    'rat': kv.get('mNetworkType', ''),
                    'band': _to_int(kv.get('mBand')),
                    'dl_arfcn': _to_int(kv.get('mDownlinkChannelNumber')),
                    'ul_arfcn': _to_int(kv.get('mUplinkChannelNumber')),
                    'pci': _to_int(kv.get('mPhysicalCellId')),
                    'bw_dl': _to_int(kv.get('mCellBandwidthDownlinkKhz', 0)) // 1000 if kv.get('mCellBandwidthDownlinkKhz') else 0,
                    'bw_ul': _to_int(kv.get('mCellBandwidthUplinkKhz', 0)) // 1000 if kv.get('mCellBandwidthUplinkKhz') else 0,
                }
                channels.append(channel)
        else:
            break
    
    return channels

def _parse_signal_strength(section: str) -> Dict:
    """解析信号强度"""
    signal_data = {'lte': {}, 'nr': {}}
    
    # 查找SignalStrength块
    signal_match = re.search(r"mSignalStrength=SignalStrength:\{(.*?)\}", section, re.DOTALL)
    if not signal_match:
        return signal_data
    
    signal_text = signal_match.group(1)
    
    # LTE信号解析 - 使用简化的字符串搜索
    if "mLte=CellSignalStrengthLte:" in signal_text:
        # 提取LTE信号强度
        rssi_match = re.search(r"rssi=(-?\d+)", signal_text)
        rsrp_match = re.search(r"rsrp=(-?\d+)", signal_text)
        rsrq_match = re.search(r"rsrq=(-?\d+)", signal_text)
        rssnr_match = re.search(r"rssnr=(-?\d+)", signal_text)
        cqi_match = re.search(r"cqi=(-?\d+)", signal_text)
        
        if rsrp_match and _to_int(rsrp_match.group(1)):  # 只使用有效信号
            signal_data['lte'] = {
                'rsrp': _to_int(rsrp_match.group(1)),
                'rsrq': _to_int(rsrq_match.group(1)) if rsrq_match else None,
                'rssnr': _to_int(rssnr_match.group(1)) if rssnr_match else None,
                'rssi': _to_int(rssi_match.group(1)) if rssi_match else None,
                'cqi': _to_int(cqi_match.group(1)) if cqi_match else None,
            }
    
    # NR信号解析 - 使用简化的字符串搜索
    if "mNr=CellSignalStrengthNr:" in signal_text:
        # 提取NR信号强度
        ss_rsrp_match = re.search(r"ssRsrp\s*=\s*(-?\d+)", signal_text)
        ss_rsrq_match = re.search(r"ssRsrq\s*=\s*(-?\d+)", signal_text)
        ss_sinr_match = re.search(r"ssSinr\s*=\s*(-?\d+)", signal_text)
        
        if ss_rsrp_match and _to_int(ss_rsrp_match.group(1)):  # 只使用有效信号
            signal_data['nr'] = {
                'ss_rsrp': _to_int(ss_rsrp_match.group(1)),
                'ss_rsrq': _to_int(ss_rsrq_match.group(1)) if ss_rsrq_match else None,
                'ss_sinr': _to_int(ss_sinr_match.group(1)) if ss_sinr_match else None,
            }
    
    return signal_data

def _parse_cellinfo_fallback(section: str) -> List[Dict]:
    """解析CellInfo（IDLE情况回退）"""
    cell_infos = []
    
    # 查找CellInfo块
    cellinfo_match = re.search(r"mCellInfo=\[(.*)\]", section, re.DOTALL)
    if not cellinfo_match:
        return cell_infos
    
    cellinfo_text = cellinfo_match.group(1)
    
    # LTE CellInfo - 解析所有LTE小区
    lte_matches = re.finditer(r"CellInfoLte:\{(.*?)\}", cellinfo_text, re.DOTALL)
    for lte_match in lte_matches:
        lte_text = lte_match.group(1)
        # 使用简化的字符串搜索方法
        registered_match = re.search(r"mRegistered=(\w+)", lte_text)
        pci_match = re.search(r"mPci=(\d+)", lte_text)
        earfcn_match = re.search(r"mEarfcn=(\d+)", lte_text)
        bands_match = re.search(r"mBands=\[([^\]]*)\]", lte_text)
        
        if pci_match and earfcn_match:
            cell_info = {
                'type': 'LTE',
                'registered': registered_match.group(1) == 'YES' if registered_match else False,
                'pci': _to_int(pci_match.group(1)),
                'earfcn': _to_int(earfcn_match.group(1)),
                'bands': [b.strip() for b in bands_match.group(1).split(',')] if bands_match else [],
            }
            cell_infos.append(cell_info)
    
    # NR CellInfo - 解析所有NR小区
    nr_matches = re.finditer(r"CellInfoNr:\{(.*?)\}", cellinfo_text, re.DOTALL)
    for nr_match in nr_matches:
        nr_text = nr_match.group(1)
        # 使用简化的字符串搜索方法
        registered_match = re.search(r"mRegistered=(\w+)", nr_text)
        pci_match = re.search(r"mPci\s*=\s*(\d+)", nr_text)
        nr_arfcn_match = re.search(r"mNrArfcn\s*=\s*(\d+)", nr_text)
        bands_match = re.search(r"mBands\s*=\s*\[([^\]]*)\]", nr_text)
        
        if pci_match and nr_arfcn_match:
            cell_info = {
                'type': 'NR',
                'registered': registered_match.group(1) == 'YES' if registered_match else False,
                'pci': _to_int(pci_match.group(1)),
                'nr_arfcn': _to_int(nr_arfcn_match.group(1)),
                'bands': [b.strip() for b in bands_match.group(1).split(',')] if bands_match else [],
            }
            cell_infos.append(cell_info)
    
    return cell_infos

def _build_ca_endc_summary(lte_channels: List[Dict], nr_channels: List[Dict]) -> str:
    """构建CA/ENDC摘要"""
    lte_count = len(lte_channels)
    nr_count = len(nr_channels)
    
    if lte_count > 0 and nr_count > 0:
        # ENDC情况
        lte_bands = [f"b{c['band']}" for c in lte_channels if c.get('band')]
        nr_bands = [f"n{c['band']}" for c in nr_channels if c.get('band')]
        band_str = "_".join(sorted(lte_bands + nr_bands))
        return f"EN_DC_{band_str}"
    elif lte_count > 1:
        # LTE CA
        lte_bands = [f"b{c['band']}" for c in lte_channels if c.get('band')]
        band_str = "_".join(sorted(lte_bands))
        return f"CA_{band_str}"
    elif lte_count == 1:
        # 单LTE
        band = lte_channels[0].get('band')
        return f"LTE_b{band}" if band else "LTE_b?"
    elif nr_count > 1:
        # NR CA
        nr_bands = [f"n{c['band']}" for c in nr_channels if c.get('band')]
        band_str = "_".join(sorted(nr_bands))
        return f"CA_{band_str}"
    elif nr_count == 1:
        # 单NR
        band = nr_channels[0].get('band')
        return f"NR_n{band}" if band else "NR_n?"
    else:
        return "No active carriers"

def _build_rows(channels: List[Dict], signal_data: Dict, cell_infos: List[Dict], sim_name: str) -> List[Dict]:
    """构建行数据"""
    rows = []
    
    # 如果没有PhysicalChannel配置，尝试从CellInfo构建
    if not channels and cell_infos:
        for cell in cell_infos:
            if not cell.get('registered'):
                continue
                
            row = {
                'SIM': sim_name,
                'CC': 'PCC' if cell['type'] == 'LTE' else 'SpCell',
                'RAT': cell['type'],
                'BAND': f"B{cell['bands'][0]}" if cell['type'] == 'LTE' and cell.get('bands') else f"n{cell['bands'][0]}" if cell.get('bands') else '',
                'DL_ARFCN': cell.get('earfcn', 0) if cell['type'] == 'LTE' else cell.get('nr_arfcn', 0),
                'UL_ARFCN': 0,
                'PCI': cell.get('pci', 0),
                'RSRP': None,
                'RSRQ': None,
                'SINR': None,
                'RSSI': None,
                'BW_DL': 0,
                'BW_UL': 0,
                'CA_ENDC': '',
                'CQI': None,
                'NOTE': 'IDLE状态'
            }
            
            # 添加信号强度
            sig_data = signal_data.get('lte' if cell['type'] == 'LTE' else 'nr', {})
            if cell['type'] == 'LTE':
                row.update({
                    'RSRP': sig_data.get('rsrp'),
                    'RSRQ': sig_data.get('rsrq'),
                    'SINR': sig_data.get('rssnr'),
                    'RSSI': sig_data.get('rssi'),
                    'CQI': sig_data.get('cqi'),
                })
            else:
                row.update({
                    'RSRP': sig_data.get('ss_rsrp'),
                    'RSRQ': sig_data.get('ss_rsrq'),
                    'SINR': sig_data.get('ss_sinr'),
                })
            
            rows.append(row)
        return rows
    
    # 分析CA/ENDC配置
    lte_channels = [c for c in channels if c['rat'] == 'LTE']
    nr_channels = [c for c in channels if c['rat'] == 'NR']
    
    # 生成CA/ENDC摘要
    ca_endc_summary = _build_ca_endc_summary(lte_channels, nr_channels)
    
    # 构建载波信息
    # LTE主载波
    primary_lte = next((c for c in lte_channels if c['connection_status'] == 'PrimaryServing'), None)
    if primary_lte:
        row = {
            'SIM': sim_name,
            'CC': 'PCC',
            'RAT': 'LTE',
            'BAND': f"B{primary_lte['band']}",
            'DL_ARFCN': primary_lte['dl_arfcn'],
            'UL_ARFCN': primary_lte['ul_arfcn'],
            'PCI': primary_lte['pci'],
            'BW_DL': primary_lte['bw_dl'],
            'BW_UL': primary_lte['bw_ul'],
            'CA_ENDC': ca_endc_summary,
            'NOTE': 'Anchor LTE'
        }
        
        # 添加信号强度
        if signal_data.get('lte'):
            lte_sig = signal_data['lte']
            row.update({
                'RSRP': lte_sig.get('rsrp'),
                'RSRQ': lte_sig.get('rsrq'),
                'SINR': lte_sig.get('rssnr'),
                'RSSI': lte_sig.get('rssi'),
                'CQI': lte_sig.get('cqi'),
            })
        
        rows.append(row)
        
        # LTE辅载波
        scc_count = 1
        for channel in lte_channels:
            if channel['connection_status'] == 'SecondaryServing':
                row = {
                    'SIM': '',  # 副载波SIM列留空
                    'CC': f"SCC{scc_count}",
                    'RAT': 'LTE',
                    'BAND': f"B{channel['band']}",
                    'DL_ARFCN': channel['dl_arfcn'],
                    'UL_ARFCN': channel['ul_arfcn'],
                    'PCI': channel['pci'],
                    'BW_DL': channel['bw_dl'],
                    'BW_UL': channel['bw_ul'],
                    'CA_ENDC': ca_endc_summary,
                    'NOTE': 'DL-only' if channel['ul_arfcn'] == 0 else ''
                }
                rows.append(row)
                scc_count += 1
    
    # NR载波
    if nr_channels:
        primary_nr = max(nr_channels, key=lambda x: x['bw_dl'])
        
        row = {
            'SIM': sim_name,
            'CC': 'SpCell' if primary_lte else 'PCell',
            'RAT': 'NR',
            'BAND': f"n{primary_nr['band']}",
            'DL_ARFCN': primary_nr['dl_arfcn'],
            'UL_ARFCN': primary_nr['ul_arfcn'],
            'PCI': primary_nr['pci'],
            'BW_DL': primary_nr['bw_dl'],
            'BW_UL': primary_nr['bw_ul'],
            'CA_ENDC': ca_endc_summary,
            'NOTE': 'Anchor NR' if not primary_lte else ''
        }
        
        # 添加信号强度
        if signal_data.get('nr'):
            nr_sig = signal_data['nr']
            row.update({
                'RSRP': nr_sig.get('ss_rsrp'),
                'RSRQ': nr_sig.get('ss_rsrq'),
                'SINR': nr_sig.get('ss_sinr'),
            })
        
        rows.append(row)
        
        # NR辅载波
        scc_count = 1
        for channel in nr_channels:
            if channel != primary_nr:
                row = {
                    'SIM': '',  # 副载波SIM列留空
                    'CC': f"SCells#{scc_count}" if primary_lte else f"SCC{scc_count}",
                    'RAT': 'NR',
                    'BAND': f"n{channel['band']}",
                    'DL_ARFCN': channel['dl_arfcn'],
                    'UL_ARFCN': channel['ul_arfcn'],
                    'PCI': channel['pci'],
                    'BW_DL': channel['bw_dl'],
                    'BW_UL': channel['bw_ul'],
                    'CA_ENDC': ca_endc_summary,
                    'NOTE': 'DL-only' if channel['ul_arfcn'] == 0 else ''
                }
                rows.append(row)
                scc_count += 1
    
    return rows

def compute_rows_for_registry(raw: str) -> List[Dict]:
    """主入口：计算telephony.registry的行数据"""
    all_rows = []
    
    # 1. 分段
    sections = _segment_by_phone_or_physical(raw)
    
    # 2. 为每个段构建行
    for idx, section in enumerate(sections):
        sim_name = f"SIM{idx + 1}"
        
        # 3. 解析各个组件
        channels = _parse_physical_channels(section)
        signal_data = _parse_signal_strength(section)
        cell_infos = _parse_cellinfo_fallback(section)
        
        # 4. 构建行
        rows = _build_rows(channels, signal_data, cell_infos, sim_name)
        all_rows.extend(rows)
    
    return all_rows
