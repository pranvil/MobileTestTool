# GitLab SSH Key 配置指南

本指南将帮助您配置 SSH Key，以便使用 SSH 协议推送代码到 GitLab。

---

## 📋 前置要求

1. **Git 已安装**：确保已安装 Git for Windows
2. **GitLab 账户**：已有公司 GitLab 账户
3. **PowerShell 或 Git Bash**：用于执行命令

---

## 🔑 第一步：检查是否已有 SSH Key

打开 PowerShell 或 Git Bash，执行：

```powershell
# 检查是否已有 SSH key
ls $env:USERPROFILE\.ssh\id_*.pub
```

如果看到 `id_ed25519.pub` 或 `id_rsa.pub` 文件，说明已有 SSH key，可以跳过生成步骤，直接跳到第二步。

---

## 🔧 第二步：生成 SSH Key

### 方式 A：使用 ed25519（推荐，更安全）

```powershell
# 生成 SSH key（替换为您的邮箱）
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 方式 B：使用 RSA（兼容性更好）

```powershell
# 生成 SSH key（替换为您的邮箱）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### 生成过程中的提示

1. **"Enter file in which to save the key"**：
   - 直接按 Enter，使用默认路径（通常是 `C:\Users\您的用户名\.ssh\id_ed25519`）

2. **"Enter passphrase"**：
   - 可以设置密码保护（推荐），也可以直接按 Enter 跳过
   - 如果设置密码，每次使用 SSH 时需要输入密码

3. **"Enter same passphrase again"**：
   - 再次输入密码（如果设置了密码）

### 验证生成成功

```powershell
# 查看生成的公钥
cat $env:USERPROFILE\.ssh\id_ed25519.pub
# 或
cat $env:USERPROFILE\.ssh\id_rsa.pub
```

应该看到类似这样的内容：
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... your_email@example.com
```
或
```
ssh-rsa AAAAB3NzaC1y... your_email@example.com
```

---

## 📋 第三步：复制 SSH 公钥

### 方式 A：使用 PowerShell

```powershell
# 复制 ed25519 公钥到剪贴板
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard

# 或复制 RSA 公钥
Get-Content $env:USERPROFILE\.ssh\id_rsa.pub | Set-Clipboard
```

### 方式 B：手动复制

```powershell
# 显示公钥内容
cat $env:USERPROFILE\.ssh\id_ed25519.pub
```

然后手动复制输出的内容（从 `ssh-ed25519` 或 `ssh-rsa` 开始，到邮箱结束）。

---

## 🔐 第四步：在 GitLab 添加 SSH Key

1. **登录 GitLab**：
   - 访问：`http://10.129.93.67`
   - 使用您的账户登录

2. **打开 SSH Keys 设置**：
   - 点击右上角头像 → **"Preferences"**（偏好设置）
   - 在左侧菜单选择 **"SSH Keys"**

3. **添加 SSH Key**：
   - 在 **"Key"** 文本框中粘贴刚才复制的公钥内容
   - 在 **"Title"** 中输入一个描述性名称（例如：`My Windows PC`）
   - 可选：设置 **"Expires at"**（过期时间）
   - 点击 **"Add key"** 按钮

4. **验证添加成功**：
   - 应该能看到新添加的 SSH key，显示指纹和创建时间

---

## 🔄 第五步：修改 Git Remote 使用 SSH

### 查看当前 remote 配置

```bash
git remote -v
```

应该看到类似：
```
gitlab    http://10.129.93.67/hao.lin/mobiletesttool.git (fetch)
gitlab    http://10.129.93.67/hao.lin/mobiletesttool.git (push)
```

### 修改为 SSH 协议

```bash
# 修改 GitLab remote 为 SSH
git remote set-url gitlab git@10.129.93.67:hao.lin/mobiletesttool.git

# 验证修改
git remote -v
```

现在应该看到：
```
gitlab    git@10.129.93.67:hao.lin/mobiletesttool.git (fetch)
gitlab    git@10.129.93.67:hao.lin/mobiletesttool.git (push)
```

**注意**：SSH URL 格式为 `git@服务器地址:用户名/仓库名.git`

---

## ✅ 第六步：测试 SSH 连接

### 测试连接

```bash
# 测试 SSH 连接到 GitLab
ssh -T git@10.129.93.67
```

**第一次连接时的提示**：
```
The authenticity of host '10.129.93.67' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no)?
```

输入 `yes` 并按 Enter，GitLab 服务器会被添加到已知主机列表。

**成功连接后**，应该看到类似：
```
Welcome to GitLab, @hao.lin!
```

### 如果连接失败

1. **检查 SSH key 是否正确添加**：
   - 回到 GitLab → Preferences → SSH Keys，确认 key 已添加

2. **检查防火墙/网络**：
   - 确保可以访问 `10.129.93.67:22`（SSH 端口）

3. **检查 SSH 配置**：
   ```bash
   # 查看 SSH 配置
   cat $env:USERPROFILE\.ssh\config
   ```

---

## 🚀 第七步：测试推送

### 测试推送代码

```bash
# 创建一个测试提交（可选）
echo "# Test" >> README.md
git add README.md
git commit -m "test: SSH connection"

# 推送到 GitLab
git push gitlab main
```

如果推送成功，说明 SSH 配置完成！

---

## 🔧 常见问题

### Q: 提示 "Permission denied (publickey)"？

**A**: 可能的原因：
1. SSH key 未正确添加到 GitLab
2. 使用了错误的 SSH key
3. GitLab 服务器配置问题

**解决方法**：
- 检查 GitLab 中的 SSH key 是否与本地公钥匹配
- 使用 `ssh -T git@10.129.93.67 -v` 查看详细错误信息

### Q: 提示 "Host key verification failed"？

**A**: 这是首次连接时的正常提示，输入 `yes` 即可。

### Q: 每次都要输入密码？

**A**: 如果生成 SSH key 时设置了密码，可以使用 SSH agent 来避免每次输入：

```powershell
# 启动 SSH agent
Start-Service ssh-agent

# 添加 SSH key 到 agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519
# 或
ssh-add $env:USERPROFILE\.ssh\id_rsa
```

### Q: 如何切换回 HTTP？

**A**: 可以随时切换回 HTTP：

```bash
git remote set-url gitlab http://10.129.93.67/hao.lin/mobiletesttool.git
```

### Q: 多个 GitLab 账户如何使用不同的 SSH key？

**A**: 可以配置 SSH config 文件：

1. 创建/编辑 `C:\Users\您的用户名\.ssh\config`：

```
Host gitlab-company
    HostName 10.129.93.67
    User git
    IdentityFile ~/.ssh/id_ed25519_company
    IdentitiesOnly yes
```

2. 修改 remote URL：

```bash
git remote set-url gitlab git@gitlab-company:hao.lin/mobiletesttool.git
```

---

## 📚 相关资源

- [GitLab SSH 文档](https://docs.gitlab.com/ee/user/ssh.html)
- [Git SSH 配置](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)

---

## ✅ 配置完成检查清单

- [ ] SSH key 已生成
- [ ] SSH 公钥已添加到 GitLab
- [ ] Git remote 已修改为 SSH URL
- [ ] SSH 连接测试成功
- [ ] 代码推送测试成功

---

**配置完成后，您就可以使用 SSH 协议安全地推送代码到 GitLab 了！**

