# GitLab 发布配置指南

本指南将帮助您配置公司 GitLab 仓库，以便同步代码并发布 Release。

## 📋 前置要求

1. **GitLab 账户**：已有公司 GitLab 账户
2. **GitLab 仓库**：已在 GitLab 上创建项目仓库
3. **PowerShell**：Windows PowerShell 5.1 或更高版本
4. **Git Remote**：已配置 gitlab remote

---

## 🔧 第一步：配置 Git Remote

如果还没有配置 GitLab remote，请执行：

### 方式 A：使用 HTTP（内网推荐，脚本会自动配置）

```bash
# 添加 GitLab remote（使用 HTTP）
git remote add gitlab http://10.129.93.67/hao.lin/mobiletesttool.git

# 验证 remote 配置
git remote -v
```

**注意**：如果 Git 提示 "Unencrypted HTTP is not recommended"，发布脚本会自动配置允许 HTTP 连接（仅针对 GitLab 服务器）。如果是手动推送，可以执行：

```bash
# 配置允许 HTTP（仅针对 GitLab 服务器）
git config --global "http.https://10.129.93.67/.sslVerify" false
```

### 方式 B：使用 SSH（需要配置 SSH Key）

如果您想使用 SSH，需要先配置 SSH Key：

1. **生成 SSH Key**（如果还没有）：
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # 或者使用 RSA
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

2. **复制公钥内容**：
   ```bash
   # Windows
   type %USERPROFILE%\.ssh\id_ed25519.pub
   # 或者
   type %USERPROFILE%\.ssh\id_rsa.pub
   ```

3. **在 GitLab 添加 SSH Key**：
   - 登录 GitLab：`http://10.129.93.67`
   - 点击右上角头像 → "Preferences" → "SSH Keys"
   - 粘贴公钥内容，点击 "Add key"

4. **配置 SSH remote**：
   ```bash
   # 删除旧的 HTTP remote（如果存在）
   git remote remove gitlab
   
   # 添加 SSH remote
   git remote add gitlab git@10.129.93.67:hao.lin/mobiletesttool.git
   
   # 验证 remote 配置
   git remote -v
   ```

**推荐**：对于内网环境，使用 HTTP 方式更简单，脚本会自动处理配置。

---

## 🔑 第二步：创建 GitLab Access Token

GitLab API 需要 Access Token 来创建 Release。

### 2.1 生成 Token

1. 登录公司 GitLab：`http://10.129.93.67`
2. 点击右上角头像 → "Preferences" 或 "Settings"
3. 左侧菜单选择 "Access Tokens"
4. 点击 "Add new token"
5. 填写信息：
   - **Token name**: `MobileTestTool Release Script`
   - **Expiration date**: 设置过期时间（或留空表示永不过期）
   - **Select scopes**: 勾选 `api` 和 `write_repository`
6. 点击 "Create personal access token"
7. **重要**：复制生成的 Token（只显示一次，请妥善保存）

### 2.2 保存 Token（推荐方式）

为了安全，建议将 Token 保存为环境变量或配置文件：

#### 方式 A：使用环境变量（推荐）

**Windows PowerShell:**
```powershell
# 临时设置（当前会话有效）
$env:GITLAB_URL = "http://10.129.93.67"
$env:GITLAB_OWNER = "hao.lin"
$env:GITLAB_REPO = "mobiletesttool"
$env:GITLAB_TOKEN = "your_token_here"

# 永久设置（用户级别，需要重启 PowerShell）
[System.Environment]::SetEnvironmentVariable("GITLAB_URL", "http://10.129.93.67", "User")
[System.Environment]::SetEnvironmentVariable("GITLAB_OWNER", "hao.lin", "User")
[System.Environment]::SetEnvironmentVariable("GITLAB_REPO", "mobiletesttool", "User")
[System.Environment]::SetEnvironmentVariable("GITLAB_TOKEN", "your_token_here", "User")
```

#### 方式 B：创建配置文件

在项目根目录创建 `.gitlab-config.ps1`（已添加到 .gitignore）：

```powershell
$GitLabUrl = "http://10.129.93.67"
$GitLabOwner = "hao.lin"
$GitLabRepo = "mobiletesttool"
$GitLabToken = "your_token_here"
```

---

## 📝 第三步：使用发布脚本

### 3.1 使用便捷脚本（推荐）

```powershell
# 使用便捷脚本（自动加载配置）
.\scripts\release-with-gitlab.ps1 -Version "0.9.6.5.5" -NotesFile "docs\notes.md"
```

### 3.2 直接使用主脚本

```powershell
# 使用环境变量
.\scripts\release.ps1 -Version "0.9.6.5.5" `
    -GitLabUrl "http://10.129.93.67" `
    -GitLabOwner "hao.lin" `
    -GitLabRepo "mobiletesttool" `
    -GitLabToken "your_token" `
    -NotesFile "docs\notes.md"
```

### 3.3 同时发布到多个平台

脚本支持同时发布到 GitHub、Gitee 和 GitLab：

```powershell
.\scripts\release.ps1 -Version "0.9.6.5.5" `
    -GitLabUrl "http://10.129.93.67" `
    -GitLabOwner "hao.lin" `
    -GitLabRepo "mobiletesttool" `
    -GitLabToken "your_gitlab_token" `
    -GiteeOwner "your_gitee_username" `
    -GiteeRepo "MobileTestTool" `
    -GiteeToken "your_gitee_token" `
    -NotesFile "docs\notes.md"
