# 卡片阴影效果使用指南

## 📋 概述

本指南展示了如何在PyQt5应用中实现现代化的卡片阴影效果。

## 🎨 效果预览

- **阴影模糊半径**: 18px
- **阴影偏移**: 0, 4px（轻微下坠）
- **阴影颜色**: 黑色，30%透明度
- **圆角**: 10px
- **悬停效果**: 背景变亮 + 边框变亮

## 🚀 快速开始

### 方法1：使用 QFrame + QGraphicsDropShadowEffect（推荐）

#### 步骤1：导入必要的模块

```python
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
```

#### 步骤2：创建卡片容器

```python
# 创建卡片容器
card = QFrame()
card.setObjectName("card")

# 添加阴影效果
shadow = QGraphicsDropShadowEffect(card)
shadow.setBlurRadius(18)              # 模糊半径
shadow.setOffset(0, 4)                # 轻微下坠
shadow.setColor(QColor(0, 0, 0, 120)) # 黑色，30%透明度
card.setGraphicsEffect(shadow)
```

#### 步骤3：设置布局和内容

```python
# 设置布局
layout = QVBoxLayout(card)
layout.setContentsMargins(14, 14, 14, 14)
layout.setSpacing(10)

# 添加标题
title = QLabel("MTKLOG 控制")
title.setObjectName("section-title")
layout.addWidget(title)

# 添加其他内容...
# ... 按钮等控件 ...
```

### 方法2：使用 QGroupBox（当前方案）

如果使用 QGroupBox，阴影效果会受限，但可以通过CSS实现部分效果：

```css
QGroupBox {
    background-color: #2E2E2E;
    border: 1px solid #3F3F3F;
    border-left: 3px solid #66B3FF;
    border-radius: 6px;
    padding: 16px;
    margin: 16px 4px 8px 4px;
}

QGroupBox:hover {
    background-color: #333333;
    border-color: #4F4F4F;
}
```

## 📝 完整示例

参考 `card_shadow_example.py` 文件，其中包含：

1. **完整的卡片创建示例**
2. **如何在 log_control_tab.py 中应用**
3. **最佳实践和注意事项**

## 🎯 最佳实践

### 推荐结构

```
QLabel.section-title（标题）
    ↓
QFrame#card（卡片容器 + 阴影）
    ↓
    内容（按钮、输入框等）
```

### 样式配置

```css
/* 卡片容器 */
QFrame#card {
    background: #2E2E2E;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 14px;
    margin: 18px 6px 12px 6px;
}

QFrame#card:hover {
    background: #333333;
    border-color: #4F4F4F;
}

/* 分区标题 */
QLabel.section-title {
    color: #66B3FF;
    font-weight: 600;
    padding: 2px 6px;
    margin: 8px 2px 6px 2px;
    background: transparent;
    border: none;
}
```

## 🔧 改造现有代码

### 改造前（QGroupBox）

```python
def create_mtklog_group(self):
    group = QGroupBox("MTKLOG 控制")
    layout = QVBoxLayout(group)
    
    # ... 添加控件 ...
    
    return group
```

### 改造后（QFrame + 阴影）

```python
def create_mtklog_group(self):
    # 创建卡片容器
    card = QFrame()
    card.setObjectName("card")
    
    # 添加阴影效果
    shadow = QGraphicsDropShadowEffect(card)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 120))
    card.setGraphicsEffect(shadow)
    
    # 设置布局
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(10)
    
    # 添加标题
    title = QLabel("MTKLOG 控制")
    title.setObjectName("section-title")
    layout.addWidget(title)
    
    # ... 添加原有控件 ...
    
    return card
```

## ⚠️ 注意事项

1. **性能考虑**: 阴影效果会略微影响性能，建议不要过度使用
2. **颜色调整**: 根据主题调整阴影颜色和透明度
3. **圆角一致性**: 保持卡片圆角与阴影的协调性
4. **间距控制**: 卡片之间的间距要适中，避免过于拥挤

## 🎨 自定义选项

### 调整阴影强度

```python
# 轻微阴影
shadow.setBlurRadius(12)
shadow.setColor(QColor(0, 0, 0, 80))

# 强烈阴影
shadow.setBlurRadius(24)
shadow.setColor(QColor(0, 0, 0, 150))
```

### 调整阴影方向

```python
# 右下角阴影
shadow.setOffset(4, 4)

# 正下方阴影
shadow.setOffset(0, 6)

# 无偏移（浮空效果）
shadow.setOffset(0, 0)
```

## 📚 相关文件

- `ui/resources/themes/dark.qss` - 主题样式文件
- `ui/tabs/card_shadow_example.py` - 完整示例代码
- `ui/tabs/log_control_tab.py` - 实际应用场景

## 🐛 常见问题

### Q1: 阴影不显示？
- 检查是否正确调用了 `setGraphicsEffect()`
- 确认卡片背景色不是透明的

### Q2: 阴影太暗/太亮？
- 调整 `QColor` 的 alpha 值（0-255）
- 调整 `setBlurRadius()` 的值

### Q3: 性能问题？
- 减少阴影数量
- 降低 `setBlurRadius()` 的值
- 使用更简单的边框效果代替阴影

