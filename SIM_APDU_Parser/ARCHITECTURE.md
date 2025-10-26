# SIM APDU Parser 架构文档

## 项目概述

SIM APDU Parser 是一个用于解析和查看SIM卡APDU（Application Protocol Data Unit）消息的图形化工具。项目采用模块化设计，支持eSIM、CAT命令和普通SIM卡消息的解析。

## 整体架构

### 核心设计原则

1. **模块化设计**: 每个功能模块职责单一，便于维护和扩展
2. **解析器注册机制**: 使用装饰器模式注册解析器，支持动态解析
3. **管道处理**: 数据通过管道模式处理，支持多种输入格式
4. **GUI适配**: 解析结果适配为GUI友好的树形结构

### 架构层次

```
┌─────────────────────────────────────────┐
│                GUI Layer                │
│  (main.py - Tkinter界面)                │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│              Application Layer           │
│  (app/adapter.py - GUI适配器)           │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│               Pipeline Layer            │
│  (pipeline.py - 处理管道)               │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│              Parser Layer               │
│  (parsers/ - 各种解析器)                │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│               Core Layer                │
│  (core/ - 核心模块)                     │
└─────────────────────────────────────────┘
```

## 核心模块详解

### 1. Core Layer (核心层)

#### `core/models.py`
- **Message**: APDU消息的数据模型
- **ParseResult**: 解析结果的数据模型
- **ParseNode**: 树形解析节点的数据模型
- **MsgType**: 消息类型枚举

#### `core/registry.py`
- **解析器注册机制**: 使用装饰器模式注册解析器
- **动态解析**: 根据消息类型和标签动态选择解析器

#### `core/tlv.py`
- **TLV解析**: 基于ASN.1的BER TLV解析
- **容错处理**: 支持不完整或格式错误的TLV数据

#### `core/utils.py`
- **APDU解析**: 解析APDU头部信息
- **工具函数**: 十六进制处理、ICCID解析等

### 2. Parser Layer (解析器层)

#### `parsers/base.py`
- **基础解析器**: 定义解析器接口
- **CatParser**: CAT命令解析器
- **EsimParser**: eSIM消息解析器
- **NormalSimParser**: 普通SIM APDU解析器

#### `parsers/esim/`
- **eSIM消息解析**: 支持BFxx系列消息
- **公用模块**: 
  - `common_signatures.py`: 签名解析公用函数
  - `common_notification.py`: 通知解析公用函数
- **具体解析器**: 各种BFxx消息的专门解析器

#### `parsers/CAT/`
- **CAT命令解析**: 支持D0、80 14、80 C2等命令
- **公用模块**: `common.py` 包含CAT命令解析的公用函数
- **具体解析器**: 各种CAT命令的专门解析器

#### `parsers/SIM_APDU/`
- **SIM APDU解析**: 支持普通SIM卡APDU解析
- **FCP解析**: 文件控制参数解析

### 3. Data I/O Layer (数据输入输出层)

#### `data_io/loaders.py`
- **文件加载**: 支持多种文件格式加载

#### `data_io/extractors/`
- **MTK提取器**: 支持MTK日志格式
- **通用提取器**: 支持纯APDU文本格式

### 4. Classification Layer (分类层)

#### `classify/rules.py`
- **消息分类**: 根据APDU内容自动分类消息类型
- **方向判断**: 判断消息的传输方向
- **标题生成**: 生成用户友好的消息标题

### 5. Render Layer (渲染层)

#### `render/gui_adapter.py`
- **GUI适配**: 将解析结果转换为GUI友好的格式
- **事件生成**: 生成GUI事件列表

#### `render/tree_builder.py`
- **树形构建**: 构建树形显示结构

## 解析器注册机制

### 注册装饰器

```python
@register(MsgType.ESIM, "BF28")
class Bf28Parser:
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        # 解析逻辑
        pass
```

### 解析器查找

```python
handler_cls = resolve(MsgType.ESIM, "BF28")
if handler_cls:
    handler = handler_cls()
    root = handler.build(payload_hex, direction)
```

## 数据处理流程

### 1. 数据输入
```
文件 → loaders.py → extractors/ → Message[]
```

### 2. 消息分类
```
Message → classify/rules.py → (MsgType, direction, tag, title)
```

### 3. 解析处理
```
Message → parsers/base.py → 选择解析器 → ParseResult
```

### 4. 结果渲染
```
ParseResult → render/ → GUI事件
```

## 扩展指南

### 添加新的eSIM消息解析器

1. 在 `parsers/esim/tlvs/` 下创建新的解析器文件
2. 使用 `@register(MsgType.ESIM, "BFxx")` 装饰器注册
3. 在 `parsers/esim/__init__.py` 中导入新模块

### 添加新的CAT命令解析器

1. 在 `parsers/CAT/cmds/` 下创建新的解析器文件
2. 使用 `@register(MsgType.CAT, "COMMAND")` 装饰器注册
3. 在 `parsers/CAT/__init__.py` 中导入新模块

### 添加新的数据提取器

1. 在 `data_io/extractors/` 下创建新的提取器
2. 实现 `extract()` 方法
3. 在 `pipeline.py` 中添加使用逻辑

## 历史重构记录

### eSIM TLV解析模块重构

#### 重构目标
将BF27、5F37和NotificationEvent的解析逻辑提取为公用模块，避免代码重复。

#### 创建的公用模块

**`parsers/esim/tlvs/common_signatures.py`**
- `parse_bf27_profile_installation_result_data()` - 解析BF27 profileInstallationResultData
- `parse_5f37_euicc_sign_pir()` - 解析5F37 euiccSignPIR签名
- `parse_5f37_euicc_notification_signature()` - 解析5F37 euiccNotificationSignature签名
- `parse_5f37_euicc_sign_rpr()` - 解析5F37 euiccSignRPR签名
- `parse_5f37_server_signature1()` - 解析5F37 serverSignature1签名

**`parsers/esim/tlvs/common_notification.py`**
- `parse_notification_event()` - 解析NotificationEvent位串
- `parse_notification_event_with_count()` - 解析NotificationEvent位串并返回计数
- `parse_notification_metadata()` - 解析NotificationMetadata结构
- `build_notification_operation_node()` - 构建profileManagementOperation节点

#### 重构优势

1. **代码复用**: 消除了重复代码，提高了维护性
2. **一致性**: 确保所有解析器使用相同的解析逻辑
3. **可维护性**: 修改解析逻辑时只需要更新公用模块
4. **可扩展性**: 新的解析器可以轻松使用这些公用函数

## 技术特点

### 1. 容错处理
- TLV解析支持不完整数据
- APDU解析支持各种格式
- 文件加载支持多种编码

### 2. 性能优化
- 解析器注册机制避免重复查找
- 缓存解析结果避免重复计算
- 延迟加载减少内存占用

### 3. 可扩展性
- 模块化设计便于添加新功能
- 注册机制支持动态扩展
- 管道模式支持新的处理步骤

## 依赖关系

### 外部依赖
- `asn1crypto`: ASN.1和BER TLV解析
- `tkinter`: GUI界面（Python标准库）

### 内部依赖
- 所有模块都依赖 `core/models.py`
- 解析器依赖 `core/registry.py` 进行注册
- GUI层依赖 `render/` 模块进行数据转换

---

*本文档记录了SIM APDU Parser的架构设计和实现细节，为开发者提供技术参考。*