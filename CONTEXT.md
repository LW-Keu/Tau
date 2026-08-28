# Tau

Tau 是一个极简、自进化的自主智能体框架。v5 起采用双运行时架构：Node/cordis 宿主为底座，Python 内核作为插件接入。

## Language

### 运行时拓扑

**宿主（Host）**:
Node 侧的 cordis 进程，拥有启动入口、插件树、配置装载与生命周期；以单例守护进程形态运行，前端即连即用，可 headless。
_Avoid_: 主进程、Node 端、服务端

**内核插件（Kernel Plugin）**:
Python 侧的 Agent 内核（tau_agent / tau_ai / memory），在宿主的插件树中占一个条目，经桥提供服务。
_Avoid_: Python 端、后端、worker

**桥（Bridge）**:
宿主与内核插件之间的进程间契约：方法调用、流式事件与生命周期信号的载体。
_Avoid_: 通道、管道、IPC（泛指时可用，指此契约时用「桥」）

**宿主服务（Host Service）**:
挂在宿主插件树上的横切能力：计划调度、IM 适配、工具注册表、事件目录的规范侧。
_Avoid_: Node 服务、平台功能

**前端客户端（Frontend Client）**:
apps/ 下的 Python 前端，不内嵌内核，经协议连宿主获取会话与事件流。
_Avoid_: 前端插件（那是重写为 TS 的另一种形态）

**内核桥（Kernel Bridge）**:
宿主与内核插件之间、基于 stdio JSON-RPC 的自定义契约：请求/应答承载方法调用，通知承载流式事件。
_Avoid_: ACP 通道（ACP 是另一种被否决的契约形态）

**网关（Gateway）**:
宿主对外提供的 localhost WebSocket 接入点：前端客户端经它进行 RPC 调用并订阅类型化事件流。OpenAI 兼容 API 是宿主上的一个兼容插件，不是前端的主通道。
_Avoid_: API（泛指，且易与 OpenAI 兼容层混淆）

### 配置

**宿主配置（tau.yml）**:
宿主域的唯一事实源：插件树与宿主服务（调度、IM、网关）的配置。
_Avoid_: cordis.yml（那是 cordis 默认名，Tau 用自己的）

**内核配置（taukey.py）**:
内核域的唯一事实源：模型密钥、模型定义与故障转移。宿主不读取；需要展示时经桥向内核查询。
_Avoid_: 把模型密钥写进宿主配置

## Language（续）

### 事件与会话

**事件目录（Event Catalog）**:
对外可见事件的名字、载荷与分发模式的规范，由宿主定义并拥有；内核在桥边界把内部事件翻译成目录中的事件。
_Avoid_: 内核事件（那是不对外的实现细节）

**工具注册表（Tool Registry）**:
宿主侧的唯一工具目录：内核工具、memory 技能、宿主插件工具以统一 schema 入册；执行时可落在任意一侧。
_Avoid_: 技能库（指 memory/ 的存储，不是目录本身）


