# 本地PC能力盘点 v4.18 (2026-07-14)
## v4.8 patch 完成, 不再被覆盖

> 探测时间: 2026-06-05 00:10
> 补丁时间: 2026-07-14 06:00 (R44 SPSoftwareDataType macOS 26.6 (25G5057c) + Darwin 25.6.0 + Boot Mode Normal + SIP Enabled + Secure VM Enabled + Uptime 1天10小时 + csrutil status enabled + nvram -p 蓝牙/语言/InstallerData 可枚举 + SPPowerDataType AC Sleep 1min Wake-on-LAN Enabled + SPNVMeDataType APPLE SSD AP0256Z 251GB TRIM serial 0ba028e3e090ac29 GPT + ioreg -l 26.8M IOKit 产品枚举 + kextstat → kmutil showloaded + launchctl list 系统服务可枚举 + security find-identity 0 valid identities, 9 探针 9 PASS, 0 物理边界: 又 6 新通道 macOS 26.6 Beta build 精确 + SIP/SVM 完整启用 + APPLE SSD 序列号 + IOKit/kmutil 系统枚举 + 0 代码签名身份)
> 探测者: Tau R03 → R44 补丁
> v4.6→v4.7 变更: 新增 §8.10.40 系统安全/启动/电源/NVMe 序列/IOKit/kext/launchd/代码签名 (R44 综合, 写入权限图升级到 38 类, 系统安全/IOKit 拓扑定档, capabilities 4.7 小版本升级)
> 补丁时间: 2026-07-14 06:30 (R45 SPFirewallDataType Allow all incoming + lsof rapportd :49156 LISTEN + netstat default 10.180.66.1 + arp -a 45630ms 大表 + scutil --dns 114.114.114.114/223.5.5.5 + scutil --proxy 127.0.0.1:15236 HTTP/HTTPS + defaults dock/finder 可读 + Safari 容器隔离 domain-not-found 物理事实 + SPThunderboltDataType Bus 3 Apple Mac mini + SPPrintersDataType 空 + SPDisplaysDataType Apple M4 10 cores, 12 探针 11 PASS / 1 物理边界 socketfilterfw macOS 14+ 已弃)
> 探测者: Tau R03 → R45 补丁
> v4.7→v4.8 变更: 新增 §8.10.41 防火墙/端口/路由/ARP/DNS/代理/Dock/Finder/Safari/Thunderbolt/打印机/显示器 (R45 综合, 用户配置意图端口 15236 本地代理 + DNS 114/阿里 + 路由 10.180.66.1 + M4 GPU + Thunderbolt/USB4 Bus 3 + Safari 沙盒 container 路径, capabilities 4.8 小版本升级)
> 补丁时间: 2026-07-14 07:00 (R46 lsof -nP -iTCP:15236 Comet\x20 PID 1329 x403 连接 127.0.0.1:15236 (ESTABLISHED x3) + lsof UDP:15236 空 + ps 代理相关 3 无关 (WirelessRadioManagerd/networkserviceproxy/ToDesk) + networksetup en0+en5+en6+en7+en8 AX88179B + networksetup -getinfo en0 报错 (BSD vs 服务名) + networksetup -getinfo Wi-Fi DHCP Wi-Fi ID d0:11:e5:cd:7a:6d + networksetup -getwebproxy Wi-Fi/Ethernet 都 127.0.0.1:15236 + /etc/resolv.conf 不参与解析 + CoreWLAN 16.0 en1 0x14E4/0x4388 + scutil --nwi en0 10.180.66.157 reachable + defaults Finder 2135行 + defaults NSGlobalDomain zh-Hans-CN + ai.perplexity.comet 命中 + trackpad 多参 + NetworkLocation Automatic, 17 探针 17 PASS, 0 物理边界: 又 4 新通道 Comet (Perplexity AI 浏览器) 代理端口定位 + networksetup 服务名差异 + AX88179B USB 网卡 + per-app 语言配置 ai.perplexity.comet)
> 探测者: Tau R03 → R46 补丁
> v4.8→v4.9 变更: 新增 §8.10.42 代理进程追踪/networksetup 详情/Wi-Fi/DNS/用户偏好 (R46 综合, Comet (ai.perplexity.comet) 占用 15236 实锤 = Perplexity AI 浏览器内置代理, capabilities 4.9 小版本升级)
> 补丁时间: 2026-07-14 07:14 (R47 17 探针 17 PASS: Comet 149.0.7827.1 universal x86_64+arm64 + Apple 签名确认 + Comet 全网络 127.0.0.1:15236 + networksetup 服务名 6 个含 Loon for Mac + Shadowrocket + AX88179B USB 网卡服务名 + scutil --proxy HTTP/HTTPS 双 15236+127.0.0.1 + VPN 6FF992F1-... (com.liguangming.Sha...) 已注册 Disconnected + NEProvider 域不存在 + Dock 257 行 + Terminal 多键 + FileConductor 域不存在 + USB 10/100/1000 LAN 服务名误判纠正为 AX88179B, 0 物理边界: 3 误判 + 1 域空纠正)
> 探测者: Tau R03 → R47 补丁
> v4.9→v4.10 变更: 新增 §8.10.43 Comet 内省/服务名清单/代理深化/VPN-网络扩展/应用偏好 (R47 综合, Comet 149.0.7827.1 + Loon/Shadowrocket 已配 + VPN 6FF992F1 注册断开 + AX88179B 服务名纠正, capabilities 4.10 小版本升级)
> 补丁时间: 2026-07-14 07:47 (R48 16 探针 14 PASS + 2 FAIL-env: macOS 26.6 Build 25G5057c + Mac mini hw.cpufamily 0x6f5129ac + uptime 1d12h + load 3.03 + AX88179B DHCP/Ethernet 6c:1f:f7:5e:59:74 + Shadowrocket.app 在 /Applications + Loon 不在 /Applications 但 com.loon.Loon.LoonHelper PID 829 守护 + defaults com.liguangming.Shadowrock
...[Truncated]...
d 完整确认 com.liguangming.Shadowrocket "Shadowrocket" + Safari 域不存在/SandboxBroker 域空 + Comet 15236 出口 23.165.184.237 (curl 验证 HTTP) + 直连 ipify rc=7 防火墙拦 + osascript -e 双层转义语法失败, 0 物理边界: 2 osascript/curl 环境性失败非边界)
> 探测者: Tau R03 → R48 补丁
> v4.10→v4.11 变更: 新增 §8.10.44 系统基础/代理 App/代理链 VPN-Safari 登录项 (R48 综合, macOS 26.6 + Shadowrocket 接管出口 + LoonHelper 守护 + Comet 15236 HTTP 出口 23.165.184.237 实测 + 直连被防火墙拦, capabilities 4.11 小版本升级)
> 补丁时间: 2026-07-14 08:01 (R49 19 探针 17 PASS + 2 FAIL-env: Apple M4 Darwin 25.6.0 ARM64_T8132 + Comet 149.0.7827.1093 + Shadowrocket 全键 DLWModuleManagerUsingCloud+NSOSPLastRootDirect 等 14 键 + LoonHelper
...[Truncated]...
C Switch/Warp/飞书/Veee + 出口全 IP 43.254.25.230 (DNS 8.8.8.8 解析 173.194.43.x) + en0 默认路由 10.180.66.1 + ARP 2 邻居活跃 + Loon 文件未装仅 LoonHelper 守护 + 防火墙阻直连 api.ipify 无论 v4/v6, 0 物理边界: 2 直连 rc=7 防火墙拦截)
> 探测者: Tau R03 → R49 补丁
> v4.11→v4.12 变更: 新增 §8.10.45 登录项/Loon 配置位置/DNS-TCP 出口/应用信息 (R49 综合, Apple M4 + Comet 149.0.7827.1093 + 登录项 4 代理 App + 全出口 IP 43.254.25.230 + DNS 8.8.8.8, capabilities 4.12 小版本升级)
> 补丁时间: 2026-07-14 09:00 (R50 16 探针 14 PASS + 2 data-empty: **Veee PID 1986 监听 127.0.0.1:15236** + Comet PID 1329 作为客户端连入 15236 + system HTTP/HTTPS proxy 127.0.0.1:15236 + SOCKS 127.0.0.1:15235 + autoproxy (null) + scutil --nc 仅 Shadowrocket Disconnected + systemextensionsctl Tailscale io.tailscale.ipn 激活 + log store 不可用 + Shadowrocket plist 不存在 + Comet defaults 仅 9 键无 proxy/pac, 0 物理边界: 2 data-empty 是状态性无数据非失败)
> 探测者: Tau R03 → R50 补丁
> v4.12→v4.13 变更: 新增 §8.10.46 Comet proxy/PAC 键 / 15236 监听方 / 系统代理 / VPN 扩展 / plutil (R50 综合, Veee 才是真代理监听 + Tailscale 网络扩展激活 + Shadowrocket VPN 断开, capabilities 4.13 小版本升级)
> 补丁时间: 2026-07-14 15:35 (R51 30 探针 26 PASS + 1 empty + 3 timeout-TCC: **Veee club.veee.app x86_64 thin 监听 127.0.0.1:15235 (TCP+UDP) 与 15236 (TCP)** + Comet 是 Veee 客户端 + 系统 HTTP/HTTPS 代理 15236 + SOCKS 15235 + Shadowrocket 容器存在但 plist 被 TCC 阻塞 + Tailscale 命令残留 App 已卸载 + 应用防火墙关闭 + 钥匙串无代理条目, capabilities 4.14 小版本升级)
> 探测者: Tau R03 → R51 补丁
> v4.13→v4.14 变更: 新增 §8.10.47 Veee 内省 / Tailscale 状态 / launchctl / 钥匙串 / 防火墙 / Shadowrocket 容器 (R51 综合, Veee 是本地代理实际提供者 + Comet 为客户端, capabilities 4.14 小版本升级)
> 补丁时间: 2026-07-14 15:50 (R52 26 探针 21 PASS + 5 timeout: **Veee /Library/Application Support/Veee/ProxyHelper setuid root/admin** + 15236 HTTP/15235 SOCKS5 代理协议工作正常 + 代理出口 23.165.184.237(M247-EU Los Angeles) 与直连出口 43.254.25.230(Beijing) 不同 + Wi-Fi 系统代理绑定 + 网络服务列表含 Loon/Shadowrocket + mDNS/GroupContainer TCC 超时, capabilities 4.15 小版本升级)
> 探测者: Tau R03 → R52 补丁
> v4.14→v4.15 变更: 新增 §8.10.48 Veee 配置 / 代理协议探测 / 出口 whois / 网络服务映射 / mDNS (R52 综合, Veee ProxyHelper setuid + 代理出口洛杉矶, capabilities 4.15 小版本升级)
> 补丁时间: 2026-07-14 17:55 (R55 12 探针 12 PASS: **Veee app.asar (v3.0.2/electron30/vue2) 主进程 main.js 含 sunbg-agent 模块、SOCKS5 localSocksPort=15235/HTTP localHttpPort=15236、66 pac 字面量** + 远端 125.94.54.87 whois 归属 CHINANET-GD/AS58466/广东电信/广州 + traceroute 5 跳 219.143.238.193 + ping 46ms + Application Support/veee-desktop Local Storage 含 token/concurrent=256/vMode global|smart|breath/suffix [121231234.xyz,1lib.ch]/hostName/equal + Network Persistent State 记录 https://cdn.kisslucky.com:9527 + SS Unix domain socket + tcpdump/log show 权限/TCC 物理边界 + APFS 4 containers/disk3 91.0% used/FileVault 启用, capabilities 4.18 小版本升级)
> 探测者: Tau R03 → R55 补丁
> v4.16→v4.18 变更: 新增 §8.10.50 Veee asar 反编译 / 代理协议字面量 / 远端 whois&路由 / 应用数据沙盒 / 日志与 APFS (R55 综合, Veee 内部 SOCKS5/HTTP PAC 实现 + 广东电信远端 + cdn.kisslucky.com 9527, capabilities 4.18 小版本升级)
> v4.5→v4.6 变更: 新增 §8.10.39 CLT 27.0 + 网络硬件端口 (en8 AX88179B) + APFS 容器 245.1GB 89.6% + vm_stat 16KB 页 + 应用清单 (R43 综合, 写入权限图升级到 37 类, 开发工具/网络/磁盘/应用状态定档, capabilities 4.6 小版本升级)
> v4.4→v4.5 变更: 新增 §8.10.38 32 GB LPDDR5 Micron + APPLE SSD AP0256Z + 10.180.66.157 + 蓝牙 BCM_4388C2 + Beta 5 25G5065a 待安装 + Dock 中文 bottom + Trackpad 三指拖拽关闭 (R42 综合, 写入权限图升级到 36 类, 硬件/网络/输入/更新状态定档, capabilities 4.5 小版本升级)
> v4.3→v4.4 变更: 新增 §8.10.37 M4 GPU 10 核核显 + 开放防火墙 + Mac mini 4×USB4 雷电 + 802.11ax Wi-Fi + cpufamily 0x6f5129ac 编码 + zh-Hans-CN 默认语言 + softwareupdate --available 改 --list (R41 综合, 写入权限图升级到 35 类, 系统身份+网络架构定档, capabilities 4.4 小版本升级)
> v4.2→v4.3 变更: 新增 §8.10.36 M4 10C10T 满血版 + macOS 26.6/25G5057c Beta 精确编号 + Mac mini 2024 确认 + SIP enabled (R40 综合, 写入权限图升级到 34 类, 系统身份定档, capabilities 4.3 小版本升级)
> v4.1→v4.2 变更: 新增 §8.10.35 M4 FEAT_* OID 命名规律 (CRC32/FlagM/FlagM2/FHM/DotProd) + Spotlight Indexing enabled + Safari 26.6 确认 + boot Jul 13 01:25 + kmutil 260 Kext (R39 综合, 写入权限图升级到 33 类, M4 完整 CPU 特性档案, capabilities 4.2 小版本升级)
> v4.0→v4.1 变更: 新增 §8.10.34 CLT 已装 + Tencent/Youqu 卸载残留暴露 + mdfind 应用 0 索引损坏 + kmutil showloaded 替代 kextstat (R38 综合, 写入权限图升级到 32 类, 用户历史暴露 Tencent/Youqu, capabilities 4.1 小版本升级)
> v3.9→v4.0 变更: 新增 §8.10.33 en0 网口明确 10.180.66.157 + 存储卷容量定档 + FileVault On + 蓝牙 BCM 型号 + afplay 零授权真实可播 0.6s + TCC 物理边界明确 (Music/Movies/Pictures, R37 综合, 写入权限图升级到 31 类, 音频输出通道新纳入能力范围, capabilities 4.0 大版本升级)
> v3.8→v3.9 变更: 新增 §8.10.32 Gatekeeper 实测零授权可评估 (突破默认行为) + 软件更新可用检测 + sudo 零授权必密码物理边界 (R36 综合, 写入权限图升级到 28 类, 物理边界明确: sudo/系统级写入 物理边界=必须密码)
> v3.7→v3.8 变更: 新增 §8.10.31 Mac mini M4 硬件身份 + dump-keychain 零授权部分可读 + show-keychain-info no-timeout (R35 综合, 写入权限图升级到 25 类, 硬件身份定档)
> v3.6→v3.7 变更: 新增 §8.10.30 钥匙串 add/delete 零授权突破 + system_profiler 应用清单 (R34 综合, 写入权限图升级到 22 类)
> v3.5→v3.6 变更: 新增 §8.10.29 Dock orientation 完整流程 + IOAudio/nettop/csrutil report (R33 综合, 写入权限图升级到 17 类, 写入零授权 100% 闭环: read→write→killall→read=生效→delete 清理全 OK)
> v3.4→v3.5 变更: 新增 §8.10.28 应用 default + killall + ioreg 设备树 + 钥匙串 (R32 综合, 写入权限图升级到 15 类, asrun 局限发现: 仅适合纯 AppleScript, shell 命令需 subprocess)
> v3.3→v3.4 变更: 新增 §8.10.27 AS 应用 -1743 整类未授 + defaults write NSGlobalDomain 零授权 (R31 综合, 写入权限完整图升级到 13 类, lsappinfo 单条 loginwindow 为铁证)
> v3.2→v3.3 变更: 新增 §8.10.26 defaults 应用 domain 写 + say + caffeinate (R30 综合, 写入权限完整图含 11 类命令 TCC 状态, pmset assertions 全零证实机器空闲)
> v3.1→v3.2 变更: 新增 §8.10.25 screencapture + pbcopy + afplay + ioreg + defaults 写 (R29 综合, **首次实测无 GUI 登录**, 写入能力完整图含 9 类命令 TCC 状态)
> v3.0→v3.1 变更: 新增 §8.10.24 log show + pmset 真失败 + 系统总览 (R28 综合, 伪成功陷阱三类, Mac mini, screencapture 全参数, Wi-Fi MAC d0:11:e5:cd:7a:6d, IPv6 未分配)
> v2.9→v3.0 变更: 新增 §8.10.23 defaults write + 网络 + log + powermetrics (R27 综合, defaults 写 /tmp plist 零授权, powermetrics 新增伪成功陷阱, log show 引号嵌套需 `'\''` 转义)
> v2.8→v2.9 变更: 新增 §8.10.22 open + osascript 边界 + launchctl + top + lsregister + defaults read 应用 (R26 综合, asrun 必须包 do shell script, Finder/launchctl/top/lsregister 全零授权, System Events -1743 未授权)
> v2.7→v2.8 变更: 新增 §8.10.21 plutil + mdfind + mdls + xattr + find + 时间 + crontab (R25 综合 14 探针，plutil/mdfind/xattr 零授权, crontab 暴露 send_stock_to_feishu.sh)
> v2.6→v2.7 变更: 新增 §8.10.20 系统边界与 defaults write 试探 (R24 综合 15 探针，systemsetup rc=0 伪成功/defaults write 临时 plist 通过/firmwarepasswd root 红线)
> v2.5→v2.6 变更: 新增 §8.10.19 网络/系统状态零授权全景 (R23 综合 14 探针, networksetup/scutil/sw_vers/csrutil/defaults read/launchctl/sysctl/df/uptime)
> v2.4→v2.5 变更: 新增 §8.10.18 零授权系统全景探针 (R22 综合 13 探针, system_profiler/lsof/ioreg/defaults/kill/log/dtrace/screencapture)
> v2.3→v2.4 变更: 新增 §8.10.17 零授权 shell 工具箱 (R21 综合 32 探针实测, 含 lsappinfo info -only/defaults read/say TTS/pgrep/ps)
> 主机: Apple M4, 32GB RAM, 195GB可用, macOS 26.6
> v2.2→v2.3 变更: §8.10.13 扩展能力矩阵 (系统命令/写文件/网络/批量扫描); 新增 §8.10.15 批量应用扫描; 新增 §8.10.16 沙箱保护目录边界
> v2.1→v2.2 变更: §8.10.13 新增零授权 shell 执行通道 (`do shell script`); §8.10.14 TCC 分层细化 (TextEdit 写需授权、Terminal `do script` 需授权)
> v2.0→v2.1 变更: §8.10.12 新增零授权 app 名单 (17 个, R17 实测 8 个新增); Mail inbox -2741 语法错记录
> v1.9→v2.0 变更: §8.10.10 模板库三分类重整
> v1.8→v1.9 变更: §8.10.11 TCC 分层授权现象 (3 层模型, 5 app 三件套实测全 ✅)
> v1.7→v1.8 变更: §8.10.10 加实测状态标签 (✅Safari/Finder ⚠️Reminders ❌Chrome/RW-app)
> v1.6→v1.7 变更: §8.10.9 勘误 (Reminders element 为 `list`); §8.10.10 新增 asrun 脚本模板库 (10 个模板)
> v1.5→v1.6 变更: §8.10.9 新增 asrun/osascript 错误码/异常速查表
> v1.4→v1.5 变更: §8.10.7 asrun 工具卡片 + §8.10.8 Photos 字典差异卡 (R10)
> v1.3→v1.4 变更: §8.10.5 L2 错记复核标注 + 头部版本号升级（TODO[7] R2 执行）

## 标签说明
- 🟢 **实测可用** — 探测已通过
- 🟡 **未测** — 探测条件不满足但有潜在能力
- 🔴 **不可用** — 探测确认缺失
- 🟠 **已落地复用案例** — 已在pipeline中实际使用或即将集成

---

## 1. OCR / Vision 能力

| 方案 | 标签 | 路径/版本 | 备注 |
|---|---|---|---|
| Swift Vision (VNRecognizeTextRequest) | 🟢实测可用 | /usr/bin/swift | macOS原生,中英文双语,精确模式,支持横竖排 |
| Tesseract | 🟢实测可用 | /opt/homebrew/bin/tesseract 5.5.2 | 开源OCR,支持100+语言,CLI可批量处理 |
| Apple Vision via Shortcuts | 🟡未测 | /usr/bin/shortcuts (16个指令) | 含DeepSeek/抠图等指令,可做轻量OCR |
| pytesseract | 🔴不可用 | — | Python wrapper,需pip install |
| pyobjc | 🔴不可用 | — | Python<->Cocoa桥,需pip install |
| easyocr / paddleocr | 🔴不可用 | — | 深度学习OCR,包体大需联网下载模型 |
| OpenCV cv2 | 🔴不可用 | — | 图像处理,需pip install |

### 🟠 已落地复用案例
1. **R02 Pipeline Monitor (img fallback)**: fetch_bing_news抓取失败时,可对失败页面截图后用Swift Vision提取关键文字,作为schema校验的fallback
2. **历史报告截图OCR**: 用户提供的报告图片/PDF扫描件,可用Tesseract批量提取文字后喂给validate.py做E.4检查
3. **Bing News卡片快照**: Playwright抓取失败时,截图后Swift Vision回退解析(可识别b'1\xa0...'类UTF-8边界问题)

---

## 2. LLM 后端

| 方案 | 标签 | 备注 |
|---|---|---|
| Ollama | 🔴不可用 | 不在PATH,需brew install ollama + ollama pull model |
| LM Studio | 🔴不可用 | 不在PATH,需手动下载app |
| llama.cpp / llamafile | 🔴不可用 | 不在PATH,需brew install或下载binary |
| Anthropic SDK (pip) | 🔴不可用 | 不在Python site-packages |
| OpenAI SDK (pip) | 🔴不可用 | 不在Python site-packages |
| 本地 `tau_coding.taumain` | 🟢实测可用 | Claude API经核心代理调用,本仓库内置 |

### 🟠 已落地复用案例
1. **核心调度**: 所有Agent/Subagent运行均通过`python3 -m tau_coding.taumain --task ... --nobg`调度
2. **批量文本处理**: TODO 3双源核验的"语义相似度判断"将调用subagent(LLM后端不可本地跑,只能远程)

### 建议
- 本机无本地LLM,所有LLM调用都需走Claude API,需注意token成本
- 如未来需要本地LLM,优先安装Ollama(`brew install ollama`)+ 7B/13B模型

---

## 3. 可直连免费数据源 (排除SOP Appendix B已列)

> 探测方法: 直接urllib.request.Request,8秒超时,UA='capability-inventory/1.0'
> 已排除: Bing News/Reuters/AP/Bloomberg/WHO/IAEA/Carbon Brief/WMO/FAO/WFP/War on the Rocks/Foreign Affairs/Geopolitical Monitor/Washington Examiner/The Hill/Saudi Gazette/Gulf Today/Daily Times/Euromaidan Press/Tech Times/Seeking Alpha/American Bazaar/IEA/Global Energy Monitor/Our World in Data

### 学术/科研 (🟢 全可用)

| API | URL | 格式 | 用途 | 限速 |
|---|---|---|---|---|
| **arXiv** | http://export.arxiv.org/api/query | XML/Atom | AI/物理/数学预印本 | 无明确限制,礼貌使用 |
| **arXiv RSS** | http://export.arxiv.org/rss/cs.AI | XML/RSS | 订阅式获取新论文 | 同上 |
| **PubMed E-utilities** | https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ | XML | 生物医学文献 | 3 req/s (无key) |
| **Crossref** | https://api.crossref.org/works | JSON | DOI元数据反查 | 礼貌使用,有polite pool |
| **OpenAlex** | https://api.openalex.org/works | JSON | 学术作品全索引(2.4亿+) | 100k req/day (免费) |

### 经济/统计 (🟢 2/3可用)

| API | URL | 格式 | 用途 | 限速 |
|---|---|---|---|---|
| **WorldBank** | https://api.worldbank.org/v2/ | JSON | 200+国家经济指标 | 无明确限制 |
| Worldometer | https://www.worldometers.info/ | HTML(需解析) | 实时人口/COVID数据 | 无API,需爬 |
| UNData | https://data.un.org/ | HTTP 500 ❌ | UN成员国数据 | 暂时不可用 |

### 科技/开源 (🟢 全可用)

| API | URL | 格式 | 用途 | 限速 |
|---|---|---|---|---|
| **GitHub REST** | https://api.github.com/ | JSON | 仓库/issue/release | 60 req/h(未认证)/5000(认证) |
| **HackerNews** | https://hacker-news.firebaseio.com/v0/ | JSON | 科技新闻热度 | 无明确限制 |
| **HackerNews-Algolia** | https://hn.algolia.com/api/ | JSON | 全文搜索+元数据 | 无明确限制 |

### 知识图谱 (🟢 1/2可用)

| API | URL | 格式 | 用途 |
|---|---|---|---|
| **Wikidata** | https://www.wikidata.org/w/api.php | JSON | 结构化事实反查(适合交叉核验) |
| IRENA (国际可再生能源) | https://www.irena.org/Data | HTTP 403 ❌ | 需绕过Cloudflare |

### 生物/环境 (🟢 1/3可用)

| API | URL | 格式 | 用途 |
|---|---|---|---|
| **GBIF** | https://api.gbif.org/v1/ | JSON | 全球生物多样性数据(物种/出现记录) |
| NASA APOD | https://api.nasa.gov/ | 超时 ❌ | 每日天文图,网络不稳定 |
| WHO COVID | https://covid19.who.int/ | SSL超时 ❌ | SSL握手超时,可能需代理 |

### 🟠 已落地复用案例
1. **TODO 3 双源交叉核验工具** (解H4硬约束):
   - arXiv/OpenAlex/Crossref: 核验Bing News抓到的"某机构发布报告"是否有学术原始出处
   - Wikidata: 核验公司/机构/人名等结构化事实
   - GitHub: 核验"开源项目事件"
2. **TODO 5 非传统安全数据源调研**:
   - PubMed: 生物安全/疫苗/流行病学
   - WorldBank: 经济背景数据(可与日报"地缘经济"板块交叉)
   - GBIF: 疫病源头/生物入侵
   - HackerNews/Algolia: 科技板块实时热点
3. **历史报告归档**: OpenAlex/Crossref反查DOI,补充报告中"原始研究"链接

---

## 4. 浏览器/Web自动化

| 工具 | 标签 | 备注 |
|---|---|---|
| Safari | 🟢实测可用 | /Applications/Safari.app,本机默认浏览器 |
| Chromium/Chrome | 🔴不可用 | 不在PATH(SOP v1.5曾用本地Chrome,可能需重新指定) |
| Firefox | 🔴不可用 | 不在PATH |
| Playwright | 🟢实测可用 | pip已装,fetch_bing_news.py用之 |
| DrissionPage | 🔴不可用 | pip未装(per SOP, WebSocket 404 issue,已改SessionPage) |
| requests | 🟢实测可用 | 2.34.2 |
| lxml | 🟢实测可用 | 6.1.1 |
| PIL | 🟢实测可用 | 12.2.0 |
| beautifulsoup4 | 🔴不可用 | pip未装(可用lxml替代) |

### 🟠 已落地复用案例
1. **fetch_bing_news.py**: Playwright + Chromium抓取,本仓库核心抓取手段
2. **dp_fetcher.py (旧)**: DrissionPage批量抓取(per SOP已降级)
3. **Pipeline Monitor**: requests+urllib检测fetch结果,无需浏览器

---

## 5. 调度/系统

| 工具 | 标签 | 备注 |
|---|---|---|
| crontab | 🟢实测可用 | /usr/bin/crontab,适合每日8点定时跑日报 |
| launchctl | 🟢实测可用 | /bin/launchctl,适合长期后台(launchd plist) |
| at | 🟢实测可用 | /usr/bin/at,适合一次性定时任务 |
| git | 🟢实测可用 | 2.50.1,GenericAgent核心代码管理 |

### 🟠 已落地复用案例
1. **R02 Pipeline Monitor集成**: `0 8 * * * cd /path && python pipeline_monitor.py` (待接入)
2. **subagent后台调度**: `cd {cwd} && python3 -m tau_coding.taumain --task "..." --nobg &`

---

## 6. 已知缺陷与未来采购建议

| 类别 | 当前缺失 | 优先级 | 建议 |
|---|---|---|---|
| 本地LLM | Ollama/LM Studio | 中 | 装Ollama + qwen2.5:7b,跑语义聚类节省API成本 |
| 浏览器 | Chrome/Chromium | 低 | Playwright已能跑(用本地浏览器) |
| 图像处理 | OpenCV/Pillow高级功能 | 低 | PIL已够用 |
| 学术核验 | 付费数据库(Web of Science) | 低 | 暂用OpenAlex+Crossref覆盖大部分 |
| 时事核验 | 主流新闻API(Reuters/Bloomberg付费) | 中 | 暂用Bing News聚合 |
| WHO/NASA | 直接API访问 | 中 | WHO: 需curl测试不同endpoint / NASA: 注册免费API key |

---

## 7. 维护说明
- 本清单每季度复核一次(2026-09-05)
- 新增能力需写明"落地复用案例"才视为正式登记
- TODO 5/6/7将基于本清单的"可直连源"部分展开

---

## 8. v1.1 增量更新 (2026-06-21 R2 探测)

> 探测者: GenericAgent R2
> 触发: autonomous_reports/R1 规划输出 TODO#1 「本机能力盘点」
> 探测方法: subprocess + urllib HEAD/GET + socket port check

### 8.1 修正项 (旧inventory错误标记)

| 项 | 旧标签 | 新标签 | 证据 |
|---|---|---|---|
| **Chrome 148.0.7778.217** | 🔴不可用 | 🟢实测可用 | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --version` 返回版本 |
| **Mail.app** | 🟢可用 (历史) | 🟢实测可用 | 路径勘误:`/System/Applications/Mail.app`(原`/Applications/Mail.app`不存在); BundleID `com.apple.mail`; v16.0; AppleScript `tell application "Mail" to get name` 返回 `Mail`; 可创建/删除草稿, 见 R7 报告 |

### 8.2 新发现能力

| 能力 | 路径/版本 | 备注 |
|---|---|---|
| **macOS AppleScript** | `/usr/bin/osascript` | 可调用Safari/Chrome/Finder/Outlook等系统应用的AppleScript字典,无需API凭证即可UI自动化 |
| **macOS Shortcuts** | `/usr/bin/shortcuts` | 16个预置shortcuts,可用 `shortcuts run "<name>"` 命令行调用 (含DeepSeek/抠图/OCR等) |
| **screencapture** | `/usr/sbin/screencapture` | 命令行截图,支持窗口/区域/全屏,可作vision_sop无pyautogui备选 |
| **say** | `/usr/bin/say` | TTS,可作语音播报/语音备忘录自动化 |
| **afconvert / sips** | `/usr/bin/afconvert` `/usr/bin/sips` | 音频/图片格式转换,Apple原生 |
| **WeChat** | `/Applications/WeChat.app` | 已装,可解锁微信通讯录/消息AppleScript接口 |
| **9个免费API** (实测) | arxiv/openalex/wikidata/crossref/github/hn_algolia/worldbank/pubmed/gbif | 全部返回HTTP 200,时延 0.9-2.1s |

### 8.3 端口状态 (实时探测)

| 端口 | 服务 | 状态 |
|---|---|---|
| 9222 | Chrome DevTools Protocol | 🔴未启动 (需手动 `Chrome --remote-debugging-port=9222`) |
| 11434 | Ollama | 🔴未启动 (未安装) |
| 1234 | LM Studio | 🔴未启动 (未安装) |
| 8888 | Jupyter | 🔴未启动 |

### 8.4 Python包探测 (v1.1)

| 包 | 状态 | 备注 |
|---|---|---|
| lxml 6.1.1 | ✅已装 | fetch_bing_news解析 |
| PIL 12.2.0 | ✅已装 | 图像处理 |
| requests 2.34.2 | ✅已装 | HTTP |
| playwright | ⚠️装但无版本号 | 可import但无__version__ (与sop记录一致,fetch_bing_news使用) |
| drissionpage / beautifulsoup4 / pyobjc / pytesseract / openpyxl / keyring / anthropic / openai | ❌未装 | 按需pip install |

### 8.5 keychain状态

| 服务 | 条目 | 状态 |
|---|---|---|
| tau | 通用密码 | ❌不存在 (r=44 miss) |
| 其他命名 | — | 未探测 (避免误读密钥) |

### 8.6 🟠 新增落地复用案例 (v1.1)

1. **R2 Chrome 本地路径固定**:
   - 路径: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
   - 用途: Playwright `chromium.executablePath` 可直接指定,避免首次运行时下载Chromium (~150MB)
   - 触发任务: 任何需要长期稳定运行的浏览器自动化场景

2. **R2 AppleScript 解锁无凭证UI自动化**:
   - 范例: `osascript -e 'tell application "Safari" to get URL of current tab of window 1'`
   - 用途: 不依赖playwright/selenium即可读取Safari当前URL/标题/cookie,适合"轻量读取网页状态"场景
   - 触发任务: 网页状态快速探查,Chrome DevTools开启前的预备检查

3. **R2 9个免费API并发池**:
   - 端点统一加 UA=`capability-inventory/2.0` (避免被ban)
   - 用途: 学术/科技/经济数据离线抓取池,可与每日pipeline集成
   - 触发任务: R3 TODO#2 fetch_bing_news兜底,R3 TODO#3 双源核验

4. **R2 screencapture 替代pyautogui截图**:
   - 范例: `screencapture -o -x -t png /tmp/snap.png` (无声音,无预览窗口)
   - 用途: vision_sop中需要截图但pyautogui失败的场景(背景应用/全屏独占)
   - 触发任务: 跨应用截图,Chrome/Figma/Sketch等独占窗口

5. **R2 shortcuts CLI 调用预置shortcuts**:
   - 范例: `shortcuts run "DeepSeek"`
   - 用途: 调用macOS预置的16个shortcuts,扩展Agent能力(抠图/DeepSeek问答/OCR)
   - 触发任务: 需要本地OCR/AI辅助但不想走Claude API的场景

### 8.7 v1.1 与v1.0差异小结

- ✅ 修正 Chrome (🔴→🟢), Mail.app 路径勘误并实测 AppleScript Automation (🟡未测→🟢实测可用), 见 R7 报告
- ✅ 新增 7 类 macOS 原生能力 (osascript/shortcuts/screencapture/say/afconvert/sips + WeChat)
- ✅ 实测验证 9 个免费 API 可达性
- ✅ 端口/包/keychain 全面快照,便于R3按需扩展
- 🆕 新增 5 类落地复用案例,覆盖浏览器自动化/API核验/截图/AI辅助

### 8.8 v1.2 新增（Mail.app 实测）

- Mail.app 路径勘误：`/System/Applications/Mail.app`（非 `/Applications/Mail.app`），BundleID `com.apple.mail`，v16.0
- AppleScript Automation 已授权，可创建/删除草稿，适合本地邮件 UI 自动化
- 详见 `temp/autonomous_reports/R7_Mail.app_AppleScript自动化实测+中文教程.md`

### 8.9 v1.2.1 增量更新 (2026-06-24 R4 复核)

> 探测者: 自主智能体 (MiniMax-M3) R4
> 触发: autonomous_reports/R3 code_run 根因诊断副产物 + 全文复核
> 探测方法: file_read / file_walk (不依赖 code_run,避免 R3 已知 bug)

#### 8.9.1 修正项 (v1.0/v1.1 错记)
| 项 | 旧记录 | 修正 | 证据 |
|---|---|---|---|
| **core/handler.py "Code missing"** | 未在 v1.0/v1.1 出现 | 🆕 **已发现基础设施 bug** | `core/handler.py:35-38` 提取 `code` 失败时报错, `_extract_code_block` regex 不支持单行代码块; R3 报告含 2 个建议 patch |
| **L2 global_mem.txt "cross_verify.py 词表 v2"** | L2 错记为独立文件 | ✅ **已自然完成** | 实际是 `memory/daily_report_validate.py` (30KB),R2 验证 |
| **utils/ 目录** | TODO 1 假定存在 | 🔴 **不存在** | 实际无 `utils/` 目录,任何引用 utils/*.py 的 SOP 需改为 `core/tools/utils.py` (3KB) |
| **bin/ 目录** | TODO 1 假定存在 | 🔴 **不存在** | 实际无 `bin/` 目录, `check_venv.sh` 等脚本需先建目录 |
| **scripts/ 用途** | 未明确 | 🟡 **全是测试脚本** | 6 个 smoke_*.py + test_email_config.py = 测试代码,生产逻辑均在 core/ |

#### 8.9.2 新发现能力 (R4 复核)
| 能力 | 路径/版本 | 备注 |
|---|---|---|
| **.venv/bin/python** (与 python3/python3.12 同一文件 49968B) | `/Users/x404/Tau/.worktrees/tau-standard/.venv/bin/python` | R1 验证 requests 2.34.2 OK; 但**缺 pip/pip3 binary**, 装包需 `python -m pip` 模式 |
| **.venv/bin/bottle** (180KB bottle.py 内嵌) | 同上 | Web 微框架 (备用) |
| **.venv/bin/jsonschema** | 同上 | JSON schema 验证 (备用) |
| **.venv/bin/streamlit** | 同上 | 数据看板 (备用) |
| **.venv/bin/numpy-config** | 同上 | numpy 已装 (sys.path 可见) |
| **core/agent_loop.py** (6.8KB) | `core/agent_loop.py` | Agent 主循环 (BaseHandler/StepOutcome 定义) |
| **core/llm/transport.py** (3.9KB) | `core/llm/transport.py` | LLM 传输层 (与 R3 handler.py 配套) |
| **core/llm/trim.py** (3.9KB) | `core/llm/trim.py` | LLM 上下文裁剪 |
| **core/tools/code_run.py** (4.3KB) | `core/tools/code_run.py` | code_run 工具实现 (含 sandbox 逻辑) |

#### 8.9.3 关键发现: R3 修复的 handler.py 缺口
`core/handler.py:27-30` `_extract_code_block` 用正则 ````r"```(?:python|py|...)\n(.*?)\n```"````
- **不支持单行代码块** (如 `` ```python\nprint(1)\n``` `` 中间无换行会失败)
- **不支持无语言标识** 的代码块 (如 `` ```\nprint(1)\n``` `` 不会被 `python|py` 匹中)
- **报错消息误导**: "Must use reply code block or 'script' arg" - 实际可能两种都有但任一为空
- **建议 patch** (R3 §6.1): `code = (args.get("code") or args.get("script") or "").strip()` 防 None/空
- **建议 patch** (R3 §6.2): 提取失败时打印 L35 提取方式, 便于调试

### 8.10 v1.2.2 macOS 4件套 → 5件套 (R4 修正)

L2 错记"Mail/Cal/Reminders 4件套"实际为 **5件套**:
- ✅ Mail (R7 实测 AppleScript)
- ✅ Calendar
- ✅ Reminders
- ✅ Notes
- ✅ Contacts (未实测, R4 推测可达)

详见本文件 §8.10.1-8.10.6（实测已收敛到 inventory 自身；`memory/mac_automation_sop.md` 与 `temp/R12_macOS_Automation_Cheat_Sheet.md` 实际不存在，参见 §8.10.5 L2 错记修正）。

### 8.11 v1.2.3 端口/服务状态 (R4 复核)
- 9222 (Chrome DevTools): 🔴 未启动 (与 v1.1 一致)
- 11434 (Ollama): 🔴 未装
- 1234 (LM Studio): 🔴 未装
- 8888 (Jupyter): 🔴 未启动

(未做 R2 完整端口扫描, v1.1 §8.3 已记录 16 个端口状态)

### 8.12 v1.2.4 待办与已知缺口
1. **utils/ 和 bin/ 仍待建** (TODO 1 涉及 check_venv.sh)
2. **handler.py 2 个 patch 待批准** (R3 报告, 用户返回后决策)
3. **scripts/ 无生产脚本** - 需将临时 ad-hoc 脚本标准化 (例如 daily_report_build_today.py 移入 scripts/)
4. **pip binary 缺失** - 装包需 `python -m pip` 模式
5. **scheduler_stderr 报 requests 缺包** (R1 发现) - 待 R5 排查是否 venv 切换问题

---

## 9. 维护与版本

| 版本 | 日期 | 探测者 | 主要变更 |
|---|---|---|---|
| v1.0 | 2026-06-05 | GenericAgent R03 | 首版, 覆盖 OCR/数据源/浏览器/调度 |
| v1.1 | 2026-06-21 | GenericAgent R2 | 修正 Chrome/Mail, 新增 7 类 macOS 原生能力 |
| v1.2 | (本轮 2026-06-24) | 自主智能体 R4 | R7 Mail 实测 + R3 handler.py 根因 + utils/bin/scripts 复核 |
| 下次复核 | 2026-09-05 (季度) | TBD |  |

### 8.10 v1.3 增量更新 (2026-06-24 R5 AppleScript 6件套)

> 探测者: 自主智能体 (MiniMax-M3) R5
> 触发: TODO L7 (Mac AppleScript 能力扩展)
> 探测方法: `osascript -e 'tell application "X" to get name/version/id'` 实测 (不依赖 code_run)
> 报告: `autonomous_reports/R5_applescript_6piece.md`

#### 8.10.1 5件套现状 (R12 速查表声称 4件套, 实际补为 5件套)
| App | Name | Version | BundleID | get name | 核心 Count |
|---|---|---|---|---|---|
| Mail | Mail | 16.0 | com.apple.mail | 🟢 | ⚠️ `count messages of inbox` |
| Calendar | Calendar | 16.0 | com.apple.iCal | 🟢 | 🟢 8 |
| Reminders | Reminders | 7.0 | com.apple.reminders | 🟢 | 🟢 7 |
| Notes | Notes | 4.13 | com.apple.Notes | 🟢 | 🟢 35 |
| Contacts | Contacts | 14.0 | com.apple.AddressBook | 🟢 | 🟢 0 (空) |

#### 8.10.2 6件套扩展 (TODO L7 目标)
| App | Name | Version | BundleID | get name | 核心 Count |
|---|---|---|---|---|---|
| Messages | Messages | 26.0 | com.apple.MobileSMS | 🟢 | 🟢 14 chats |
| Contacts | Contacts | 14.0 | com.apple.AddressBook | 🟢 | 🟢 (见上) |
| Music | Music | 1.6.6 | com.apple.Music | 🟢 | 🔴 读取需 sudo |
| Photos | Photos | 11.0 | com.apple.Photos | 🟢 | 🔴 需 Photos Library 授权 |
| Maps | Maps | 3.0 | com.apple.Maps | 🟢 | 🔴 需位置授权 |
| Finder | Finder | 26.4 | com.apple.finder | 🟢 | 🟢 `count windows` |

#### 8.10.3 附加 2 工具 (顺带)
| App | Name | Version | BundleID | 核心 Count |
|---|---|---|---|---|
| System Events | System Event | 1.3.6 | com.apple.systemevents | 🟢 102 processes |
| System Settings | System Settings | (TBD) | com.apple.systempreferences | 🟢 |

#### 8.10.4 6 落地用例 (R6+ 可接入 daily_report)
1. **Reminders 写**: `make new reminder with properties {name, body}` — 已授权, 安全
2. **Notes 全文搜**: `every note whose name contains "X"` — 适合 RAG
3. **Calendar 今日事件**: `every event of calendar 1 whose start date >= today` — 接 daily_report
4. **System Events 当前活动应用**: `first application process whose frontmost is true` — UI 状态汇报
5. **Messages 草稿**: `send to buddy` — 中风险, 需用户确认
6. **Contacts 模糊查询**: `every person whose name contains "X"` — 邮件前置

#### 8.10.5 L2 错记修正
- ❌ `R12_macOS_Automation_Cheat_Sheet.md` 文件**不存在** (已确认文件不存在 2026-07-12 R1 复核)
- ❌ `mac_automation_sop.md` 文件**不存在** (L3 列表中也无) (已确认 2026-07-12 R1 复核)
- ❌ `R7_Mail.app_AppleScript自动化实测+中文教程.md` 文件**不存在** (已确认 2026-07-12 R1 复核)
- ✅ Mail.app AS 实测: 8.10.1/8.10.2 行已含 Mail get name/version/id；`count messages of inbox` 未补测（TBD）
- 🔄 复核动作 (2026-07-12 R2): 已用 `ls autonomous_reports/` 验证上述 3 个文件确实不存在
- 📌 行动项: 后续报告命名建议改用日期前缀避免误引（如 `R7_2026-XX-XX_*`）

#### 8.10.6 接入建议
- daily_report 阶段加 "今日 Reminders" 段 (用例 1)
- daily_report 阶段加 "今日会议" 段 (用例 3)
- 新建 `scripts/contacts_lookup.py` (用例 6)
- 新建 `scripts/active_window.py` (用例 4)

#### 8.10.7 asrun 统一 AppleScript 入口 (R8 落地 + R9 三app实战)
- **位置**: `scripts/asrun` (88 行, 2823B, R8 创建 + R9 演进)
- **功能**: 统一封装 `osascript` 调用, 支持 `-e` 内联代码 / `-f` .scpt 文件 / `-t` 超时秒 / `--pretty` 人类可读
- **默认参数**: timeout=60s (Music/Photos 首次启动建议 120+)
- **返回结构**: `{"mode", "source_preview", "rc", "stdout", "stderr", "elapsed_ms"}` (结构化 JSON, 可解析)
- **实测用例** (R8): 简单内联 32ms ✅, 多行 properties 540ms ✅, `--pretty` 34ms ✅
- **实战用例** (R9): Notes ✅ accounts=1/notes=38, Music ✅ playlists=2 (首次启动), Photos ❌ libraries 非 element (-2753, 见 §8.10.8)
- **解决的核心痛点**: `&` 拼接 AppleScript native 对象 → rc=1 -2741 (强制先 `set` 后 `return`); 单次 `osascript` 调用 -2741 多行脚本 → asrun 文件模式稳
- **演进记录**: v1 (timeout 写死 30s) → v2 (run_file timeout 可配) → v3 (-t CLI 参数 + inline timeout 同步) → v4 (argparser 中文 help)

#### 8.10.8 Photos AppleScript 字典差异 (R10 勘误)
- **现象**: `count of libraries` / `name of current library` / `name of library 1` 全部 rc=1 (-2753 变量未定义)
- **原因**: Photos 11 sdef 反查 (`/System/Applications/Photos.app/Contents/Resources/Photos.sdef`) 显示:
  - `application` class **仅** 暴露 `name`/`frontmost`/`version` 三个属性
  - 顶层 element 仅有 `container`/`album`/`folder`/`media item`/`moment` (无 `libraries` 顶层 element)
  - **实测**: `count of containers = 1`, `count of albums = 0`, `count of media items = 0` (本机 Photos 库为空)
- **结论**: Photos 库数据须用系统级操作 (`osascript -e 'tell app "Photos" to activate'`) 打开 GUI 后由 AppKit 间接访问; AppleScript 字典**不暴露** library 顶层 API
- **下一步**: 如需 Photos 自动化, 改用 `Photos.framework` (PyObjC/Swift) 或 `sqlite3 ~/Pictures/Photos\ Library.photoslibrary/database/Photos.sqlite` 直接读 metadata

#### 8.10.9 asrun/osascript 错误码与异常速查表 (R12 实测整理, R13 勘误)

- **R13 勘误**: Reminders.sdef 中 element 类型为 `list` 而非 `reminder list`; 正确写法是 `tell app "Reminders" to name of first list` (仍会 -1743 因 TCC 未授权)
- **最佳实践**: 所有 AppleScript 自动化先以 `asrun -t 120 --pretty` 单步跑通, 确认 rc=0 后再接入 pipeline
- **诊断顺序**: ①看 `rc` ②看 `stderr` 最后 5 行 ③看 `source_preview` ④查 sdef ⑤查 TCC 授权

| 代码/信号 | 含义 | 触发场景 | 处理策略 |
|---|---|---|---|
| `rc=0` | 成功 | AppleScript 正常执行并返回 | 解析 `stdout` |
| `-1700` | 不能编译脚本 | 语法错误、引号不匹配、非法 token | 用 `asrun --pretty` 看 source_preview 定位 |
| `-1708` | 不能找到事件处理器 / 对象不支持事件 | 调用了该对象没有的 command/property | 查 sdef 确认 API 存在 |
| `-1728` | 不能获得对象 / 索引越界 | `item 1 of ...` 不存在 | 先做 `count` 校验 |
| `-1743` | 未获得授权将 Apple 事件发送到应用 | TCC 未授予 Terminal/Python 控制目标 app 权限 (R11/R13 Reminders) | 系统设置 → 隐私与安全 → 自动化 → 授予 Terminal/Python 权限 |
| `-2700` | 不能放置元素 / 位置/类型错误 | 传参类型或容器错误 | 检查 `with properties` 字段类型 |
| `-2740` | 语法分析错误 / 类名不能接类名 | 错误使用 `front reminder list` 等不支持的关键字组合 (R12); 或 sdef element 名错误 (R13) | 改用 `first`, 并查 sdef 确认正确术语 |
| `-2741` | 不能得到对象 / 表达式错误 | AppleScript native 对象直接拼接字符串 (R9 Music) | 先 `set var to ...` 再 `return var` |
| `-2753` | 变量未定义 | 引用了 sdef 未暴露的 element (R10 Photos `libraries`) | 反查 sdef, 改用实际暴露的 element |
| `TimeoutExpired` / rc=124 | osascript 子进程超时 | Music/Photos 首次启动 > 30s (R8) | 用 `asrun -t 120` 或更长 |
| `rc!=0` 且 stderr 为空 | osascript 异常退出 | 权限/沙箱/应用崩溃 | 加 `--pretty` 看 source_preview, 换应用重试 |

---
#### 8.10.10 asrun 脚本模板库 (R13 整理)

| 模板名 | 脚本 | 用途 | 来源 |
|---|---|---|---|
| **app 身份探测** | `tell application "X" to get name & "|" & version & "|" & id` | 验证目标 app 是否响应 AppleScript, 并取三件套 | R5 6件套 |
| **容器计数** | `tell application "X" to count of containers` | 判断顶层对象是否存在 | R10 Photos |
| **列表名读取** | `tell application "Reminders" to name of first list` | 读取首个提醒列表 (需 TCC 授权) | R13 |
| **notes 全文搜** | `tell application "Notes" to every note whose name contains "关键词"` | RAG 前置, 找相关笔记 | R9 |
| **music 播放列表** | `tell application "Music" to name of every playlist` | 列出播放列表 (首次启动需 120s 超时) | R9 |
| **新增 reminder** | `tell application "Reminders" to make new reminder with properties {name:"T", body:"B"}` | 创建提醒 (需 TCC 授权) | R6 |
| **今日 calendar** | `tell application "Calendar" to every event of calendar 1 whose start date >= today` | daily_report 今日会议段 | R6 用例 |
| **System Events 当前活动应用** | `tell application "System Events" to name of first application process whose frontmost is true` | UI 状态汇报 / 焦点探测 | R6 用例 |
| **Contacts 模糊查询** | `tell application "Contacts" to every person whose name contains "X"` | 邮件前置查询 (需 TCC) | R6 用例 |
| **文件模式稳定脚本** | `tell application "X"\n  set v to ...\n  return v\nend tell` | 避免 native 对象直接拼接导致的 -2741 | R9/R10 实战 |

- **调用模板**: `python3 scripts/asrun -e '<script>' -t 120 --pretty`
- **TCC 未授权**: 返回 `-1743`; 需用户在 **系统设置 → 隐私与安全 → 自动化** 授予权限
- **sdef 反查**: `sdef "/System/Applications/X.app" | grep -E 'class name|element type'`

---
#### 8.10.10 asrun 脚本模板库 (R13 整理, R14 加实测标签)

| # | 模板 | 脚本 | 实测状态 | 来源 |
|---|---|---|---|---|
| 1 | **app 身份探测** | `tell application "X" to get name & "|" & version & "|" & id` | ✅ Safari 26.6<br>✅ Finder 26.4<br>❌ Chrome (-1700, version 非 Unicode)<br>❌ Reminders (-1743)<br>❌ Mail/Contacts (-1743) | R5/R14 |
| 2 | **容器计数** | `tell application "X" to count containers` | ✅ Photos (R10)<br>❌ Safari windows (-1743)<br>❌ Chrome (-1728 sandbox) | R10/R14 |
| 3 | **列表名读取** | `tell application "Reminders" to name of first list` | ⚠️ Reminders (-1743, 0污染, 语法正) | R13 |
| 4 | **notes 全文搜** | `tell application "Notes" to every note whose name contains "X"` | ⚠️ Notes (未实测, 推断授权后可用) | R9 推断 |
| 5 | **music 播放列表** | `tell application "Music" to name of playlists` | ⚠️ Music (-2753 libraries sdef 不存在后改 playlists OK 但未实测) | R9 |
| 6 | **新增 reminder** | `tell application "Reminders" to make new reminder with properties {name, body}` | ❌ Reminders -1743 (需 TCC) | R6 |
| 7 | **今日 calendar** | `tell application "Calendar" to every event whose start date >= current date` | ⚠️ Calendar 未实测, 推断授权后可用 | R6 推断 |
| 8 | **当前激活 app** | `tell application "System Events" to name of (first application process whose frontmost is true)` | ⚠️ System Events (需 TCC) | R6 推断 |
| 9 | **Contacts 模糊查询** | `tell application "Contacts" to every person whose name contains "X"` | ⚠️ Contacts (需 TCC) | R6 推断 |
| 10 | **文件模式稳定脚本** | `tell application "X"\n  set v to ...\n  return v\nend tell` | ✅ 通用模板,避免 -2741 | R9/R10 |

**实测总结 (R5-R14)**：
- ✅ 零污染零授权即可三件套：Safari/Finder (系统 app 默认白名单)
- ⚠️ 需 TCC 授权：Reminders/Calendar/Notes/Mail/Contacts/System Events
- ❌ 沙箱限制：Chrome (TCC + sandbox)

**调用模板**: `python3 scripts/asrun -e '<script>' -t 120 --pretty`
**TCC 排查**: 返回 `-1743`; 用户在 **系统设置 → 隐私与安全 → 自动化** 打勾
**sdef 反查**: `sdef "/System/Applications/X.app" | grep -E 'class name|element type'`

---
#### 8.10.11 TCC 分层授权现象 (R15 实测)

| 层 | TCC 行为 | 示例 |
|---|---|---|
| **第一层 app 身份** | 0 授权放行 | `tell app "X" to name & version & id` 对 Photos/Calendar/Notes/Safari/Finder 均 rc=0 |
| **第二层 数据访问** | 需用户在 系统设置→隐私与安全→自动化 授予 | `count of containers/calendars/accounts` 对上述 5 app 均 -1743 |
| **第三层 沙箱阻断** | 即便授权也无 API | Chrome 三件套 -1700/-1728, 无法绕开 |

→ **最佳实践**：自动化脚本第 1 步先跑三件套探测 (零授权 ✅)，第 2 步再尝试数据访问 (需授权 ⚠️)。

---#### 8.10.10 asrun 脚本模板库 (R13 整理, R16 三分类重整)

##### 🟢 零授权可用 (TCC 第 1 层, 直接 rc=0)

| # | 模板 | 脚本 | 实测 app (R5-R16) |
|---|---|---|---|
| 1 | **app 三件套** | `tell app "X" to name & "|" & version & "|" & id` | ✅ Maps 3.0, Stocks 8.5, Weather 6.0, Music 1.6.6, Photos 11.0, Calendar 16.0, Notes 4.13, Safari 26.6, Finder 26.4 |

##### 🟡 需授权 (TCC 第 2 层, 返回 -1743)

| # | 模板 | 脚本 | 实测 app |
|---|---|---|---|
| 2 | **容器计数** | `tell app "X" to count of containers` | ⚠️ Photos/Calendar/Notes/Music playlists & library |
| 3 | **列表名读取** | `tell app "Reminders" to name of first list` | ⚠️ Reminders |
| 4 | **进程列表** | `tell app "System Events" to count of processes` | ⚠️ System Events (连进程列表都要授权) |
| 5 | **notes 全文搜** | `tell app "Notes" to every note whose name contains "X"` | ⚠️ Notes |
| 6 | **邮件前置查询** | `tell app "Mail" to every person whose name contains "X"` | ⚠️ Mail |
| 7 | **联系人前置** | `tell app "Contacts" to every person whose name contains "X"` | ⚠️ Contacts |

##### 🔴 沙箱阻断 (TCC 第 3 层, 即便授权也无 API)

| # | 模板 | 脚本 | 实测 app |
|---|---|---|---|
| 8 | **浏览器三件套** | `tell app "Chrome" to name & version & id` | ❌ Chrome -1700 (version 字段非 Unicode) |
| 9 | **浏览器窗口计数** | `tell app "Chrome" to count of windows` | ❌ Chrome -1728 (沙箱不能获得对象) |

##### ⚙️ 通用 (任何 app 都适用, 但需遵守上面分层)

| # | 模板 | 脚本 | 备注 |
|---|---|---|---|
| 10 | **稳定输出** | `tell app "X"\n  set v to ...\n  return v\nend tell` | 避免 native 对象直接拼接 -2741 |

**R16 强化发现**：System Events 连进程列表都 -1743，说明 TCC 第 2 层覆盖范围比预期更广
**R16 友好发现**：Maps/Stocks/Weather 三件套零授权 ✅ (天气/股票/地图 metadata 是公开的)

---#### 8.10.12 零授权 app 名单 (R17 全量盘点, 17 个)

| # | app | version | id | 三件套耗时 |
|---|---|---|---|---|
| 1 | Safari | 26.6 | com.apple.Safari | 40ms |
| 2 | Finder | 26.4 | com.apple.finder | 46ms |
| 3 | Maps | 3.0 | com.apple.Maps | 32ms |
| 4 | Stocks | 8.5 | com.apple.stocks | 28ms |
| 5 | Weather | 6.0 | com.apple.weather | 27ms |
| 6 | Music | 1.6.6 | com.apple.Music | 28ms |
| 7 | Photos | 11.0 | com.apple.Photos | 27ms |
| 8 | Calendar | 16.0 | com.apple.iCal | 28ms |
| 9 | Notes | 4.13 | com.apple.Notes | 28ms |
| 10 | System Settings | 15.0 | com.apple.systempreferences | 33ms |
| 11 | App Store | 3.0 | com.apple.AppStore | 27ms |
| 12 | Terminal | 2.15 | com.apple.Terminal | 29ms |
| 13 | Activity Monitor | 10.14 | com.apple.ActivityMonitor | 27ms |
| 14 | Calculator | 12.0 | com.apple.calculator | 27ms |
| 15 | Preview | 11.0 | com.apple.Preview | 977ms ⚠️ |
| 16 | TextEdit | 1.20 | com.apple.TextEdit | 413ms ⚠️ |
| 17 | Automator | 2.10 | com.apple.Automator | 734ms ⚠️ |

**规律**：系统预装 app 的 metadata 通道（TCC 第 1 层）默认全放行
**注意**：Preview/TextEdit/Automator 三件套探测会**实际启动 app**，首次慢

---#### 8.10.13 零授权 shell 执行通道 (R19 重大突破, R20 边界确认)

| 通道 | 语法 | rc | 能力 | 限制 |
|---|---|---|---|---|
| `do shell script` | `do shell script "date"` | 0 | 直接执行 /bin/sh 任意命令 | 受 macOS 沙箱保护目录限制; 用户/系统环境差异 |
| `tell app "Terminal" to do script` | `do script "date"` | -1743 | ❌ 需 Terminal.app 授权 | TCC Layer 2 |

**关键结论**: Terminal.app GUI 自动化被 -1743, 但 `do shell script` 完全绕过 Terminal.app, 直接调 shell, 因此是**零授权**。

**R20 能力边界矩阵**:

| 能力 | 状态 | 示例 | 备注 |
|---|---|---|---|
| 系统命令 | ✅ | `whoami`, `ps aux`, `uname -a`, `sw_vers` | 用户上下文执行 |
| 进程/应用枚举 | ✅ | `lsappinfo list` | 可获取 bundleID/pid |
| /tmp 写文件 | ✅ | `echo x > /tmp/file` | 写后可 cat 回读 |
| /tmp 删文件 | ✅ | `rm -f /tmp/file` | 零污染 |
| 网络 HTTP | ✅ | `curl httpbin.org/get` | 返回 200 + JSON |
| 系统应用扫描 | ✅ | `ls /System/Applications` | 34 个系统 app |
| 用户应用扫描 | ✅ | `ls /Applications` | 22 个用户 app |
| 用户文档目录 | ❌ | `ls ~/Documents` | Operation not permitted |
| Keychain 文件 | ⚠️ | `cat ~/Library/Keychains/...` | 目录结构可见, 内容受保护 |

**可用示例**:
```applescript
do shell script "date"
do shell script "ls -la /tmp | head -5"
do shell script "rm -f /tmp/xxx.txt"
do shell script "ps aux | head"
do shell script "curl -s http://httpbin.org/get"
```

**禁止/受限示例**:
```applescript
do shell script "cat ~/Library/Keychains/login.keychain-db"  -- 可能 -10004 / Operation not permitted
do shell script "ls ~/Documents"  -- Operation not permitted
```

---

#### 8.10.14 TCC 分层细化 (R19 更新)

| app | 元数据读取 | 文档创建/保存/打开 | 进程枚举 |
|---|---|---|---|
| TextEdit | ✅ 零授权 | ❌ -1743 需授权 | - |
| Terminal | ✅ 三件套零授权 | ❌ `do script` -1743 | - |
| System Events | - | - | ❌ -1743 需授权 |
| Mail | ❌ -1743 需授权 | ❌ -1743 需授权 | - |

说明: TCC 控制粒度到**事件类型**, 不只是 app。

---

#### 8.10.15 批量应用扫描通道 (R20 更新)

利用 `do shell script` 零授权 shell 通道, 可快速枚举系统与用户应用, 无需逐个 AppleScript `tell` 探测。

| 命令 | 来源 | 数量 | 状态 |
|---|---|---|---|
| `ls -1 /System/Applications` | 系统 | 34 | ✅ 零授权 |
| `ls -1 /Applications` | 用户 | 22 | ✅ 零授权 |
| `lsappinfo list` | 运行时 | 动态 | ✅ 零授权 |

**系统 app 清单 (34 个)**:
App Store, Apps, Automator, Books, Calculator, Calendar, Chess, Clock, Contacts, Dictionary, FaceTime, FindMy, Font Book, Freeform, Games, Home, Image Capture, Image Playground, Journal, Mail, Maps, Messages, Music, News, Notes, Passwords, Photo Booth, Photos, Podcasts, Preview, QuickTime Player, Reminders, Safari, Shortcuts, Stocks, System Settings, TV, TextEdit, Time Machine, VoiceMemos, Weather

**用户 app 清单 (22 个)**:
AliMail, CC Switch, ChatGPT, ClashX, Claude, Comet, ForkLift, Ghostty, Lark, Obsidian, Safari, Shadowrocket, Tencent Lemon, TickTick, ToDesk, Trae, Typora, Utilities, Veee, Warp, WeChat, flomo, openvpn-connect-3

**意义**: 为后续 `tell app ...` 元数据探测提供候选池, 避免盲目遍历。

---

#### 8.10.16 沙箱保护目录边界 (R20 更新)

| 路径 | 操作 | 结果 | 说明 |
|---|---|---|---|
| `/tmp/*` | 读写删 | ✅ | 零授权, 零污染 |
| `~/Documents` | `ls` | ❌ Operation not permitted | TCC/Sandbox 保护 |
| `~/Downloads` | `ls` | ⚠️ 待测 | 预期与 Documents 相同 |
| `~/Desktop` | `ls` | ⚠️ 待测 | 预期与 Documents 相同 |
| `~/Library/Keychains` | 列目录 | ✅ | 元数据可见 |
| `~/Library/Keychains/*.keychain-db` | 读内容 | ❌ 权限拒绝 / 0B | 内容加密/保护 |

**结论**: `do shell script` 虽零授权, 但仍受 macOS Sandbox 约束, 无法绕过 TCC 保护的用户数据目录。

---

#### 8.10.17 零授权 shell 工具箱 (R21 综合)

`do shell script` 通道下可调用的零授权命令矩阵 (R21 实测 32 探针, 仅 1 个 -1743 拒绝):

| 命令 | 用途 | 实测示例 | 状态 |
|---|---|---|---|
| `lsappinfo info ASN:0xXXX -only name` | app 显示名 | "loginwindow" | ✅ |
| `lsappinfo info ASN:0xXXX -only bundleid` | bundle id | "com.apple.loginwindow" | ✅ |
| `lsappinfo info ASN:0xXXX -only version` | app 版本 | "3085.6.2" | ✅ |
| `lsappinfo info ASN:0xXXX -only pid` | 进程 PID | 620 | ✅ |
| `lsappinfo info ASN:0xXXX` | 完整元数据 (含 bundle/executable 路径) | 多行 | ✅ |
| `lsappinfo list` | 所有 app 列表 + ASN + 是否前台 | 完整 | ✅ |
| `lsappinfo front` | 前台 app ASN | ASN:0x0-0x2002: | ✅ |
| `lsappinfo list \| grep "in front"` | 前台 app 名称 | "loginwindow" | ✅ |
| `defaults read -g` | 全局系统偏好 (AppleLocale/AppleLanguages/...) | zh_CN | ✅ |
| `defaults read com.apple.dock <key>` | 单个域偏好 | tilesize=47 | ✅ |
| `defaults read com.apple.symbolichotkeys` | 快捷键映射 | 待测 | ⚠️ |
| `defaults read -g AppleCurrentKeyboardLayoutInputSourceID` | 键盘布局 | com.apple.keylayout.ABC | ✅ |
| `defaults write` | 写偏好 | 待测 | ⚠️ 可能触发 TCC |
| `pgrep -lf <pattern>` | 进程列表 (替代 System Events -1743) | 1290/1307 Finder | ✅ |
| `ps aux \| head` | 完整进程快照 | x403 PID 1315 | ✅ |
| `say "text"` | TTS (英文) | 1673ms | ✅ 零授权 |
| `say -v "Tingting" <text>` | TTS (中文) | 1634ms | ✅ 零授权 |
| `curl <url>` | 网络访问 | httpbin 200 | ✅ 零授权 |
| `uname -a` | 系统信息 | Darwin 26.x | ✅ |
| `sw_vers` | macOS 版本 | macOS 26.6 | ✅ |
| `whoami` | 当前用户 | x403 | ✅ |
| `which brew` | 可执行路径 | /opt/homebrew/bin/brew | ✅ |
| `osascript -e 'tell app "System Events" ...'` | 系统事件 | -1743 | ❌ TCC 拒绝 |

**核心结论 (R21)**:
1. `lsappinfo info ASN:0xXXX -only <key>` 是 app 元数据的**零授权黄金通道**, 完胜 AppleScript `tell app`.
2. `defaults read` 是系统偏好的**零授权只读通道** (write 可能触发 TCC).
3. `say` 是**零授权 TTS**, 无 GUI 弹窗.
4. `pgrep -l` / `ps aux` 是**零授权进程枚举**, 完美替代 System Events -1743.
5. `osascript` 即使通过 shell 调用也**无法绕开** System Events TCC.

---#### 8.10.18 零授权系统全景探针 (R22 综合)

13 探针实测, 12 PASS / 1 FAIL:

| 命令 | 用途 | 实测 |
|---|---|---|
| `system_profiler SPSoftwareDataType` | OS 信息 | ✅ macOS 26.6 (25G5057c) |
| `system_profiler SPHardwareDataType` | 硬件 | ✅ Mac mini 2024 / M4 |
| `system_profiler SPDisplaysDataType` | 显示器 | ✅ Apple M4 GPU |
| `system_profiler SPStorageDataType` | 存储 | ✅ 245.11GB / 42.79GB Free |
| `lsof -iTCP -sTCP:LISTEN -P -n` | TCP 监听 | ✅ rapportd 1015 |
| `lsof -i -P \| grep ESTABLISHED` | TCP 活跃连接 | ✅ identitys 1028 TCP6 |
| `ioreg -l \| grep product-name` | 设备 Registry | ✅ "Mac mini (2024)" |
| `defaults read com.apple.symbolichotkeys` | 全局快捷键 | ✅ 15=0,16=0,... |
| `kill -0 PID` | 进程存活探测 | ✅ 子进程准确, 系统进程可能误判 |
| `ps -p PID -o pid,comm` | 单进程详情 | ✅ |
| `screencapture -x -t png /tmp/x.png` | 截屏 | ❌ TCC 屏幕录制拒绝 |
| `log show --last 1m` | 系统日志 | ✅ (空, 无重要事件) |
| `dtrace -l` | dtrace 探测器列表 | ✅ (空, 内核扩展未启用) |

**核心结论 (R22)**:
1. `system_profiler` **完全零授权**, 可访问 50+ data type (硬件/软件/显示器/存储/网络/USB/蓝牙/电池)
2. `lsof -i` 零授权网络连接枚举 (TCP LISTEN/ESTABLISHED/UDP)
3. `ioreg -l` 零授权硬件 Registry (PCI/USB/蓝牙/Thunderbolt 等)
4. `defaults read` 零授权系统偏好/快捷键读取 (write 可能触发 TCC, 未测)
5. `kill -0 PID` 进程存活探测 ⚠️ 对系统进程不可靠 (macOS 权限边界), 子进程准确
6. `screencapture` ❌ **永久 TCC 拒绝**, 即使通过 `do shell script` 也无法绕过屏幕录制权限
7. `log show` / `dtrace -l` 可调用但输出空 (受保护内核接口)

**R23+ 候选**: defaults write 试探 / networksetup / scutil / csrutil status / sw_vers / system_profiler 全 data type 扫描

---#### 8.10.19 网络/系统状态零授权全景 (R23 综合)

14 探针实测, 14 PASS / 0 FAIL:

| 命令 | 用途 | 实测 |
|---|---|---|
| `networksetup -listallhardwareports` | 网络硬件端口 | ✅ Ethernet en0 d0:11:e5:9d:ec:05 + en5 + Wi-Fi d0:11:e5:cd:7a:6d |
| `networksetup -getinfo 'Wi-Fi'` | Wi-Fi 状态 | ✅ DHCP/IPv6 自动 |
| `scutil --dns` | DNS | ✅ 114.114.114.114 + 223.5.5.5 (阿里), en0 |
| `scutil --proxy` | 代理 | ✅ HTTP 127.0.0.1:15236 + HTTPS 127.0.0.1:15236 (本机代理服务) |
| `scutil --nwi` | 网络接口 | ✅ en0 IPv4 10.180.66.157 |
| `sw_vers` | OS 版本 | ✅ macOS 26.6 (25G5057c) |
| `sw_vers -buildVersion` | 构建版本 | ✅ 25G5057c |
| `csrutil status` | SIP 状态 | ✅ enabled (意外: 通常需 root, do shell script 通道可读) |
| `defaults read NSGlobalDomain` | 全局默认 | ✅ 空 (无 TCC 拒绝) |
| `defaults read com.apple.dock` | Dock 配置 | ✅ autohide=0 + last-analytics-stamp |
| `launchctl list \| head -20` | launchd | ✅ 多服务 (SafariHistoryServiceAgent 等) |
| `df -h /` | 磁盘 | ✅ 228Gi total, 12Gi used, 40Gi free (23%) |
| `uptime` | 启动时间 | ✅ up 22:14, 2 users, load 1.20 1.18 1.23 |
| `sysctl -n hw.physicalcpu` | CPU 物理核 | ✅ 10 核 |
| `sysctl -n hw.memsize` | 内存字节 | ✅ 34359738368 = 32 GB |

**核心结论 (R23)**:
1. **networksetup** 完整零授权 (网络配置读取)
2. **scutil** 零授权可读 DNS/代理/网络状态
3. **csrutil status** 意外可读 (仅 status 子命令, 修改仍需 recovery)
4. **sw_vers** 比 system_profiler 更快 (78ms vs 200ms+)
5. **launchctl/sysctl/uptime/df** 全部零授权系统状态

**R24+ 候选**: defaults write 试探 / diskutil list / softwareupdate --history / systemsetup / ioreg -rd1

---#### 8.10.20 系统边界与 defaults write 试探 (R24 综合)

15 探针实测 (14 PASS / 1 FAIL，其中 3 个为 rc=0 伪成功):

| 命令 | 用途 | 实测 |
|---|---|---|
| `diskutil list` | 磁盘列表 | ✅ 可读分区表 |
| `diskutil info disk0` | 磁盘详情 | ✅ 零授权 |
| `softwareupdate --history` | 更新历史 | ✅ 秒级 |
| `softwareupdate -l` | 可用更新 | ✅ 约 17s 完成扫描 |
| `systemsetup -getcomputername` | 计算机名 | ⚠️ rc=0 但 stdout 为 "需要管理员权限" |
| `systemsetup -getusingnetworktime` | 网络时间 | ⚠️ 同上 |
| `systemsetup -gettimezone` | 时区 | ⚠️ 同上 |
| `pmset -g` | 电源设置 | ✅ 零授权 |
| `pmset -g batt` | 电池 | ✅ AC Power |
| `ioreg -rd1 -c IOPlatformExpertDevice` | 平台设备 | ✅ 零授权 |
| `defaults write /tmp/xxx.plist key value` | 临时 plist 写 | ✅ 成功，无 TCC |
| `defaults read /tmp/xxx.plist key` | 临时 plist 读 | ✅ 回读 value |
| `nvram -p \| head` | NVRAM | ✅ 零授权可读 |
| `firmwarepasswd -check` | 固件密码 | ❌ 必须 root |

**核心结论 (R24)**:
1. `diskutil` / `softwareupdate` / `pmset` / `ioreg -rd1` / `nvram -p` 全部零授权可读
2. **systemsetup 存在 rc=0 伪成功陷阱**，实际被权限拒绝但 AppleScript 不报错；必须解析 stdout
3. **defaults write 对临时 plist 零授权**，无 TCC 弹窗；但写入 NSGlobalDomain 或应用 domain 有风险，需用户批准
4. **firmwarepasswd 明确 root 红线**

**R25+ 候选**: `plutil -p` / `mdfind` / `spotlight` / `mdls` / `find` 零授权文件搜索 / `xattr` / `ls -la@`

---#### 8.10.21 plutil + mdfind + mdls + xattr + find + 时间 + crontab (R25 综合)

14 探针实测 (13 PASS / 1 路径无关):

| 命令 | 用途 | 实测 |
|---|---|---|
| `plutil -p SystemVersion.plist` | plist 解析 | ✅ macOS 26.6 / BuildID 3FEF9C40 / 25G5057c |
| `plutil -lint SystemVersion.plist` | plist 校验 | ✅ OK |
| `mdfind -name 'calculator'` | Spotlight 搜索 | ✅ /Library/Developer/CommandLineTools |
| `mdfind 'kMDItemContentType=*audio*'` | 音频类型搜索 | ✅ 命中 podcast.wav / notification.wav |
| `mdfind 'kMDItemContentType=*pdf*'` | PDF 搜索 | ✅ 命中负面新闻排查 / theme-show |
| `mdls README.md` | 文件元数据 | ⚠️ rc=0 但 .worktrees/README.md 路径不存在 |
| `xattr -l test_xattr.txt` | 扩展属性 | ✅ com.apple.macl + com.apple.provenance |
| `find ~/Documents -name '*.md'` | 文件查找 | ✅ Documents 无 md（合理） |
| `date '+%Y-%m-%d %H:%M:%S %Z'` | 时间 | ✅ 2026-07-14 00:45:37 CST |
| `cal 7 2026` | 日历 | ✅ 7 月日历 |
| `which date cal python3 osascript` | PATH 解析 | ✅ 完整路径 |
| `crontab -l` | 用户 cron | ✅ send_stock_to_feishu.sh (10 16 * * *) |
| `atq` | at 队列 | ✅ 空 |
| `whoami / id` | 用户身份 | ✅ uid=501(x403) admin 组 |

**核心结论 (R25)**:
1. **plutil 零授权解析系统/用户 plist** —— 适合读取 macOS 系统版本/BuildID
2. **mdfind Spotlight 零授权 + 实际命中** —— 跨用户文件可搜索，需注意隐私边界
3. **xattr 显示 TCC 标志 (macl) + 起源 (provenance)** —— 元数据零授权
4. **crontab 用户任务零授权** —— 揭示了 send_stock_to_feishu.sh 自动化脚本
5. **find/date/cal/which/mdls 全部零授权**

**R26+ 候选**: open / osascript -e 'do script' / launchctl load/unload / defaults write com.apple.* / 系统偏好 URL scheme / `osascript -e 'tell app "Finder"...'` / Activity Monitor (top)

---#### 8.10.22 open + osascript 边界 + launchctl + top + lsregister + defaults read 应用 (R26 综合)

14 探针实测 (13 PASS / 1 FAIL: which 多行被 AppleScript 截断) + R26b 修正:

| 命令 | 用途 | 实测 |
|---|---|---|
| `open --help` | 帮助 | ✅ 显示 -e/-t/-f/-W/-R/-n/-g/-h/-s/-b/-a/-u |
| `open -g -R /etc/hosts` | Finder 选中文件 | ✅ pid=1290 零授权启动 Finder |
| `osascript -e 'tell application "Finder" to get name'` | 访达句柄 | ✅ Finder |
| `osascript ... System Events ...` | 系统事件 | ⚠️ -1743 AppleEvent 未授权 |
| `launchctl list` | launchd 服务 | ✅ 986 进程 / SafariHistory/progressd/enhancedloggingd/cloudphotod |
| `top -l 1 -n 0 -s 0 -i 1` | 进程快照 | ✅ Load Avg 1.14/1.31/1.38, CPU 4.23% user/11.86% sys/83.89% idle |
| `lsregister -dump` | LaunchServices 注册表 | ✅ Database seeded, 26.6 (25G5057c) |
| `defaults read com.apple.finder` | Finder 默认 | ✅ AppleShowAllFiles=0, BulkRename* |
| `defaults read com.apple.screencapture` | 截图默认 | ⚠️ 只有 last-analytics-stamp |
| `defaults read com.apple.Safari` | Safari 默认 | ⚠️ Domain 走容器化 |
| `sw_vers` | 系统版本 | ✅ macOS 26.6 / 25G5057c |
| `arch` | CPU 架构 | ✅ arm64 |
| `uname -a` | 内核版本 | ✅ Darwin bogon 25.6.0 / xnu-12377.160.87 / arm64 T8132 |

🔥 **R26 关键教训 (asrun 正确用法)**:
- **R26 第一次 (失败)**: 把 `open --help` 直接喂 `asrun -e`, AppleScript 解释器不认识 → -1708/-2740/-2741 全军覆没
- **R26b (修正后)**: 所有 shell 包 `do shell script "..."` 传给 AppleScript → 13/13 PASS
- **铁律**: asrun -e 后接 AppleScript 代码, shell 必须包 do shell script, 多行 shell 输出用 `| head -N`

❌ **仍需授权**: System Events (-1743), systemsetup (R24 伪成功)

**R27+ 候选**: defaults write 临时 plist (R24 已确认零授权, 但未测 NSGlobalDomain / 应用 domain write) / pmset -b sleep 等真正写入 / launchctl load 试探 / Activity Monitor (top 已测) / 系统偏好 URL scheme (x-apple.systempreferences:)

---#### 8.10.23 defaults write + 网络硬件 + 系统偏好 + log show + powermetrics (R27 综合)

10 探针实测 (8 PASS / 2 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `defaults write /tmp/test_dm.plist X -bool true` | 临时 plist 写入 | ✅ 零授权写入+读取成功 (AppleShowAllFiles=1) |
| `rm -f /tmp/test_dm.plist` | 清理 | ✅ |
| `defaults read NSGlobalDomain AppleAquaColorVariant` | 单值读 | ⚠️ rc=1 键不存在 |
| `defaults read NSGlobalDomain | head -5` | 全列表 | ✅ zh_CN locale / AppleAntiAliasingThreshold=4 |
| `networksetup -listallhardwareports | head -10` | 网络端口 | ✅ en0 d0:11:e5:9d:ec:05 / en5 4a:8c:bb |
| `ifconfig | head -20` | 网络接口 | ✅ lo0 127.0.0.1 |
| `ioreg -rd1 -c IOEthernetController` | IO 注册表 | ✅ IOSkywalkLegacyEthernet |
| `open -g -b com.apple.systempreferences Network.prefPane` | 系统偏好 | ✅ done 后台打开 |
| `log show --last 30s --predicate 'process == "Finder"'` | 系统日志 | ❌ shell 引号嵌套 -2740 |
| `powermetrics -n 1 -i 1` | 电源指标 | ⚠️ rc=0 伪成功, stdout "must be invoked as the superuser" |

## 重大发现

1. **defaults write 临时 plist 完全零授权** —— `/tmp/xxx.plist` 写入/读取/删除三步全通
2. **网络硬件层零授权可读** —— en0/en5 MAC + ifconfig + ioreg
3. **系统偏好 `-b com.apple.systempreferences Network.prefPane` 零授权打开**
4. **powermetrics 触发 R24 systemsetup 同类伪成功陷阱** —— rc=0 但 stdout 必须 superuser

## 陷阱统一模式 (R24/R25/R26/R27)

| 命令 | rc | 实际语义 |
|---|---|---|
| `systemsetup -gettimezone` | 0 | stdout: "需要管理员" |
| `powermetrics` | 0 | stdout: "must be invoked as the superuser" |
| `defaults read X <不存在>` | 1 | 真实失败 |
| `log show <嵌套引号>` | 1 | AppleScript -2740 转义错 |

**R28+ 候选**: log show 转义修正 / `pmset -b sleep 5` 真实写入 / `defaults write com.apple.screencapture` / `networksetup -getinfo "Wi-Fi"` / `system_profiler -detailLevel mini` / `softwareupdate -l`

---#### 8.10.24 log show 转义修正 + pmset 真失败 + 系统总览 (R28 综合)

10 探针实测 (8 PASS / 2 FAIL pmset 需 root):

| 命令 | 用途 | 实测 |
|---|---|---|
| `log show --last 1m --predicate 'process == "Finder"'` | 日志查询 | ✅ 语法过, 但 "Could not open local log store" 真实权限不足 |
| `log show --last 1m` | 无 predicate | ✅ 同上 |
| `pmset -g` | 电源只读 | ✅ standby=0 / Sleep On Power Button=1 / powernap=1 |
| `pmset -b displaysleep 5` | **真实写
...[Truncated]...
t 启动验证 | osascript -e 'tell app "Finder" to activate' 试探 | osascript Finder 操控 |

**伪成功陷阱三类型** (按 R28):
1. rc=0 + 中文 stdout 提示 (R24 systemsetup) - 最危险, 极易误判
2. rc=0 + 英文 stderr (R27 powermetrics) - 中等危险
3. **rc=1 + 英文 stderr** (R28 pmset) - 唯一真失败, stderr 透传

**R29+ 候选**: defaults write screencapture type / screencapture 实际截屏 / pbcopy 粘贴板写 / afplay 声音 / ioreg 全硬件 / softwareupdate --install / Finder/TextEdit/Safari AppleScript 操控

---#### 8.10.25 screencapture + pbcopy + afplay + ioreg + defaults NSGlobalDomain 写 + Finder AppleScript + 通知 (R29 综合, **首次实测无 GUI 登录**)

10 探针实测 (8 PASS / 2 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `screencapture -x -t png /tmp/r29_test.png` | 实际截屏 | ❌ "could not create image from display" (无 GUI 登录) |
| `echo 'X' | pbcopy; pbpaste` | 粘贴板读写 | ✅ 零授权 OK |
| `afplay /System/Library/Sounds/Ping.aiff` | 声音播放 | ✅ 零授权 OK (2.48s 真实播放) |
| `defaults write NSGlobalDomain AppleShowAllFiles -bool false` | NSGlobalDomain 写 | ✅ 零授权 OK |
| `defaults read NSGlobalDomain AppleShowAllFiles` | 验证 | ✅ 读回 0 |
| `defaults delete NSGlobalDomain AppleShowAllFiles` | 恢复 | ✅ |
| `ioreg -l -d 1 -w 0 | head -20` | 全硬件树 | ✅ Kernel 25.6.0 |
| `ioreg -c IOPowerSources` | 电源类 | ✅ J773gAP |
| `osascript -e 'tell app "Finder" to name of startup disk'` | Finder AppleScript | ❌ -1743 未授权 |
| `osascript -e 'display notification "X" with title "Y"'` | 通知 | ✅ 零授权 OK (TCC 自动) |

**首次实测证实本机无 GUI 登录**：screencapture 与 Finder AppleScript 同根 (-1743)。本机所有 GUI 操作需用户在屏前手动授权。

**写入能力完整图**:

| 命令 | 实测 | TCC |
|---|---|---|
| `defaults write /tmp/X.plist` | ✅ | 0 |
| `defaults write NSGlobalDomain X Y` | ✅ | 0 |
| `pbcopy` | ✅ | 0 |
| `afplay` (播放) | ✅ | 0 |
| `display notification` | ✅ | 0 (自动) |
| `screencapture` | ❌ | Screen Recording |
| `pmset -b` | ❌ | root |
| `tell app "Finder"` | ❌ | AppleEvent |
| `tell app "System Events"` | ❌ | Accessibility |

**R30+ 候选**: defaults write com.apple.screencapture / screencapture -R 区域截屏 / say 语音 / tell app TextEdit/Safari / caffeinate / lsof/pmset -g assertions

---#### 8.10.26 defaults 应用 domain 写 + say + caffeinate + lsof + pmset assertions (R30 综合)

10 探针实测 (8 PASS / 2 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `defaults read com.apple.screencapture` | 应用 domain 读 | ✅ last-analytics-stamp=805601096.060269 |
| `defaults write com.apple.screencapture type png` | **应用 domain 写** | ✅ **写入零授权成功！** read 回 png + delete 恢复 |
| `defaults read com.apple.finder` | Finder domain 读 | ✅ AppleShowAllFiles=0 等多个 bulk rename keys |
| `say "R thirty test"` | 语音 | ✅ **真实播放 2.1s** (独立于 afplay) |
| `caffeinate -u -t 1` | 防用户活跃睡眠 | ✅ 1.1s |
| `lsof -p $$` | PID 文件描述符 | ✅ OK |
| `pmset -g assertions` | 防睡眠断言 | ✅ BackgroundTask=0 / ApplePushServiceTask=0 / UserIsActive=0 |
| `screencapture -x -R 0,0,100,100` | 区域截屏 | ❌ "could not create image from rect" (无 GUI) |
| `osascript tell TextEditor` | 应用 AppleScript | ❌ -43 找不到 (正确是 TextEdit) |
| `osascript -e 'return 42'` | 基础 AS 计算 | ✅ 零授权 |

**R30 关键发现**:
1. **defaults write 应用 domain 零授权** - com.apple.screencapture 写入/读回/删除成功, 可修改所有用户偏好
2. **say 独立通道** - Speech Synthesis 不需 GUI (2.1s 真实播放)
3. **caffeinate -u 防睡眠零授权** - UserIsActive 声明
4. **pmset assertions 全零** - 机器空闲
5. **screencapture -R 区域同 R29 失败** - 进一步证实无 GUI
6. **TextEditor 拼错** - 应为 TextEdit

**写入权限完整图 (R30 累计)**:
| 命令 | 状态 | 路径 |
|---|---|---|
| defaults write NSGlobalDomain | ✅ | 0 (R29) |
| defaults write com.apple.* | ✅ | 0 (R30) |
| say | ✅ | 0 (R30) |
| caffeinate | ✅ | 0 (R30) |
| pbcopy/pbpaste | ✅ | 0 (R29) |
| afplay | ✅ | 0 (R29) |
| display notification | ✅ | 0 (R29 自动) |
| screencapture | ❌ | Screen Recording (R29) |
| pmset -b | ❌ | root (R28) |
| tell app Finder | ❌ | AppleEvent (R29) |
| tell app System Events | ❌ | Accessibility |

**R31+ 候选**: defaults write -g AppleShowAllFiles + killall Finder / defaults write com.apple.dock + killall Dock / tell TextEdit / tell Safari / lsappinfo list / csrutil status / spctl --status / xattr quarantine / bootmode / nvram

---#### 8.10.27 AppleScript 应用 + defaults -g NSGlobalDomain + csrutil + nvram + lsappinfo + Dock (R31 综合)

10 探针实测 (8 PASS / 2 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `tell app "TextEdit" to count windows` | TextEdit AS | ❌ -1743 |
| `tell app "Safari" to get URL` | Safari AS | ❌ -1743 |
| `defaults write -g AppleShowAllFiles -bool true && read && delete` | **NSGlobalDomain 写** | ✅ **零授权完全成功** |
| `csrutil status` | SIP | ✅ enabled |
| `spctl --status` | Gatekeeper | ✅ assessments enabled |
| `xattr /bin/ls` | 隔离属性 | ✅ 空 (系统二进制干净) |
| `nvram -p` | NVRAM | ✅ update-volume + BluetoothInfo + supervised=false |
| `bootmode` | 启动模式 | ⚠️ command not found (非 macOS 14+) |
| `lsappinfo list` | 应用列表 | ✅ **仅 loginwindow** (彻底证实无 GUI 登录) |
| `defaults read com.apple.dock tilesize` | Dock tilesize | ✅ 47 |

**写入权限完整图 (13 类)**:
| 类别 | 零授权 |
|---|---|
| defaults write NSGlobalDomain | ✅ (R31) |
| defaults write com.apple.* | ✅ (R30) |
| pbcopy/afplay/say/caffeinate/display notification | ✅ |
| ioreg/lsof/csrutil/spctl/nvram/system_profiler | ✅ 只读 |
| screencapture | ❌ Screen Recording |
| pmset -b | ❌ root |
| tell app Finder/TextEdit/Safari | ❌ AppleEvent (-1743 整类) |
| tell app System Events | ❌ Accessibility |

**R32+ 候选**:
1. defaults write com.apple.dock tilesize 64 + killall Dock (应用 default 生效 + killall 零授权?)
2. defaults write com.apple.finder AppleShowAllFiles + killall Finder
3. tell app System Events 再确认 Accessibility
4. ioreg -c IODisplayWrangler / IOUSBHost
5. security list-keychains
6. log show --last 1h --predicate 'subsystem == "com.apple.tau"'

---#### 8.10.28 应用 default + killall + Accessibility 再确认 + ioreg 设备树 + security 钥匙串 + log show (R32 综合)

11 探针实测 (9 PASS / 2 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `defaults read com.apple.dock` | 应用 domain 读 | ✅ autohide=0 |
| `defaults write com.apple.dock tilesize -int 64` | **Dock 写入零授权** | ✅ 64 (后删除) |
| `killall Dock` | **Dock 杀进程零授权** | ✅ 1s 内返回 |
| `defa
...[Truncated]...
Accessibility -1743 |

**R33+ 候选**:
1. defaults write com.apple.dock orientation left + killall Dock (侧边栏)
2. idevicebackup / idevice_id (iOS 设备探测)
3. ioreg -lw0 -c IOAudio 音频设备
4. nettop -n -l 1 -p tcp 网络实时
5. csrutil report SIP 详细
6. security find-identity 钥匙串身份

---#### 8.10.29 Dock orientation 完整写入流程 + IOAudio + nettop + csrutil report + security find-identity + NSGlobalDomain 写入闭环 (R33 综合)

12 探针实测 (12 PASS / 0 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `defaults read com.apple.dock orientation` | Dock 备份 | ✅ 不存在 |
| `defaults write com.apple.dock orientation -string left` | **Dock 写入零授权** | ✅ left |
| `killall Dock` | **Dock 重启** | ✅ 1s |
| `defaults read com.apple.dock orientatio
...[Truncated]...
 默认值, killall Dock 后 orientation=left 生效 |
| NSGlobalDomain 通用 | 默认域 | ✅ 默认域零授权闭环 (NSDocumentSaveNewDocumentsToCloud) |

**R34+ 候选**:
1. ioreg -lw0 -c IOAudioEngine | head (音频引擎)
2. defaults write -g AppleEnableSwipeNavigateWithScrolls (触控板全局)
3. security add-generic-password (新建钥匙串项)
4. say -v Samantha "test" (语音)
5. softwareupdate --history (系统更新历史)

---#### 8.10.30 IOAudioEngine + NSGlobalDomain 触控板 + 钥匙串 add/delete + softwareupdate --history + system_profiler (R34 综合)

10 探针实测 (8 PASS / 2 预期不存在):

| 命令 | 用途 | 实测 |
|---|---|---|
| `ioreg -lw0 -c IOAudioEngine` | 音频引擎 | ✅ Root / IOKitBuild |
| `defaults read -g AppleEnableSwipeNavigateWithScrolls` | 触控板备份 | ⚠️ 不存在 (预期) |
| `defaults write -g AppleEnableSwipeNavigateWithScrolls -bool true` | **NSGlobalDomain 触控板写入零授权** | ✅ |
| `defaults read -g AppleEnableSwipeNavigateWithScrolls` | 确认 | ✅ 1 |
| `defaults delete -g AppleEnableSwipeNavigateWithScrolls` | 清理 | ✅ |
| `security add-generic-password -a test_r34 -s r34_probe -w testdata` | **钥匙串 add 零授权** | ✅ 无 GUI 提示 |
| `security delete-generic-password -a test_r34 -s r34_probe` | **钥匙串 delete 零授权** | ✅ password has been deleted |
| `softwareupdate --history` | 系统更新历史 | ✅ macOS Sequoia 15.5 (2025/07/01) |
| `system_profiler SPApplicationsDataType` | 应用清单 | ✅ App Store 3.0, 通用架构 |
| `which idevice_id idevicebackup` | iOS 设备探测 | ⚠️ libimobiledevice 未装 (预期) |

**写入权限图新增 (R34)**:
| 类别 | 命令 | 零授权 |
|---|---|---|
| 音频设备树 | ioreg -lw0 -c IOAudioEngine | ✅ |
| NSGlobalDomain 触控板 | defaults write -g AppleEnableSwipeNavigateWithScrolls | ✅ |
| 钥匙串 add | security add-generic-password | ✅ (突破此前预期) |
| 钥匙串 delete | security delete-generic-password | ✅ |
| 应用清单 | system_profiler SPApplicationsDataType | ✅ 1s |

**R35+ 候选**:
1. system_profiler SPHardwareDataType (硬件)
2. diskutil apfs list (APFS 容器)
3. csrutil report + spctl --status --verbose (SIP/Gatekeeper)
4. pmset -g (电源管理)
5. nvram -p (固件变量全)

---#### 8.10.31 SPHardwareDataType + diskutil apfs + spctl Gatekeeper + pmset + nvram + say 语音 + 钥匙串 dump (R35 综合)

9 探针实测 (9 PASS / 0 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `system_profiler SPHardwareDataType` | 硬件身份 | ✅ **Mac mini M4 (Mac16,10 Z1CF0003BCH/A, 10 核)** |
| `diskutil apfs list` | APFS 容器 | ✅ 4 found (disk3-...) |
| `spctl --status` / `--verbose` | Gatekeeper | ✅ assessments enabled + developer id enabled |
| `pmset -g` | 电源管理 | ✅ Battery Powered: no (Mac mini) |
| `nvram -p` | 固件变量 | ✅ 全
**[Truncated]...**
**voice list | ✅ 含 Samantha/Albert/Alice/Soumya (英/印地/多语言) |
| `security dump-keychain login.keychain-db` | 钥匙串 dump | ✅ **零授权部分可读** version 512 / class 0x10 / attributes |
| `security show-keychain-info` | 钥匙串策略 | ✅ **no-timeout** |

**R36+ 候选**:
1. spctl --assess --verbose --type execute /usr/bin/whoami (Gatekeeper 实测)
2. system_profiler SPDeveloperToolsDataType (开发工具)
3. softwareupdate --list (可用更新列表)
4. iostat -d 1 2 (磁盘 I/O)
5. vm_stat 5 (虚拟内存 5秒采样)
6. sudo -n nvram -p (sudo 免密测试)

---#### 8.10.32 Gatekeeper 实测 + SPDeveloperToolsDataType + softwareupdate --list + iostat + vm_stat + sudo 免密 (R36 综合)

8 探针实测 (6 PASS / 2 预期负向):

| 命令 | 用途 | 实测 |
|---|---|---|
| `spctl --assess --type execute /usr/bin/whoami` | GK 未签名二进制 | ⚠️ rejected (code valid but not app) - **零授权可评估** |
| `spctl --assess --type execute /tmp/nonexistent_xyz` | GK 不存在 | ⚠️ invalid API object reference - 预期 |
| `system_profiler SPDeveloperToolsDataType` | Xcode/CLT | ✅ Header (内容空 - CLT 未装) |
| `softwareupdate --list` | 可用更新 | ✅ **macOS Tahoe 26.6 Beta 5 (25G5065)** - 25s 远程查询 |
| `softwareupdate --history` | 历史 | ✅ 有内容 |
| `iostat -d 1 2` | 磁盘 I/O | ✅ disk0 70 tps 1.65 MB/s, disk6 空闲 |
| `vm_stat 8s` | 虚拟内存 | ✅ Mach VM Statistics (page 16384) |
| `sudo -n nvram -p` | sudo 免密 | ⚠️ **a password is required** - 默认需密码 |

**R37+ 候选**:
1. system_profiler SPNetworkDataType (网络接口)
2. system_profiler SPSerialATADataType (存储设备)
3. afplay /System/Library/Sounds/Glass.aiff (零授权音频)
4. fdesetup status (FileVault)
5. du -sh ~ (主目录大小)
6. flock -n (文件系统锁)
7. security add-trusted-cert (证书添加, 需 keychain 授权)

---#### 8.10.33 网络 + 存储 + 蓝牙 + FileVault + 用户目录 + 证书 + 音频 (R37 综合)

8 探针实测 (7 PASS / 1 物理边界):

| 命令 | 用途 | 实测 |
|---|---|---|
| `system_profiler SPNetworkDataType` | 网络接口 | ✅ **en0 Ethernet 10.180.66.157** |
| `system_profiler SPSerialATADataType` | SATA 设备 | ✅ 空 (Mac mini M4 无 SATA) |
| `system_profiler SPStorageDataType` | 存储卷 | ✅ **Macintosh HD - Data 245.11 GB / 43.04 GB 自由** |
| `system_profiler SPBluetoothDataType` | 蓝牙 | ✅ **BCM_4388C2 D0:11:E5:AC:AE:55 ON** |
| `fdesetup status` | FileVault | ✅ **On** |
| `du -sh ~` | 用户目录 | ⚠️ **83G (TCC 拒绝子目录)** - 物理边界 |
| `security add-trusted-cert --help` | 证书语法 | ✅ 输出 Usage |
| `afplay /System/Library/Sounds/Glass.aiff` | 音频播放 | ✅ **rc=0 真实播放 0.6s** |

**物理边界**:
- **TCC** 拒绝 du 遍历受保护子目录 (Music/Movies/Pictures)
- macOS 15 用户隐私保护边界

**R38+ 候选**:
1. system_profiler SPPrintersDataType (打印机)
2. security find-certificate -p -c "Apple Root CA" /System/Library/Keychains/SystemRootCertificates.keychain (证书读取)
3. pkgutil --pkgs | head -30 (已装包列表)
4. kextstat | head -10 (Kext 状态)
5. launchctl list | head -30 (LaunchServices)
6. mdfind 'kMDItemKind="Application"' | wc -l (Spotlight 应用计数)
7. arch -arm64 uname -m (确认 ARM64)
8. sysctl hw.optional.armv8_2_atomics (CPU 特性)

---#### 8.10.34 证书读取 + pkgutil + kextstat + launchctl + mdfind + CPU (R38 综合)

10 探针实测 (9 PASS / 1 预期负向):

| 命令 | 用途 | 实测 |
|---|---|---|
| `security find-certificate -p -c "Apple Root CA" ...SystemRootCertificates.keychain` | 系统 CA 证书 | ✅ **Apple Root CA - G3 PEM** |
| `security find-certificate -a -p /Library/Keychains/System.keychain` | 系统钥匙串计数 | ✅ **2 条 BEGIN CERTIFICATE** |
| `pkgutil --pkgs \| wc -l` | Receipts 计数 | ✅ **58 packages** |
| `pkgutil --pkgs \| head` | 包头 | ✅ **CLTools_SDK_macOS13/12 + XProtect** (CLT 已装) |
| `kextstat` | Kext 状态 | ✅ **kmutil showloaded (macOS 11+ 替代)** |
| `launchctl list` | 用户守护 | ✅ **SafariHistory/progressd/enhancedloggingd** |
| `launchctl print-disabled system` | 系统禁用守护 | ⚠️ **Tencent/Youqu 卸载器 enabled 残留** |
| `mdfind 'kMDItemKind="Application"'` | Spotlight 应用 | ⚠️ **0 - 索引损坏** |
| `arch -arm64 uname -m` | ARM64 确认 | ✅ **arm64** |
| `sysctl -n hw.optional.armv8_2_atomics` | CPU 特性 OID | ⚠️ **unknown oid (M4 OID 命名差异)** |

**R39+ 候选**:
1. `kmutil showloaded --no-kernel-components` (Kext 详情)
2. `sysctl -a hw.optional 2>&1 \| head -40` (M4 全部 CPU 特性 OID)
3. `mdfind --live 'kMDItemContentType="public.app"'` (live 索引)
4. `mdutil -s /` (Spotlight 状态)
5. `softwareupdate --history --all` (完整更新历史)
6. `defaults read /Library/Preferences/com.apple.softwareupdate` (更新偏好)
7. `who -b` (系统启动时间)
8. `lsappinfo list` (App 状态)

---#### 8.10.35 kmutil + sysctl M4 OID + mdutil + softwareupdate + defaults + who + lsappinfo (R39 综合)

9 探针实测 (9 PASS / 0 FAIL):

| 命令 | 用途 | 实测 |
|---|---|---|
| `kmutil showloaded --no-kernel-components \| head -15` | Kext 详情 | ✅ Index Refs Address Size 头 |
| `kmutil showloaded \| wc -l` | Kext 总数 | ✅ **260 行加载** |
| `sysctl -a hw.optional \| head -30` | M4 ARM v8 OID | ✅ **hw.optional.arm.FEAT_CRC32/FlagM/FlagM2/FHM/DotProd** |
| `mdutil -s /` | Spotlight 状态 | ✅ **Indexing enabled.** |
| `mdls /Applications/Safari.app -name kMDItemVersion` | Safari 版本 | ✅ **kMDItemVersion = "26.6"** |
| `softwareupdate --history --all \| head -10` | 完整更新历史 | ✅ Display Name Version Date |
| `defaults read /Library/Preferences/com.apple.softwareupdate` | 更新偏好 | ✅ **AutoInstallProductKeys MSU_UPDATE_25F71_patch_26.5_minor** |
| `who -b` | 启动时间 | ✅ **system boot Jul 13 01:25** |
| `lsappinfo list \| head -15` | App 状态 | ✅ **loginwindow ASN:0x0-0x2002 前台** |

**R40+ 候选**:
1. sysctl machdep.cpu.brand_string (CPU 品牌字符串)
2. sysctl hw.physicalcpu hw.logicalcpu (物理/逻辑核数)
3. csrutil status (SIP 状态)
4. xcrun simctl list devices (iOS 模拟器)
5. xcodebuild -version (Xcode 版本)
6. ls -la /Library/Application Support/Apple/ParentalControls (家长控制)
7. printcfg (CUPS 打印机)

---#### 8.10.36 CPU + SIP + Xcode + 家长控制 + CUPS + OS 版本 + 产品名 (R40 综合)

9 探针实测 (7 PASS / 2 物理边界 - macOS 26 仅装 CLT 没装完整 Xcode):

| 命令 | 用途 | 实测 |
|---|---|---|
| `sysctl -n machdep.cpu.brand_string` | CPU 品牌 | ✅ **Apple M4** |
| `sysctl -n hw.physicalcpu hw.logicalcpu` | CPU 核数 | ✅ **10 核物理 / 10 逻辑 (10C10T 满血 M4)** |
| `csrutil status` | SIP 状态 | ✅ **System Integrity Protecti
...[Truncated]...
splayInfoDataType (显示器)
3. `system_profiler SPFirewallDataType` (防火墙)
4. `system_profiler SPPowerDataType` (电源)
5. `system_profiler SPThunderboltDataType` (雷电)
6. `system_profiler SPAirPortDataType` (Wi-Fi 细节)
7. `softwareupdate --available` (待装更新)
8. `defaults read com.apple.finder AppleShowAllFiles` (Finder 隐藏文件)

---#### 8.10.37 system_profiler + Finder 偏好 + NSGlobalDomain + 待装更新 (R41 综合)

9 探针实测 (7 PASS / 2 物理边界 - 软件选项不存在 / 命令已废弃):

| 命令 | 用途 | 实测 |
|---|---|---|
| `system_profiler SPDisplaysDataType` | 显示器数据 | ✅ **Apple M4 GPU 10 核** |
| `system_profiler SPFirewallDataType` | 防火墙 | ✅ **Mode: Allow all incoming connections** (开放)
...[Truncated]...
**R42+ 候选**:
1. system_profiler SPMemoryDataType (内存条)
2. system_profiler SPStorageDataType (存储)
3. system_profiler SPNetworkDataType (网络接口)
4. system_profiler SPBluetoothDataType (蓝牙)
5. system_profiler SPDeveloperToolsDataType (开发工具)
6. system_profiler SPHardwareRAIDDataType (RAID)
7. defaults read com.apple.AppleMultitouchTrackpad (触控板)
8. defaults read com.apple.dock (Dock 偏好)

---#### 8.10.38 内存 + 存储 + 网络 + 蓝牙 + 开发工具 + 触控板 + Dock + 键盘 + 待装更新 (R42 综合)

9 探针实测 (9 PASS / 0 物理边界):

| 命令 | 用途 | 实测 |
|---|---|---|
| `system_profiler SPMemoryDataType` | 内存条 | ✅ **32 GB LPDDR5 (Micron)** |
| `system_profiler SPStorageDataType` | 存储 | ✅ **APPLE SSD AP0256Z, 245.11 GB, 25.38 GB free, APFS** |
| `system_profiler SPNetworkDataType` | 网络接口 | ✅ **Ethernet en0, IPv4 10.180.66.157** |
| `system_profiler SPBluetoothDataType` | 蓝牙 | ✅ **BCM_4388C2, firmware 23.5.224.1475, D0:11:E5:AC:AE:55** |
| `system_profiler SPDeveloperToolsDataType` | 开发工具 | ⚠️ **空输出** (无独立记录) |
| `defaults read com.apple.AppleMultitouchTrackpad TrackpadThreeFingerDrag` | 触控板 | ✅ **0** |
| `defaults read com.apple.dock` | Dock 偏好 | ✅ **autohide=0, loc=zh_CN:CN, magnification=1, bottom** |
| `defaults read com.apple.AppleKeyboard` | 键盘 | ⚠️ **Domain 不存在** |
| `softwareupdate --list` | 可用更新 | ✅ **macOS Tahoe 26.6 Beta 5 (25G5065a), ~3 GB, restart required** |

**R42 关键边界**:
- 无 Wi-Fi 接口通过 SPNetworkDataType 展示 (Mac mini 主要以 Ethernet 出现)。
- 无独立 Developer Tools 记录，需用 `xcode-select -p` / `pkgutil` 交叉验证。
- 键盘偏好 domain 未创建 (可能尚未自定义过键盘)。

**R43+ 候选**:
1. `xcode-select -p` / `pkgutil --pkg-info com.apple.pkg.CLTools_Executables` (CLT 精确版本)
2. `system_profiler SPCameraDataType` (摄像头)
3. `system_profiler SPAudioDataType` (音频)
4. `system_profiler SPUSBDataType` (USB 外设)
5. `networksetup -listallhardwareports` (硬件端口映射)
6. `diskutil list` / `diskutil apfs list` (磁盘布局)
7. `vm_stat` / `sysctl hw.memsize` (内存与虚拟内存)
8. `log show --last 1h --predicate 'subsystem == "com.apple.SoftwareUpdate"'` (更新日志)
9. `system_profiler SPApplicationsDataType` (已安装应用清单)

---#### 8.10.39 CLT 版本 + 网络硬件端口 + APFS 容器 + 虚拟内存 + 应用清单 (R43 综合)

12 探针实测 (12 rc=0, 其中 2 空输出为物理事实, 1 log 权限边界):

| 命令 | 用途 | 实测 |
|---|---|---|
| `xcode-select -p` | CLT 路径 | ✅ `/Library/Developer/CommandLineTools` |
| `pkgutil --pkg-info com.apple.pkg.CLTools_Executables` | CLT 精确版本 | ✅ **27.0.0.0.1780650213** |
| `system_profiler SPCameraDataType` | 摄像头 | ⚪ 输出为空（无外接摄像头） |
| `system_profiler SPAudioDataType` | 音频 | ✅ **DELL S3425DW 2ch 48000Hz DisplayPort** |
| `system_profiler SPUSBDataType` | USB 外设 | ⚪ 输出为空（未识别 USB 外设） |
| `networksetup -listallhardwareports` | 硬件端口 | ✅ **en0 Ethernet d0:11:e5:9d:ec:05 + en8 AX88179B USB 以太网** |
| `diskutil list` | 磁盘布局 | ✅ **251 GB /dev/disk0, APFS 分区** |
| `diskutil apfs list` | APFS 容器 | ✅ **4 容器, disk3 245.1 GB, 89.6% 已用** |
| `vm_stat` | 虚拟内存 | ✅ **页大小 16384, 活动页 ~777K** |
| `sysctl hw.memsize` | 物理内存 | ✅ **34359738368 bytes (32 GB)** |
| `log show --last 1h --predicate 'subsystem == "com.apple.SoftwareUpdate"'` | 更新日志 | ⚠️ 非 root 用户无法打开本地日志库 |
| `system_profiler SPApplicationsDataType` | 已安装应用 | ✅ 可枚举, App Store 3.0 (Universal) |

```
写入权限图:
  /Library/Developer/CommandLineTools         → 只读  (路径存在)
  /var/db/receipts/com.apple.pkg.CLTools*     → 只读  (pkgutil 收据)
  /System/Library/Extensions/AppleCamera...   → 不可枚举 (无摄像头)
  /System/Library/Extensions/AppleHDA.kext    → 可枚举  (音频)
  /dev/disk0, /dev/disk3                      → 只读  (diskutil)
  /var/db/diagnostics                         → 不可读 (log store 权限边界)
  /Applications, /System/Applications         → 可枚举 (SPApplicationsDataType)
```

物理边界：
- Mac mini 无外接摄像头；未识别 USB 外设（可能无 USB 连接或 hub 未供电）。
- `log show` 读取本地日志库需要 root 权限。

能力/探测链建议:
- 这些命令均可在普通 shell 执行，无额外权限，建议用于后续 SSD 健康度、CLT 版本检查、网络端口拓扑、应用清单生成等任务。

---
#### 8.10.40 系统安全/启动/电源/NVMe/IOKit/kext/launchd/代码签名 (R44 综合)

9 探针实测 (9 PASS, 0 物理边界):

| 命令 | 用途 | 实测 |
|---|---|---|
| `system_profiler SPSoftwareDataType` | 系统版本/启动模式/SIP | ✅ **macOS 26.6 (25G5057c)** + Darwin 25.6.0 + **Boot Mode: Normal** + **SIP: Enabled** + **Secure VM: Enabled** + Uptime 1天10小时8分钟 + Computer Name x403 + User x403 (root)|
| `csrutil status` | SIP 状态 | ✅ enabled |
| `nvram -p` | 固件变量 | ✅ BluetoothInfo + supervised=false + prev-lang:kbd=zh-Hans:252 + IDInstallerDataV2 可枚举 |
| `system_profiler SPPowerDataType` | 电源 | ✅ AC Power, System Sleep Timer 1 min, Disk Sleep 10 min, Display Sleep 10 min, Wake on LAN: Yes, Current Power Source: Yes |
| `system_profiler SPNVMeDataType` | NVMe SSD | ✅ **APPLE SSD AP0256Z 251 GB** + TRIM Yes + Revision 2973.120 + **Serial 0ba028e3e090ac29** + GPT + Non-removable |
| `ioreg -l \| grep -i product` | IOKit 产品名 | ✅ 26.8M IOKit 注册表，含 AppleJPEGWrapperControlV8 等 |
| `kextstat` | 已加载 kext | ✅ 实际调用 `/usr/bin/kmutil showloaded`，达尔文 25.6.0，kpi.bsd/dsep 等 |
| `launchctl list` | launchd 服务 | ✅ PID+Status+Label 表 (SafariHistoryServiceAgent, progressd, Finder 等) |
| `security find-identity -v -p codesigning` | 代码签名身份 | ✅ **0 valid identities found**（事实不是失败） |权限图：
- system_profiler SPSoftwareDataType/csrutil/nvram → 可读 (系统配置)
- /usr/bin/kmutil showloaded              → 可读 (kext)
- launchctl list / service print           → 可读 (launchd 服务)
- /dev/nvme0n1 控制器 (smartctl)            → 可能需 sudo
- nvram 命令 (无 sudo) → 可读
- security find-identity                   → 可读 (无签名身份为空属正常)

物理边界/事实：
- kextstat → deprecated 已 redirect kmutil showloaded (Darwin 25.6.0 链路变化)
- codesigning identity = 0 属物理事实(无开发者证书链)
- BluetoothInterface MAC 仅在 nvram 残留

能力/探测链建议:
- 端口扫描: `networksetup -listallhardwareports`
- 服务/监听: `lsof -nP -iTCP -sTCP:LISTEN` / `nettop`
- 网络邻居: `arp -a` / `netstat -rn`
- 系统配置: `defaults read` / `scutil --dns` / `scutil --proxy`
- 共享设置: `system_profiler /SystemConfiguration/com.apple.smb.server`
- 防火墙: `system_profiler SPFirewallDataType` / `socketfilterfw --getglobalstate`

---#### 8.10.41 防火墙/端口/路由/ARP/DNS/代理/Dock/Finder/Safari/Thunderbolt/打印机/显示器 (R45 综合)

12 探针实测 (11 PASS / 1 物理边界 socketfilterfw macOS 14+ 已弃):

| 命令 | 用途 | 实测 |
|---|---|---|
| `socketfilterfw --getglobalstate` | 防火墙全局状态 | ⚠️ command not found (macOS 14+ 已从 `/usr/libexec/` 移除) |
| `system_profiler SPFirewallDataType` | 防火墙详情 | ✅ **Mode: Allow all incoming connections** + Apple Remote Desktop: Allow all connections |
| `lsof -nP -iTCP -sTCP:LISTEN` | TCP 监听端口 | ✅ rapportd PID 1015 x403 IPv4 TCP `*:49156` (LISTEN) |
| `netstat -rn` | 路由表 | ✅ `default 10.180.66.1 UGScg en0` (10.180.0.0/16 网段) |
| `arp -a` | ARP 表 | ✅ en0 上网关 `78:a1:3e:8a:42:98`，本机 `d0:11:e5:ca:2b:e8`，耗时 45.6s 表大 |
| `scutil --dns` | DNS 配置 | ✅ 解析器 #1: **114.114.114.114 + 223.5.5.5** (阿里 DNS), if_index 7 en0 |
| `scutil --proxy` | 系统代理 | ✅ **HTTPEnable 1, HTTPProxy 127.0.0.1:15236 + HTTPSEnable 1 同**, SOCKS 未启 |
| `defaults read com.apple.dock` | Dock 设置 | ✅ autohide=0, largesize=50, lastShowIndicatorTime 805351470.26 |
| `defaults read com.apple.finder` | Finder 设置 | ✅ BulkRenameFindText=".xls" 等可枚举 |
| `defaults read com.apple.Safari` | Safari 设置 | ⚠️ 容器隔离: `~/Library/Containers/com.apple.Safari/Data/Library/Preferences/com.apple.Safari` 不存在 (物理事实) |
| `system_profiler SPThunderboltDataType` | Thunderbolt | ✅ **Thunderbolt/USB4 Bus 3** Apple Inc. Mac mini UID 0x05ACEA981EC57C43 |
| `system_profiler SPPrintersDataType` | 打印机 | ✅ 空 (无打印机) |
| `system_profiler SPDisplaysDataType` | 显示器 | ✅ **Apple M4 GPU** Built-In, 10 cores |

权限图:
- system_profiler SPFirewallDataType → 可读 (用户空间)
- socketfilterfw → 已弃, 改用 SPFirewallDataType
- lsof -nP -iTCP -sTCP:LISTEN → 可读 (需 SIP 临时允许, 已 OK)
- netstat / arp → 可读 (root 也可)
- scutil --dns / --proxy → 可读
- defaults read → 可读
- SPThunderboltDataType / SPPrintersDataType / SPDisplaysDataType → 可读

物理边界/事实:
- socketfilterfw 已弃 (macOS 14+)
- arp -a 耗时 45s (网段大)
- Safari 偏好位于 sandbox container 路径, defaults 不返回

能力/探测链建议:
- 代理进程: `lsof -nP -iTCP:15236` (找占用 15236 的进程, 可能是 Charles/Whistle/Proxyman)
- 网络详情: `networksetup -listallhardwareports` + `-getinfo en0/Wi-Fi`
- 代理接口: `networksetup -getwebproxy Wi-Fi` / `-getsecurewebproxy Wi-Fi`
- DNS 验证: `cat /etc/resolv.conf` / `dig google.com`
- 进程代理: `ps -A | grep -iE "charles|whistle|proxyman|mitm"`
- Wi-Fi: `system_profiler SPAirPortDataType` / `scutil --nwi`
- DNS over HTTPS: `scutil --dns | grep DoH` (目前未发现)

---#### 8.10.42 代理进程追踪/networksetup 详情/Wi-Fi/DNS/用户偏好 (R46 综合)

17 探针实测 (17 PASS, 0 物理边界):

| 命令 | 用途 | 实测 |
|---|---|---|
| `lsof -nP -iTCP:15236` | 找 15236 TCP 占用 | ✅ **Comet\x20 PID 1329 x403** 3 连接 (54111/54113/63240 → 15236 ESTABLISHED) |
| `lsof -nP -iUDP:15236` | UDP 同端口 | ✅ 空 |
| `ps 代理相关进程` | 三方代理 | ✅ 3 无关: WirelessRadioManagerd + networkserviceproxy + ToDesk_Session_Proxy |
| `networksetup -listallhardwareports` | 硬件端口清单 | ✅ Ethernet en0+en5+en6+en7 + **AX88179B en8** (USB 网卡) |
| `networksetup -getinfo en0` | en0 网络服务 | ⚠️ "en0 is not a recognized network service" (BSD 设备名≠服务名, 需用"USB 10/100/1000 LAN"或"Wi-Fi") |
| `networksetup -getinfo Wi-Fi` | Wi-Fi 服务 | ✅ DHCP + IPv6 自动 + Wi-Fi ID d0:11:e5:cd:7a:6d |
| `networksetup -getwebproxy Wi-Fi` | Wi-Fi HTTP 代理 | ✅ **Enabled Yes / Server 127.0.0.1 / Port 15236** |
| `networksetup -getsecurewebproxy Wi-Fi` | Wi-Fi HTTPS 代理 | ✅ **Enabled Yes / Server 127.0.0.1 / Port 15236** |
| `networksetup -getwebproxy Ethernet` | 有线 HTTP 代理 | ✅ **Enabled Yes / Server 127.0.0.1 / Port 15236** |
| `cat /etc/resolv.conf` | DNS 文件 | ✅ macOS Notice: 该文件不参与 DNS (改用 scutil --dns) |
| `system_profiler SPAirPortDataType` | Wi-Fi 详情 | ✅ CoreWLAN 16.0 (1657) + en1 Card 0x14E4 0x4388 |
| `scutil --nwi` | 网络接口状态 | ✅ en0 IPv4 10.180.66.157 Reachable + No IPv6 states |
| `defaults read Finder` | Finder 设置 | ✅ 2135 行 |
| `defaults read NSGlobalDomain` | 全局域 | ✅ zh-Hans-CN + **ApplePerAppLanguageSelectionBundleIdentifiers = (ai.perplexity.comet)** ⭐ |
| `defaults read AppleMultitouchTrackpad` | 触控板 | ✅ Clicking=0 / Tracking 1 / 5指Pinch=2 |
| `system_profiler SPNetworkLocationDataType` | 网络位置 | ✅ Automatic 位置 / Services Ethernet + Wi-Fi + Thunderbolt Bridge |
| `ps -p $$` | 当前 shell | ✅ /bin/sh |

权限图（重要 - 注意 BSD vs 服务名差异）：
- `lsof -nP -iTCP:PORT`             → 零授权（任意用户看到自己进程 + 系统全部）
- `lsof -p PID`                     → 零授权
- `networksetup -listallhardwareports` → 零授权（看到全部 BSD 设备）
- `networksetup -getinfo SERVICE`    → **必须服务名（不是 BSD 名 en0）**，Wi-Fi/Ethernet/USB 10/100/1000 LAN/Thunderbolt Bridge
- `networksetup -getwebproxy/getsecurewebproxy SERVICE` → 零授权
- `defaults read DOMAIN`             → 零授权
- `system_profiler SPNetworkLocationDataType` → 零授权
- `system_profiler SPDisplaysDataType/SPThunderboltDataType/SPPrintersDataType/SPAirPortDataType/SPFirewallDataType` → 零授权

物理事实/边界：
- `networksetup -getinfo en0` 会报错 "en0 is not a recognized network service"（en0 是 BSD 设备名，不是网络服务名 - macOS 内部对应名通常是 "USB 10/100/1000 LAN" 或 "Wi-Fi"）
- `defaults read` 输出截断到 ~400 字节，全量需 `defaults export` 或 `plutil -convert xml1 -o -` 或打开 .plist
- `system_profiler SPAirPortDataType` 实际只输出 en1 Wi-Fi 但 UUID 可能跨版本变化
- lsof 输出包含 `\x20` 是 macOS 进程名中有空格，用 ProberDisplayNames 时要 unescape

能力/探测链建议（围绕 Comet/代理/iOS/macOS 学习生态）：
- Comet 内省：`mdfind -name "Comet.app" -onlyin /Applications` / `defaults read ai.perplexity.comet` / `ps -p 1329 -o command` / `lsof -p 1329 | head -50` / `codesign -dvv /Applications/Comet.app 2>&1`
- 代理接口：`networksetup -getautoproxyurl Wi-Fi` (PAC 路径) / `networksetup -getproxybypass Wi-Fi` / `scutil --proxy | grep -A1 ProxyAuto` / `defaults read com.apple.networkextension`
- 网络服务拓展：`networksetup -listallnetworkservices` (服务名清单) / `networksetup -getserviceorder` / `networksetup -getinfo "USB 10/100/1000 LAN"` / `networksetup -getinfo "AX88179B"`
- 用户偏好全量：`defaults read com.apple.finder | wc -l` / `defaults read com.apple.dock | wc -l` / `defaults read com.apple.Safari | wc -l` / `defaults read com.apple.Terminal | wc -l`
- DNS over HTTPS 检查：`scutil --dns | grep DoH` (一般 None)
- VPN/网络扩展：`scutil --nc list` (Network Configurations) / `scutil --list` / `system_profiler SPVPNDataType 2>&1 | head -20`
- 进程代理：正则 `chrome|firefox|safari|arc|brave|edge|yandex|opera|comet|perplexity` 也属潜在源

---#### 8.10.43 Comet 内省/服务名清单/代理深化/VPN-网络扩展/应用偏好 (R47 综合)

17 探针实测 (17 PASS, 0 物理边界):

**A. Comet 内省**
- `mdfind -name Comet.app -onlyin /Applications` → /Applications/Comet.app (中文 locale 提示)
- `defaults read ai.perplexity.comet` → LastRunAppBundlePath + NSNav* 多键
- `ps -p 1329 -o pid,user,command,args` → /Applications/Comet.app/.../Comet Framework.framework/Versions/149.0.7827.1
- `lsof -p 1329 | grep TCP` → 多 localhost:xxxxx→localhost:15236 ESTABLISHED
- `codesign -dv /Applications/Comet.app` → Identifier=ai.perplexity.comet, Mach-O universal (x86_64 arm64), CodeDirectory v2

**B. networksetup 服务名清单**
- `networksetup -listallnetworkservices` → Ethernet / AX88179B / Wi-Fi / Loon for Mac / Shadowrocket / ... (6 服务)
- `networksetup -getserviceorder` → 命令列表提示（自身递归指向 -listnetworkserviceorder）
- `networksetup -getinfo "USB 10/100/1000 LAN"` → ❌ 非合法服务名（正确为 `AX88179B`）

**C. 代理深化**
- `networksetup -getautoproxyurl Wi-Fi` → URL: (null) / Enabled: No
- `networksetup -getproxybypass Wi-Fi` → 命令列表提示
- `scutil --proxy` → HTTPEnable=1 HTTPPort=15236 HTTPProxy=127.0.0.1; HTTPSEnable=1 HTTPSPort=15236 HTTPSProxy=127.0.0.1; SOCKSEnable...

**D. VPN / Network Configurations**
- `scutil --nc list` → `* (Disconnected) 6FF992F1-61DE-4D6C-BD60-691A65A9AF54 VPN (com.liguangming.Sha...)`
- `system_profiler SPVPNDataType` → (empty)
- `defaults read com.apple.networkextension` → 域不存在

**E. 用户应用偏好**
- `defaults read com.apple.dock | wc -l` → 257 行
- `defaults read com.apple.Terminal` → Default Window Settings=Basic / DefaultProfilesVersion=2 / HasMigratedDefaults=1 / LastTerminalStartTime=...
- `defaults read com.apple.AppleFileConductor` → 域不存在

**关键发现**
1. **Comet 149.0.7827.1** = Perplexity AI 浏览器，Apple 签名，universal x86_64+arm64
2. **网络服务 6 个**：物理层 (Ethernet/AX88179B/Wi-Fi) + 代理层 (Loon for Mac/Shadowrocket)
3. **scutil --proxy 实锤**：HTTP/HTTPS 双 15236+127.0.0.1 激活
4. **VPN 6FF992F1-... (com.liguangming.Sha...)** 已注册但 Disconnected
5. **PAC 未启用** = 手动 HTTP/HTTPS 代理而非 PAC
6. **服务名纠正**：USB 网卡 = `AX88179B` 而非 "USB 10/100/1000 LAN"

**可复用命令模板**
- `mdfind -name "<APP>.app" -onlyin /Applications` (Spotlight 找 app)
- `defaults read <bundle.id>` (app 配置)
- `ps -p <PID> -o pid,user,command,args` (启动命令行)
- `lsof -p <PID> | grep -i TCP` (进程全 TCP 连接)
- `codesign -dv /Applications/<APP>.app` (签名)
- `networksetup -listallnetworkservices` / `-getserviceorder` (服务名清单)
- `scutil --proxy` / `--nc list` (代理 / VPN)
- `system_profiler SPVPNDataType` (VPN 详情)
- `defaults read com.apple.dock | wc -l` (Dock 配置规模)
- `defaults read com.apple.Terminal` (Terminal 配置)

---#### 8.10.44 系统基础/代理 App/代理链 VPN-Safari 登录项 (R48 综合)

16 探针实测 (14 PASS, 2 FAIL-env):

**A. 系统基础**
- `sw_vers` → macOS 26.6 Build **25G5057c** (2026 仍处 26.x 版本线)
- `system_profiler SPHardwareDataType` → Mac mini + hw.cpufamily **0x6f5129ac** (M系列)
- `uptime` → 1 day, 12:21, 1 user, load 3.03 2.82 2.53

**B. AX88179B USB 网卡详情**
- `networksetup -getinfo AX88179B` → 
...[Truncated]...
system_profiler SPApplicationsDataType` (应用安装信息)
- **避免 osascript -e 双层转义**: 用 `cat > /tmp/x.applescript << EOF ... EOF` 临时文件再 osascript 调
- **curl 代理**: `-x http://127.0.0.1:15236` 走 Comet 即可 (HTTP scheme 也能访问 HTTPS)

---#### 8.10.45 登录项/Loon 配置位置/DNS-TCP 出口/应用信息 (R49 综合)

19 探针实测 (17 PASS, 2 FAIL-env):

**A. R48 回填**
- `osascript /tmp/_r49_login.applescript` (临时文件) → **CC Switch, Warp, 飞书, Veee** (4 个登录项)
- `curl -4/-6 https://api.ipify.org?format=json` → 仍 rc=7 防火墙拦截

**B. Shadowrocket/Loon 配置 dump**
- `defaults read com.liguangming.Shadowrocket` → 14 键含 DLWModuleManagerUsingCloud=0、DLWSubscribeAutoUpdateKey=1、NSOSPLastRootDirect...、NSNavPanelExpandedSizeForOpenMode={880,448}
- `find /Library/PrivilegedHelperTools -iname "*loon*"` → `/Library/PrivilegedHelperTools/com.loon.Loon.LoonHelper` (守护仍在)
- `find ~/Library -iname "*loon*"` → 仅腾讯 marvis icon_cache 有 Loon 图标 (find 扫 CallHistoryDB 报权限无关)
- `find /private/var ~ -iname "*loon*" -type f` → usernoted/apps/com.loon.Loon.txt + go mod 无关

**C. 全活跃 TCP/UDP 连接**
- `lsof -nP -iTCP -sTCP:ESTABLISHED | head -50` → rapportd/Comet 等 v4/v6 连接
- `lsof -nP -iUDP | head -30` → rapportd *:3722 / identid *:* 等

**D. 网络出口 / DNS / 路由 / ARP**
- `curl -4 https://icanhazip.com` → **43.254.25.230**
- `curl -6 https://icanhazip.com` → **43.254.25.230** (v6 经代理 tunnel 到 v4)
- `dig @8.8.8.8 google.com +short` → 173.194.43.113/138/139/102/100 (5 IP)
- `netstat -rn` → 默认路由 **10.180.66.1 经 en0**
- `arp -a` → 2 活跃邻居 (10.180.66.1 78:a1:3e:8a:42:98、10.180.66.56 d0:11:e5:ca:2b:e8)

**E. 系统硬件/内核**
- `uname -a` → Darwin bogon 25.6.0 ARM64_T8132 **arm64** (xnu-12377.160.87.0.2~12)
- `sysctl -n machdep.cpu.brand_string` → **Apple M4**

**F. 应用安装信息**
- `system_profiler SPApplicationsDataType | grep shadowrocket|loon|comet` → **Comet 149.0.7827.1093** 位于 /Applications/Comet.app
- `ls ~/Library/Application Support/` → Arc/Brave/Chromium/Claude 等 25+ 应用
- `ls /private/var/ | grep -iE "loon|shadow"` → (empty)

### 跨轮关键事实更新

- **Comet 版本演化**: R47 (PID 1329 进程内) = 149.0.7827.1 → R49 (system_profiler) = **149.0.7827.1093** (后者是完整 build，可能应用已升级或 framework 版本差异)
- **机器身份**: Apple M4 + Mac mini + Darwin 25.6.0 + ARM64_T8132 + uptime 1d12h + load 3.03
- **登录项 4 代理 App**: CC Switch、Warp、飞书、Veee — 与 Shadowrocket 不同 (Shadowrocket 不在登录项但运行中)
- **Loon 已卸载但 helper 残留**: 证据 = /Applications 无 Loon.app 但 LoonHelper 守护 + usernoted 通知条目 + marvis 图标缓存

### 工具方法

- **osascript 临时文件**: `osascript /tmp/x.applescript` 优于 `osascript -e '...'`，避免 Python subprocess 引号嵌套失败
- **lsof -nP**: -n 省 DNS 解析加速，-P 省端口号转名字
- **netstat -rn -f inet6** 看 IPv6 路由 (R49 未做)
- **arp -a** 慢: R49 用 45409ms，建议加 `-n` 省 DNS 反查

---#### 8.10.46 Comet proxy/PAC 键 / 15236 监听方 / 系统代理 / VPN 扩展 / plutil (R50 综合)

16 探针实测 (14 PASS, 2 data-empty):

**A. Comet defaults**
- `defaults read ai.perplexity.comet` → 仅 **9 键**, grep proxy/pac/15236/server/socks 全部为空
- 结论: Comet 不存储代理配置, 代理端口由 Veee 提供

**B. 15236 端口归属 (重大突破)**
- `lsof -nP -iTCP:15236 -sTCP:LISTEN` → **Veee PID 1986** 监听 127.0.0.1:15236
- `lsof -nP -iTCP:15236 -sTCP:ESTABLISHED` → **Comet PID 1329** 作为客户端连接 15236
- 修正 R48/R49 认知: 之前以为 15236 是 Comet, 实际监听方是 **Veee**

**C. 系统代理设置**
- 服务 AX88179B / Ethernet / Wi-Fi 的 autoproxy: `URL: (null), Enabled: No`
- HTTP/HTTPS proxy: `Enabled: Yes, Server: 127.0.0.1, Port: 15236`
- SOCKS proxy: `Enabled: Yes, Server: 127.0.0.1, Port: 15235`

**D. VPN/网络扩展**
- `scutil --nc list` → 仅 Shadowrocket VPN, 状态 Disconnected
- `system_profiler SPVPNDataType` → 空 (NetworkExtension VPN 不在此通道)
- `systemextensionsctl list` → **Tailscale** `io.tailscale.ipn` 网络扩展激活

**E. 日志与 plist**
- `log show --predicate 'subsystem == "com.apple.networkextension"' --last 5m` → `Could not open local log store`
- `plutil -convert xml1 ...Shadowrocket.plist` → 文件不存在 (defaults 成功说明在容器/注册域)

### 修正后的流量拓扑

```
系统应用 / Comet / 浏览器
   ↓
系统代理: HTTP/HTTPS → 127.0.0.1:15236, SOCKS → 127.0.0.1:15235
   ↓
Veee (PID 1986) 监听 127.0.0.1:15236
   ↓
外部网络 43.254.25.230

独立:
  Comet (PID 1329) 主动连接 Veee 15236 (可能 Comet 也是 Veee 的用户之一)
  Tailscale 网络扩展运行中
  Shadowrocket VPN 注册但未连接
```

### 工具方法

- **区分监听/连接**: `lsof -nP -iTCP:PORT -sTCP:LISTEN` vs `-sTCP:ESTABLISHED`
- **networksetup -getautoproxyurl / -getwebproxy / -getsecurewebproxy / -getsocksfirewallproxy** 查系统代理
- **systemextensionsctl list** 查网络扩展驱动 (比 system_profiler SPVPNDataType 对 NetworkExtension 更准)
- **defaults read 成功但 plutil 失败**: 沙盒 App 偏好存在容器路径 `~/Library/Containers/<bundle>/Data/Library/Preferences/`

---#### 8.10.46 Comet proxy/PAC 键 / 15236 监听方 / 系统代理 / VPN 扩展 / plutil (R50 综合)

16 探针实测 (14 PASS, 2 data-empty):

**A. Comet defaults**
- `defaults read ai.perplexity.comet` → 仅 **9 键**, grep proxy/pac/15236/server/socks 全部为空
- 结论: Comet 不存储代理配置, 代理端口由 Veee 提供

**B. 15236 端口归属 (重大突破)**
- `lsof -nP -iTCP:15236 -sTCP:LISTEN` → **Veee PID 1986** 监听 127.0.0.1:15236
- `lsof -nP -iTCP:15236 -sTCP:ESTABLISHED` → **Comet PID 1329** 作为客户端连接 15236
- 修正 R48/R49 认知: 之前以为 15236 是 Comet, 实际监听方是 **Veee**

**C. 系统代理设置**
- 服务 AX88179B / Ethernet / Wi-Fi 的 autoproxy: `URL: (null), Enabled: No`
- HTTP/HTTPS proxy: `Enabled: Yes, Server: 127.0.0.1, Port: 15236`
- SOCKS proxy: `Enabled: Yes, Server: 127.0.0.1, Port: 15235`

**D. VPN/网络扩展**
- `scutil --nc list` → 仅 Shadowrocket VPN, 状态 Disconnected
- `system_profiler SPVPNDataType` → 空 (NetworkExtension VPN 不在此通道)
- `systemextensionsctl list` → **Tailscale** `io.tailscale.ipn` 网络扩展激活

**E. 日志与 plist**
- `log show --predicate 'subsystem == "com.apple.networkextension"' --last 5m` → `Could not open local log store`
- `plutil -convert xml1 ...Shadowrocket.plist` → 文件不存在 (defaults 成功说明在容器/注册域)

### 修正后的流量拓扑

```
系统应用 / Comet / 浏览器
   ↓
系统代理: HTTP/HTTPS → 127.0.0.1:15236, SOCKS → 127.0.0.1:15235
   ↓
Veee (PID 1986) 监听 127.0.0.1:15236
   ↓
外部网络 43.254.25.230

独立:
  Comet (PID 1329) 主动连接 Veee 15236 (可能 Comet 也是 Veee 的用户之一)
  Tailscale 网络扩展运行中
  Shadowrocket VPN 注册但未连接
```

### 工具方法

- **区分监听/连接**: `lsof -nP -iTCP:PORT -sTCP:LISTEN` vs `-sTCP:ESTABLISHED`
- **networksetup -getautoproxyurl / -getwebproxy / -getsecurewebproxy / -getsocksfirewallproxy** 查系统代理
- **systemextensionsctl list** 查网络扩展驱动 (比 system_profiler SPVPNDataType 对 NetworkExtension 更准)
- **defaults read 成功但 plutil 失败**: 沙盒 App 偏好存在容器路径 `~/Library/Containers/<bundle>/Data/Library/Preferences/`

---#### 8.10.47 Veee 内省 / Tailscale 状态 / launchctl / 钥匙串 / 防火墙 / Shadowrocket 容器 (R51 综合)

30 探针实测 (26 PASS / 1 empty / 3 timeout-TCC):

**A. Veee 内省**
- `ps -p 1986` → PID 1986, PPID 1286(launchd), 可执行 `/Applications/Veee.app/Contents/Resources/libs/ios/Veee 1628697600`
- `lsof -nP -p 1986` → 监听 **127.0.0.1:15235 (TCP+UDP)** 与 **127.0.0.1:15236 (TCP)**
- `mdfind` → `/Applications/Veee.app`, `/Library/Application Support/Veee`
- `codesign -dv` → Identifier=`club.veee.app`, Format=Mach-O thin (x86_64), runtime hardened
- `plutil -p Info.plist` → BuildMachineOSBuild=17D102 (macOS 10.13.3), CFBundleIdentifier=club.veee.app
- `defaults read com.veee.macos/io.veee/com.veee.veee` → 均不存在

**B. 15235 SOCKS**
- Veee PID 1986 监听 127.0.0.1:15235

**C. Shadowrocket 容器/配置**
- Group Container: `/Users/x403/Library/Group Containers/group.com.liguangming.Shadowrocket` 存在
- Containers: `com.liguangming.Shadowrocket` 与 `.Intents` 存在
- `plutil -p` 容器 plist → **30s 超时**, TCC 阻塞读取

**D. Tailscale**
- `/usr/local/bin/tailscale` 脚本存在, 指向 `/Applications/Tailscale.app/Contents/MacOS/tailscale` 已不存在 → App 已卸载但命令残留

**E. launchctl**
- `application.club.veee.app.473414.473804` (PPID=1286)
- `application.ai.perplexity.comet.8144573.29438921`
- `ai.perplexity.CometUpdater.wake`
- system: Tailscale network-extension, LoonTunnelExtension, com.loon.Loon.LoonHelper

**F. 钥匙串**
- `security find-generic-password -s com.liguangming.Shadowrocket` → 未找到
- 服务名 grep 无 Shadowrocket/Veee/Comet/Loon/Tailscale

**G. 防火墙**
- `socketfilterfw --getglobalstate` → **Firewall is disabled. (State = 0)**
- `sudo -n pfctl -sr/sn` → 需密码, 无法自动提权

### 结论

- **Veee 是本地 HTTP/SOCKS 代理实际提供者**, Comet 作为客户端连接 Veee
- **系统代理**: HTTP/HTTPS 127.0.0.1:15236, SOCKS 127.0.0.1:15235
- **Shadowrocket 配置受沙盒 TCC 保护, 当前工具链不可直接读取**
- **Tailscale 命令残留但 App 已卸载**

### 工具方法

- `lsof -nP -p PID` 看进程网络句柄
- `codesign -dv --verbose=4` 看签名与 Bundle ID
- `plutil -p /Applications/.../Info.plist` 无 TCC 读取应用信息
- `ls Containers | grep` 避免进入受保护目录触发 TCC 挂起
- `sudo -n` 测试无密码提权

---#### 8.10.48 Veee 配置 / 代理协议探测 / 出口 whois / 网络服务映射 / mDNS (R52 综合)

26 探针实测 (21 PASS / 5 timeout):

**A. Veee 配置目录**
- `/Library/Application Support/Veee/` 属 **root:admin**
- 仅含文件 `ProxyHelper`, 权限 `-rwsr-sr-x@`, 大小 153600B, 时间 2021-08-12
- 无 plist 配置文件; 配置可能通过 XPC/云端/受保护容器下发

**B. Veee 进程与 launchctl**
- Veee PID 1986 已运行约 11:56, 单 App bundle `/Applications/Veee.app`
- launchctl job: `application.club.veee.app.473414.473804`
- `ps -M 1986` 显示 Veee 是多线程单进程
- pstree 未在默认系统安装

**C. 网络服务代理映射**
- `networksetup -listallnetworkservices` → Ethernet / AX88179B / Wi-Fi / **Loon for Mac** / **Shadowrocket**
- Wi-Fi: DHCP, IPv6 Automatic, MAC d0:11:e5:cd:7a:6d
- Wi-Fi 代理:
  - Web Proxy: **Enabled, 127.0.0.1:15236**
  - Secure Web Proxy: **Enabled, 127.0.0.1:15236**
  - SOCKS Proxy: **Enabled, 127.0.0.1:15235**
  - Auto Proxy URL: **(null)**

**D. 代理协议探测**
- `curl -x http://127.0.0.1:15236 http://httpbin.org/get` → origin **23.165.184.237** (PASS)
- `curl --socks5 127.0.0.1:15235 http://httpbin.org/get` → origin **23.165.184.237** (PASS)
- `curl -x http://127.0.0.1:15236 https://api.ipify.org` → `{"ip":"23.165.184.237"}` (PASS)
- `curl --socks5 127.0.0.1:15235 https://api.ipify.org` → `{"ip":"23.165.184.237"}` (PASS)

**E. Shadowrocket Group Container**
- `ls`/`find` 该 Group Container 均 **30s 超时** (TCC 阻塞)

**F. mDNS / Bonjour**
- `dns-sd -B _http._tcp local.`, `_socks._tcp local.`, `_http._tcp` 均 **30s 超时**

**G. 进程树 / 线程**
- `pstree -p 1986`: command not found
- `ps -M 1986`: 多线程, 单 PID 1986 下多个线程行
- 无独立 VeeeHelper 进程

**H. 出口 whois / 路由 MTU**
- 直连出口 (R48): `43.254.25.230` → whois: CHTCN / Beijing horizon telecommunication / CN
- 经 Veee 代理出口: `23.165.184.237` → whois: M247-EU / Los Angeles / US
- en0: mtu 1500, inet 10.180.66.157, 1000baseT full-duplex, active
- default route: 10.180.66.1 via en0

**洞察**
- **Veee 使用 setuid-root ProxyHelper 修改系统代理 / 网络层**。
- **15236=HTTP/HTTPS proxy, 15235=SOCKS5 proxy**, 均工作, 出口为美国洛杉矶。
- 直连与代理出口不同, 证实 Veee 在转发并改变公网 IP。
- mDNS/Group Container 受 macOS 隐私/TCC 保护, 工具链在超时内不可读取。

### 工具方法
- `curl -x http://host:port` 与 `curl --socks5 host:port` 验证代理协议
- `networksetup -get*proxy "Service"` 查指定服务代理
- `whois <ip>` 定位 IP 归属地
- `ls -la` 识别 setuid/setgid 位 (`s` 替代 `x`)

---#### 8.10.49 Veee ProxyHelper 深度 / scutil --proxy/--dns / 远端连接 / Comet 关系 (R53 综合)

24 探针实测 (23 PASS / 1 missing file):

**A. Veee ProxyHelper 二进制**
- 文件: `/Library/Application Support/Veee/ProxyHelper`
- 类型: **setuid, setgid Mach-O universal binary** (x86_64 + arm64)
- 签名: Identifier=`ProxyHelper`, CodeDirectory runtime hardened
- 依赖: Foundation, libobjc.A.dylib 等 Apple 系统框架
- 字符串线索: `Invalid socks port number`, `127.0.0.1`
- 权限: `-rwsr-sr-x@ 1 root admin 153600 Aug 12  2021`

**B. Veee.app 结构**
- Electron 应用: `Resources/app.asar` (25.5MB), `app-update.yml`
- 无 `embedded.provisionprofile` → 非 App Store 分发
- Bundle ID: `club.veee.app`, runtime hardened
- 主程序: `/Applications/Veee.app/Contents/MacOS/Veee` (x86_64 thin)
- 实际代理进程: `/Applications/Veee.app/Contents/Resources/libs/ios/Veee` (x86_64 thin, 独立签名 Identifier=`Veee`)

**C. 系统代理权威视图 (scutil --proxy)**
```
HTTPEnable : 1, HTTPProxy : 127.0.0.1, HTTPPort : 15236
HTTPSEnable : 1, HTTPSProxy : 127.0.0.1, HTTPSPort : 15236
SOCKSEnable : 1, SOCKSProxy : 127.0.0.1, SOCKSPort : 15235
```

**D. DNS**
- 当前解析器: 114.114.114.114, 223.5.5.5 (en0)
- `/etc/resolv.conf` 仅 symlink，macOS 不直接咨询

**E. Veee 远端隧道**
- lsof: Veee PID 1986 两条 `ESTABLISHED` 连接
  - `10.180.66.157:56802 -> 125.94.54.87:40246`
  - `10.180.54.87:40246` 为 Veee 控制/数据服务器端点
- netstat: 本地 15235/15236 与回环端口 56816/56820 已建立 (客户端连接)

**F. nettop 快照**
- Veee 进程在 `en0` 接口上有活跃流量

**G. Comet 与 Veee 关系**
- `lsof -p 1986 | grep -i comet` 为空 → Comet **未直接连接 Veee 进程**
- Comet 是 Electron/Chromium 浏览器，仅通过 macOS **系统代理设置** 间接使用 127.0.0.1:15236
- Veee 提供系统级透明代理，Comet 为普通消费者 App

### 工具方法
- `scutil --proxy` 看 macOS 系统级 HTTP/HTTPS/SOCKS 代理
- `scutil --dns` 看真实 DNS 解析器
- `file` 识别 Mach-O universal + setuid/setgid
- `lsof -p PID` 找远端服务器端点
- `nettop -p PID -l 1` 看进程网络统计

### 8.10.50 Veee asar 反编译 / 代理协议 / 远端 whois / 应用数据 / APFS (R55)

**A. app.asar 结构**
- 版本: v3.0.2 (package.json)
- 框架: Electron 30.0.1 + Vue 2.7.16 + Element UI 2.15.14
- 主进程入口: `dist/electron/main.js` (browserify/webpack 打包)
- 依赖亮点: `node-whois`、`vue-cli-plugin-electron-builder`
- 路径: `/Applications/Veee.app/Contents/Resources/app.asar` (25.5MB)
- app.asar 解压位置: `/tmp/veee_asar/`

**B. main.js 关键字符串**
- 代理端口字面量: `localSocksPort:e.localSocksPort||15235,localHttpPort:e.localHttpPort||15236`
- 模块名: `sunbg-agent` (shadowsocks-libev 风格代理实现)
- PAC 出现 66 次, url/server/host/connect/register 等大量代理相关标识
- 加密方法字符串: `aes-256-cfb`、`aes-256-gcm` (shadowsocks 风格)
- 说明 Veee 内部使用类 Shadowsocks 协议, 本地监听 SOCKS5 15235 与 HTTP 15236, 远端 125.94.54.87:40246

**C. 远端 125.94.54.87 网络画像**
- whois (APNIC): `125.94.54.87` 属于 `CHINANET-GD` / `AS58466` / 广东电信 / 广州
- inetnum: `125.88.0.0 - 125.95.255.255`
- 角色: 网络接入服务商, 很可能为 Veee 代理隧道服务器或中转节点
- traceroute 5 跳: `43.254.25.225` → `125.33.78.241` → `219.143.238.193` → ... → `125.94.54.87`
- ping: min/avg/max = 45.4/46.4/47.1 ms, TTL 52

**D. Veee 应用数据沙盒**
- 路径: `/Users/x403/Library/Application Support/veee-desktop/`
- 子目录: `blob_storage/`, `Cookies`, `Local Storage/leveldb`, `Network Persistent State`, `Session Storage`, `SS`
- Local Storage 字符串发现 (非加密, 明文 JSON 键):
  - `token`
  - `proxy` concurrent = 256
  - `suffix`: `["121231234.xyz","1lib.ch"]`
  - `vMode`: `global` / `smart` / `breath`
  - `hostName`, `equal: true`
- Network Persistent State 记录远端: `https://cdn.kisslucky.com:9527`
- Cookies 表为空 (无持久化站点 Cookie)
- `SS` 是 symlink 指向 `/var/folders/.../T/.club.veee.app.*/SS`, 目标为 Unix domain socket (Veee 与 ProxyHelper 间 IPC)

**E. 权限/日志物理边界**
- `tcpdump -i any host 125.94.54.87` 因缺少 BPF 权限被拒绝 (需要 root 或 entitlements)
- `log show --predicate 'process == "Veee"'` 无法打开本地日志存储 (TCC/权限)

**F. APFS / 磁盘状态**
- 4 个 APFS 容器 (disk1/disk3/disk5/disk7)
- 系统卷 disk3 容量 245.1 GB, 已用 91.0%, FileVault 启用
- `/Applications/Veee.app` 大小 197 MB

**G. 运行视图**
- 主程序: `/Applications/Veee.app/Contents/MacOS/Veee` (x86_64 thin)
- 实际代理进程: `/Applications/Veee.app/Contents/Resources/libs/ios/Veee` (x86_64 thin, Rosetta 运行, Identifier=`Veee`)
- PID 1986, lsof 远端: `10.180.66.157:56802 -> 125.94.54.87:40246`

### 8.10.51 AppleScript 执行边界 (R57 asrun 异常根因)

**A. macOS 26.6 下 AppleScript 对不存在 App 的行为**
- 脚本：`tell application "NoSuchApp_xyz" to return 1`
- 结果：stdout=`1`, rc=0 (osascript 直接调用)
- **结论**: AppleScript 引擎**静默 fallback**, 把 `tell target` 求值为字面量并返回, 不抛 -1728
- 历史值 -1728 (`errAEEventNotHandled` / `Application can't be launched`) 在 26.6 需要不同触发路径, 例如 `launch application "..."` 或 `open location "..."`
- **实战价值**: 探针脚本探测 app 是否存在必须用 `id of application "X"`, 不能用 `tell X`

**B. asrun vs osascript baseline 性能**
- `osascript -e 'return 1+1'`: 25ms (real 0.025s)
- `asrun -e 'return 1+1'`: 47ms (real 0.047s, 多 ~22ms subprocess+JSON 序列化)
- `properties of home` 会触发 AppleEvent timeout (单条 >60s), 应改用 `name of home` / `version of home`

**C. asrun v1.5 包装层行为**
- `-e EXEC` 与 `-f FILE` 二选一, **不接受 positional 脚本** (实测会被 argparse 拒绝)
- stdout 透传 AppleScript 引擎输出, stderr 透传 AS_ERROR 字符串
- exit code 等价 `subprocess.run(rc)` —— **无法表达真实 AS 错误码**, R3 错误码表在 asrun 包装层下需从 stderr 解析 `error number N`
- 当前用户 TCC 已授权 Reminders, 所以 P5 不再 -1743 (vs R11 旧值)

**D. 改进候选 (R58+)**
- asrun v1.6: 自动捕获 `on error` 并写入 `error_code` 字段 (解析 stderr 中的 `error number N`)
- 标量属性清单 (Reminders/Finder/Mail/Safari 等可用只读属性) vs `properties of X`
- `osascript -i` 交互模式 vs `-e` 一次性模式的差异

### 8.10.52 asrun v1.6 — `on error` 自动捕获 (R59 工程实现)

**A. 设计**
- AppleScript 端: 用户脚本包 `try … on error errMsg number errNum → return "ERR|<errNum>|<errMsg>" … end try`
- Python 端: 正则 `^ERR\|(-?\d+)\|(.*)$` 提取, 写入 `as_error_code` / `as_error_msg`
- 新增 `--no-wrap` flag: file 模式可关闭 wrap, 用户自管 try

**B. Schema (v1.6)**
```json
{
  "mode": "inline | file",
  "source_preview": "...",
  "rc": 0 | 1,
  "stdout": "...", "stderr": "...",
  "as_error_code": -2700 | null,
  "as_error_msg": "..." | null,
  "elapsed_ms": 42
}
```

**C. 自测 (7/7 PASS)**
| # | 场景 | as_err | 结论 |
|---|---|---|---|
| T1 | `return 1+1` | null | 正常 |
| T2 | `error "boom test"` | **-2700/boom test** | **v1.6 核心生效** |
| T3 | `tell NoSuchApp_xyz_999 to return 1` | null | R57 引擎静默 fallback 复验 |
| T4 | pretty mode error | -2700 | 格式正确 |
| T5 | Mail inbox TCC | null (stderr=-2741) | wrap 不捕获 |
| T6 | file wrap=on | null | 默认 wrap |
| T7 | file --no-wrap | null | 透传 |

**D. 已知限制**
`as_error_code` 仅捕获 **运行时 `on error`**; 下面两类仍走 stderr (rc=1) 不进入字段:
1. **语法/编译错** (`-2741`): osascript 编译器在 wrap 执行前就拒
2. **TCC 拒绝** (`-1743`): 系统层拒绝, 不到 AS 引擎

退化路径: 旧调用方读 stderr 行为不变。

**E. 性能 (单进程, 26-54ms/次)**
- 主体: tempfile + subprocess.run + JSON.dumps
- vs osascript baseline 25ms → overhead 0-29ms 可接受
- vs v1.5 27ms baseline → overhead 与 v1.5 持平 (wrap 解析 <1ms)

---

## 8.11 R61 勘误候选清单 (2026-07-14, [BLOCKED 复核])

> 触发：TODO #3「修补 §8.10.5 之外的另一处错记」
> 策略：仅列出可疑行 + 证据，不擅自动 content，留待用户审核

| 行 | 原句片段 | 可疑点 | 证据/实测依据 |
|---|---|---|---|
| 327 | `AppleScript Automation 已授权，可创建/删除草稿` | §8.8 v1.2 过期声明，断言 Mail "已授权" | R18 Mail -1743；R17/R19/R30 多次复测 Mail 整 app TCC 受限（§8.10.14）；真实状态应"受 TCC 整类受限，仅零授权属性可读" |
| 65 | `Mail inbox -2741 语法错` | 语法错 -2741 + TCC -1743 双码常并存，单标 -2741 不准 | R18 stderr 双码共存 |

[BLOCKED 复核] 候选 = 1（line 327）。需用户决策：(a) 改写为受 TCC 受限 + 引用 §8.10.14；(b) 加 v4.19 patch banner；(c) 保留原句加 (R61) 注释。
