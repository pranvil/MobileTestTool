# JIRA 自动化工具 (JIRA Automation Tool)

基于 **PySide6** 的图形化 JIRA 自动化工具，用于通过 REST API 与 JIRA 系统（TCL Internal）进行交互。

## 📋 目录

- [功能特性](#-功能特性)
- [环境准备](#-环境准备)
- [快速开始](#-快速开始)
- [功能模块](#-功能模块)
  - [1. 查询Issue评论](#1-查询issue评论)
  - [2. 批量创建Test Progress](#2-批量创建test-progress)
- [项目结构](#-项目结构)
- [常见问题 (FAQ)](#-常见问题-faq)

---

## ✨ 功能特性

- 🖥️ **图形化界面**：基于 PySide6 的现代化 GUI，操作简单直观
- 🔐 **安全配置**：Token 存储在配置文件中，不会泄露到代码中
- ✅ **智能校验**：两层校验机制（文件级 + 行级），确保数据质量
- 📊 **详细日志**：所有操作记录日志，便于问题排查
- 🚀 **异步处理**：长时间操作使用多线程，界面不卡顿
- 📁 **统一输出**：所有输出文件统一管理，结构清晰

---

## 🛠 环境准备

### 系统要求

- Python **3.8+**
- 网络环境：需连接公司内网或 VPN（访问 `jira.tcl.com`）

### 安装依赖

在终端运行以下命令安装所需 Python 库：

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install PySide6 PySide6-WebEngine requests pandas openpyxl urllib3
```

---

## 🚀 快速开始

### 1. 启动程序

```bash
python main.py
```

### 2. 配置 Token

首次运行需要配置 JIRA URL 和 API Token：

1. 点击菜单栏 **文件 → 设置** 或工具栏的 **设置** 按钮
2. 填写 JIRA URL（默认：`https://jira.tcl.com`）
3. 填写 Personal Access Token（见下方获取方法）
4. 点击 **验证Token** 测试配置
5. 点击 **保存** 保存配置

#### 获取 Personal Access Token

1. 登录 JIRA **Profile**
2. 在左侧菜单点击 **Personal Access Tokens**
3. 点击 **Create token**，设置名称和过期时间
4. 复制生成的 Token 并粘贴到设置对话框中

> ⚠️ **安全提示**：请勿将包含真实 Token 的代码上传到公共代码仓库（如 GitHub）。配置文件 `config/config.ini` 已在 `.gitignore` 中排除。

---

## 🚀 功能模块

### 1. 查询Issue评论

用于获取指定 Issue 的所有评论，并生成 HTML 文件。

#### 使用步骤

1. 在左侧导航栏选择 **查询评论**
2. 在输入框中输入 Issue Key（如：`GF65DISH-1347`）
3. 点击 **查询** 按钮
4. 查询成功后，点击 **打开文件** 按钮在浏览器中查看 HTML 文件

#### GUI 预览（推荐）

- 勾选 **在GUI预览**：直接在应用内预览评论（渲染引擎优先使用 `PySide6-WebEngine`，效果接近浏览器）
- 勾选 **显示图片**：会尝试把评论里的图片下载到本地，并在预览/HTML中用本地资源展示

#### 输出说明

- 输出位置：`output/comments/{IssueKey}_comments.html`
- 格式：完整的 HTML 文件，保留 JEditor 插件的表格样式和格式
- 适用场景：查看带有复杂格式（颜色、表格）的 Log 分析记录

#### 图片资源说明（方案2）

- 图片会保存到：`output/comments/{IssueKey}_assets/`
- HTML 中图片链接会改写为相对路径：`{IssueKey}_assets/...`
- 如果图片下载失败（权限/链接格式等），文字仍可正常显示，图片会自动降级为不显示

---

### 2. 批量创建Test Progress

用于从 Excel 表格中批量创建 Test Progress 类型的 Issue。

#### Excel 模板

模板文件位置：`templates/test_plan_template.xlsx`

#### 必需列（区分大小写）

| 列名 | 说明 | 示例 |
|------|------|------|
| `Project` | 项目 Key | `MNTNPDH` |
| `Summary` | Issue 摘要 | `US VAL Sanity Test` |
| `StartDate` | 计划开始日期 | `2025-01-01` |
| `FinishDate` | 计划完成日期 | `2025-01-10` |

#### 可选列

| 列名 | 说明 | 示例 |
|------|------|------|
| `Amount - Function` | 额外数值字段（如填写会写入JIRA对应字段） | `3` |

#### 使用步骤

1. 在左侧导航栏选择 **创建Test Progress**
2. 点击 **选择Excel文件** 按钮，选择包含数据的 Excel 文件
3. 查看数据预览和校验结果
4. 选择创建选项：
   - **跳过错误行继续创建**（推荐）：只创建有效数据，跳过错误行
   - **全部失败不创建**：如果有任何错误，不创建任何 Issue
5. 点击 **开始创建** 按钮
6. 查看创建结果和统计信息

#### 校验机制

**文件级校验**：
- 检查必需列是否存在
- 如果缺列，直接拒绝，不进行后续处理

**行级校验**：
- Project 字段为空或包含多余空格
- Summary 字段为空
- StartDate/FinishDate 格式错误
- StartDate 不能晚于 FinishDate
- Project Key 格式验证

#### 输出说明

- **成功创建的 Issue**：显示 Issue Key 和摘要
- **错误报告**：失败的行导出到 `output/error_reports/error_report_YYYYMMDD_HHMMSS.xlsx`
- **创建日志**：详细日志保存到 `output/create_progress_logs/create_progress_YYYYMMDD_HHMMSS.log`

---

### 3. Issue Export（导出 Excel）

用于通过 Better Excel 插件接口，按 JQL 导出 Issue 列表为 `.xlsx` 文件，并支持管理“常用 JQL”。（导出接口 base URL 使用设置里的 JIRA URL）

#### 使用步骤

1. 在左侧导航栏选择 **Issue Export**
2. 在 **JQL** 输入框中输入要导出的 JQL
3. 点击 **导出 Excel**，选择保存路径，程序会下载并保存 `.xlsx`

#### 常用 JQL

- 点击 **添加为常用 JQL**：弹窗输入名称后保存
- 右侧列表支持：
  - **加载 JQL**：将选中记录的 JQL 填回输入框
  - **删除**：删除选中的常用 JQL

#### 数据文件位置

- 常用 JQL 会保存到：`output/cache/jql_records.json`

## 📁 项目结构

```
Jira/
├── main.py                    # 程序入口
├── jira_client.py             # JIRA API 客户端封装
├── core/                      # 核心模块
│   ├── paths.py              # 路径管理
│   ├── logger.py             # 日志系统
│   ├── exceptions.py         # 异常类定义
│   └── config_manager.py     # 配置管理
├── ui/                        # UI 模块
│   ├── main_window.py        # 主窗口
│   ├── settings_dialog.py    # 设置对话框
│   ├── comment_widget.py     # 查询评论界面
│   └── create_widget.py      # 创建Test Progress界面
├── modules/                   # 业务逻辑模块
│   ├── comment_fetcher.py    # 查询评论逻辑
│   └── test_progress_creator.py  # 创建Test Progress逻辑
├── config/                    # 配置文件目录
│   └── config.ini            # 配置文件（.gitignore）
├── output/                    # 输出目录（.gitignore）
│   ├── logs/                 # 应用日志
│   │   └── app.log
│   ├── comments/             # 评论HTML文件
│   ├── create_progress_logs/ # 创建进度日志
│   └── error_reports/        # 错误报告Excel/CSV
├── templates/                 # 模板文件
│   └── test_plan_template.xlsx  # Excel模板
├── requirements.txt           # 依赖列表
└── README.md                  # 本文档
```

---

## ❓ 常见问题 (FAQ)

### Q1: 为什么代码里有 `verify=False` 和 `InsecureRequestWarning`?

**A:** 因为 `jira.tcl.com` 使用的是公司内网自签名的 SSL 证书，Python 默认不信任。  
`verify=False` 用于跳过证书验证，`urllib3.disable_warnings` 用于屏蔽控制台的警告信息。

### Q2: 创建Issue时报错 `"Field 'description' cannot be set"`?

**A:** JIRA API 的限制规则：如果某个字段没有出现在 JIRA 网页端的"创建界面"上，API 就无法给它赋值。  
目前 **Test Progress** 类型隐藏了描述字段，因此不能设置该字段。

### Q3: 程序报错 `401 Unauthorized`?

**A:** Token 可能已过期或填写错误。请：
1. 检查 Token 是否正确复制（不要包含多余空格）
2. 重新生成 Token 并更新配置
3. 使用 **设置** 对话框中的 **验证Token** 功能测试 Token 是否有效

### Q4: 如何查看日志排查问题?

**A:** 有两种方式：
1. 点击菜单栏 **帮助 → 打开日志** 或工具栏的 **打开日志** 按钮
2. 直接打开文件：`output/logs/app.log`

### Q5: Excel 文件校验失败怎么办?

**A:** 检查以下几点：
- 确保列名完全匹配（区分大小写）：`Project`, `Summary`, `StartDate`, `FinishDate`
- 检查日期格式是否正确
- 查看校验结果中的详细错误信息，修正对应的行数据
- 可以选择"跳过错误行继续创建"，先处理有效数据

### Q6: 创建Issue时如何支持不同的项目?

**A:** Excel 文件的 `Project` 列可以包含不同的项目 Key，程序会自动根据每行的 Project 值创建对应项目的 Issue。

---

## 📝 技术说明

### 动态字段映射

程序支持动态获取不同 Project/IssueType 的字段定义，自动处理：
- 自定义字段（customfield_XXXXX）的映射
- 日期格式转换（Excel格式 → JIRA格式）
- 字段名称到字段ID的匹配

### 扩展性设计

如需添加新功能：
1. 在 `modules/` 创建业务逻辑文件
2. 在 `ui/` 创建对应的 Widget
3. 在 `main_window.py` 的侧边栏添加新菜单项

---

## 📄 许可证

内部使用工具，仅供 TCL 内部使用。
