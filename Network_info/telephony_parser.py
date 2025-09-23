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

def _parse_phone_metadata(raw: str) -> Dict[str, Any]:
    """解析Phone元数据：活跃SIM判断所需的关键字段"""
    metadata = {
        'active_data_sub_id': None,
        'default_sub_id': None,
        'default_phone_id': None,
        'phone_states': {}  # {phone_id: {radio_power, service_state, network, data_state, has_channels}}
    }
    
    # 解析全局字段
    active_data_match = re.search(r'mActiveDataSubId=(\d+)', raw)
    if active_data_match:
        metadata['active_data_sub_id'] = int(active_data_match.group(1))
    
    default_sub_match = re.search(r'mDefaultSubId=(\d+)', raw)
    if default_sub_match:
        metadata['default_sub_id'] = int(default_sub_match.group(1))
    
    default_phone_match = re.search(r'mDefaultPhoneId=(\d+)', raw)
    if default_phone_match:
        metadata['default_phone_id'] = int(default_phone_match.group(1))
    
    # 解析每个Phone Id的状态
    phone_pattern = r'Phone Id=(\d+)(.*?)(?=Phone Id=\d+|$)'
    for match in re.finditer(phone_pattern, raw, re.DOTALL):
        phone_id = int(match.group(1))
        phone_content = match.group(2)
        
        phone_state = {
            'radio_power': None,
            'service_state': None,
            'network': None,
            'data_state': None,
            'has_channels': False
        }
        
        # 解析mRadioPowerState
        radio_match = re.search(r'mRadioPowerState=(\d+)', phone_content)
        if radio_match:
            phone_state['radio_power'] = int(radio_match.group(1))
        
        # 解析mServiceState - 需要更精确的匹配
        service_match = re.search(r'mServiceState=\{.*?mVoiceRegState=(\d+)\(([^)]+)\).*?mDataRegState=(\d+)\(([^)]+)\)', phone_content, re.DOTALL)
        if service_match:
            voice_reg_state = int(service_match.group(1))
            voice_state = service_match.group(2)
            data_reg_state = int(service_match.group(3))
            data_state = service_match.group(4)
            
            # 如果语音或数据状态为IN_SERVICE，则认为服务状态正常
            if voice_state == 'IN_SERVICE' or data_state == 'IN_SERVICE':
                phone_state['service_state'] = 'IN_SERVICE'
            elif voice_state == 'POWER_OFF' or data_state == 'POWER_OFF':
                phone_state['service_state'] = 'POWER_OFF'
            elif voice_state == 'OUT_OF_SERVICE' or data_state == 'OUT_OF_SERVICE':
                phone_state['service_state'] = 'OUT_OF_SERVICE'
            else:
                phone_state['service_state'] = 'UNKNOWN'
        
        # 解析mTelephonyDisplayInfo.network
        network_match = re.search(r'mTelephonyDisplayInfo.*?network=([A-Z_]+)', phone_content)
        if network_match:
            phone_state['network'] = network_match.group(1)
        
        # 解析mDataConnectionState
        data_match = re.search(r'mDataConnectionState=(\d+)', phone_content)
        if data_match:
            phone_state['data_state'] = int(data_match.group(1))
        
        # 检查是否有PhysicalChannelConfigs
        if 'mPhysicalChannelConfigs=[' in phone_content and 'mPhysicalChannelConfigs=[]' not in phone_content:
            phone_state['has_channels'] = True
        
        metadata['phone_states'][phone_id] = phone_state
    
    return metadata

