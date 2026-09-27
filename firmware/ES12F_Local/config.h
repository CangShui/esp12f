/*
 * ES12F 本地化固件 —— 硬件接口与行为配置
 * ---------------------------------------------------------------
 * 本文件中的引脚与时间是【从原始固件反汇编中提取】的，用于保持
 * “原有的开机关机重启电源状态功能继续用着不动”。
 *
 * 原始固件 (esp8266_V1.1) 中的实际代码序列：
 *   setup():  pinMode(2,OUTPUT)  digitalWrite(2,HIGH)
 *             pinMode(12,OUTPUT) pinMode(14,INPUT)
 *             pinMode(5,OUTPUT)  pinMode(4,INPUT_PULLUP)
 *             digitalWrite(5,HIGH)
 *             等待 digitalRead(4) 变低
 *             digitalWrite(5,LOW)
 *
 *   开机 / 关机切换 : digitalWrite(12,HIGH); delay(500);  digitalWrite(12,LOW);
 *   强制关机        : digitalWrite(12,HIGH); delay(8000); digitalWrite(12,LOW); delay(2000);
 *   重启(复位)      : digitalWrite(5,HIGH);  ... ;        digitalWrite(5,LOW);
 *   电源状态        : digitalRead(14)
 *   辅助检测        : digitalRead(4)
 * ---------------------------------------------------------------
 * 如果你的板子和上面的推断不一致，只改本文件即可，无需动主程序。
 */
#ifndef ES12F_CONFIG_H
#define ES12F_CONFIG_H

/* ---------------- 引脚 ---------------- */
#define PIN_LED       2    /* 状态指示灯（低电平点亮，与原固件一致）        */
#define PIN_PWR       12   /* 电源按键 PWR_SW 驱动：短按=开/关机，长按=强制关机 */
#define PIN_RST       5    /* 复位按键 RESET_SW 驱动：高电平脉冲=按一下复位   */
#define PIN_STATE     14   /* 电源状态检测输入（HIGH = 开机）              */
#define PIN_SENSE2    4    /* 辅助检测输入（上拉），保持原固件的读取行为     */

/* 各引脚“有效电平”定义（原固件：12 高=按下，5 高=按下，2 低=灯亮） */
#define PWR_ACTIVE    HIGH
#define PWR_IDLE      LOW
#define RST_ACTIVE    HIGH
#define RST_IDLE      LOW
#define LED_ON        LOW
#define LED_OFF       HIGH

/* ---------------- 时间（毫秒） ---------------- */
#define T_PWR_SHORT     500UL    /* 短按电源键：开机 / 关机切换 */
#define T_PWR_LONG     8000UL    /* 长按电源键：强制关机        */
#define T_PWR_SETTLE   2000UL    /* 强制关机后的静置时间        */
#define T_RST_PULSE     200UL    /* 复位脉冲宽度（原固件为一次发布耗时，这里取 200ms 更稳） */
#define T_BOOT_SENSE   2000UL    /* 上电时等待 GPIO4 变低的最长时间（原固件为无限等待） */
#define T_STA_CONNECT 20000UL    /* 连接路由器的超时时间 */

/* ---------------- 其他 ---------------- */
#define ES12F_VERSION   "local-1.3"
#define AP_SSID_PREFIX  "ES12F_"
#define HOSTNAME        "es12f"
#define SERIAL_BAUD     115200
#define LED_BLINK_MS    250      /* 配网模式下的闪烁周期 */

/* ---- 可调开关（默认按原固件行为，一般不用改） ---- */
/* 1 = 上电时复刻原固件的“拉高 GPIO5 → 等 GPIO4 变低 → 拉低 GPIO5”时序
   0 = 上电不碰 GPIO5（如果发现每次上电都会动到主板复位/继电器，可改成 0） */
#define BOOT_USE_RST_HOLD   1
/* 电源状态判定：1 = GPIO14 高电平表示“已开机”；0 = 低电平表示“已开机” */
#define STATE_ACTIVE_HIGH   1
/* 状态 JSON 里返回原始电平，便于现场核对极性 */

/* ---- 局域网刷机（OTA / 网页上传固件） ----
   设计原则：
     · 只接受【局域网私有源 IP】的请求，公网 IP 一律 403
     · 固件只由浏览器/工具“推”给设备，设备绝不主动连接任何 IP 或域名
     · 上传的文件与串口刷写用的是同一个 .ino.bin，效果等价于 write-flash 0x0
     · 新固件暂存在 0xFB000 下方，由 eboot 拷回 0x0；配置扇区 0xFB000 不动   */
#define OTA_ENABLE        1
/* 非空时 /update 必须带 ?token=xxxx 才允许刷机；留空 = 仅靠 IP 白名单 */
#define OTA_TOKEN         ""
/* 允许的源 IP 网段开关（RFC1918 + 回环） */
#define OTA_ALLOW_10      1   /* 10.0.0.0/8        */
#define OTA_ALLOW_172     1   /* 172.16.0.0/12     */
#define OTA_ALLOW_192     1   /* 192.168.0.0/16    */
#define OTA_ALLOW_LOOP    1   /* 127.0.0.0/8       */

#endif /* ES12F_CONFIG_H */
