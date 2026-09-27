# ES12F 固件备份说明

备份日期：2026-09-27 16:05
备份方式：CH341A（USB 转串口模式）+ esptool `read-flash`（只读，未擦除、未写入）

---

## 1. 芯片信息

| 项目 | 值 |
|---|---|
| 芯片型号 | **ESP8285N08**（ESP8266 内核 + 内置 1MB Flash） |
| Chip ID | `0x00849206` |
| MAC 地址 | `ec:94:cb:84:92:06` |
| 晶振 | 26 MHz |
| Flash 容量 | 1 MB (0x100000) |
| Flash 厂商/型号 | Manufacturer `0x51` (GigaDevice), Device `0x4014` |
| 启动模式（正常） | `boot mode:(3,7)` = Flash 启动 |
| 启动模式（烧录） | `boot mode:(1,x)` = UART 下载模式 |

## 2. 固件识别

对 dump 做离线分析得到：

- 0x00000 处有合法 ESP8266 镜像头（`0xE9` 魔数，1 段，入口 `0x4010F45C`）→ 引导程序
- 0x01000 处有第二镜像头（5 段，入口 `0x401000B8`）→ 应用程序
- 基于 **Arduino ESP8266 core** 编译（含 `core_esp8266_main.cpp`、`ESP8266-http-Update`、`x-ESP8266-*` 头）
- SDK 编译时间：**2019-07-03 15:53:05**
- 版本字符串：**`esp8266_V1.1`**
- 功能特征：SmartConfig 配网、MQTT 客户端、自定义 HTTP 协议
  （`/Esp_get_AccessKey.php?wifi_pass=`、`stassid:`、`stapsw:`、`AccessKey:`、`CheckStateEnable:`、`LedEnable:`）
- 存储占用：0x00000–0x5FFFF 有数据（约 320KB），0x60000–0xEFFFF 为空（0xFF），0xF0000–0xFFFFF 为 SDK 参数/RF_CAL 区

## 3. 备份文件

| 文件 | 大小 | SHA256 | MD5 |
|---|---|---|---|
| `es12f_firmware_backup_1MB.bin` | 1 048 576 字节 | `1D4F1FDF97F7165A5F79DE5BC692506E04FA7E68E54166F48319ECCF36DB12A3` | `16A9BCC3EF9BF6D17A13DA20C2E1C345` |
| `ES8285N08_full_20260927_160556.bin` | 同上（同一份，原始文件名带时间戳） | 同上 | 同上 |

> 两个文件内容完全一致（SHA256 相同），互为副本。

## 4. 如何恢复（刷回去）

```powershell
# 需要先让模块进入下载模式：GPIO0 接 GND → 上电
python -m esptool --port COM3 --baud 460800 --before no-reset --after hard-reset `
  write-flash 0x0 "C:\Users\Administrator\Desktop\es12f\es12f_firmware_backup_1MB.bin"
```

或先擦除再写入：

```powershell
python -m esptool --port COM3 --baud 460800 --before no-reset erase-flash
python -m esptool --port COM3 --baud 460800 --before no-reset --after hard-reset `
  write-flash 0x0 "C:\Users\Administrator\Desktop\es12f\es12f_firmware_backup_1MB.bin"
```

## 5. 本次使用的接线与操作步骤（复现用）

**接线（CH341A 处于串口模式时）**

- CH341A 的 3 针模式跳线：**跳线帽完全拔掉**（SDA/SCL 悬空 = UART 模式），此时芯片枚举为 `VID_1A86 & PID_5523`，Windows 生成 COM 口
- 跳线帽插在 1-2 时是 EPP/编程模式（`PID_5512`），**没有 COM 口**
- ESP TXD → CH341A RXD
- ESP RXD → CH341A TXD
- ESP GND ↔ CH341A GND（必须共地）
- 注意：CH341A 的 TXD 空载约 4.6V（5V 电平），ESP8266 是 3.3V 器件，建议把板子电压跳线切到 3.3V 更安全

**进入下载模式（关键）**

1. 把模块的 **GPIO0 用线接到 GND**（保持接着）
2. 保持 GPIO0 接地的情况下，给模块**断电再上电**
3. 上电后启动日志会显示 `boot mode:(1,x)`（而不是 `(3,7)`），此时芯片停在 bootloader 等待命令
4. 用 esptool 连接：`python -m esptool --port COM3 --before no-reset chip-id`

**注意事项**

- 板子上的按键**不是** GPIO0（按住按键上电仍是 `boot mode:(3,7)`）
- 每次关闭串口后模块会退出下载模式，需要**重新按上面步骤进一次下载模式**再执行下一条命令
- `read-flash` 是纯读取操作，不会改动模块里的任何数据

## 6. 本次用到的工具版本

- esptool 5.4.0（`python -m pip install --upgrade esptool`）
- 驱动：WCH 官方 WHQL 版 CH341SER（`wch.cn - Ports - 3.9.2024.9`，通过 Windows Update 安装）
