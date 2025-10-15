# 阴影工具优化说明

## 🎯 优化内容

### 1️⃣ 类型标注与参数校验

#### 类型标注
所有函数都添加了完整的类型标注，便于IDE智能提示和静态检查：

```python
def add_shadow(
    widget: QWidget,
    blur: float = 18,
    dx: float = 0,
    dy: float = 4,
    alpha: int = 120,
    color: Optional[Union[QColor, Tuple[int, int, int]]] = None
) -> QGraphicsDropShadowEffect:
    ...
```

**好处：**
- IDE智能提示更准确
- 静态类型检查（如mypy）可以发现问题
- 代码更易维护和理解

#### 参数校验与限制

```python
# 自动限制blur ≥ 0
blur = max(0, blur)

# 自动限制alpha在0-255范围
alpha = max(0, min(255, int(alpha)))
```

**好处：**
- 避免异常值导致的显示问题
- 防止负数blur或超出范围的alpha
- 自动修正用户输入的错误值

### 2️⃣ 幂等性与复用

#### 问题
旧版本每次调用都会创建新的effect，导致：
- 内存泄漏
- 性能问题
- 无法更新现有effect

#### 解决方案
检查是否已存在QGraphicsDropShadowEffect：

```python
existing_effect = widget.graphicsEffect()
if isinstance(existing_effect, QGraphicsDropShadowEffect):
    # 更新现有effect
    existing_effect.setBlurRadius(blur)
    existing_effect.setOffset(dx, dy)
    existing_effect.setColor(shadow_color)
    return existing_effect
else:
    # 创建新effect
    ...
```

**好处：**
- 多次调用不会重复创建effect
- 可以安全地更新阴影参数
- 避免内存泄漏

**示例：**
```python
# 第一次调用：创建effect
add_shadow(card, blur=18)

# 第二次调用：更新现有effect（不会创建新的）
add_shadow(card, blur=24)  # 更新blur

# 第三次调用：再次更新
add_shadow(card, blur=30, alpha=150)  # 更新blur和alpha
```

### 3️⃣ 主题化与可扩展

#### 自定义颜色支持

现在支持多种颜色格式：

```python
# 方式1：使用QColor
from PyQt5.QtGui import QColor
add_shadow(card, color=QColor(255, 0, 0), alpha=120)

# 方式2：使用RGB元组
add_shadow(card, color=(255, 0, 0), alpha=120)

# 方式3：默认黑色
add_shadow(card, alpha=120)  # 默认黑色
```

**实现：**
```python
if color is None:
    shadow_color = QColor(0, 0, 0, alpha)
elif isinstance(color, QColor):
    shadow_color = QColor(color)
    shadow_color.setAlpha(alpha)
elif isinstance(color, (tuple, list)) and len(color) >= 3:
    shadow_color = QColor(color[0], color[1], color[2], alpha)
```

#### 预设方法优化

所有预设方法都直接调用统一的`add_shadow`：

```python
def add_card_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """标准卡片阴影"""
    return add_shadow(widget, blur=18, dx=0, dy=4, alpha=120)

def add_light_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """轻微阴影"""
    return add_shadow(widget, blur=12, dx=0, dy=2, alpha=80)

def add_strong_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """强烈阴影"""
    return add_shadow(widget, blur=24, dx=0, dy=6, alpha=150)
```

**好处：**
- 代码复用，减少重复
- 参数统一管理
- 易于维护和扩展

### 4️⃣ 性能优化提示

#### 滚动区域性能注意

在文档中添加了性能提示：

```python
def add_card_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """
    给卡片添加标准阴影效果（最常用）
    
    性能提示:
        - 大量卡片在QScrollArea中时，阴影会增加合成成本
        - 大列表建议按需开关或只为"首层卡片"加阴影
        - 确保卡片四周有margin（8-16px），否则阴影会被父容器裁掉
    """
    return add_shadow(widget, blur=18, dx=0, dy=4, alpha=120)
```

#### 最佳实践

**场景1：少量卡片（< 20个）**
```python
# 所有卡片都添加阴影
for card in cards:
    add_card_shadow(card)
```

