# ES12F 本地化固件 v1.3

把基于 **ESP8285N08** 的电脑远程开关机卡，从「连厂商云服务器」改造为**纯本地局域网设备**。

## 这一版做了什么

**删除的能力**

| 能力 | 原厂实现 |
|---|---|
| 远程固件更新 | `http://songguoyun.topwd.top/Esp_OTA_Update/wifiBootUp` |
| 云端状态上报 | `http://songguoyun.topwd.top/Esp_updata_state.php?state=` |
| MQTT 控制通道 | `mqtt.topwd.top` + 明文口令 |
| 上传 WiFi 密码 | `/Esp_get_AccessKey.php?wifi_pass=` |

新固件里 `topwd` / `songguoyun` / `mqtt` / `https://` / `ArduinoOTA` / `ESP8266HTTPUpdate` / `PubSubClient` **全部不存在**，也没有任何 HTTP 客户端 —— 设备不主动发起任何出站连接。

**保留并新增的能力**

| 功能 | 说明 |
|---|---|
| ① 热点配网 | 按住配网按钮(GPIO4)上电 / 无配置时自动；配网页 HTML 与原厂逐字节一致 |
| ② 电源控制网页 | 80 端口，2 秒自动刷新，开机/关机/重启按钮 |
| ③ GET 一键 API | `/api?cmd=on\|off\|restart\|status`，非阻塞状态机 |
| ④ 局域网刷机 | `/update` 网页上传固件，仅接受私有网段源 IP |

## 硬件时序（从原厂固件反汇编还原 + 真机验证）

| GPIO | 作用 |
|---|---|
| 12 | 电源键：高 500ms = 开/关机；高 8000ms = 强制关机 |
| 5 | 复位键：高 200ms 脉冲 |
| 14 | 电源状态（**高 = 已开机**，真机确认） |
| 4 | 配网按钮（**低 = 按下**，真机确认） |
| 2 | 状态指示灯 |

## 刷写

**必须写 flash `0x0`**，不是 `0x1000`。
`.ino.bin` 是 `[eboot@0x0] + [app@0x1000]` 合并镜像，写 `0x1000` 会死循环
（`Fatal exception (0): epc1=0x4010f480`）。

```powershell
# 串口刷写（首次）
# 先：GPIO0→GND 保持 → 断电 → 上电
python tools\flash_now.py COM3 500

# 或网页刷机（设备已联网时）
# 浏览器打开 http://<设备IP>/update，上传 ES12F_Local_firmware.bin
```

## 附件

| 文件 | 说明 |
|---|---|
| `ES12F_Local_firmware.bin` | **主固件**，写 `0x0`。保留芯片上的 WiFi 配置 |
| `ES12F_Local_full_1MB.bin` | 完整 1MB 出厂镜像，写 `0x0`。配置清空，首次上电进配网 |
| `SHA256SUMS.txt` | 指纹 |

```
1677EF36DDD17D7CADAF67A5A19F3259B80DF05B1DCCC252516D34205F7476DD  ES12F_Local_firmware.bin
64080D653AC8D79E8171C35DC2E361AEFC0BA2B0FBA5122C36A3704C26AF8D5E  ES12F_Local_full_1MB.bin
```

## 教程

仓库内的 `docs/` 是完整教程：

| 文档 | 内容 |
|---|---|
| [01-硬件与连线](docs/01-硬件与连线.md) | 连线图解、引脚表、下载模式时序 |
| [02-固件逆向](docs/02-固件逆向.md) | 从 1MB dump 反推硬件行为的完整可复现流程 |
| [03-功能模块](docs/03-功能模块.md) | 六个模块的实现方式 |
| [04-刷写指南](docs/04-刷写指南.md) | 串口刷写 + 局域网刷机 + 从源码构建 |
| [05-使用与API](docs/05-使用与API.md) | 配网、网页、GET API |
| [06-排错](docs/06-排错.md) | 现象→原因→处理 |
| [07-安全与脱敏](docs/07-安全与脱敏.md) | 安全设计、已删除能力、脱敏记录 |

## 已知限制

1. `/api` 与 `/update` **未做鉴权**（设计取舍）。`/update` 有源 IP 白名单与可选 `OTA_TOKEN`。
2. GPIO14 极性与 GPIO4 按钮已真机验证；GPIO12/GPIO5 驱动主板的实际效果未做端到端验证。
3. IRAM 占用 92%，加新功能前留意是否溢出。
