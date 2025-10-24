# Tab管理功能说明

## 功能概述

本次更新为手机测试辅助工具添加了三个重要的Tab管理功能：

1. **Tab拖拽排序** - 用户可以通过拖拽来调整Tab的顺序
2. **Tab显示/隐藏** - 用户可以隐藏不需要的Tab
3. **自定义Tab和Card** - 用户可以创建自己的Tab和Card

## 功能详细说明

### 1. Tab拖拽排序

- **启用方式**: 自动启用，无需额外配置
- **使用方法**: 直接拖拽Tab标题即可调整顺序
- **保存机制**: 拖拽后自动保存新的顺序到配置文件
- **配置文件**: `~/.netui/tab_config.json`

### 2. Tab显示/隐藏

- **访问方式**: 在"其他"Tab中点击"📋 Tab管理"按钮
- **功能位置**: Tab管理对话框 -> "Tab排序和显示"标签页
- **使用方法**: 
  - 勾选/取消勾选Tab名称前的复选框来控制显示/隐藏
  - 点击"保存"按钮应用更改
- **即时生效**: 保存后立即重新加载Tab布局

### 3. 自定义Tab和Card

#### 自定义Tab功能

- **创建方式**: Tab管理对话框 -> "自定义Tab"标签页 -> "添加Tab"
- **配置项**:
  - Tab名称
  - 描述信息
  - 包含的Card列表
- **管理功能**:
  - 编辑现有Tab
  - 删除不需要的Tab

#### 自定义Card功能

- **创建方式**: Tab管理对话框 -> "自定义Card"标签页 -> "添加Card"
- **配置项**:
  - Card名称
  - 描述信息
  - 所属Tab
  - 按钮列表（可扩展）
- **管理功能**:
  - 编辑现有Card
  - 删除不需要的Card

## 技术实现

### 新增文件

1. **core/tab_config_manager.py** - Tab配置管理器
   - 负责Tab配置的保存和加载
   - 支持自定义Tab和Card的CRUD操作
   - 提供配置验证和默认值处理

2. **ui/tab_manager_dialog.py** - Tab管理对话框
   - 提供Tab排序和显示控制界面
   - 提供自定义Tab和Card的编辑界面
   - 支持配置的导入导出功能

### 修改文件

1. **ui/main_window.py** - 主窗口
   - 集成Tab配置管理器
   - 启用Tab拖拽功能
   - 实现动态Tab加载和重新加载
   - 添加Tab管理对话框调用

2. **ui/tabs/other_tab.py** - 其他Tab
   - 添加"📋 Tab管理"按钮
   - 支持语言切换时的文本刷新

## 配置文件格式

Tab配置保存在 `~/.netui/tab_config.json` 文件中：

```json
{
  "tab_order": ["log_control", "log_filter", "network_info", ...],
  "tab_visibility": {
    "log_control": true,
    "log_filter": true,
    "network_info": false,
    ...
  },
  "custom_tabs": [
    {
      "id": "custom_001",
      "name": "自定义Tab",
      "description": "描述信息",
      "cards": [],
      "created_time": "2024-01-01T00:00:00",
      "visible": true
    }
  ],
  "custom_cards": [
    {
      "id": "card_001",
      "name": "自定义Card",
      "description": "描述信息",
      "tab_id": "custom_001",
      "buttons": [],
      "created_time": "2024-01-01T00:00:00"
    }
  ],
  "version": "1.0",
  "last_updated": "2024-01-01T00:00:00"
}
```

## 使用流程

### 基本使用

1. **调整Tab顺序**: 直接拖拽Tab标题
2. **隐藏Tab**: 
   - 点击"其他"Tab中的"📋 Tab管理"
   - 在"Tab排序和显示"中取消勾选不需要的Tab
   - 点击"保存"

### 高级使用

1. **创建自定义Tab**:
   - 打开Tab管理对话框
   - 切换到"自定义Tab"标签页
   - 点击"添加Tab"
   - 填写Tab信息并保存

2. **创建自定义Card**:
   - 在Tab管理对话框中切换到"自定义Card"标签页
   - 点击"添加Card"
   - 选择所属Tab并填写Card信息
   - 保存配置

## 注意事项

1. **配置备份**: 建议定期备份 `~/.netui/tab_config.json` 文件
2. **重置功能**: 可以使用"重置为默认"功能恢复原始配置
3. **自定义Tab**: 目前自定义Tab为简单实现，后续可以扩展为完整的动态UI生成
4. **兼容性**: 新功能向后兼容，不会影响现有配置

## 后续扩展计划

1. **动态UI生成**: 支持完全自定义的Tab和Card布局
2. **按钮模板**: 提供常用按钮模板
3. **配置导入导出**: 支持配置文件的导入导出
4. **主题支持**: 为自定义Tab和Card提供主题支持
