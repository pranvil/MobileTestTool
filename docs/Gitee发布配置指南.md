# Gitee 发布配置指南

本指南将帮助您配置 Gitee 账户和仓库，以便为国内用户提供更快的下载速度。

## 📋 前置要求

1. **Gitee 账户**：如果没有，请先注册
2. **GitHub 仓库**：已有项目仓库
3. **PowerShell**：Windows PowerShell 5.1 或更高版本

---

## 🔧 第一步：创建 Gitee 账户和仓库

### 1.1 注册 Gitee 账户

1. 访问 [Gitee.com](https://gitee.com)
2. 点击右上角"注册"
3. 填写注册信息并完成注册
4. 验证邮箱（如果需要）

### 1.2 创建 Gitee 仓库

有两种方式：

#### 方式 A：从 GitHub 导入（推荐）

1. 登录 Gitee
2. 点击右上角 "+" → "从 GitHub 导入仓库"
3. 授权 Gitee 访问 GitHub
4. 选择 `pranvil/MobileTestTool` 仓库
5. 点击"导入"
6. 等待导入完成

#### 方式 B：手动创建并同步

1. 登录 Gitee
2. 点击右上角 "+" → "新建仓库"
3. 填写仓库信息：
   - **仓库名称**：`MobileTestTool`
   - **仓库路径**：`pranvil/MobileTestTool`（或您的用户名）
   - **可见性**：公开
4. 点击"创建"
5. 添加 GitHub 作为远程仓库：
   ```bash
   git remote add gitee https://gitee.com/您的用户名/MobileTestTool.git
   ```

---

## 🔑 第二步：创建 Gitee Access Token

Gitee API 需要 Access Token 来创建 Release。

### 2.1 生成 Token

1. 登录 Gitee
2. 点击右上角头像 → "设置"
3. 左侧菜单选择"安全设置" → "私人令牌"
4. 点击"生成新令牌"
5. 填写信息：
   - **令牌描述**：`MobileTestTool Release Script`
   - **权限范围**：勾选 `projects`（仓库权限）
6. 点击"提交"
7. **重要**：复制生成的 Token（只显示一次，请妥善保存）

### 2.2 保存 Token（可选但推荐）

为了安全，建议将 Token 保存为环境变量：

**Windows PowerShell:**
```powershell
# 临时设置（当前会话有效）
$env:GITEE_TOKEN = "your_token_here"

# 永久设置（需要管理员权限）
[System.Environment]::SetEnvironmentVariable("GITEE_TOKEN", "your_token_here", "User")
```

**或者使用统一配置文件（推荐）：**

在项目根目录创建 `.release-config.ps1`（可参考 `.release-config.ps1.example`）：
```powershell
# Gitee 配置
$GiteeOwner = "您的用户名"
$GiteeRepo = "MobileTestTool"
$GiteeToken = "您的Token"

# 也可以同时配置 GitLab
$GitLabUrl = "http://10.129.93.67"
$GitLabOwner = "hao.lin"
$GitLabRepo = "mobiletesttool"
$GitLabToken = "your_gitlab_token"
```

**注意**：`.release-config.ps1` 已添加到 `.gitignore`，不会被提交到仓库。

---

## 📝 第三步：使用发布脚本

### 3.1 使用统一发布脚本（推荐）

现在所有平台使用统一的 `scripts/release.ps1` 脚本，通过 `-Platform` 参数选择发布平台：

```powershell
# 发布到所有已配置的平台（包括 Gitee）
.\scripts\release.ps1 -Version "0.9.6.5.5" -NotesFile "docs\notes.md"

# 仅发布到 Gitee
.\scripts\release.ps1 -Version "0.9.6.5.5" -Platform gitee -NotesFile "docs\notes.md"

# 仅发布到 GitHub
.\scripts\release.ps1 -Version "0.9.6.5.5" -Platform github

# 仅发布到 GitLab
.\scripts\release.ps1 -Version "0.9.6.5.5" -Platform gitlab
```

### 3.2 配置说明

脚本会自动从以下位置加载配置（按优先级）：
1. **环境变量**（最高优先级）
2. **`.release-config.ps1` 配置文件**（项目根目录）

如果使用配置文件，脚本会自动加载，无需手动指定参数。

创建 `scripts\release-with-gitee.ps1`：

```powershell
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = ""
)

# 从环境变量或配置文件读取 Gitee 配置
$giteeOwner = $env:GITEE_OWNER
$giteeRepo = $env:GITEE_REPO
$giteeToken = $env:GITEE_TOKEN

# 如果环境变量未设置，尝试从配置文件读取
if (-not $giteeOwner -and (Test-Path ".\.gitee-config.ps1")) {
    . .\.gitee-config.ps1
    $giteeOwner = $GiteeOwner
    $giteeRepo = $GiteeRepo
    $giteeToken = $GiteeToken
}

if (-not $giteeOwner -or -not $giteeRepo -or -not $giteeToken) {
    Write-Error "Gitee configuration not found. Please set environment variables or create .gitee-config.ps1"
    exit 1
}

& .\scripts\release.ps1 -Version $Version -NotesFile $NotesFile `
    -GiteeOwner $giteeOwner -GiteeRepo $giteeRepo -GiteeToken $giteeToken
```

然后使用：
```powershell
.\scripts\release-with-gitee.ps1 -Version "0.9.6.4.4"
```

---

## 🚀 第四步：执行发布

### 4.1 完整发布流程

```powershell
# 1. 确保代码已提交到 GitHub
git status

# 2. 执行发布（会自动发布到所有已配置的平台）
.\scripts\release.ps1 -Version "0.9.6.5.5" -NotesFile "docs\notes.md"

# 或者仅发布到 Gitee
.\scripts\release.ps1 -Version "0.9.6.5.5" -Platform gitee -NotesFile "docs\notes.md"
```

### 4.2 发布流程说明

脚本会执行以下步骤：

1. **更新版本号**：更新 `core/version.py` 中的版本号
2. **构建打包**：运行 `build.bat` 并压缩打包
3. **计算 SHA256**：计算安装包的校验值
4. **生成 latest.json**：生成包含多下载源的配置文件
   - GitHub 下载源（US 和 default）
   - Gitee 下载源（CN，如果配置了）
5. **Git 提交推送**：提交更改并推送到 GitHub
6. **创建 GitHub Release**：使用 GitHub CLI 创建 Release
7. **创建 Gitee Release**：使用 Gitee API 创建 Release
8. **手动上传文件**：由于 Gitee API 限制，需要手动上传安装包

### 4.3 手动上传安装包到 Gitee

脚本创建 Gitee Release 后，会提示您手动上传：

1. 打开脚本输出的 Gitee Release URL
2. 点击"上传附件"（Upload Attachment）按钮
3. 选择 `dist/MobileTestTool_版本号.zip` 文件
4. 等待上传完成

---

## ✅ 验证配置

### 检查 latest.json

发布完成后，检查 `releases/latest.json` 是否包含 Gitee 下载源：

```json
{
  "download_urls": [
    {
      "url": "https://github.com/pranvil/MobileTestTool/releases/download/v0.9.6.4.4/...",
      "region": "us",
      "platform": "windows",
      "priority": 10
    },
    {
      "url": "https://gitee.com/您的用户名/MobileTestTool/releases/download/v0.9.6.4.4/...",
      "region": "cn",
      "platform": "windows",
      "priority": 20
    },
    {
      "url": "https://github.com/pranvil/MobileTestTool/releases/download/v0.9.6.4.4/...",
      "region": "default",
      "platform": "all",
      "priority": 5
    }
  ]
}
```

### 测试下载

1. **中国用户**：应该自动选择 Gitee 下载源
2. **海外用户**：应该自动选择 GitHub 下载源

---

## 🔒 安全建议

1. **不要将 Token 提交到 Git**：
   - 使用环境变量或配置文件
   - 确保 `.gitee-config.ps1` 在 `.gitignore` 中

2. **Token 权限最小化**：
   - 只授予必要的权限（`projects`）
   - 定期轮换 Token

3. **使用环境变量**：
   - 优先使用系统环境变量
   - 避免在脚本中硬编码

---

## ❓ 常见问题

### Q: Gitee API 上传文件失败？

A: Gitee API 的文件上传功能有限制，脚本会创建 Release 但需要手动上传文件。这是正常流程。

### Q: 如何同步代码到 Gitee？

A: 可以设置 Git 远程仓库：
```bash
git remote add gitee https://gitee.com/您的用户名/MobileTestTool.git
git push gitee main
```

### Q: 可以只发布到 Gitee 吗？

A: 可以，使用 `-SkipPublish` 跳过 GitHub，然后手动创建 Gitee Release。但不推荐，因为海外用户需要 GitHub。

### Q: Token 过期了怎么办？

A: 重新生成 Token 并更新环境变量或配置文件。

---

## 📚 相关资源

- [Gitee API 文档](https://gitee.com/api/v5/swagger)
- [Gitee 帮助中心](https://gitee.com/help)
- [GitHub CLI 文档](https://cli.github.com/manual/)

---

**最后更新**：2025年1月

