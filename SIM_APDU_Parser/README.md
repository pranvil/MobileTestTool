# SIM APDU Viewer

一个用于解析和查看SIM卡APDU（Application Protocol Data Unit）消息的图形化工具，支持eSIM、CAT命令和普通SIM卡消息的解析。

## 功能特性

- **多格式支持**: 支持MTK原始日志、MTK表格格式和通用APDU文本格式
- **消息分类**: 自动识别和分类不同类型的APDU消息
  - eSIM消息 (BFxx系列)
  - CAT命令 (D0系列、80系列、91系列)
  - 普通SIM卡消息
- **详细解析**: 对每种消息类型提供详细的TLV结构解析
- **图形界面**: 基于Tkinter的用户友好界面
- **搜索功能**: 支持正则表达式搜索和过滤
- **复制功能**: 支持复制消息内容和解析结果
- **滚动支持**: 详情区域支持垂直和水平滚动

## 安装依赖

```bash
pip install asn1crypto
```

## 运行方式

### 源码运行
```bash
python main.py
```

### EXE版本
项目提供了预编译的EXE版本，无需安装Python环境即可运行：
- 文件位置：`dist/SIM APDU Viewer.exe`
- 双击运行即可

#### EXE版本功能特性
- 支持加载MTK原始日志文件
- 支持加载APDU文本文件（每行一条）
- 实时搜索和筛选功能
- 详细的APDU解析显示
- 支持复制功能（右键菜单或Ctrl+C）
- 支持快捷键操作（Ctrl+F搜索）

#### EXE版本使用方法
1. **启动程序**: 双击 `SIM APDU Viewer.exe` 启动程序
2. **加载数据**: 
   - 点击"加载 MTK 原始日志"按钮选择MTK日志文件
   - 或点击"加载 APDU 文本（每行）"按钮选择APDU文本文件
3. **筛选和搜索**: 
   - 使用"筛选类别"下拉菜单选择要显示的APDU类型
   - 在搜索框中输入关键词进行搜索
   - 勾选"搜索右侧详情"可在详情内容中搜索
4. **查看详情**: 点击左侧列表中的项目查看详细解析，右侧显示解析树和原始数据
5. **复制功能**: 
   - 右键点击左侧项目可复制标题或原始数据
   - 右键点击右侧详情可复制节点或子树
   - 使用Ctrl+C快捷键快速复制

#### 系统要求
- Windows 10/11
- 无需安装Python环境
- 建议屏幕分辨率 1200x760 或更高

#### 注意事项
- 首次启动可能需要几秒钟时间
- 程序会自动处理各种编码格式的文本文件
- 支持大文件处理，但建议文件大小不超过100MB

## 使用说明

### 加载数据
1. **MTK原始日志**: 点击"加载 MTK 原始日志"按钮，选择包含APDU_tx/APDU_rx格式的日志文件
2. **MTK表格格式**: 支持制表符分隔的表格格式日志（如QXDM导出的格式）
3. **APDU文本**: 点击"加载 APDU 文本（每行）"按钮，选择每行一条APDU的文本文件

### 筛选和搜索
- **类别筛选**: 使用"筛选类别"下拉菜单选择要显示的消息类型
- **文本搜索**: 在搜索框中输入正则表达式进行搜索
- **详情搜索**: 勾选"搜索右侧详情"可在解析结果中搜索

### 查看详情
- 点击左侧列表中的消息可在右侧查看详细解析结果
- 右键菜单提供多种复制选项

## 项目结构

