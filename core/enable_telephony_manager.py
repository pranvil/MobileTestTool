#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 Telephony日志启用管理器
适配原Tkinter版本的Telephony日志启用功能
"""

import subprocess
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox


class TelephonyWorker(QThread):
    """Telephony日志启用工作线程"""
    
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, device, telephony_commands):
        super().__init__()
        self.device = device
        self.telephony_commands = telephony_commands
        
    def run(self):
        """执行Telephony命令"""
        try:
            self.progress.emit("正在准备Telephony命令...")
            
            # 准备所有命令（移除"adb shell"前缀）
            command_list = []
            for command in self.telephony_commands:
                # 移除 "adb shell " 前缀，只保留setprop命令
                if command.startswith("adb shell "):
                    command_list.append(command[10:])  # 移除 "adb shell " (10个字符)
                else:
                    command_list.append(command)
            
            # 将所有命令连接成一个字符串，用换行符分隔
            all_commands = "\n".join(command_list)
            
            self.progress.emit("正在执行Telephony命令...")
            
            # 执行adb shell一次，通过stdin发送所有命令
            result = subprocess.run(
                ["adb", "-s", self.device, "shell"],
                input=all_commands,
                text=True,
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                print(f"[WARNING] 部分命令执行失败")
                print(f"[WARNING] 错误信息: {result.stderr}")
                # 即使有错误，也继续执行，因为setprop命令通常不会失败
            
            self.progress.emit("所有命令执行完成")
            self.finished.emit(True, "Telephony日志设置完成")
            
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "命令执行超时")
        except Exception as e:
            self.finished.emit(False, f"执行Telephony命令失败: {str(e)}")


class PyQtTelephonyManager(QObject):
    """PyQt5 Telephony日志启用管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.worker = None
        
        # Telephony相关的adb命令列表
        self.telephony_commands = [
            "adb shell setprop persist.log.tag.RfxController D",
            "adb shell setprop persist.log.tag.RILC-RP D",
            "adb shell setprop persist.log.tag.RfxTransUtils D",
            "adb shell setprop persist.log.tag.RfxMclDisThread D",
            "adb shell setprop persist.log.tag.RfxCloneMgr D",
            "adb shell setprop persist.log.tag.RfxHandlerMgr D",
            "adb shell setprop persist.log.tag.RfxIdToStr D",
            "adb shell setprop persist.log.tag.RfxDisThread D",
            "adb shell setprop persist.log.tag.RfxMclStatusMgr D",
            "adb shell setprop persist.log.tag.RIL-Fusion D",
            "adb shell setprop persist.log.tag.RfxContFactory D",
            "adb shell setprop persist.log.tag.RfxChannelMgr D",
            "adb shell setprop persist.log.tag.RIL-Parcel D",
            "adb shell setprop persist.log.tag.RIL-Socket D",
            "adb shell setprop persist.log.tag.RIL-DATA D",
            "adb shell setprop persist.log.tag.GsmCdmaPhone D",
            "adb shell setprop persist.log.tag.RILMD2-SS D",
            "adb shell setprop persist.log.tag.CapaSwitch D",
            "adb shell setprop persist.log.tag.DSSelector D",
            "adb shell setprop persist.log.tag.DSSExt D",
            "adb shell setprop persist.log.tag.Op01DSSExt D",
            "adb shell setprop persist.log.tag.Op02DSSExt D",
            "adb shell setprop persist.log.tag.Op09DSSExt D",
            "adb shell setprop persist.log.tag.Op18DSSExt D",
            "adb shell setprop persist.log.tag.DSSelectorUtil D",
            "adb shell setprop persist.log.tag.Op01SimSwitch D",
            "adb shell setprop persist.log.tag.Op02SimSwitch D",
            "adb shell setprop persist.log.tag.Op18SimSwitch D",
            "adb shell setprop persist.log.tag.IccProvider D",
            "adb shell setprop persist.log.tag.IccPhoneBookIM D",
            "adb shell setprop persist.log.tag.AdnRecordCache D",
            "adb shell setprop persist.log.tag.AdnRecordLoader D",
            "adb shell setprop persist.log.tag.AdnRecord D",
            "adb shell setprop persist.log.tag.RIL-PHB D",
            "adb shell setprop persist.log.tag.MtkIccProvider D",
            "adb shell setprop persist.log.tag.MtkIccPHBIM D",
            "adb shell setprop persist.log.tag.MtkAdnRecord D",
            "adb shell setprop persist.log.tag.MtkRecordLoader D",
            "adb shell setprop persist.log.tag.RpPhbController D",
            "adb shell setprop persist.log.tag.RmcPhbReq D",
            "adb shell setprop persist.log.tag.RmcPhbUrc D",
            "adb shell setprop persist.log.tag.RtcPhb D",
            "adb shell setprop persist.log.tag.VT D",
            "adb shell setprop persist.log.tag.ImsVTProvider D",
            "adb shell setprop persist.log.tag.IccCardProxy D",
            "adb shell setprop persist.log.tag.IsimFileHandler D",
            "adb shell setprop persist.log.tag.IsimRecords D",
            "adb shell setprop persist.log.tag.SIMRecords D",
            "adb shell setprop persist.log.tag.SpnOverride D",
            "adb shell setprop persist.log.tag.UiccCard D",
            "adb shell setprop persist.log.tag.UiccController D",
            "adb shell setprop persist.log.tag.RIL-SIM D",
            "adb shell setprop persist.log.tag.CountryDetector D",
            "adb shell setprop persist.log.tag.DataDispatcher D",
            "adb shell setprop persist.log.tag.ImsService D",
            "adb shell setprop persist.log.tag.IMS_RILA D",
            "adb shell setprop persist.log.tag.IMSRILRequest D",
            "adb shell setprop persist.log.tag.ImsManager D",
            "adb shell setprop persist.log.tag.ImsApp D",
            "adb shell setprop persist.log.tag.ImsBaseCommands D",
            "adb shell setprop persist.log.tag.MtkImsManager D",
            "adb shell setprop persist.log.tag.MtkImsService D",
            "adb shell setprop persist.log.tag.RP_IMS D",
            "adb shell setprop persist.log.tag.RtcIms D",
            "adb shell setprop persist.log.tag.RtcImsConfigController D",
            "adb shell setprop persist.log.tag.RtcImsConference D",
            "adb shell setprop persist.log.tag.RtcImsDialog D",
            "adb shell setprop persist.log.tag.RmcImsCtlUrcHdl D",
            "adb shell setprop persist.log.tag.RmcImsCtlReqHdl D",
            "adb shell setprop persist.log.tag.ImsCall D",
            "adb shell setprop persist.log.tag.ImsPhone D",
            "adb shell setprop persist.log.tag.ImsPhoneCall D",
            "adb shell setprop persist.log.tag.ImsPhoneBase D",
            "adb shell setprop persist.log.tag.ImsCallSession D",
            "adb shell setprop persist.log.tag.ImsCallProfile D",
            "adb shell setprop persist.log.tag.ImsEcbm D",
            "adb shell setprop persist.log.tag.ImsEcbmProxy D",
            "adb shell setprop persist.log.tag.OperatorUtils D",
            "adb shell setprop persist.log.tag.WfoApp D",
            "adb shell setprop persist.log.tag.GsmCdmaConn D",
            "adb shell setprop persist.log.tag.Phone D",
            "adb shell setprop persist.log.tag.RIL-CC D",
            "adb shell setprop persist.log.tag.RpCallControl D",
            "adb shell setprop persist.log.tag.RpAudioControl D",
            "adb shell setprop persist.log.tag.GsmCallTkrHlpr D",
            "adb shell setprop persist.log.tag.MtkPhoneNotifr D",
            "adb shell setprop persist.log.tag.MtkGsmCdmaConn D",
            "adb shell setprop persist.log.tag.RadioManager D",
            "adb shell setprop persist.log.tag.RIL_Mux D",
            "adb shell setprop persist.log.tag.RIL-OEM D",
            "adb shell setprop persist.log.tag.RIL D",
            "adb shell setprop persist.log.tag.RIL_UIM_SOCKET D",
            "adb shell setprop persist.log.tag.RILD D",
            "adb shell setprop persist.log.tag.RIL-RP D",
            "adb shell setprop persist.log.tag.RfxMessage D",
            "adb shell setprop persist.log.tag.RfxDebugInfo D",
            "adb shell setprop persist.log.tag.RfxTimer D",
            "adb shell setprop persist.log.tag.RfxObject D",
            "adb shell setprop persist.log.tag.SlotQueueEntry D",
            "adb shell setprop persist.log.tag.RfxAction D",
            "adb shell setprop persist.log.tag.RFX D",
            "adb shell setprop persist.log.tag.RpRadioMessage D",
            "adb shell setprop persist.log.tag.RpModemMessage D",
            "adb shell setprop persist.log.tag.PhoneFactory D",
            "adb shell setprop persist.log.tag.ProxyController D",
            "adb shell setprop persist.log.tag.RfxDefDestUtils D",
            "adb shell setprop persist.log.tag.RfxSM D",
            "adb shell setprop persist.log.tag.RfxSocketSM D",
            "adb shell setprop persist.log.tag.RfxDT D",
            "adb shell setprop persist.log.tag.RpCdmaOemCtrl D",
            "adb shell setprop persist.log.tag.RpRadioCtrl D",
            "adb shell setprop persist.log.tag.RpMDCtrl D",
            "adb shell setprop persist.log.tag.RpCdmaRadioCtrl D",
            "adb shell setprop persist.log.tag.RpFOUtils D",
            "adb shell setprop persist.log.tag.C2K_RIL-SIM D",
            "adb shell setprop persist.log.tag.MtkGsmCdmaPhone D",
            "adb shell setprop persist.log.tag.MtkRILJ D",
            "adb shell setprop persist.log.tag.MtkRadioInd D",
            "adb shell setprop persist.log.tag.MtkRadioResp D",
            "adb shell setprop persist.log.tag.ExternalSimMgr D",
            "adb shell setprop persist.log.tag.VsimAdaptor D",
            "adb shell setprop persist.log.tag.MtkCsimFH D",
            "adb shell setprop persist.log.tag.MtkIsimFH D",
            "adb shell setprop persist.log.tag.MtkRuimFH D",
            "adb shell setprop persist.log.tag.MtkSIMFH D",
            "adb shell setprop persist.log.tag.MtkSIMRecords D",
            "adb shell setprop persist.log.tag.MtkSmsCbHeader D",
            "adb shell setprop persist.log.tag.MtkSmsManager D",
            "adb shell setprop persist.log.tag.MtkSmsMessage D",
            "adb shell setprop persist.log.tag.MtkSpnOverride D",
            "adb shell setprop persist.log.tag.MtkUiccCardApp D",
            "adb shell setprop persist.log.tag.MtkUiccCtrl D",
            "adb shell setprop persist.log.tag.MtkUsimFH D",
            "adb shell setprop persist.log.tag.RpRilClientCtrl D",
            "adb shell setprop persist.log.tag.RilMalClient D",
            "adb shell setprop persist.log.tag.RpSimController D",
            "adb shell setprop persist.log.tag.MtkSubCtrl D",
            "adb shell setprop persist.log.tag.RP_DAC D",
            "adb shell setprop persist.log.tag.RP_DC D",
            "adb shell setprop persist.log.tag.NetAgentService D",
            "adb shell setprop persist.log.tag.NetAgent_IO D",
            "adb shell setprop persist.log.tag.NetLnkEventHdlr D",
            "adb shell setprop persist.log.tag.RmcDcCommon D",
            "adb shell setprop persist.log.tag.RmcDcDefault D",
            "adb shell setprop persist.log.tag.RtcDC D",
            "adb shell setprop persist.log.tag.RilClient D",
            "adb shell setprop persist.log.tag.RmcCommSimReq D",
            "adb shell setprop persist.log.tag.RmcCdmaSimRequest D",
            "adb shell setprop persist.log.tag.RmcGsmSimRequest D",
            "adb shell setprop persist.log.tag.RmcCommSimUrc D",
            "adb shell setprop persist.log.tag.RmcGsmSimUrc D",
            "adb shell setprop persist.log.tag.RtcCommSimCtrl D",
            "adb shell setprop persist.log.tag.RmcCommSimOpReq D",
            "adb shell setprop persist.log.tag.RtcRadioCont D",
            "adb shell setprop persist.log.tag.MtkRetryManager D",
            "adb shell setprop persist.log.tag.RmcDcPdnManager D",
            "adb shell setprop persist.log.tag.RmcDcReqHandler D",
            "adb shell setprop persist.log.tag.RmcDcUtility D",
            "adb shell setprop persist.log.tag.RfxIdToMsgId D",
            "adb shell setprop persist.log.tag.RfxOpUtils D",
            "adb shell setprop persist.log.tag.RfxMclMessenger D",
            "adb shell setprop persist.log.tag.RfxRilAdapter D",
            "adb shell setprop persist.log.tag.RfxFragEnc D",
            "adb shell setprop persist.log.tag.RfxStatusMgr D",
            "adb shell setprop persist.log.tag.RmcRadioReq D",
            "adb shell setprop persist.log.tag.RmcCapa D",
            "adb shell setprop persist.log.tag.RtcCapa D",
            "adb shell setprop persist.log.tag.RpMalController D",
            "adb shell setprop persist.log.tag.WORLDMODE D",
            "adb shell setprop persist.log.tag.RtcWp D",
            "adb shell setprop persist.log.tag.RmcWp D",
            "adb shell setprop persist.log.tag.RmcOpRadioReq D",
            "adb shell setprop persist.log.tag.RfxRilUtils D",
            "adb shell setprop persist.log.tag.RmcCdmaSimUrc D",
            "adb shell setprop persist.log.tag.MtkPhoneNumberUtils D",
            "adb shell setprop persist.log.tag.RmcOemHandler D",
            "adb shell setprop persist.log.tag.CarrierExpressServiceImpl D",
            "adb shell setprop persist.log.tag.CarrierExpressServiceImplExt D",
            "adb shell setprop persist.log.tag.PhoneConfigurationSettings D",
            "adb shell setprop persist.log.tag.RfxContFactory D",
            "adb shell setprop persist.log.tag.RfxChannelMgr D",
            "adb shell setprop persist.log.tag.RfxMclDisThread D",
            "adb shell setprop persist.log.tag.RfxCloneMgr D",
            "adb shell setprop persist.log.tag.RfxHandlerMgr D",
            "adb shell setprop persist.log.tag.RtcModeCont D",
            "adb shell setprop persist.log.tag.RIL-SocListen D",
            "adb shell setprop persist.log.tag.RIL-Netlink D",
            "adb shell setprop persist.log.tag.RfxVersionMgr D",
            "adb shell setprop persist.log.tag.RilOpProxy D",
            "adb shell setprop persist.log.tag.RILC-OP D",
            "adb shell setprop persist.log.tag.RilOemClient D",
            "adb shell setprop persist.log.tag.Telecom D",
            "adb shell setprop persist.log.tag.MwiRIL D",
            "adb shell setprop persist.log.tag.SmartRatController D",
            "adb shell setprop persist.log.tag.SmartGearsController D",
            "adb shell setprop persist.log.tag.SocketStatusProvider D",
            "adb shell setprop persist.log.tag.AppStatusProvider D",
            "adb shell setprop persist.log.tag.InformationUtil D",
            "adb shell setprop persist.log.tag.SmartRatDummyUsageGenerator D",
            "adb shell setprop persist.log.tag.SmartRatSwitchIntfMgr D",
            "adb shell setprop persist.log.tag.SmartRatSwitcher D",
            "adb shell setprop persist.log.tag.RtcCodec D",
            "adb shell setprop persist.log.tag.SmRATCdcNoti D",
            "adb shell setprop persist.log.tag.SmartRatInd D",
            "adb shell setprop persist.log.tag.WpfaCcciDataHeaderEncoder D",
            "adb shell setprop persist.log.tag.WpfaCcciReader D",
            "adb shell setprop persist.log.tag.WpfaCcciSender D",
            "adb shell setprop persist.log.tag.WpfaControlMsgHandler D",
            "adb shell setprop persist.log.tag.WpfaDriver D",
            "adb shell setprop persist.log.tag.WpfaDriverAccept D",
            "adb shell setprop persist.log.tag.WpfaDriverAdapter D",
            "adb shell setprop persist.log.tag.WpfaDriverDeReg D",
            "adb shell setprop persist.log.tag.WpfaDriverMessage D",
            "adb shell setprop persist.log.tag.WpfaDriverRegFilter D",
            "adb shell setprop persist.log.tag.WpfaDriverULIpPkt D",
            "adb shell setprop persist.log.tag.WpfaDriverUtilis D",
            "adb shell setprop persist.log.tag.WpfaDriverVersion D",
            "adb shell setprop persist.log.tag.WpfaFilterRuleReqHandler D",
            "adb shell setprop persist.log.tag.WpfaRingBuffer D",
            "adb shell setprop persist.log.tag.WpfaShmAccessController D",
            "adb shell setprop persist.log.tag.WpfaShmReadMsgHandler D",
            "adb shell setprop persist.log.tag.WpfaShmSynchronizer D",
            "adb shell setprop persist.log.tag.WpfaShmWriteMsgHandler D",
            "adb shell setprop persist.log.tag.wpfa_iptable_android D",
            "adb shell setprop persist.log.tag.WpfaRuleRegister D",
            "adb shell setprop persist.log.tag.WpfaParsing D",
            "adb shell setprop persist.log.tag.WpfaRuleContainer D",
            "adb shell setprop persist.log.tag.RtmDC D",
            "adb shell setprop persist.log.tag.RmmDcEvent D",
            "adb shell setprop persist.log.tag.RmmDcUrcHandler D",
            "adb shell setprop persist.log.tag.MipcEventHandler D",
            "adb shell setprop persist.log.tag.InterfaceManager D",
            "adb shell setprop persist.log.tag.RmmPhbReq D",
            "adb shell setprop persist.log.tag.RmmPhbUrc D",
            "adb shell setprop persist.log.tag.RtmPhb D",
            "adb shell setprop persist.log.tag.RtmIms D",
            "adb shell setprop persist.log.tag.RtmImsConfigController D",
            "adb shell setprop persist.log.tag.RtmImsConference D",
            "adb shell setprop persist.log.tag.RtmImsDialog D",
            "adb shell setprop persist.log.tag.RmmImsCtlUrcHdl D",
            "adb shell setprop persist.log.tag.RmmImsCtlReqHdl D",
            "adb shell setprop persist.log.tag.RmmEmbmsReq D",
            "adb shell setprop persist.log.tag.RmmEmbmsUrc D",
            "adb shell setprop persist.log.tag.RtmEmbmsUtil D",
            "adb shell setprop persist.log.tag.RtmEmbmsAt D",
            "adb shell setprop persist.log.tag.RmmSimCommReq D",
            "adb shell setprop persist.log.tag.RmmSimCommUrc D",
            "adb shell setprop persist.log.tag.RmmSimBaseHandler D",
            "adb shell setprop persist.log.tag.RtmRadioConfig D",
            "adb shell setprop persist.log.tag.RtmCommSimCtrl D",
            "adb shell setprop persist.log.tag.RmmCommSimOpReq D",
            "adb shell setprop persist.log.tag.RtmRadioCont D",
            "adb shell setprop persist.log.tag.RmmDcPdnManager D",
            "adb shell setprop persist.log.tag.RmmDcUtility D",
            "adb shell setprop persist.log.tag.RmmRadioReq D",
            "adb shell setprop persist.log.tag.RmmCapa D",
            "adb shell setprop persist.log.tag.RtcCapa D",
            "adb shell setprop persist.log.tag.RtmWp D",
            "adb shell setprop persist.log.tag.RmmWp D",
            "adb shell setprop persist.log.tag.RmmOpRadioReq D",
            "adb shell setprop persist.log.tag.RmmOemHandler D",
            "adb shell setprop persist.log.tag.RtmModeCont D",
            "adb shell setprop persist.log.tag.RtmEccNumberController D",
            "adb shell setprop persist.log.tag.RmmEccNumberReqHdlr D",
            "adb shell setprop persist.log.tag.RmmEccNumberUrcHandler D",
            "adb shell setprop persist.log.tag.mipc_lib D",
            "adb shell setprop persist.log.tag.trm_lib D",
            "adb shell setprop persist.log.tag.RfxBaseHandler D",
            "adb shell setprop persist.log.tag.RmmMwi D",
            "adb shell setprop persist.log.tag.RtmMwi D",
            "adb shell setprop persist.log.tag.MtkTelephonyManagerEx D",
            "adb shell setprop persist.log.tag.MtkUsimPhoneBookManager D",
            "adb shell setprop persist.log.tag.MtkIccSmsInterfaceManager D",
            "adb shell setprop persist.log.tag.RmmDch D",
            "adb shell setprop persist.log.tag.RmmDchUrc D",
            "adb shell setprop persist.log.tag.WpfaCppUtils D",
            "adb shell setprop persist.log.tag.libmnlUtils D",
            "adb shell setprop persist.log.tag.NetworkStats V",
            "adb shell setprop persist.log.tag.NetworkPolicy V",
            "adb shell setprop persist.log.tag.RTC_DAC V",
            "adb shell setprop persist.log.tag.RmcEmbmsReq V",
            "adb shell setprop persist.log.tag.RmcEmbmsUrc V",
            "adb shell setprop persist.log.tag.RtcEmbmsUtil V",
            "adb shell setprop persist.log.tag.RtcEmbmsAt V",
            "adb shell setprop persist.log.tag.MtkEmbmsAdaptor V",
            "adb shell setprop persist.log.tag.MTKSST V",
            "adb shell setprop persist.log.tag.RmcNwHdlr V",
            "adb shell setprop persist.log.tag.RmcNwReqHdlr V",
            "adb shell setprop persist.log.tag.RmcNwRTReqHdlr V",
            "adb shell setprop persist.log.tag.RmcRatSwHdlr V",
            "adb shell setprop persist.log.tag.RtcRatSwCtrl V",
            "adb shell setprop persist.log.tag.RtcNwCtrl V",
            "adb shell setprop persist.log.tag.MtkPhoneSwitcher V",
            "adb shell setprop persist.log.tag.RmmNwHdlr V",
            "adb shell setprop persist.log.tag.RmmNwReqHdlr V",
            "adb shell setprop persist.log.tag.RmmNwRTReqHdlr V",
            "adb shell setprop persist.log.tag.RmmNwAsyncHdlr V",
            "adb shell setprop persist.log.tag.RmmNwNrtReqHdlr V",
            "adb shell setprop persist.log.tag.RmmNwRatSwHdlr V",
            "adb shell setprop persist.log.tag.RmmNwUrcHdlr V",
            "adb shell setprop persist.log.tag.RtmNwCtrl V",
            "adb shell setprop persist.log.tag.Telephony V",
            "adb shell setprop persist.log.tag.VoLTE_Stack V",
            "adb shell setprop persist.log.tag.VoLTE_IF_CH V",
            "adb shell setprop persist.log.tag.VoLTE_WAKELOCK V",
            "adb shell setprop persist.log.tag.VoLTE_CONFPKG V",
            "adb shell setprop persist.log.tag.VoLTE_DISP V",
            "adb shell setprop persist.log.tag.VoLTE_UA V",
            "adb shell setprop persist.log.tag.VoLTE_MWI V",
            "adb shell setprop persist.log.tag.VoLTE_REG V",
            "adb shell setprop persist.log.tag.VoLTE_Service V",
            "adb shell setprop persist.log.tag.VoLTE_SIPTimer V",
            "adb shell setprop persist.log.tag.VoLTE_TRANS V",
            "adb shell setprop persist.log.tag.VoLTE_SIPTX V",
            "adb shell setprop persist.log.tag.VoLTE_SMS V",
            "adb shell setprop persist.log.tag.VoLTE_SOC V",
            "adb shell setprop persist.log.tag.VoLTE_DNS V",
            "adb shell setprop persist.log.tag.VoLTE_IF_SERVICE V",
            "adb shell setprop persist.log.tag.VoLTE_IF_CORE V",
            "adb shell setprop persist.log.tag.VoLTE_Auto_Testing V",
            "adb shell setprop persist.log.tag.VoLTE_IMCB-CM V",
            "adb shell setprop persist.log.tag.VoLTE_IMCB-0 V",
            "adb shell setprop persist.log.tag.VoLTE_IMCB-1 V",
            "adb shell setprop persist.log.tag.VoLTE_IMCB-2 V"
        ]
    
    def enable_telephony(self):
        """启用Telephony日志"""
        device = self.device_manager.validate_device_selection()
        if not device:
            self.status_message.emit("请先选择设备")
            return
        
        try:
            # 创建工作线程
            self.worker = TelephonyWorker(device, self.telephony_commands)
            # 先连接信号，再启动线程
            self.worker.progress.connect(self.status_message.emit)
            self.worker.finished.connect(self._on_telephony_finished)
            # 启动线程
            self.worker.start()
            
        except Exception as e:
            self.status_message.emit(f"启用Telephony日志失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"启用Telephony日志失败: {str(e)}")
    
    def _on_telephony_finished(self, success, message):
        """Telephony设置完成"""
        if success:
            self.status_message.emit(message)
            
            # 询问是否立即重启
            reply = QMessageBox.question(
                None,
                "重启确认",
                "Telephony日志设置完成！\n\n"
                "为了确保设置生效，建议立即重启设备。\n"
                "是否现在重启设备？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.reboot_device()
            else:
                QMessageBox.information(None, "完成", "Telephony日志设置完成！\n请手动重启设备以使设置生效。")
        else:
            QMessageBox.critical(None, "错误", f"设置Telephony日志失败: {message}")
    
    def reboot_device(self):
        """重启设备"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 执行重启命令
            result = subprocess.run(
                ["adb", "-s", device, "reboot"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                QMessageBox.information(None, "成功", f"设备 {device} 正在重启...")
                self.status_message.emit(f"设备 {device} 正在重启...")
            else:
                QMessageBox.critical(None, "错误", f"重启设备失败: {result.stderr}")
                self.status_message.emit(f"重启设备失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            QMessageBox.critical(None, "错误", "重启命令超时")
            self.status_message.emit("重启命令超时")
        except Exception as e:
            QMessageBox.critical(None, "错误", f"重启设备失败: {str(e)}")
            self.status_message.emit(f"重启设备失败: {str(e)}")

