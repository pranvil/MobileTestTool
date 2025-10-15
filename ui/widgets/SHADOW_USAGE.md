# 阴影效果使用指南

## 📋 概述

本模块提供了便捷的阴影效果工具函数，用于给PyQt5控件添加现代化的阴影效果。

## 🚀 快速开始

### 1. 导入模块

```python
from ui.widgets.shadow_utils import add_card_shadow
```

### 2. 给卡片添加阴影

```python
from PyQt5.QtWidgets import QFrame

# 创建卡片
card = QFrame()
card.setObjectName("card")

# 添加阴影
add_card_shadow(card)
```

## 📚 可用函数

### `add_shadow(widget, blur, dx, dy, alpha)`

通用阴影函数，可以自定义所有参数。

**参数：**
- `widget`: 要添加阴影的控件
- `blur`: 模糊半径（默认18）
- `dx`: 水平偏移（默认0）
- `dy`: 垂直偏移（默认4）
- `alpha`: 透明度0-255（默认120）

**示例：**
```python
from ui.widgets.shadow_utils import add_shadow

# 自定义阴影
add_shadow(card, blur=20, dx=0, dy=5, alpha=150)
```

### `add_card_shadow(widget)`

给卡片添加标准阴影效果（最常用）。

**参数：**
- `widget`: 要添加阴影的卡片控件

**效果：**
- 模糊半径：18px
- 垂直偏移：4px（轻微下坠）
- 透明度：47%（120/255）

**示例：**
```python
from ui.widgets.shadow_utils import add_card_shadow

card = QFrame()
card.setObjectName("card")
add_card_shadow(card)
```

### `add_light_shadow(widget)`

给控件添加轻微阴影效果，适用于较小的元素。

**效果：**
- 模糊半径：12px
- 垂直偏移：2px
- 透明度：31%（80/255）

**示例：**
```python
from ui.widgets.shadow_utils import add_light_shadow

small_card = QFrame()
add_light_shadow(small_card)
```

### `add_strong_shadow(widget)`

给控件添加强烈阴影效果，适用于需要突出显示的元素。

**效果：**
- 模糊半径：24px
- 垂直偏移：6px
- 透明度：59%（150/255）

**示例：**
```python
from ui.widgets.shadow_utils import add_strong_shadow

important_card = QFrame()
add_strong_shadow(important_card)
```

### `add_floating_shadow(widget)`

给控件添加浮空阴影效果，无偏移，适合悬浮按钮等。

**效果：**
- 模糊半径：20px
- 偏移：0, 0（无偏移）
- 透明度：39%（100/255）

**示例：**
```python
from ui.widgets.shadow_utils import add_floating_shadow

floating_btn = QPushButton()
add_floating_shadow(floating_btn)
```

### `remove_shadow(widget)`

移除控件的阴影效果。

**示例：**
```python
from ui.widgets.shadow_utils import remove_shadow

# 移除阴影
remove_shadow(card)
```

## 🎨 完整示例

### 示例1：创建带阴影的卡片

```python
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from ui.widgets.shadow_utils import add_card_shadow

def create_card(title, buttons):
    """创建带阴影的卡片"""
    # 创建卡片容器
    card = QFrame()
    card.setObjectName("card")
    
    # 添加阴影效果
    add_card_shadow(card)
    
    # 设置布局
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 14, 14, 14)
    
    # 添加内容
    title_label = QLabel(title)
    title_label.setObjectName("section-title")
    layout.addWidget(title_label)
    
    for btn_text in buttons:
        btn = QPushButton(btn_text)
        layout.addWidget(btn)
    
    return card

# 使用
mtklog_card = create_card("MTKLOG 控制", ["开启", "停止导出", "删除"])
```

### 示例2：动态添加/移除阴影

```python
from PyQt5.QtWidgets import QPushButton
from ui.widgets.shadow_utils import add_card_shadow, remove_shadow

card = QFrame()
card.setObjectName("card")

# 添加阴影
add_card_shadow(card)

# 某些条件下移除阴影
if some_condition:
    remove_shadow(card)

# 重新添加阴影
add_card_shadow(card)
```

### 示例3：不同类型控件的阴影

```python
from PyQt5.QtWidgets import QFrame, QPushButton, QWidget
from ui.widgets.shadow_utils import (
    add_card_shadow, 
    add_light_shadow, 
    add_strong_shadow,
    add_floating_shadow
)

# 卡片：标准阴影
card = QFrame()
card.setObjectName("card")
add_card_shadow(card)

# 小卡片：轻微阴影
small_card = QFrame()
add_light_shadow(small_card)

# 重要卡片：强烈阴影
important_card = QFrame()
add_strong_shadow(important_card)

# 悬浮按钮：浮空阴影
floating_btn = QPushButton("悬浮")
add_floating_shadow(floating_btn)
```

## ⚙️ 配合QSS使用

确保在QSS中为卡片设置了足够的margin，让阴影有空间显示：

```css
/* 卡片容器样式 */
QFrame#card {
    background: #2E2E2E;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 14px;
    margin: 18px 8px 14px 8px;  /* 重要：给阴影留空间 */
}

QFrame#card:hover {
    background: #333333;
    border-color: #4F4F4F;
}
```

## 🎯 最佳实践

1. **卡片间距**：确保卡片之间有足够的间距（至少16-18px），让阴影能够完全显示
2. **背景色**：使用深色背景（#262626）以突出阴影效果
3. **圆角一致性**：阴影的模糊半径应该与卡片的圆角协调
4. **性能考虑**：不要给太多控件同时添加阴影，会影响性能
5. **层次感**：使用不同强度的阴影来区分元素的层级

## 🐛 常见问题

### Q1: 阴影不显示？
- 检查控件是否有背景色
- 确认控件在父容器中可见
- 检查父容器的背景色是否与阴影颜色太接近

### Q2: 阴影被裁剪？
- 增加父容器的margin或padding
- 确保父容器没有设置`clip: true`
- 检查是否有其他控件覆盖在阴影上方

### Q3: 性能问题？
- 减少阴影数量
- 降低模糊半径（blur值）
- 使用更简单的边框效果代替阴影

## 📚 相关文件

- `ui/widgets/shadow_utils.py` - 阴影工具函数
- `ui/resources/themes/dark.qss` - 主题样式文件
- `ui/tabs/card_demo.py` - 完整示例
- `ui/tabs/CARD_SHADOW_README.md` - 详细文档

