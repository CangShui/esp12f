# ES12F 固件安全审查报告

审查对象：`backup/es12f_firmware_backup_1MB.bin`（1MB，ESP8285N08，SHA256 `1D4F1FDF…12A3`）
> 注：该备份已做脱敏处理（WiFi 名称/密码/AccessKey/MQTT 口令以 0x00 覆写），
> 因此指纹与原始 dump 不同；固件代码区与 eboot 未改动。本报告中所有凭据均以 `<REDACTED>` 表示。
审查方式：纯离线静态分析（字符串提取 + 网络地址提取 + 攻击特征扫描 + 存储区解析）
审查日期：2026-09-27

---

## 一、结论速览

| 问题 | 结论 |
|---|---|
| **有没有被下发指令的能力？** | **有，而且是设计好的**（云端 MQTT 下发 + 远程 OTA 刷固件） |
| **有没有攻击网络的能力？** | **未发现**。镜像里没有 deauth / 注入 / 混杂模式 / shell / 后门 / 端口扫描 等攻击代码 |
| **有没有安全风险？** | **有，而且比较严重**：全部走明文 HTTP/MQTT，OTA 无签名，凭据硬编码，WiFi 密码明文上传第三方 |
| 设备性质 | 一个联网型 IoT 从设备（智能插座/开关类），由「松果云 songguoyun」平台托管 |

---

## 二、固件里的外部服务器（全部硬编码）

| 地址 | 用途 |
|---|---|
| `http://songguoyun.topwd.top/Esp_OTA_Update/wifiBootUp` | **OTA 远程固件升级接口**（下载 .bin 并刷写） |
| `http://songguoyun.topwd.top/Esp_updata_state.php?state=…&remind=…&AccessKey=…` | 向云端上报设备状态 |
| `http://songguoyun.topwd.top/Esp_get_AccessKey.php?wifi_pass=<WiFi密码>` | **用 WiFi 密码向云端换取 AccessKey** |
| `mqtt.topwd.top` | **MQTT 服务器**（下发指令通道） |

全部是 **`http://`，没有任何 `https://`**（全镜像 `https://` 出现 0 次）。

## 三、"被下发指令"能力的证据

1. **MQTT 客户端**（明文 1883 端口）连接到 `mqtt.topwd.top`
2. **凭据硬编码在固件里**（字符串表 0x5011A 起）：
   - `wang`
   - `<REDACTED>`（形如 "wd" + 手机号 13097777592）
3. 相关字符串：`Connecting to MQTT...`、`MQTT Connected!`、`Failed to subscribe`、`mqtt.ping`、**`Get Command`**、`AutoBootUp`、心跳主题 **`EspHeartTest1`**
4. **`start_OTA_update` + OTA URL + `OTA_update_fail`** → 云端可以让设备下载并刷写新固件

**含义**：设备会连上厂商的 MQTT 服务器并订阅主题，云端（或任何拿到这组凭据的人）可以向它下发指令；再加上 OTA 通道，等于**固件可被远程整体替换**。

## 四、"攻击网络"能力 —— 未发现

对全镜像做了攻击类关键词扫描（deauth / disassoc / beacon / inject / promiscuous / sniff / monitor / freedom / handshake / pmkid / brute / flood / spoof / evil twin / shell / telnet / backdoor / reverse shell / execve / port scan / nmap 等），命中项只有 3 处，且**全部是乐鑫 SDK 的正常组件**：

| 命中 | 位置 | 判定 |
|---|---|---|
| `ieee80211.c` / `ieee80211_hostap.c` / `ieee80211_input.c` / `ieee80211_output.c` / `ieee80211_scan.c` / `ieee80211_sta.c` | 0x45E60–0x46050 | SDK 源码文件名（出现在断言信息里），正常 |
| `ap_probe_send over, rest wifi status to disassoc` | 0x46130 | SDK 的 AP 探测状态机日志，正常 |
| `send payload failed` | 0x48138 | HTTP/MQTT 发送失败提示，正常 |

