# ES12F 本地化固件 —— 完整工程包

> 把一台基于 **ESP8285N08** 的电脑远程开关机卡，从「连厂商云服务器」改造为
> **纯本地局域网设备**：删掉远程固件更新与全部对外连接，只保留
> **WiFi 配网** + **网页/API 电源控制** + **局域网网页刷机**。

---

## 0. 30 秒速览

| 项目 | 值 |
|---|---|
| 芯片 | ESP8285N08（ESP8266 内核，1MB Flash，26MHz 晶振） |
| MAC / ChipID | `ec:94:cb:84:92:06` / `0x00849206` |
| 固件框架 | arduino-cli + `esp8266:esp8266@3.1.2` |
| FQBN | `esp8266:esp8266:generic:eesz=1M,CrystalFreq=26` |
| 刷写地址 | **`0x0`**（合并镜像，见 §4.1，写 `0x1000` 必炸） |
| 配置扇区 | `0xFB000`（与原厂一致，刷固件不会丢 WiFi 配置） |
| 对外连接 | **无**（无 HTTP 客户端、无 MQTT、无域名、无远程 IP） |
| 当前版本 | `local-1.3` |

**要刷机** → 直接看 [docs/04-刷写指南.md](docs/04-刷写指南.md)
**要重新编译** → 看 §5
**要理解原理** → 按 `docs/` 顺序读

---

## 1. 目录结构（本教程与目录严格对齐）

```
es12f/
├── README.md                    ← 你在这里：总入口
├── docs/                        ← 教程（skill 级，按顺序读）
│   ├── 01-硬件与连线.md          连线图解、引脚定义、下载模式
│   ├── 02-固件逆向.md            如何从原厂 .bin 反推出全部行为
│   ├── 03-功能模块.md            每个功能模块的实现方式
│   ├── 04-刷写指南.md            串口刷写 + 局域网刷机
│   ├── 05-使用与API.md           配网、网页、GET API
│   ├── 06-排错.md                故障现象 → 原因 → 处理
│   ├── 07-安全与脱敏.md          安全设计、已删除能力、脱敏清单
│   ├── report.md                 正式改造报告（证据链）
│   ├── security-review.md        原厂固件安全审查
│   └── security-report.md        原厂固件安全扫描明细
├── firmware/ES12F_Local/        ← 固件源码（唯一真源）
│   ├── ES12F_Local.ino          主程序
│   ├── config.h                 ★ 引脚/时序/开关，只改这个文件
│   ├── storage.h                EEPROM 配置读写（0xFB000）
│   └── pages.h                  三个网页（配网/控制/刷机）
├── release/                     ← 可刷写镜像（只留最新一版）
│   ├── ES12F_Local_firmware.bin      主固件，写 0x0
│   ├── ES12F_Local_full_1MB.bin      完整 1MB 出厂镜像，写 0x0
│   └── SHA256SUMS.txt                指纹
├── tools/                       ← 全部工具
│   ├── build.ps1                编译
│   ├── make_images.py           生成镜像
│   ├── flash.ps1                串口刷写（备份/刷写/恢复/校验）
│   ├── verify.ps1               独立读回校验
│   ├── flash_now.py             ★ 单会话自动刷写（推荐）
│   ├── listen_boot.py           串口监听（115200 + 74880）
│   ├── monitor.py               只读状态监控
│   ├── reverse/                 逆向工具（见 tools/reverse/README.md）
│   └── drivers/CH341SER/        CH341 串口驱动
├── backup/
│   ├── es12f_firmware_backup_1MB.bin  ★ 原厂备份（已脱敏），回滚依据
│   └── README.md
├── assets/
│   ├── board/                   真机照片 + 连线图
│   │   ├── wiring.svg           ★ 连线图解
│   │   ├── esp-module-pads.png  模块焊盘实拍
│   │   ├── board-front-left.png / board-front-right.png
│   │   ├── board-back-labels.png / board-bottom.png
│   │   └── can-connector.png
│   └── webui/                   网页截图
│       ├── control-page.png  config-page.png  update-page.png
├── toolchain/                   ← 第三方工具链（可整目录删除，重编译时需重下）
│   ├── tools/arduino-cli.exe
│   └── arduino/                 esp8266 core 3.1.2
├── build/                       ← 临时编译产物（可删）
└── logs/                        ← 运行日志（可删）
```

