/*
 * ES12F 本地化固件 —— 配置存储
 * ---------------------------------------------------------------
 * 存储位置：Flash 扇区 0xFB000（ESP8266 Arduino core，Flash Size = 1M (FS:none)
 *           时 _EEPROM_start = 0x402FB000，即 flash 偏移 0xFB000）。
 *           这与【原始固件保存 WiFi 配置的位置完全一致】。
 *
 * 布局与原始固件向后兼容：
 *   0x000  char ssid[32]   —— 与原固件相同
 *   0x020  char pass[64]   —— 原固件为 32 字节；前 32 字节仍然兼容
 *   0x080  ES12F_EXTRA     —— 本固件新增（原固件此处为 0xFF，未被使用）
 *
 * 因此：本固件第一次启动时会自动读出原固件里已经配好的 WiFi，不需要重新配网。
 */
#ifndef ES12F_STORAGE_H
#define ES12F_STORAGE_H

#include <EEPROM.h>
#include "config.h"

#define CFG_OFF_SSID   0x000
#define CFG_OFF_PASS   0x020
#define CFG_OFF_EXTRA  0x080
#define CFG_SIZE       256
#define CFG_MAGIC      0x32464631UL /* '1FF2' */

struct ES12FExtra {
  uint32_t magic;
  uint16_t version;
  uint16_t flags;      /* bit0: 配网成功后重启时保留 */
  char     ap_pass[32];/* 预留：配网热点密码，空=开放热点（与原固件一致） */
};

struct ES12FConfig {
  char ssid[32];
  char pass[64];
  ES12FExtra extra;
};

static ES12FConfig g_cfg;
static bool        g_cfgDirty = false;

static inline void cfgLoad() {
  EEPROM.begin(CFG_SIZE);
  memset(&g_cfg, 0, sizeof(g_cfg));

  char s[32];
  for (int i = 0; i < 32; i++) s[i] = (char)EEPROM.read(CFG_OFF_SSID + i);
  s[31] = 0;
  memcpy(g_cfg.ssid, s, sizeof(g_cfg.ssid));
  g_cfg.ssid[31] = 0;

  char p[64];
  for (int i = 0; i < 64; i++) p[i] = (char)EEPROM.read(CFG_OFF_PASS + i);
  p[63] = 0;
  memcpy(g_cfg.pass, p, sizeof(g_cfg.pass));
  g_cfg.pass[63] = 0;

  uint8_t *ex = (uint8_t *)&g_cfg.extra;
  for (size_t i = 0; i < sizeof(ES12FExtra); i++) ex[i] = EEPROM.read(CFG_OFF_EXTRA + i);
  if (g_cfg.extra.magic != CFG_MAGIC) {
    memset(&g_cfg.extra, 0, sizeof(g_cfg.extra));
    g_cfg.extra.magic   = CFG_MAGIC;
    g_cfg.extra.version = 1;
  }
  g_cfgDirty = false;
}

static inline void cfgSaveSsidPass(const char *ssid, const char *pass) {
  memset(g_cfg.ssid, 0, sizeof(g_cfg.ssid));
  memset(g_cfg.pass, 0, sizeof(g_cfg.pass));
  if (ssid) strncpy(g_cfg.ssid, ssid, sizeof(g_cfg.ssid) - 1);
  if (pass) strncpy(g_cfg.pass, pass, sizeof(g_cfg.pass) - 1);
  g_cfg.extra.magic   = CFG_MAGIC;
  g_cfg.extra.version = 1;
  g_cfg.extra.flags  |= 1;

  for (int i = 0; i < 32; i++) EEPROM.write(CFG_OFF_SSID + i, (uint8_t)g_cfg.ssid[i]);
  for (int i = 0; i < 64; i++) EEPROM.write(CFG_OFF_PASS + i, (uint8_t)g_cfg.pass[i]);
  uint8_t *ex = (uint8_t *)&g_cfg.extra;
  for (size_t i = 0; i < sizeof(ES12FExtra); i++) EEPROM.write(CFG_OFF_EXTRA + i, ex[i]);
  EEPROM.commit();
  g_cfgDirty = false;
}

static inline void cfgClear() {
  memset(&g_cfg, 0, sizeof(g_cfg));
  for (int i = 0; i < 32; i++) EEPROM.write(CFG_OFF_SSID + i, 0);
  for (int i = 0; i < 64; i++) EEPROM.write(CFG_OFF_PASS + i, 0);
  g_cfg.extra.magic   = CFG_MAGIC;
  g_cfg.extra.version = 1;
  uint8_t *ex = (uint8_t *)&g_cfg.extra;
  for (size_t i = 0; i < sizeof(ES12FExtra); i++) EEPROM.write(CFG_OFF_EXTRA + i, ex[i]);
  EEPROM.commit();
}

static inline bool cfgHasWifi() {
  return g_cfg.ssid[0] != 0 && g_cfg.ssid[0] != (char)0xFF;
}

#endif /* ES12F_STORAGE_H */
