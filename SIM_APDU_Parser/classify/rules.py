
from typing import Tuple
from SIM_APDU_Parser.core.models import MsgType, Message
from SIM_APDU_Parser.core.utils import parse_apdu_header, first_tlv_tag_after_store_header

# Request titles mapping per spec
RESP_TITLES = {  
    'BF20': 'EUICCInfo1',
    'BF21': 'PrepareDownloadResponse',
    'BF22': 'EUICCInfo2',
    'BF27': 'Reserved',
    'BF28': 'ListNotificationResponse',
    'BF29': 'SetNicknameResponse',
    'BF2A': 'UpdateMetadataResponse',
    'BF2B': 'RetrieveNotificationsListResponse',
    'BF2D': 'ProfileInfoListResponse',
    'BF2E': 'GetEuiccChallengeResponse',
    'BF2F': 'NotificationMetadata',
    'BF30': 'NotificationSentResponse',
    'BF31': 'EnableProfileResponse',
    'BF32': 'DisableProfileResponse',
    'BF33': 'DeleteProfileResponse',
    'BF34': 'EuiccMemoryResetResponse',
    'BF35': 'Reserved',
    'BF36': 'BoundProfilePackage',
    'BF37': 'ProfileInstallationResult',
    'BF38': 'AuthenticateServerResponse',
    'BF39': 'InitiateAuthenticationResponse',
    'BF3A': 'GetBoundProfilePackageResponse',
    'BF3B': 'AuthenticateClientResponseEs9',
    'BF3C': 'EuiccConfiguredDataResponse',
    'BF3D': 'HandleNotification',
    'BF3E': 'GetEuiccDataResponse',
    'BF3F': 'SetDefaultDpAddressResponse',
    'BF40': 'AuthenticateClientResponseEs11',
    'BF41': 'CancelSessionResponse',
    'BF42': 'LpaeActivationResponse',
    'BF43': 'GetRatResponse',
    'BF44': 'LoadRpmPackageResult',
    'BF45': 'VerifySmdsResponseResponse',
    'BF46': 'CheckEventResponse',
    'BF4A': 'AlertData',
    'BF4B': 'VerifyDeviceChangeResponse',
    'BF4C': 'ConfirmDeviceChangeResponse',
    'BF4D': 'PrepareDeviceChangeResponse',
}

REQ_TITLES = {
    'BF20': 'GetEuiccInfo1Request',
    'BF21': 'PrepareDownloadRequest',
    'BF22': 'GetEuiccInfo2Request',
    'BF23': 'InitialiseSecureChannelRequest',
    'BF24': 'ConfigureISDPRequest',
    'BF25': 'StoreMetadataRequest',
    'BF26': 'ReplaceSessionKeysRequest',
    'BF27': 'Reserved',
    'BF28': 'ListNotificationRequest',
    'BF29': 'SetNicknameRequest',
    'BF2A': 'UpdateMetadataRequest',
    'BF2B': 'RetrieveNotificationsListRequest',
    'BF2D': 'ProfileInfoListRequest',
    'BF2E': 'GetEuiccChallengeRequest',
    'BF2F': 'NotificationMetadata',
    'BF30': 'NotificationSentRequest',
    'BF31': 'EnableProfileRequest',
    'BF32': 'DisableProfileRequest',
    'BF33': 'DeleteProfileRequest',
    'BF34': 'EuiccMemoryResetRequest',
    'BF35': 'Reserved',
    'BF36': 'BoundProfilePackage',
    'BF37': 'ProfileInstallationResult',
    'BF38': 'AuthenticateServerRequest',
    'BF39': 'InitiateAuthenticationRequest',
    'BF3A': 'GetBoundProfilePackageRequest',
    'BF3B': 'AuthenticateClientRequestEs9',
    'BF3C': 'EuiccConfiguredDataRequest',
    'BF3D': 'HandleNotification',
    'BF3E': 'GetEuiccDataRequest',
    'BF3F': 'SetDefaultDpAddressRequest',
    'BF40': 'AuthenticateClientRequestEs11',
    'BF41': 'CancelSessionRequest',
    'BF42': 'LpaeActivationRequest',
    'BF43': 'GetRatRequest',
    'BF44': 'LoadRpmPackageRequest',
    'BF45': 'VerifySmdsResponsesRequest',
    'BF46': 'CheckEventRequest',
    'BF4A': 'AlertData',
    'BF4B': 'VerifyDeviceChangeRequest',
    'BF4C': 'ConfirmDeviceChangeRequest',
    'BF4D': 'PrepareDeviceChangeRequest',
}



