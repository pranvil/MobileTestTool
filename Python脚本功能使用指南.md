# Python脚本功能使用指南

## 🐍 Python脚本功能

现在Python脚本的输出结果会完整显示在日志区域中！

## ✅ 修复内容

### **输出捕获**
- ✅ 捕获 `print()` 输出
- ✅ 捕获错误信息
- ✅ 显示在日志区域
- ✅ 区分正常输出和错误信息

### **扩展模块支持**
- ✅ `datetime` - 日期时间处理
- ✅ `platform` - 系统信息
- ✅ `os` - 操作系统接口
- ✅ `json` - JSON数据处理
- ✅ `math` - 数学函数
- ✅ `random` - 随机数生成
- ✅ `time` - 时间处理

## 🎯 实用示例

### **示例1：系统信息收集**
```python
import platform
import os
from datetime import datetime

print("=== 系统信息收集 ===")
print(f"操作系统: {platform.system()}")
print(f"系统版本: {platform.version()}")
print(f"处理器架构: {platform.machine()}")
print(f"Python版本: {platform.python_version()}")
print(f"当前用户: {os.getenv('USERNAME', 'Unknown')}")
print(f"当前目录: {os.getcwd()}")
print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
```

### **示例2：数据处理**
```python
import json
import math

# 模拟一些数据
data = {
    "设备数量": 5,
    "测试用例": [1, 2, 3, 4, 5],
    "成功率": 0.85
}

print("=== 数据处理示例 ===")
print(f"JSON数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
print(f"测试用例总数: {len(data['测试用例'])}")
print(f"成功率百分比: {data['成功率'] * 100:.1f}%")
print(f"成功率平方根: {math.sqrt(data['成功率']):.3f}")
```

### **示例3：随机数生成**
```python
import random
import time

print("=== 随机数生成 ===")
for i in range(5):
    random_num = random.randint(1, 100)
    print(f"随机数 {i+1}: {random_num}")
    time.sleep(0.1)  # 模拟处理时间
```

### **示例4：文件系统信息**
```python
import os
from datetime import datetime

print("=== 文件系统信息 ===")
current_dir = os.getcwd()
print(f"当前目录: {current_dir}")

try:
    files = os.listdir(current_dir)
    print(f"目录中文件数量: {len(files)}")
    print("前5个文件:")
    for i, file in enumerate(files[:5]):
        print(f"  {i+1}. {file}")
except Exception as e:
    print(f"读取目录失败: {e}")
```

### **示例5：数学计算**
```python
import math

print("=== 数学计算示例 ===")
numbers = [1, 4, 9, 16, 25]

print("原数字:", numbers)
print("平方根:", [math.sqrt(n) for n in numbers])
print("自然对数:", [math.log(n) for n in numbers])
print("正弦值:", [math.sin(n) for n in numbers])

# 统计信息
print(f"总和: {sum(numbers)}")
print(f"平均值: {sum(numbers)/len(numbers):.2f}")
print(f"最大值: {max(numbers)}")
print(f"最小值: {min(numbers)}")
```

## 🔧 使用步骤

### **1. 创建Python脚本按钮**
1. 选择按钮类型："Python脚本"
2. 在"高级设置"区域输入Python代码
3. 保存按钮

### **2. 执行脚本**
1. 点击自定义按钮
2. 查看日志区域的输出结果
3. 输出会显示：
   - ✅ 正常输出（print语句）
   - ❌ 错误信息（如果有错误）

## 📊 输出格式

### **成功执行**
```
🔧 执行自定义按钮: 系统信息收集
✅ 执行成功
输出:
=== 系统信息收集 ===
操作系统: Windows
系统版本: 10.0.19042
处理器架构: AMD64
Python版本: 3.9.7
当前用户: hao.lin
当前目录: C:\Users\hao.lin\OneDrive\work\04 Code\Python Project\MobileTestTool
当前时间: 2024-12-01 15:30:45
```

### **执行错误**
```
🔧 执行自定义按钮: 错误脚本
❌ 执行失败: Python脚本执行错误: name 'undefined_variable' is not defined
```

## ⚠️ 注意事项

### **安全限制**
- 只能使用预定义的安全模块
- 无法访问网络、文件系统等敏感操作
- 无法导入危险的第三方模块

### **执行环境**
- 脚本在独立的环境中执行
- 不会影响主程序的状态
- 有执行超时保护

### **输出限制**
- 输出结果会在日志区域显示
- 过长的输出会被截断
- 错误信息会单独显示

## 💡 最佳实践

### **1. 代码简洁**
- 保持脚本简单明了
- 添加适当的注释
- 使用清晰的变量名

### **2. 错误处理**
```python
try:
    # 你的代码
    result = some_operation()
    print(f"结果: {result}")
except Exception as e:
    print(f"错误: {e}")
```

### **3. 输出格式化**
```python
# 使用格式化输出
print(f"设备ID: {device_id}")
print(f"测试结果: {result:.2f}%")
print(f"时间戳: {datetime.now():%Y-%m-%d %H:%M:%S}")
```

现在Python脚本的输出结果会完整显示在日志区域中了！🎉
