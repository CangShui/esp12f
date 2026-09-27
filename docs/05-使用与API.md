# 05 · 使用与 API

---

## 1. 进配网模式

三种方式，任选其一：

| 方式 | 操作 |
|---|---|
| **按住配网按钮上电**（原厂方式） | GPIO4 按钮按住 → 断电 → 上电，串口打印 `[BOOT] config-button(GPIO4)=按下 -> 进配网` |
| 没配过网 / 20 秒连不上 | 自动进配网 |
| 已联网想换 | 浏览器开 `/config`，或 `/reset` 清空重配 |

配网流程：

```
手机连热点  ES12F_<6位芯片ID>   （无密码）
     ↓
打开 http://192.168.4.1/        （DNS 强制门户会自动跳出）
     ↓
选 WiFi、填密码 → 点「连接 WIFI」
     ↓
返回 "OK"，设备 1.2 秒后自动重启并连网
```

配网页 HTML 与原厂固件**逐字节一致**，协议也一致（`POST /?ssid=&password=` 返回纯文本 `OK`）。

---

## 2. 正常模式：控制网页

访问 `http://<设备IP>/`

```
┌─────────────────────────────────────┐
│  ●  电源已开启                       │   ← 状态点：绿=开 红=关 黄=执行中
│  GPIO14=1  GPIO4=1  IP 192.168.4.221│
│  RSSI -30dBm  运行 128s  local-1.3  │
│  最近指令：开机指令已执行（累计 3 条）│
├─────────────────────────────────────┤
│  ┌─────────── 开 机 ───────────┐    │
│  │  关 机    │    重 启         │    │
│  │        刷新状态              │    │
│  └──────────────────────────────┘    │
│  状态每 2 秒自动刷新，无需手动刷新页面 │
├─────────────────────────────────────┤
│  API（GET 一键命令）                 │
│  /api?cmd=on   /api?cmd=off  ...    │
│  重新配置 WiFi ｜ 局域网刷机 ｜ JSON │
└─────────────────────────────────────┘
```

设计要点：

- **按钮永不置灰**，随时可以再按；重复点击返回 409 + 提示，不会叠加动作
- **2 秒自动刷新**，请求带 4 秒超时，失败自动重试
- **首次加载不弹提示**，避免误以为刷新重发了命令
- 「累计已执行 N 条」可用来确认刷新**不会**下发命令

---

## 3. GET 一键命令 API

### 3.1 命令表

| 命令 | 作用 | 耗时 |
|---|---|---|
| `http://<IP>/api?cmd=on` | 开机（GPIO12 高 500ms） | ~0.5s |
| `http://<IP>/api?cmd=off` | 关机（GPIO12 高 8000ms + 静置 2000ms） | ~10s |
| `http://<IP>/api?cmd=restart` | 重启（GPIO5 高 200ms） | ~0.2s |
| `http://<IP>/api?cmd=status` | 状态 JSON | 立即 |

### 3.2 等价写法

```
/api?cmd=on        /api/on        /?cmd=on
/api?cmd=off       /api/off       /?cmd=off
/api?cmd=restart   /api/restart   /?cmd=restart
/api?cmd=status    /api/status    /?cmd=status
```

别名：`on` = `poweron` = `open` = `1`；`off` = `poweroff` = `close` = `0`；
`restart` = `reset` = `reboot`；`status` = `state`。

### 3.3 响应

**下发成功**（动作已排队，响应立即返回，不等动作完成）：

```json
{"ok":true,"queued":"开机","msg":"开机指令执行中…"}
```

**已有动作在执行**：

```json
{"ok":false,"busy":true,"msg":"关机正在执行中，请稍候"}
```
HTTP 状态码 `409`。

**状态查询** `GET /api/status`：

```json
{
  "power": 1,          // 判定结果：1=已开机 0=已关机
  "state": 1,          // GPIO14 原始电平
  "sense": 1,          // GPIO4 原始电平（配网按钮，按下为 0）
  "busy": false,       // 是否有动作在执行
  "cmd": 0,            // 当前动作：0=空闲 1=开机 2=关机 3=重启
  "cmds": 3,           // 累计已执行指令数（用于证明刷新不下发命令）
  "portal": false,     // 是否处于配网热点模式
  "ip": "192.168.4.221",
  "rssi": -30,
  "uptime": 128,       // 秒
  "version": "local-1.3",
  "last": "开机指令已执行"
}
```

### 3.4 用法示例

```powershell
# PowerShell
Invoke-RestMethod http://192.168.4.221/api?cmd=status
Invoke-RestMethod http://192.168.4.221/api?cmd=on

# curl
curl.exe "http://192.168.4.221/api?cmd=restart"

# 定时检测电源状态
while ($true) {
  $s = Invoke-RestMethod http://192.168.4.221/api?cmd=status
  "{0}  power={1}  uptime={2}s" -f (Get-Date -Format HH:mm:ss), $s.power, $s.uptime
  Start-Sleep 5
}
```

### 3.5 只读监控脚本

```powershell
python tools\monitor.py 192.168.4.221 30      # 监控 30 分钟
```

每 2 秒轮询一次 `/api/status`，电平变化时高亮标记。**只发 GET，不发送任何动作命令。**

输出示例：

```
[18:35:02] 初始  state(GPIO14)=1  sense(GPIO4)=1  power=1  rssi=-28
[18:40:14] *** 变化 ***  sense(GPIO4): 1 -> 0    ← 按下配网按钮
[18:40:16] *** 变化 ***  sense(GPIO4): 0 -> 1    ← 松开
```

---

## 4. 局域网刷机

见 [04-刷写指南.md 方式 B](04-刷写指南.md)。

```
http://<IP>/update
```

---

## 5. 常用地址一览

| 地址 | 作用 |
|---|---|
| `/` | 控制页（配网模式下是配网页） |
| `/config` | 配网页（任何时候都可访问） |
| `/scan` | 扫描附近 WiFi，返回 JSON 数组 |
| `/reset` | 清空 WiFi 配置并重启进配网 |
| `/update` | 局域网刷机页 |
| `/api?cmd=...` | 电源控制 API |
| `/api/status` | 状态 JSON |

---

## 6. 恢复出厂 / 换 WiFi

| 场景 | 操作 |
|---|---|
| 换 WiFi | 开 `/config` 重配，或按住配网按钮上电 |
| 忘记设备 IP | 串口看 `[STA] connected ip=...`；或按住按钮上电进配网 |
| 清空配置 | 开 `/reset`，或刷 `ES12F_Local_full_1MB.bin` |
| 完全回原厂 | `flash.ps1 -Mode Restore`，见 [04-刷写指南.md](04-刷写指南.md) |