- `wpa_auth.c` / `wpa_main.c` / `wpa_auth_ie.c` 也是 SDK 的 WPA 实现，不是攻击代码
- `[handleScan]%d` + `/scan` 只是**配网页面扫描周围 WiFi 列表**（给用户选 SSID），属正常功能
- 没有开放 telnet / 反弹 shell / 任意端口连接 / 网络扫描 的痕迹

**结论：这个固件不像"攻击工具"，它是个被云端控制的联网从设备。**

## 五、真正的安全风险（重点）

### 1. OTA 明文 HTTP + 仅 MD5 校验，无签名、无 TLS —— 最高风险
- 升级地址是 `http://…/Esp_OTA_Update/wifiBootUp`，走明文
- 全镜像中：`https://` 0 次、证书 0 次、`mbedtls` 0 次、`AES` 0 次、`sha256` 0 次，只有 `MD5`（完整性校验，不是防篡改）
- **后果**：同一局域网内的攻击者通过 ARP/DNS 劫持 `songguoyun.topwd.top`，即可给设备推送任意固件 → **设备被完全接管**，并可作为跳板进入你的内网

### 2. MQTT 凭据硬编码
任何拿到这份固件的人都能得到 `mqtt.topwd.top` 的账号密码，可能控制同一批次的所有设备。

### 3. WiFi 密码被明文上传给第三方
`/Esp_get_AccessKey.php?wifi_pass=<你的WiFi密码>` 走 HTTP，链路上任何一跳都能看到。

### 4. 设备内保存的 WiFi 凭据是明文（已直接读出）
EEPROM 区（0xFB000，另有两份副本 0xFD000 / 0xFE000）：

| 偏移 | 内容 |
|---|---|
| +0x000 | SSID：**`<REDACTED>`** |
| +0x020 | 密码：**`<REDACTED>`** |
| +0x060 | AccessKey：**`<REDACTED>`**（从服务器响应里存下来的） |

### 5. 配网热点无认证
配网 Web 页面用 `POST /?ssid=xxx&password=xxx` 直接写配置，**没有密码/认证**，配网期间附近的人可以重配这台设备。

### 6. 其它
- MQTT 走明文 1883，无 TLS
- 编译用的 Arduino ESP8266 core 版本为 **`2.2.2-dev(38a443e)`**（2017 年前后版本，较老）
- 固件版本字符串 `esp8266_V1.1`，SDK 编译时间 2019-07-03

---

## 六、处置建议

1. **⚠️ 不要把这块板子接进你家的 WiFi。** 如果已经配过网，建议**立刻修改家里 WiFi 密码**（因为密码已被明文发给第三方服务器）。
2. 如果必须使用：隔离到**访客网络 / 独立 VLAN**，禁止它访问内网其它设备（尤其是 NAS、路由器管理页）。
3. 由于 OTA 是明文 HTTP，**长期联网存在被远程刷入恶意固件的风险**；来源不明的设备最安全的做法是**刷成你自己的固件**（原始固件已备份，可随时刷回）。
4. 已备份的固件内**包含硬编码凭据**（MQTT 密码、WiFi 密码），注意不要外传/上传到公开网盘。
5. 如需进一步确认，可做动态验证：把设备接入**隔离的测试热点**，抓包看它是否真的连 `mqtt.topwd.top` / `songguoyun.topwd.top`，以及上报了哪些字段。

---

## 附：审查方法

- 全量可打印字符串提取（2592 条）→ `security/strings_all.txt（已删除，可用 tools/reverse/appstr.py 重建）`
- 关键词分类报告 → `security/keywords_report.txt（已删除，可用 tools/reverse/sec_scan.py 重建）`
- 网络地址提取 → `security/urls.txt（已删除，可用 tools/reverse/sec_scan.py 重建）`、`security/domains.txt（已删除，可用 tools/reverse/sec_scan.py 重建）`、`security/ip_like.txt（已删除）`
- 应用字符串表与存储区解析 → `security/app_strings_4F000_52000.txt（已删除）`、`security/tail_strings.txt（已删除）`
- 原始数据报告 → `docs/security-report.md`