```

---

## 🚀 第四步：执行发布

### 4.1 完整发布流程

```powershell
# 1. 确保代码已提交
git status

# 2. 执行发布（会自动发布到 GitLab）
.\scripts\release-with-gitlab.ps1 -Version "0.9.6.5.5" -NotesFile "docs\notes.md"
```

### 4.2 发布流程说明

脚本会执行以下步骤：

1. **更新版本号**：更新 `core/version.py` 中的版本号
2. **构建打包**：运行 `build_pyqt.bat` 并压缩打包
3. **计算 SHA256**：计算安装包的校验值
4. **生成 latest.json**：生成包含多下载源的配置文件
   - GitHub 下载源（US 和 default）
   - Gitee 下载源（CN，如果配置了）
   - GitLab 下载源（Internal，如果配置了）
5. **Git 提交推送**：提交更改并推送到所有配置的远程仓库
   - GitHub (origin)
   - Gitee (如果配置了)
   - GitLab (gitlab)
6. **创建 Tags**：创建版本标签并推送到所有远程仓库
7. **创建 Releases**：
   - GitHub Release（使用 GitHub CLI，自动上传文件）
   - Gitee Release（如果配置了，需要手动上传文件）
   - GitLab Release（如果配置了，自动上传文件）

### 4.3 GitLab 自动上传文件

脚本会自动上传安装包到 GitLab Release，无需手动操作：

1. 创建 Release 后，脚本会自动上传 ZIP 文件
2. 文件会自动添加到 Release 的 Assets 中
3. 上传成功后，会显示下载 URL

**注意**：如果自动上传失败，脚本会显示警告信息，您可以手动上传文件。

---

## ✅ 验证配置

### 检查 latest.json

发布完成后，检查 `releases/latest.json` 是否包含 GitLab 下载源：

```json
{
  "download_urls": [
    {
      "url": "https://github.com/pranvil/MobileTestTool/releases/download/v0.9.6.5.5/...",
      "region": "us",
      "platform": "windows",
      "priority": 10
    },
    {
      "url": "http://10.129.93.67/hao.lin/mobiletesttool/-/releases/v0.9.6.5.5/downloads/...",
      "region": "internal",
      "platform": "windows",
      "priority": 15
    }
  ]
}
```

### 测试同步

1. **检查代码同步**：在 GitLab 仓库中查看是否有最新代码
2. **检查 Tags**：在 GitLab 仓库的 Tags 页面查看是否有版本标签
3. **检查 Releases**：在 GitLab 仓库的 Releases 页面查看是否有版本发布

---

## 🔒 安全建议

1. **不要将 Token 提交到 Git**：
   - 使用环境变量或配置文件
   - 确保 `.gitlab-config.ps1` 在 `.gitignore` 中

2. **Token 权限最小化**：
   - 只授予必要的权限（`api` 和 `write_repository`）
   - 定期轮换 Token

3. **使用环境变量**：
   - 优先使用系统环境变量
   - 避免在脚本中硬编码

---

## ❓ 常见问题

### Q: GitLab 文件上传失败？

A: 脚本会自动尝试上传文件。如果上传失败，请检查：
1. Token 是否有足够的权限（需要 `api` 和 `write_repository`）
2. 文件大小是否超过 GitLab 限制
3. 网络连接是否正常
4. 如果自动上传失败，可以手动上传文件到 Release 页面

### Q: 如何只同步代码到 GitLab？

A: 可以手动推送：

```bash
# 推送主分支
git push gitlab main

# 推送所有标签
git push gitlab --tags
```

### Q: 可以只发布到 GitLab 吗？

A: 可以，使用 `-SkipPublish` 跳过 GitHub，然后手动创建 GitLab Release。或者只提供 GitLab 参数。

### Q: Token 过期了怎么办？

A: 重新生成 Token 并更新环境变量或配置文件。

### Q: GitLab API 返回 404 错误？

A: 检查以下几点：
1. GitLab URL 是否正确（包含 http:// 或 https://）
2. Owner 和 Repo 名称是否正确（注意大小写）
3. Token 是否有足够的权限
4. 项目路径是否正确编码

### Q: Git 推送时提示 "Unencrypted HTTP is not recommended"？

A: 这是因为 Git 默认不允许未加密的 HTTP 连接。有两种解决方案：

**方案 1（推荐，内网环境）**：脚本会自动配置允许 HTTP，如果手动推送，执行：
```bash
git config --global "http.https://10.129.93.67/.sslVerify" false
```

**方案 2**：使用 SSH（需要配置 SSH Key）：
1. 在 GitLab 添加 SSH Key（Preferences → SSH Keys）
2. 修改 remote 为 SSH：
   ```bash
   git remote set-url gitlab git@10.129.93.67:hao.lin/mobiletesttool.git
   ```

### Q: GitLab 提示需要添加 SSH key？

A: 这个提示只在您使用 SSH 协议时才会出现。如果使用 HTTP，可以忽略此提示。如果使用 SSH，请按照上述步骤添加 SSH Key。

### Q: 如何查看 GitLab 项目路径？

A: 在 GitLab 项目页面，项目路径显示在项目名称下方，格式为 `owner/repo`。

---

## 📚 相关资源

- [GitLab API 文档](https://docs.gitlab.com/ee/api/releases/)
- [GitLab 帮助中心](https://docs.gitlab.com/)
- [项目发布脚本](../scripts/release.ps1)

---

**最后更新**：2025年1月

**仓库地址**：`http://10.129.93.67/hao.lin/mobiletesttool.git`