**场景2：大量卡片（> 50个）**
```python
# 只为可见区域或首层卡片添加阴影
for i, card in enumerate(cards):
    if i < 10:  # 只给前10个添加
        add_card_shadow(card)
```

**场景3：动态加载**
```python
# 按需添加/移除阴影
def on_item_visible(item):
    if item.is_visible:
        add_card_shadow(item.card)
    else:
        remove_shadow(item.card)
```

#### 卡片边距要求

确保卡片四周有足够的margin：

```css
QFrame#card {
    background: #2E2E2E;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 14px;
    margin: 18px 8px 14px 8px;  /* 重要：给阴影留空间 */
}
```

**原因：**
- 阴影需要空间渲染
- 没有margin会被父容器裁剪
- 建议至少8-16px的margin

## 📊 性能对比

### 优化前
```python
# 每次调用都创建新effect
for i in range(100):
    add_shadow(card)  # 创建100个effect！
```

**问题：**
- 内存泄漏
- 性能下降
- 无法更新

### 优化后
```python
# 幂等：只创建一次，后续更新
for i in range(100):
    add_shadow(card, blur=i)  # 只创建1个effect，更新100次
```

**好处：**
- 无内存泄漏
- 性能稳定
- 可以更新参数

## 🎨 使用示例

### 基础使用
```python
from ui.widgets.shadow_utils import add_card_shadow

card = QFrame()
card.setObjectName("card")
add_card_shadow(card)
```

### 自定义阴影
```python
from ui.widgets.shadow_utils import add_shadow
from PyQt5.QtGui import QColor

# 使用QColor
add_shadow(card, blur=20, color=QColor(255, 0, 0), alpha=150)

# 使用RGB元组
add_shadow(card, blur=20, color=(255, 0, 0), alpha=150)
```

### 更新阴影
```python
# 第一次：创建阴影
add_shadow(card, blur=18, alpha=120)

# 第二次：更新阴影（不会创建新的）
add_shadow(card, blur=24, alpha=150)

# 第三次：再次更新
add_shadow(card, blur=30, alpha=180)
```

### 移除阴影
```python
from ui.widgets.shadow_utils import remove_shadow

remove_shadow(card)
```

## 🔍 类型检查

使用mypy进行静态类型检查：

```bash
# 安装mypy
pip install mypy

# 检查类型
mypy ui/widgets/shadow_utils.py
```

**好处：**
- 在运行前发现类型错误
- 提高代码质量
- 更好的IDE支持

## ✅ 测试建议

### 单元测试
```python
def test_add_shadow():
    """测试添加阴影"""
    widget = QFrame()
    
    # 第一次调用
    effect1 = add_shadow(widget)
    assert isinstance(effect1, QGraphicsDropShadowEffect)
    
    # 第二次调用（幂等）
    effect2 = add_shadow(widget)
    assert effect1 is effect2  # 同一个对象
    
    # 参数校验
    add_shadow(widget, blur=-10)  # 自动修正为0
    add_shadow(widget, alpha=300)  # 自动修正为255
```

### 性能测试
```python
import time

def test_performance():
    """测试性能"""
    widget = QFrame()
    
    # 测试多次调用
    start = time.time()
    for _ in range(1000):
        add_shadow(widget, blur=18)
    elapsed = time.time() - start
    
    print(f"1000次调用耗时: {elapsed:.3f}秒")
```

## 📚 相关文档

- `ui/widgets/SHADOW_USAGE.md` - 详细使用指南
- `ui/tabs/CARD_SHADOW_README.md` - 卡片阴影文档
- `THEME_FIX_SUMMARY.md` - 主题修复总结

## 🎯 总结

### 优化前的问题
- ❌ 无类型标注
- ❌ 无参数校验
- ❌ 重复创建effect
- ❌ 不支持自定义颜色
- ❌ 无性能提示

### 优化后的改进
- ✅ 完整类型标注
- ✅ 自动参数校验
- ✅ 幂等性（不重复创建）
- ✅ 支持自定义颜色
- ✅ 性能提示和最佳实践

### 使用建议
1. 优先使用预设方法（`add_card_shadow`等）
2. 需要自定义时使用`add_shadow`
3. 大量卡片时注意性能优化
4. 确保卡片有足够的margin
5. 使用类型检查工具（mypy）