def _get_active_phone_ids(metadata: Dict[str, Any]) -> List[int]:
    """按优先级选择活跃的Phone Id - 支持多SIM显示"""
    active_phones = []
    phone_states = metadata['phone_states']
    
    # 首先添加所有活跃的Phone（支持多SIM）
    for phone_id, phone_state in phone_states.items():
        # 判断是否为活跃状态
        is_active = False
        
        # 条件1: mRadioPowerState==1 且 mServiceState 为 IN_SERVICE
        if (phone_state['radio_power'] == 1 and 
            phone_state['service_state'] == 'IN_SERVICE'):
            is_active = True
        
        # 条件2: mPhysicalChannelConfigs 非空 且 ServiceState不是OUT_OF_SERVICE
        elif (phone_state['has_channels'] and 
              phone_state['service_state'] not in ['OUT_OF_SERVICE', 'POWER_OFF']):
            is_active = True
        
        # 条件3: mTelephonyDisplayInfo.network != UNKNOWN 或 mDataConnectionState==2
        elif ((phone_state['network'] and phone_state['network'] != 'UNKNOWN') or 
              phone_state['data_state'] == 2):
            is_active = True
        
        if is_active and phone_id not in active_phones:
            active_phones.append(phone_id)
    
    # 如果没有任何活跃的Phone，尝试优先级1的逻辑
    if not active_phones:
        target_phone_ids = []
        if metadata['active_data_sub_id'] is not None:
            target_phone_ids.append(metadata['active_data_sub_id'])
        if metadata['default_sub_id'] is not None:
            target_phone_ids.append(metadata['default_sub_id'])
        if metadata['default_phone_id'] is not None:
            target_phone_ids.append(metadata['default_phone_id'])
        
        for phone_id in target_phone_ids:
            if phone_id in phone_states and phone_id not in active_phones:
                phone_state = phone_states[phone_id]
                # 检查是否为有效状态（非POWER_OFF/UNKNOWN/OUT_OF_SERVICE）
                if (phone_state['service_state'] not in ['POWER_OFF', 'UNKNOWN', 'OUT_OF_SERVICE'] and 
                    phone_state['network'] != 'UNKNOWN'):
                    active_phones.append(phone_id)
    
    return active_phones

