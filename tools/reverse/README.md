# tools/reverse —— 逆向工具集

> 这些脚本用于**从原厂 1MB flash dump 反推固件行为**。
> 方法论文档见 [`../../docs/02-固件逆向.md`](../../docs/02-固件逆向.md)。

所有脚本都是纯 Python，除了 `esptool` 之外不依赖第三方库（`capstone` 可选）。

---

## 快速开始

```powershell
cd C:\Users\Administrator\Desktop\es12f

# 结构总览
python -m esptool image-info backup\es12f_firmware_backup_1MB.bin

# 字符串
python tools\reverse\appstr.py backup\es12f_firmware_backup_1MB.bin

# 字面量槽 → 字符串映射（找出谁引用了 "Wait for Webconfig"）
python tools\reverse\xl32r.py backup\es12f_firmware_backup_1MB.bin

# GPIO 使用表（引脚号 + 电平 + 延时）
python tools\reverse\findgpio.py backup\es12f_firmware_backup_1MB.bin

# 看某个地址附近的上下文
python tools\reverse\ctx.py backup\es12f_firmware_backup_1MB.bin 0x402039EC

# 配置扇区
python tools\reverse\dump_config.py backup\es12f_firmware_backup_1MB.bin
```

---

## 脚本清单

| 脚本 | 作用 | 关键实现 |
|---|---|---|
| **`xdis.py`** | 自研 Xtensa LX106 解码器 + 段地址换算 | 逐条按真实指令长度前进，避免 objdump 在数据区漂移 |
| **`findgpio.py`** | 扫 `digitalWrite` / `digitalRead` 调用点，提取引脚号、电平、延时 | 用 `l32r` 拿到函数地址，回看 `movi.n a2,N` 拿引脚 |
| **`gpio.py`** | 输出更结构化的 GPIO 使用表 | |
| **`ctx.py`** | 打印指定地址附近的上下文反汇编 | |
| **`xl32r.py`** | 扫全部 `l32r`，建立「字面量槽 → 值/字符串」映射 | `目标 = ((pc+3)&~3) - ((0x10000-imm16)<<2)` |
| **`xscan.py`** | 通用线性扫描器 | |
| **`fit16.py` / `fit24.py` / `fitbr.py`** | 编码拟合器：验证指令字段布局 | 把候选编码算出来与真实 V 精确匹配 |
| **`appstr.py`** | 提取应用段字符串并分类（URL / 域名 / 凭据 / 中文） | |
| **`mkelf.py`** | 由 dump 重建可被 objdump 分析的 ELF | 用段表拼出标准 ELF |
| **`dump_config.py`** | 解析 `0xFB000` 配置扇区 | |
| **`sec_scan.py` / `sec_regions.py` / `sec_report.py`** | 安全扫描：域名、URL、凭据、可疑区域 | 输出 `docs/security-report.md` |
| **`analyze_dump.py`** | dump 结构总览 | |

---

## 必须知道的坑

### 1. objdump 会在数据区漂移

ESP8266 镜像把代码段和数据段混排。`objdump -D` 按线性扫描，
一旦扫到数据区就"错位"，之后所有指令都是错的。

**解决**：用 `xdis.py`，逐条按真实长度前进（`(V & 0xF) >= 8` → 2 字节，否则 3 字节）。

### 2. op0 `0x2` 分组同时含 RRI8 和 MOVI

光看 `t`/`s` 字段顺序会误判。正确做法是**比特位拟合**（`fit16.py` / `fit24.py`），
并与 objdump 在**代码区**的输出交叉验证。

### 3. `ret.n` 要特判

字面量 `0xF00D`，否则会被 op0 `0xC` 的分支逻辑吃掉。

### 4. 段地址 → 文件偏移要按段表算

| 内存段 | 文件偏移 |
|---|---|
| `0x40200000` 起（irom0） | `0x1000 + (addr - 0x40200000)` |
| IRAM / DRAM | 按段表逐段算 |

`xdis.py` 的 `foff()` 已封装。

---

## 关键结论（本项目实测）

| 结论 | 来源 |
|---|---|
| GPIO12 = 电源键 | `digitalWrite(12,1)` + `movi.n a3,500` @ `0x40203BB2` |
| 关机 = 长按 8000ms + 静置 2000ms | `movi.n a3,8000` @ `0x40203BF1` |
| GPIO5 = 复位键 | `digitalWrite(5,1)` @ `0x40203CAE` |
| GPIO14 = 电源状态（高=开机） | `digitalRead(14)` @ `0x40203AF6` + 真机实测 |
| **GPIO4 = 配网按钮（低=按下）** | function A `0x402039EC` 首条 `digitalRead(4)`；字面量池含 `"\r\nWait for Webconfig"` |
| 配置区 = flash `0xFB000` | core 链接脚本 `_EEPROM_start = 0x402fb000` |

---

## 注意

`backup/es12f_firmware_backup_1MB.bin` 已脱敏（凭据被 `0x00` 覆写），
所以：
- `appstr.py` 的输出里**不会**再出现明文凭据
- `dump_config.py` 会显示空 SSID/密码 —— 这是预期的
- 段表、代码、字符串结构**未受影响**，逆向方法仍可完整复现
