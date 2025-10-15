# 深色主题修复总结

## 🎯 修复的问题

### 1️⃣ 白色空白区域问题

**问题：** 应用中出现白色条带/空白块

**原因：**
- 只给部分控件设置了深色背景
- Tab页内部容器、滚动区域、普通QWidget等容器仍是系统默认的白色背景

**解决方案：**
在QSS顶部添加全局容器底色：

```css
/* 全局容器底色 */
QWidget {
    background-color: #262626;
    color: #EAEAEA;
}

/* Tab 内容区 */
QTabWidget QWidget {
    background-color: #262626;
}

/* 滚动区域 */
QAbstractScrollArea,
QScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QAbstractScrollArea::viewport {
    background-color: #262626;
    border: none;
}
```

### 2️⃣ 卡片没有立体效果

**问题：** 卡片看起来像面板，没有层次感

**原因：**
- 使用QGroupBox + 左侧蓝边，更像"分组标签"
- QSS不支持box-shadow，无法仅靠CSS实现阴影

**解决方案：**

#### 方案A：使用QFrame + 阴影（推荐）

**Python代码：**
```python
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor

def add_shadow(widget, blur=18, dx=0, dy=4, alpha=120):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(dx, dy)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)

# 使用
card = QFrame()
card.setObjectName("card")
add_shadow(card)
```

**配套QSS：**
```css
QFrame#card {
    background: #2E2E2E;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 14px;
    margin: 18px 8px 14px 8px;  /* 给阴影留空间 */
}

QLabel.section-title {
    color: #66B3FF;
    font-weight: 600;
    padding: 2px 6px;
    margin: 10px 2px 6px 2px;
    background: transparent;
    border: none;
}
```

#### 方案B：使用QGroupBox（伪立体）

**QSS：**
```css
QGroupBox {
    background-color: #2E2E2E;
    border: 1px solid #1F1F1F;
    border-radius: 8px;
    padding: 14px 12px 12px 12px;
    margin: 18px 8px 14px 8px;
}

QGroupBox::title {
    color: #66B3FF;
    font-weight: bold;
    background: #2E2E2E;
    padding: 4px 10px;
    margin-left: 10px;
}
```

### 3️⃣ 其他小问题修复

#### 问题A：负margin导致标题压线

**修复前：**
```css
QGroupBox::title {
    margin-top: -8px;  /* 负margin */
}
```

**修复后：**
```css
QGroupBox {
    padding-top: 14px;  /* 给标题让位 */
}

QGroupBox::title {
    /* 去掉负margin */
}
```

#### 问题B：分隔线选择器过宽

**修复前：**
```css
QFrame[frameShape="4"], QFrame::horizontal { ... }
/* QFrame::horizontal 会误伤其他QFrame */
```

**修复后：**
```css
QFrame[frameShape="4"] { ... }
/* 只针对HLine */
```

#### 问题C：重复的QCheckBox定义

**修复前：**
```css
QCheckBox::indicator:checked { ... }
QCheckBox::indicator:checked { ... }  /* 重复 */
```

**修复后：**
```css
QCheckBox::indicator:checked {
    /* 合并为一段 */
}
```

## 📁 文件清单

### 更新的文件

1. **`ui/resources/themes/dark.qss`**
   - 添加全局容器底色
   - 添加Tab和滚动区域样式
   - 优化卡片样式
   - 统一背景色为 #262626
   - 修复所有小问题

### 新增的文件

2. **`ui/widgets/shadow_utils.py`**
   - 阴影效果工具函数
   - 提供多种预设阴影配置
   - 方便项目中使用

3. **`ui/tabs/card_demo.py`**
   - 完整的卡片demo
   - 可直接运行查看效果
   - 展示最佳实践

4. **`ui/tabs/card_shadow_example.py`**
   - 示例代码
   - 可复用的函数
   - 使用说明

5. **`ui/widgets/SHADOW_USAGE.md`**
   - 阴影效果使用指南
   - 完整示例
   - 最佳实践

6. **`ui/tabs/CARD_SHADOW_README.md`**
   - 卡片阴影详细文档
   - 改造指南
   - 常见问题

## 🚀 如何使用

### 方法1：使用工具函数（推荐）

```python
from ui.widgets.shadow_utils import add_card_shadow
from PyQt5.QtWidgets import QFrame

# 创建卡片
card = QFrame()
card.setObjectName("card")

# 添加阴影
add_card_shadow(card)
```

### 方法2：直接使用demo代码

```python
from ui.tabs.card_demo import make_card, make_shadow

# 创建卡片
card = make_card("MTKLOG 控制", ["开启", "停止导出", "删除"])
```

### 方法3：手动添加阴影

```python
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor

card = QFrame()
shadow = QGraphicsDropShadowEffect(card)
shadow.setBlurRadius(18)
shadow.setOffset(0, 4)
shadow.setColor(QColor(0, 0, 0, 120))
card.setGraphicsEffect(shadow)
```

## 🎨 样式要点

### 颜色方案

- **主背景**: #262626（深灰）
- **卡片背景**: #2E2E2E（稍亮）
- **边框**: #333333（柔和）
- **标题文字**: #66B3FF（亮蓝）
- **按钮文字**: #EAEAEA（浅灰）

### 间距规范

- **卡片margin**: 18px 8px 14px 8px
- **卡片padding**: 14px
- **标题margin**: 10px 2px 6px 2px
- **圆角**: 10px（卡片） / 8px（QGroupBox）

### 阴影参数

- **模糊半径**: 18px
- **垂直偏移**: 4px
- **透明度**: 120/255（约47%）

## ✅ 验证清单

- [x] 全局容器底色设置
- [x] Tab内容区背景色
- [x] 滚动区域背景色
- [x] 卡片样式优化
- [x] 阴影效果工具函数
- [x] 完整示例代码
- [x] 使用文档
- [x] 所有小问题修复

## 🎯 预期效果

应用现在应该具有：
- ✅ 统一的深色背景，无白色空白
- ✅ 有层次感的卡片设计
- ✅ 柔和的阴影效果
- ✅ 清晰的视觉分层
- ✅ 现代化的UI风格

## 📚 相关文档

- `ui/widgets/SHADOW_USAGE.md` - 阴影效果使用指南
- `ui/tabs/CARD_SHADOW_README.md` - 卡片阴影详细文档
- `ui/tabs/card_demo.py` - 完整可运行demo

## 🐛 常见问题

### Q1: 阴影不显示？
- 确保控件有背景色
- 检查父容器是否有足够的margin
- 确认没有其他控件覆盖

### Q2: 白色区域还在？
- 检查是否应用了新的QSS
- 确认所有容器都设置了背景色
- 查看是否有内联样式覆盖

### Q3: 性能问题？
- 减少阴影数量
- 降低模糊半径
- 使用更简单的边框效果

## 📞 技术支持

如有问题，请参考：
1. `ui/widgets/SHADOW_USAGE.md` - 详细使用指南
2. `ui/tabs/card_demo.py` - 完整示例代码
3. `ui/tabs/CARD_SHADOW_README.md` - 详细文档