---

## 2. 五分钟上手（AI 或人都照这个走）

### 场景 A：只是想刷最新固件

```powershell
cd C:\Users\Administrator\Desktop\es12f

# 1) 进下载模式：GPIO0→GND 保持，断电，再上电
#    （接线见 docs/01-硬件与连线.md，或直接看 assets/board/wiring.svg）

# 2) 一条命令搞定：备份 + 刷写 + 读回校验
python tools\flash_now.py COM3 500

# 3) 断开 GPIO0 与 GND，断电再上电
# 4) 看启动日志确认
python tools\listen_boot.py COM3 60 20
```

期望日志：

```
===== ES12F local firmware local-1.3 =====
chipId=0x849206  flash=1024KB  freeHeap=...
[BOOT] config-button(GPIO4)=未按下
[STA] connecting to <你的WiFi> ...
[STA] connected  ip=192.168.x.x  rssi=-30
[MODE] NORMAL-STA  ip=192.168.x.x
```

### 场景 B：设备已经联网，想更新固件（**不用接线**）

```
浏览器打开 http://<设备IP>/update
选 release\ES12F_Local_firmware.bin → 点「开始刷机」
```

或：

```powershell
curl.exe -F "firmware=@release\ES12F_Local_firmware.bin" http://192.168.4.221/update
```

### 场景 C：改了源码要重新出固件

```powershell
cd C:\Users\Administrator\Desktop\es12f
powershell -File tools\build.ps1          # 编译 → build\
python tools\make_images.py               # 出镜像 → release\
```

---

## 3. 功能一览

| 功能 | 入口 | 实现 |
|---|---|---|
| **① 热点配网** | 按住配网按钮(GPIO4)上电 / 无配置时自动 | AP 热点 `ES12F_<chipid>` + DNS 强制门户 + 原厂配网页 |
| **② 电源控制网页** | `http://<IP>/` | 80 端口，3 秒自动刷新，开机/关机/重启按钮 |
| **③ GET 一键 API** | `http://<IP>/api?cmd=on\|off\|restart\|status` | 非阻塞状态机，响应 < 100ms |
| **④ 局域网刷机** | `http://<IP>/update` | 网页上传固件，仅允许私有源 IP |

**电源动作时序（与原厂固件逐条对齐，见 [docs/03-功能模块.md](docs/03-功能模块.md)）**

| 动作 | GPIO12（电源键） | GPIO5（复位键） |
|---|---|---|
| 开机 | 高 500ms → 低 | 不动 |
| 关机 | 高 8000ms → 低 → 静置 2000ms | 不动 |
| 重启 | 不动 | 高 200ms → 低 |
| 状态 | `digitalRead(14)`：**高 = 已开机** | |

---

## 4. 三条必须记住的坑

### 4.1 ESP8266 的 `.ino.bin` 必须写 `0x0`，不是 `0x1000`

`.ino.bin` 是 **`[eboot 引导程序 @0x0] + [应用 @0x1000]` 的合并镜像**
（见 core 的 `platform.txt`：`write_flash 0x0 {build.project_name}.bin`）。

写成 `0x1000` 会让原厂 eboot 把「新 eboot」当应用跳进去，入口 `0x4010F480`
直接非法指令异常死循环：

```
Fatal exception (0):
epc1=0x4010f480 ...
```

> 这是本项目真实踩过的坑，`tools/make_images.py` 里已加结构自检：
> 镜像 `0x0` 与 `0x1000` 处必须都有 `E9` 魔数，否则拒绝出镜像。

### 4.2 进下载模式必须「先接 GPIO0，再上电」

ESP8266 只在**复位瞬间**采样 GPIO0。板上那个按键**不是 GPIO0**（是配网按钮，接 GPIO4），
按住按键上电无效。

