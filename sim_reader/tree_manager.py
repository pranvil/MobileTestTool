import logging
from PySide6.QtWidgets import QTreeWidgetItem

class TreeManager:
    """SIM卡文件树形结构管理器
    负责管理SIM卡文件的树形显示结构，维护文件路径和ADF类型的映射关系
    提供文件路径和ADF类型的查询功能
    """
    def __init__(self, tree_widget):
        """初始化树形管理器
        
        Args:
            tree_widget: PySide6树形控件实例，用于显示文件结构
        """
        self.tree_widget = tree_widget
        logging.debug("初始化树形管理器")

        # EF文件ID映射表，用于将显示名称映射到实际的EF ID
        # 格式: {"显示名称": "EF_ID", ...}
        self.file_paths = {
            "ARR_6F06": "6F06",
            "IMSI": "6F07",
            "AD": "6FAD",
            "UST": "6F38",            
            "MSISDN": "6F40",
            "PNN": "6FC5",
            "OPL": "6FC6",
            "5GS3GPPLOCI": "5FC04F01",
            "5GSN3GPPLOCI": "5FC04F02",
            "5GS3GPPNSC": "5FC04F03",
            "5GSN3GPPNS": "5FC04F04",
            "5GAUTHKEYS": "5FC04F05",
            "UAC_AIC": "5FC04F06",
            "SUCI_Calc_Info": "5FC04F07",
            "OPL5G": "5FC04F08",
            "SUPI_NAI": "5FC04F09",
            "Routing_Indicator": "5FC04F0A",
            "URSP": "5FC04F0B",
            "IMPI": "6F02",
            "IMPU": "6F04",
            "DOMAIN": "6F03",
            "DIR": "2F00",
            "ICCID": "2FE2",
            "MBDN": "6FC7",
            "GID1": "6F3E",
            "GID2": "6F3F",
            "FPLMN": "6F7B",
            "SMSP": "6F42",
            "IST": "6F07IST",
            "P-CSCF": "6F09",
            "GBAP": "6FD5",
            "GBANL": "6FD7",
            "NAFKCA": "6FDD",
            "UICCIARI": "6FE7",
            "FromPreferred": "6FF7",
            "IMSConfigData": "6FF8",
            "XCAPConfigData": "6FFC",
            "SPN": "6F46",
            "EHPLMN": "6FD9",
            "OPLMNwACT": "6F61",
            "HPLMNwACT": "6F62",
            "HPPLMN": "6F31",
            "PLMNwACT": "6F60",
            "ARR_2F06": "2F06",
            "ePDGId": "6FF3",
        }

        # ADF类型映射表，用于确定文件所属的应用类型
        # 格式: {"文件名": "ADF类型", ...}
        self.adf_types = {key: "ISIM" for key in [
            "DOMAIN", "IMPU", "IMPI", "IST", "P-CSCF", "GBAP", "GBANL",
            "NAFKCA", "UICCIARI", "FromPreferred", "IMSConfigData", "XCAPConfigData"
        ]}
        self.adf_types.update({key: "MF" for key in ["ICCID", "DIR", "ARR_2F06"]})
        logging.debug("初始化完成 - 文件映射数量: %d, ADF类型映射数量: %d", 
                     len(self.file_paths), len(self.adf_types))

    def populate_tree(self):
        """构建并显示SIM卡文件的树形结构
        创建USIM、ISIM等主要分支，并在其下添加相应的EF文件节点
        """
        logging.info("开始构建文件树形结构")
        self.tree_widget.clear()
        
        # 创建USIM分支
        usim = QTreeWidgetItem(self.tree_widget, ["USIM"])
        df5gs = QTreeWidgetItem(usim, ["[DF]DF5GS"])
        logging.debug("创建USIM分支")

        # 添加USIM下的EF文件
        usim_files = [
            "UST", "ARR_6F06", "IMSI", "MSISDN", "PNN", "OPL", "DIR", "ICCID",
            "MBDN", "SMSP", "GID1", "GID2", "AD", "FPLMN", "PLMNwACT",
            "OPLMNwACT", "HPLMNwACT", "SPN", "EHPLMN", "HPPLMN", "ARR_2F06",
            "ePDGId"
        ]
        for file_name in usim_files:
            QTreeWidgetItem(usim, [file_name])
        logging.debug("添加USIM EF文件 - 数量: %d", len(usim_files))

        # 添加5G相关文件
        df5gs_files = [
            "5GS3GPPLOCI", "5GSN3GPPLOCI", "5GS3GPPNSC", "5GSN3GPPNS",
            "5GAUTHKEYS", "UAC_AIC", "SUCI_Calc_Info", "OPL5G",
            "SUPI_NAI", "Routing_Indicator", "URSP"
        ]
        for file_name in df5gs_files:
            QTreeWidgetItem(df5gs, [file_name])
        logging.debug("添加5G相关文件 - 数量: %d", len(df5gs_files))

        # 创建ISIM分支
        isim = QTreeWidgetItem(self.tree_widget, ["ISIM"])
        logging.debug("创建ISIM分支")

        # 添加ISIM下的EF文件
        isim_files = [
            "IMPI", "IMPU", "DOMAIN", "IST", "P-CSCF", "GBAP", "GBANL",
            "NAFKCA", "UICCIARI", "FromPreferred", "IMSConfigData", "XCAPConfigData"
        ]
        for file_name in isim_files:
            QTreeWidgetItem(isim, [file_name])
        logging.debug("添加ISIM EF文件 - 数量: %d", len(isim_files))
        
        logging.info("文件树形结构构建完成")

    def get_file_path(self, item_text):
        """获取文件对应的EF ID
        
        Args:
            item_text (str): 文件显示名称
            
        Returns:
            str: 对应的EF ID，如果未找到则返回空字符串
        """
        ef_id = self.file_paths.get(item_text, "")
        logging.debug("获取文件路径 - 名称: %s, EF ID: %s", item_text, ef_id)
        return ef_id

    def get_adf_type(self, item_text):
        """获取文件所属的ADF类型
        
        Args:
            item_text (str): 文件显示名称或EF ID
            
        Returns:
            str: 文件所属的ADF类型（USIM/ISIM/MF），默认为USIM
        """
        # 如果传入的是EF ID，先查找对应的文件名
        if item_text in self.file_paths.values():
            file_name = next((key for key, value in self.file_paths.items() 
                            if value == item_text), None)
            if file_name:
                adf_type = self.adf_types.get(file_name, "USIM")
                logging.debug("通过EF ID获取ADF类型 - EF ID: %s, 文件名: %s, ADF类型: %s", 
                            item_text, file_name, adf_type)
                return adf_type
        
        # 如果传入的是文件名，直接查找
        adf_type = self.adf_types.get(item_text, "USIM")
        logging.debug("通过文件名获取ADF类型 - 文件名: %s, ADF类型: %s", 
                     item_text, adf_type)
        return adf_type