def _segment_by_phone_or_physical(raw: str) -> List[str]:
    """分段：只返回活跃的Phone Id段"""
    # 1) 解析Phone元数据，获取活跃的Phone Id
    metadata = _parse_phone_metadata(raw)
    active_phone_ids = _get_active_phone_ids(metadata)
    
    if not active_phone_ids:
        # 如果没有活跃的Phone，返回空列表
        return []
    
    # 2) 根据活跃的Phone Id提取对应的段
    sections = []
    phone_matches = list(re.finditer(r'Phone Id=(\d+)', raw))
    
    for i, match in enumerate(phone_matches):
        phone_id = int(match.group(1))
        if phone_id in active_phone_ids:
            start_pos = match.start()
            end_pos = phone_matches[i + 1].start() if i + 1 < len(phone_matches) else len(raw)
            sections.append(raw[start_pos:end_pos])
    
    return sections

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
                # 获取ARFCN - 优先从PhysicalChannelConfigs，如果为0则从ServiceState获取（仅限PCC）
                dl_arfcn = _to_int(kv.get('mDownlinkChannelNumber'))
                ul_arfcn = _to_int(kv.get('mUplinkChannelNumber'))
                
                # 如果ARFCN为0或无效，且是PCC，则尝试从ServiceState中获取
                if (not dl_arfcn or dl_arfcn == 0) and kv.get('mConnectionStatus') == 'PrimaryServing':
                    service_match = re.search(r'mServiceState=\{.*?mChannelNumber=(\d+)', section, re.DOTALL)
                    if service_match:
                        dl_arfcn = int(service_match.group(1))
                
                channel = {
                    'connection_status': kv.get('mConnectionStatus', ''),
                    'rat': kv.get('mNetworkType', ''),
                    'band': _to_int(kv.get('mBand')),
                    'dl_arfcn': dl_arfcn,
                    'ul_arfcn': ul_arfcn,
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
    
    # 查找SignalStrength块 - 支持两种格式
    signal_match = re.search(r"mSignalStrength=SignalStrength:\{(.*?)\}", section, re.DOTALL)
    if not signal_match:
        return signal_data
    
    signal_text = signal_match.group(1)
    
    # LTE信号解析 - 支持两种格式
    if "mLte=CellSignalStrengthLte:" in signal_text:
        # 提取LTE信号强度 - 支持新格式（带冒号）
        rssi_match = re.search(r"rssi=(-?\d+)", signal_text)
        rsrp_match = re.search(r"rsrp=(-?\d+)", signal_text)
        rsrq_match = re.search(r"rsrq=(-?\d+)", signal_text)
        rssnr_match = re.search(r"rssnr=(-?\d+)", signal_text)
        cqi_match = re.search(r"cqi=(-?\d+)", signal_text)
        
        # 检查信号是否有效（不是MAXINT）
        rsrp_val = _to_int(rsrp_match.group(1)) if rsrp_match else None
        if rsrp_val:  # 只使用有效信号
            signal_data['lte'] = {
                'rsrp': rsrp_val,
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
        
        ss_rsrp_val = _to_int(ss_rsrp_match.group(1)) if ss_rsrp_match else None
        if ss_rsrp_val:  # 只使用有效信号
            signal_data['nr'] = {
                'ss_rsrp': ss_rsrp_val,
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

def _primary_first(chs: List[Dict]) -> List[Dict]:
    """把主小区放到列表第一位：优先按 PrimaryServing，兜底按 DL 带宽最大"""
    if not chs:
        return []
    primary = next((c for c in chs if c.get('connection_status') == 'PrimaryServing'), None)
    if not primary:
        primary = max(chs, key=lambda x: (x.get('bw_dl') or 0, x.get('dl_arfcn') or -1))
    rest = [c for c in chs if c is not primary]
    return [primary] + rest

def _build_ca_endc_summary(lte_channels: List[Dict], nr_channels: List[Dict]) -> str:
    """构建CA/ENDC摘要"""
    lte_ordered = _primary_first([c for c in lte_channels if c.get('band')])
    nr_ordered = _primary_first([c for c in nr_channels if c.get('band')])

    lte_bands = [f"b{c['band']}" for c in lte_ordered]
    nr_bands = [f"n{c['band']}" for c in nr_ordered]

    if lte_bands and nr_bands:
        # ENDC：先 LTE（PCC,SCC...），再 NR（SpCell,SCells...）
        return "EN_DC_" + "_".join(lte_bands + nr_bands)
    elif len(nr_bands) > 1:
        return "CA_" + "_".join(nr_bands)          # NR CA（主->辅）
    elif len(lte_bands) > 1:
        return "CA_" + "_".join(lte_bands)         # LTE CA（主->辅）
    elif nr_bands:
        return f"NR_{nr_bands[0]}"
    elif lte_bands:
        return f"LTE_{lte_bands[0]}"
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
                'CC': 'PCC' if cell['type'] == 'LTE' else 'PCell',  # IDLE场景下NR用PCell而不是SpCell
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
    lte_channels = [c for c in channels if c['rat'] in ['LTE', 'LTE_CA']]
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
        primary_nr = next((c for c in nr_channels if c.get('connection_status') == 'PrimaryServing'), None) \
                     or max(nr_channels, key=lambda x: (x.get('bw_dl') or 0, x.get('dl_arfcn') or -1))
        
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
                    'CC': f"SCell#{scc_count}",  # 无论ENDC还是NR-CA，NR的辅载波都叫SCell
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
    
    # 1. 分段（只返回活跃的Phone Id段）
    sections = _segment_by_phone_or_physical(raw)
    
    # 调试信息
    if not sections:
        print("警告：没有检测到活跃的SIM卡")
        return all_rows
    
    # 2. 为每个段构建行
    for idx, section in enumerate(sections):
        # 从section中提取Phone Id来确定SIM名称
        phone_id_match = re.search(r'Phone Id=(\d+)', section)
        if phone_id_match:
            phone_id = int(phone_id_match.group(1))
            sim_name = f"SIM{phone_id + 1}"  # Phone Id=0 -> SIM1, Phone Id=1 -> SIM2
        else:
            sim_name = f"SIM{idx + 1}"  # 备用方案
        
        # 3. 解析各个组件
        channels = _parse_physical_channels(section)
        signal_data = _parse_signal_strength(section)
        cell_infos = _parse_cellinfo_fallback(section)
        
        # 4. 构建行
        rows = _build_rows(channels, signal_data, cell_infos, sim_name)
        all_rows.extend(rows)
    
    return all_rows