### 4.3 串口波特率有两个

- **115200** —— 应用自己的日志（`Serial.begin(115200)`）
- **74880** —— ROM 启动横幅 / 崩溃异常（26MHz 晶振默认）

崩溃若发生在 `Serial.begin` 之前，只能从 74880 看到。`tools/listen_boot.py` 会自动两段都抓。

---

## 5. 重新编译

```powershell
cd C:\Users\Administrator\Desktop\es12f
powershell -File tools\build.ps1 -Clean     # 编译
python tools\make_images.py                 # 出镜像
```

`tools/build.ps1` 会把 arduino-cli 的所有目录指向仓库内的 `toolchain\`，
不污染用户全局环境：

```powershell
$env:ARDUINO_DIRECTORIES_DATA      = "$Root\toolchain\arduino"
$env:ARDUINO_DIRECTORIES_DOWNLOADS = "$Root\toolchain\ardl"
$env:ARDUINO_DIRECTORIES_USER      = "$Root\toolchain\user"
```

**只改 `firmware/ES12F_Local/config.h` 就能适配**：引脚、时序、状态极性、OTA 白名单开关全在里面。

编译实测占用：RAM 37%、IRAM 92%、flash 约 301KB / 1MB。

---

## 6. 与原厂固件的差异

| 能力 | 原厂 | 现在 |
|---|---|---|
| 远程固件更新 | `http://songguoyun.topwd.top/Esp_OTA_Update/wifiBootUp` | **删除** |
| 云端状态上报 | `http://songguoyun.topwd.top/Esp_updata_state.php?state=` | **删除** |
| MQTT 控制通道 | `mqtt.topwd.top` + 明文口令 | **删除** |
| 上传 WiFi 密码 | `/Esp_get_AccessKey.php?wifi_pass=` | **删除** |
| 主动连接外网 | 有 | **无**（代码里没有任何 HTTP 客户端 / 域名） |
| WiFi 配网 | 按住按钮上电 | 保留，且新增「连不上自动进配网 / 网页随时重配」 |
| 电源控制 | 仅云端 MQTT | 网页 + GET API（本地） |
| 局域网刷机 | 无 | **新增**（仅私有网段源 IP） |

详见 [docs/07-安全与脱敏.md](docs/07-安全与脱敏.md) 与 [docs/report.md](docs/report.md)。

---

## 7. 硬件引脚（从原厂固件反汇编 + 真机验证）

| GPIO | 方向 | 作用 | 证据 |
|---|---|---|---|
| 2 | 输出 | 状态指示灯（低电平点亮） | `digitalWrite(2,1)` @ `0x40203EDA` |
| 12 | 输出 | 电源键：500ms 短按=开/关机；8000ms=强制关机 | `0x40203BB2/BBB/BC5`、`0x40203BF1/BFA/C04` |
| 5 | 输出 | 复位键：高电平脉冲 | `0x40203CAE→0x40203CCE` |
| 14 | 输入 | 电源状态（**高 = 开机**，真机确认） | `digitalRead(14)` @ `0x40203AF6` |
| 4 | 输入(上拉) | **配网按钮**（低 = 按下） | function A `0x402039EC` 开头 `digitalRead(4)`；字面量池含 `"\r\nWait for Webconfig"`；真机实测按下时 1→0 |

---

## 8. 已知限制

1. **未做鉴权**：局域网内任何人都能操作 `/api` 和 `/update`。这是设计取舍（用户要求"和关机 API 一样简单"），缓解手段是 `/update` 的源 IP 白名单 + 可选 `OTA_TOKEN`。
2. **引脚角色来自反汇编推断**，已用真机验证 GPIO14 极性与 GPIO4 按钮，但 GPIO12/GPIO5 驱动主板电源键/复位键的**实际效果未做端到端验证**（用户要求不测试开关机动作）。
3. **每次重新编译镜像指纹都会变**，以 `release/SHA256SUMS.txt` 为准。
4. 原厂备份已脱敏，其中的 WiFi 配置已清零，刷回后需重新配网。