def classify_message(msg: Message):
    """Return (msg_type, direction_hint, tag, title). Direction uses ASCII '=>'."""
    s = msg.raw
    # ESIM => LPA (response from eUICC): BF..
    if s.startswith('BF'):
        tag = s[:4] if len(s) >= 4 else 'BF'
        title = f"[ESIM=>LPA] {RESP_TITLES.get(tag, tag)}"
        return MsgType.ESIM, 'ESIM=>LPA', tag, title
    # CAT UICC => Terminal: D0.. or 91.. (2 bytes)
    if s.startswith('D0'):
        return MsgType.CAT, 'UICC=>TERMINAL', 'D0', '[UICC=>TERMINAL] (D0)'
    # CAT UICC => Terminal: 91.. (Proactive Command Pending)
    if s.startswith('91') and len(s) == 4:
        return MsgType.CAT, 'UICC=>TERMINAL', '91', '[UICC=>TERMINAL] Proactive Command Pending'
    # Parse header
    cla, ins, _, _ = parse_apdu_header(s).cla, parse_apdu_header(s).ins, None, None
    # Terminal => UICC CAT
    if cla == 0x80 and ins in (0x10, 0x12, 0x14, 0xC2, 0xAA):
        names = {0x10:'TERMINAL PROFILE',0x12:'FETCH',0x14:'TERMINAL RESPONSE',0xC2:'ENVELOPE',0xAA:'TERMINAL CAPABILITY'}
        return MsgType.CAT, 'TERMINAL=>UICC', f'80{ins:02X}', f"[TERMINAL=>UICC] CAT: {names[ins]}"
    # LPA => ESIM (STORE DATA E2)
    if ins == 0xE2 and ((0x80 <= (cla or -1) <= 0x83) or (0xC0 <= (cla or -1) <= 0xCF)):
        tag = first_tlv_tag_after_store_header(s) or 'E2'
        name = REQ_TITLES.get(tag)
        if name:
            return MsgType.ESIM, 'LPA=>ESIM', tag, f"[LPA=>ESIM] {name}"
        return MsgType.ESIM, 'LPA=>ESIM', 'E2', '[LPA=>ESIM] eSIM STORE DATA (E2)'
    # Others - 使用SIM APDU解析器生成标题和方向
    try:
        from SIM_APDU_Parser.parsers.sim_apdu_parser import SimApduParser
        parser = SimApduParser()
        hdr = parse_apdu_header(s)
        is_ue_to_sim = parser._is_ue_to_sim(s, hdr)
        direction_hint = "UE=>SIM" if is_ue_to_sim else "SIM=>UE"
        
        if is_ue_to_sim and hdr.ins is not None:
            # UE->SIM: 显示命令名称
            command_name = parser.ue_to_sim_commands.get(hdr.ins, f"Unknown Command (0x{hdr.ins:02X})")
            
            # 如果是SELECT FILE命令，尝试显示文件名或AID
            if hdr.ins == 0xA4 and hdr.data_hex and len(hdr.data_hex) >= 4:
                data_length = len(hdr.data_hex) // 2  # 转换为字节数
                
                if data_length > 6:
                    # 长度大于6字节，显示为AID
                    title = f"[UE->SIM] {command_name} - AID"
                else:
                    # 长度小于等于6字节，显示文件名
                    # 如果数据长度大于2个字节，取数据部分的最后两个字节作为EF ID
                    if data_length > 2:
                        # 从hdr.data_hex中取最后两个字节作为文件ID
                        file_id = hdr.data_hex[-4:]  # 最后4个字符（2个字节）
                    else:
                        # 正常情况，取前两个字节
                        file_id = hdr.data_hex[:4]
                    
                    file_name = parser._get_file_name(file_id)
                    title = f"[UE->SIM] {command_name} - {file_name}"
            elif hdr.ins == 0x70:  # MANAGE CHANNEL
                # 解析P1参数
                if hdr.p1 == 0x00:
                    operation = "Open channel"
                elif hdr.p1 == 0x01:
                    operation = "Close channel"
                elif hdr.p1 == 0x02:
                    operation = "Get channel status"
                elif hdr.p1 == 0x80:
                    operation = "Close channel"
                else:
                    operation = f"Unknown operation (0x{hdr.p1:02X})"
                
                # 解析P2参数（Channel number）
                if hdr.p2 is not None and hdr.p2 != 0x00:
                    title = f"[UE->SIM] {command_name}-{operation} {hdr.p2}"
                else:
                    title = f"[UE->SIM] {command_name}-{operation}"
            else:
                title = f"[UE->SIM] {command_name}"
        else:
            # SIM->UE: 显示响应类型
            if s.startswith("62") or s.startswith("6F"):
                # 尝试从FCP中提取文件名
                file_id = parser._extract_file_id_from_fcp(s)
                if file_id:
                    file_name = parser._get_file_name(file_id)
                    title = f"[SIM->UE] FCP_{file_name}"
                else:
                    title = "[SIM->UE] FCP Response"
            elif len(s) == 4:
                status = int(s, 16)
                status_desc = parser.sim_to_ue_status.get(status, "Unknown Status")
                title = f"[SIM->UE] {status_desc}"
            else:
                title = "[SIM->UE] Response Data"
        
        return MsgType.NORMAL_SIM, direction_hint, None, title
    except Exception:
        # 如果解析失败，回退到默认值
        return MsgType.NORMAL_SIM, 'UNKNOWN', None, 'SIM APDU'


