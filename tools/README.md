# tools —— 工具集

> 全部工具的入口。路径都相对于仓库根目录 `C:\Users\Administrator\Desktop\es12f`。

---

## 1. 构建

| 脚本 | 用法 | 作用 |
|---|---|---|
| `build.ps1` | `powershell -File tools\build.ps1 [-Clean]` | 编译 `firmware/ES12F_Local` → `build/` |
| `make_images.py` | `python tools\make_images.py` | `build/*.ino.bin` → `release/*.bin` + 指纹 |

编译用的 arduino-cli 目录全部指向仓库内 `toolchain\`，不污染全局环境。

---

## 2. 刷写

| 脚本 | 用法 | 说明 |
|---|---|---|
| **`flash_now.py`** | `python tools\flash_now.py COM3 500` | ★ **推荐**：单会话完成「备份→刷写→读回校验」 |
| `flash.ps1` | `.\tools\flash.ps1 -Mode Flash -Port COM3` | 分步式：`Backup`/`Flash`/`Full`/`Restore`/`Verify` |
| `verify.ps1` | `.\tools\verify.ps1 -Port COM3` | 独立读回校验（5 项检查） |

**为什么推荐 `flash_now.py`**：esptool 命令行一个进程只做一件事，第一个进程退出时会把
stub flasher 留在 460800 波特率，第二个进程再用 `--before no-reset` 同步 ROM 协议就同步不上，
报 `No serial data received`。`flash_now.py` 用 esptool 的 Python API 在**同一个
`ESPLoader` 会话**里做完所有事，不存在这个问题。

详细说明见 [`../docs/04-刷写指南.md`](../docs/04-刷写指南.md)。

---

## 3. 调试 / 观测

| 脚本 | 用法 | 作用 |
|---|---|---|
| `listen_boot.py` | `python tools\listen_boot.py COM3 60 20` | 双波特率串口监听：115200 抓应用日志，74880 抓 ROM 横幅/异常 |
| `monitor.py` | `python tools\monitor.py 192.168.4.221 30` | **只读**轮询 `/api/status`，电平变化高亮（不发任何动作命令） |
| `multibaud.py` | `python tools\multibaud.py COM3` | 扫描常见波特率，找设备真实输出速率 |
| `loopback_test.py` | `python tools\loopback_test.py COM3` | CH341A 自发自收，验证串口线是否接对 |

日志统一写入仓库根目录的 `logs/`（可随时删除）。

---

## 4. 逆向

见 [`reverse/README.md`](reverse/README.md)，方法论文档见
[`../docs/02-固件逆向.md`](../docs/02-固件逆向.md)。

---

## 5. 驱动

`drivers/CH341SER/` —— CH341 串口驱动（Windows）。
设备管理器里若出现带感叹号的 `USB-SERIAL CH341`，运行其中的 `SETUP.EXE` 安装。

---

## 6. 环境依赖

| 组件 | 用途 | 来源 |
|---|---|---|
| Python 3.8+ | 所有 .py 脚本 | 系统已装 |
| `esptool` | 读/写 flash、解析镜像 | `pip install esptool` |
| `pyserial` | 串口监听 | `pip install pyserial` |
| arduino-cli + esp8266 core 3.1.2 | 编译 | 仓库内 `toolchain/` |
| Xtensa objdump | 反汇编 | 仓库内 `toolchain/arduino/.../xtensa-lx106-elf-gcc/` |

---

## 7. 注意事项

### PowerShell 脚本必须带 UTF-8 BOM

否则 Windows PowerShell 会按 GBK 读中文，把字符串引号搞坏，报
`字符串缺少终止符`。仓库内的 `.ps1` 都已带 BOM；自己编辑后请保留：

```powershell
$f = 'tools\build.ps1'
$c = Get-Content -Raw -Encoding UTF8 $f
[System.IO.File]::WriteAllText((Resolve-Path $f), $c, (New-Object System.Text.UTF8Encoding($true)))
```

### 刷写地址永远是 `0x0`

ESP8266 的 `.ino.bin` 是 `[eboot@0x0]+[app@0x1000]` 合并镜像。
写 `0x1000` 会死循环（`Fatal exception (0): epc1=0x4010f480`）。
`make_images.py` 已加结构自检。