```
├── main.py                 # 主程序入口
├── app/                    # 应用层
│   └── adapter.py          # GUI适配器
├── core/                   # 核心模块
│   ├── models.py           # 数据模型
│   ├── registry.py         # 解析器注册
│   ├── tlv.py             # TLV解析
│   └── utils.py            # 工具函数
├── classify/               # 消息分类
│   └── rules.py           # 分类规则
├── data_io/                # 数据输入输出
│   ├── loaders.py         # 文件加载器
│   └── extractors/         # 数据提取器
│       ├── generic.py      # 通用提取器
│       └── mtk.py          # MTK格式提取器
├── parsers/                # 消息解析器
│   ├── base.py            # 基础解析器
│   ├── esim/              # eSIM消息解析
│   │   └── tlvs/          # eSIM TLV解析器
│   ├── CAT/               # CAT命令解析
│   │   ├── common.py      # 通用CAT解析函数
│   │   ├── terminal_to_uicc.py    # Terminal->UICC命令解析
│   │   ├── uicc_to_terminal.py    # UICC->Terminal命令解析
│   │   ├── terminal_profile_parser.py    # TERMINAL PROFILE解析
│   │   └── terminal_capability_parser.py # TERMINAL CAPABILITY解析
│   ├── SIM_APDU/          # SIM APDU解析
│   └── sim_apdu_parser.py # SIM APDU解析器
├── render/                 # 渲染模块
│   ├── gui_adapter.py     # GUI适配
│   └── tree_builder.py    # 树形结构构建
├── pipeline.py            # 处理管道
└── requirements.txt       # 依赖文件
```

## 支持的消息类型

### eSIM消息 (BFxx系列)
- **BF20/BF22**: GetEuiccInfo1/GetEuiccInfo2
- **BF28**: ListNotificationRequest/Response
- **BF29**: SetNicknameRequest/Response
- **BF2B**: RetrieveNotificationsListRequest/Response
- **BF2D**: ProfileInfoListRequest/Response
- **BF2E**: GetEuiccChallengeRequest/Response
- **BF30**: NotificationSentRequest/Response
- **BF31**: EnableProfileRequest/Response
- **BF32**: DisableProfileRequest/Response
- **BF37**: ProfileInstallationResult
- **BF38**: AuthenticateServerRequest/Response
- **BF3E**: SetNicknameRequest/Response

### CAT命令

#### Terminal => UICC 命令 (80系列)
- **8010**: TERMINAL PROFILE - 终端能力配置，支持详细的位图解析
- **8014**: TERMINAL RESPONSE - 终端响应，支持TLV解析
- **80C2**: ENVELOPE - 封装命令，显示原始数据
- **8012**: FETCH - 获取命令，显示原始数据
- **80AA**: TERMINAL CAPABILITY - 终端能力，支持详细的能力位解析

#### UICC => Terminal 命令
- **D0**: Proactive UICC Command - 主动命令，支持TLV解析
- **91**: Proactive Command Pending - 主动命令待处理，显示长度信息

### 普通SIM卡消息
- **6F**: FCP (File Control Parameters) - 文件控制参数
- **62**: FCP 信息
- 其他标准SIM APDU消息

## 解析特性

### TERMINAL PROFILE (8010)
- 支持29字节的详细能力解析
- 每个能力位独立显示
- 支持电压等级、功率、时钟频率等参数解析
- 垂直显示格式，便于阅读

### TERMINAL CAPABILITY (80AA)
- 支持A9容器标签解析
- 包含以下子标签的详细解析：
  - **80**: Terminal power supply (电源供应)
  - **81**: Extended logical channels (扩展逻辑通道)
  - **82**: Additional interfaces (附加接口)
  - **83**: LPA & Device capabilities (LPA和设备能力)
  - **84**: eUICC-related IoT Device Capabilities (eUICC物联网设备能力)

### CAT TLV解析
- 支持33个常用CAT标签的解析
- 包括Command details、Device identity、Result等
- 支持File List (12/92)的详细解析
- 自动识别标签含义和值

## 快捷键

- `Ctrl+F`: 打开搜索对话框
- `Ctrl+C`: 复制选中内容
- `Ctrl+A`: 全选文本

## 开发说明

项目采用模块化设计，易于扩展新的消息类型解析器。要添加新的解析器：

1. 在相应的解析器目录下创建新的解析器文件
2. 使用`@register`装饰器注册解析器
3. 在相应的`__init__.py`中导入新模块

### CAT解析器扩展
CAT解析器已重构为两个主要方向：
- `terminal_to_uicc.py`: 处理手机发给UICC的命令
- `uicc_to_terminal.py`: 处理UICC发给手机的命令

### 添加新的CAT标签解析
在`parsers/CAT/common.py`的`parse_comp_tlvs_to_nodes`函数中添加新的标签处理逻辑。

## 许可证

本项目采用MIT许可证。