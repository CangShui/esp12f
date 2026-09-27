/*
 * ============================================================================
 *  ES12F 本地化固件  (ESP8285 / ESP8266, 1MB Flash)
 * ============================================================================
 *  目标：
 *    1) 删除原固件的“远程固件更新(OTA)”能力；
 *    2) 不连接任何外部服务器（原固件会连 songguoyun.topwd.top / mqtt.topwd.top）；
 *    3) 只保留两个功能：
 *       ① 原样的 WiFi 热点配网（手机连热点 → 网页设置家里 WiFi 密码）；
 *       ② 正常启动连上 WiFi 后，80 端口提供网页：手动点击 开机/关机/重启、
 *          查看电源状态；同时提供 GET 方式的一键命令 API。
 *       原有的开机关机重启电源状态功能（GPIO 时序）保持不动。
 *
 *  外部依赖：仅 ESP8266 Arduino core 自带的库（WiFi / WebServer / DNSServer / EEPROM）。
 *            不使用 HTTPClient、不使用 WiFiClient、不使用 MQTT、不使用 ArduinoOTA。
 *
 *  构建：见同目录 README.md（arduino-cli，FQBN = esp8266:esp8266:generic:eesz=1M）
 * ============================================================================
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <DNSServer.h>
#include <EEPROM.h>

#include "config.h"
#include "storage.h"
#include "pages.h"

/* ------------------------------------------------------------------ */
/* 全局状态                                                            */
/* ------------------------------------------------------------------ */
static ESP8266WebServer server(80);
static DNSServer        dns;

static bool     g_portal      = false;   /* true = 配网热点模式          */
static uint32_t g_rebootAt    = 0;       /* >0 表示到点重启              */
static uint32_t g_ledBlinkAt  = 0;
static bool     g_ledState    = false;
static uint32_t g_lastStaTry  = 0;
static char     g_lastMsg[96] = "就绪";
static uint32_t g_cmdCount    = 0;       /* 已执行的指令条数（用于证明刷新不下发命令） */

static const uint8_t ACT_ON = 1, ACT_OFF = 2, ACT_RST = 3;

/* 非阻塞动作状态机：动作在 loop() 里分步推进，期间 Web 服务照常响应，
   所以网页上的状态和「执行中」提示能实时刷新，不会再出现按钮卡灰。 */
static uint8_t  g_act      = 0;          /* 0=空闲 1=开机 2=关机 3=重启 */
static uint8_t  g_actPhase = 0;
static uint32_t g_actT0    = 0;

static inline bool actBusy() { return g_act != 0; }

static const char *actName(uint8_t a) {
  return a == ACT_ON ? "开机" : (a == ACT_OFF ? "关机" : (a == ACT_RST ? "重启" : "?"));
}

static void actFinish(const char *msg) {
  g_act = 0;
  g_actPhase = 0;
  g_cmdCount++;
  snprintf(g_lastMsg, sizeof(g_lastMsg), "%s", msg);
  Serial.printf("[ACT] done (%u): %s\n", g_cmdCount, msg);
}

/* 启动一个动作（立即返回，不阻塞） */
static void actStart(uint8_t a) {
  g_act = a;
  g_actPhase = 0;
  g_actT0 = millis();
  snprintf(g_lastMsg, sizeof(g_lastMsg), "%s指令执行中…", actName(a));
  Serial.printf("[ACT] start %s\n", actName(a));
}

/* 在 loop() 里推进；时序与原固件一致（见 config.h 注释） */
static void actService() {
  if (!g_act) return;
  uint32_t el = millis() - g_actT0;
  if (g_act == ACT_ON) {
    if (g_actPhase == 0) { digitalWrite(PIN_PWR, PWR_ACTIVE); g_actPhase = 1; g_actT0 = millis(); }
    else if (g_actPhase == 1 && el >= T_PWR_SHORT) {
      digitalWrite(PIN_PWR, PWR_IDLE);
      actFinish("开机指令已执行");
    }
  } else if (g_act == ACT_OFF) {
    if (g_actPhase == 0) { digitalWrite(PIN_PWR, PWR_ACTIVE); g_actPhase = 1; g_actT0 = millis(); }
    else if (g_actPhase == 1 && el >= T_PWR_LONG) {
      digitalWrite(PIN_PWR, PWR_IDLE); g_actPhase = 2; g_actT0 = millis();
    } else if (g_actPhase == 2 && el >= T_PWR_SETTLE) {
      actFinish("关机指令已执行");
    }
  } else if (g_act == ACT_RST) {
    if (g_actPhase == 0) { digitalWrite(PIN_RST, RST_ACTIVE); g_actPhase = 1; g_actT0 = millis(); }
    else if (g_actPhase == 1 && el >= T_RST_PULSE) {
      digitalWrite(PIN_RST, RST_IDLE);
      actFinish("重启指令已执行");
    }
  }
}

static uint8_t readPowerState() {
#if STATE_ACTIVE_HIGH
  return digitalRead(PIN_STATE) == HIGH ? 1 : 0;
#else
  return digitalRead(PIN_STATE) == LOW ? 1 : 0;
#endif
}

/* ------------------------------------------------------------------ */
/* 网页/接口                                                            */
/* ------------------------------------------------------------------ */
static void sendJson(int code, const String &body) {
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.sendHeader(F("Connection"), F("close"));   /* 避免 keep-alive 连接被长动作拖死 */
  server.send(code, F("application/json; charset=utf-8"), body);
}

/* 统一发送 HTML 页面：no-store + Connection: close */
static void sendPage(PGM_P page) {
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.sendHeader(F("Connection"), F("close"));
  server.send_P(200, PSTR("text/html; charset=utf-8"), page);
}

static void handleApi();   /* 前置声明 */

static String jsonEscape(const String &in) {
  String out;
  out.reserve(in.length() + 8);
  for (size_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '"' || c == '\\') { out += '\\'; out += c; }
    else if ((uint8_t)c < 0x20) { /* 跳过控制字符 */ }
    else out += c;
  }
  return out;
}

static void handleRoot() {
  /* 支持 http://<ip>/?cmd=on 这种“一键命令”写法 */
  if (server.hasArg("cmd")) { handleApi(); return; }
  sendPage(g_portal ? (PGM_P)PAGE_CONFIG : (PGM_P)PAGE_INDEX);
}

static void handleConfigPage() {
  sendPage((PGM_P)PAGE_CONFIG);
}

/* 扫描附近 WiFi，返回 JSON 数组（与原固件 /scan 行为一致） */
static void handleScan() {
  int n = WiFi.scanNetworks(false, true);
  String out = "[";
  bool first = true;
  for (int i = 0; i < n; i++) {
    String s = WiFi.SSID(i);
    if (s.length() == 0) continue;
    if (!first) out += ",";
    out += "\"" + jsonEscape(s) + "\"";
    first = false;
  }
  out += "]";
  WiFi.scanDelete();
  sendJson(200, out);
}

/* 保存 WiFi：兼容原固件的 POST /?ssid=xxx&password=xxx，返回纯文本 OK */
static void handleSaveWifi() {
  String ssid = server.arg("ssid");
  String pass = server.arg("password");
  if (ssid.length() == 0) {
    server.send(200, F("text/plain; charset=utf-8"), F("error, not found ssid"));
    return;
  }
  cfgSaveSsidPass(ssid.c_str(), pass.c_str());
  Serial.printf("[CFG] saved ssid=%s\n", ssid.c_str());
  server.send(200, F("text/plain; charset=utf-8"), F("OK"));
  g_rebootAt = millis() + 1200;   /* 给浏览器一点时间收到响应后重启 */
}

static void handleClearWifi() {
  cfgClear();
  server.send(200, F("text/plain; charset=utf-8"), F("OK, rebooting to config mode"));
  g_rebootAt = millis() + 800;
}

static void handleStatus() {
  String s = "{";
  s += "\"power\":" + String(readPowerState());
  s += ",\"state\":" + String(digitalRead(PIN_STATE));
  s += ",\"sense\":" + String(digitalRead(PIN_SENSE2));
  s += ",\"busy\":" + String(actBusy() ? "true" : "false");
  s += ",\"cmd\":" + String(g_act);
  s += ",\"cmds\":" + String(g_cmdCount);
  s += ",\"portal\":" + String(g_portal ? "true" : "false");
  s += ",\"ip\":\"" + (g_portal ? WiFi.softAPIP().toString() : WiFi.localIP().toString()) + "\"";
  s += ",\"rssi\":" + String(g_portal ? 0 : WiFi.RSSI());
  s += ",\"uptime\":" + String(millis() / 1000UL);
  s += ",\"version\":\"" ES12F_VERSION "\"";
  s += ",\"last\":\"" + jsonEscape(String(g_lastMsg)) + "\"";
  s += "}";
  sendJson(200, s);
}

/* 下发一个动作：立即返回，实际动作由 loop() 分步执行，不阻塞 Web 服务 */
static void queueAction(uint8_t act, const char *name) {
  if (actBusy()) {
    sendJson(409, String("{\"ok\":false,\"busy\":true,\"msg\":\"") + actName(g_act)
                     + "正在执行中，请稍候\"}");
    return;
  }
  actStart(act);
  sendJson(200, String("{\"ok\":true,\"queued\":\"") + name + "\",\"msg\":\""
                   + g_lastMsg + "\"}");
}

static void handleApi() {
  String cmd = server.arg("cmd");
  if (cmd.length() == 0) {
    /* /api/on  /api/off  /api/restart  /api/status 形式 */
    String uri = server.uri();
    int slash = uri.lastIndexOf('/');
    cmd = (slash >= 0) ? uri.substring(slash + 1) : uri;
  }
  cmd.toLowerCase();
  if (cmd == "on" || cmd == "poweron" || cmd == "open" || cmd == "1")        queueAction(ACT_ON, "开机");
  else if (cmd == "off" || cmd == "poweroff" || cmd == "close" || cmd == "0") queueAction(ACT_OFF, "关机");
  else if (cmd == "restart" || cmd == "reset" || cmd == "reboot")             queueAction(ACT_RST, "重启");
  else if (cmd == "status" || cmd == "state")                                 handleStatus();
  else sendJson(400, F("{\"ok\":false,\"msg\":\"cmd 支持 on|off|restart|status\"}"));
}

static void handleNotFound() {
  if (g_portal) {
    /* 强制门户：任何未知请求都跳到配网页 */
    server.sendHeader(F("Location"), String("http://") + WiFi.softAPIP().toString() + "/", true);
    server.send(302, F("text/plain"), "");
    return;
  }
  server.send(404, F("text/plain; charset=utf-8"), F("404 Not Found"));
}

/* ------------------------------------------------------------------ */
/* 局域网刷机（OTA）                                                    */
/*   只接受私有网段源 IP；设备不主动连接任何 IP/域名，固件由浏览器推上来   */
/* ------------------------------------------------------------------ */
static bool g_otaAllowed = false;

static bool isLocalClient() {
  IPAddress ip = server.client().remoteIP();
#if OTA_ALLOW_LOOP
  if (ip[0] == 127) return true;                                    /* 127.0.0.0/8     */
#endif
#if OTA_ALLOW_10
  if (ip[0] == 10) return true;                                     /* 10.0.0.0/8      */
#endif
#if OTA_ALLOW_172
  if (ip[0] == 172 && ip[1] >= 16 && ip[1] <= 31) return true;      /* 172.16.0.0/12   */
#endif
#if OTA_ALLOW_192
  if (ip[0] == 192 && ip[1] == 168) return true;                    /* 192.168.0.0/16  */
#endif
  return false;
}

static bool otaTokenOk() {
  if (sizeof(OTA_TOKEN) <= 1) return true;      /* 未设置 token */
  return server.arg("token") == F(OTA_TOKEN);
}

static void handleUpdatePage() {
  if (!isLocalClient() || !otaTokenOk()) {
    server.send(403, F("text/plain; charset=utf-8"),
                F("403 只允许局域网私有 IP 访问刷机页面"));
    return;
  }
  sendPage((PGM_P)PAGE_UPDATE);
}

/* 上传结束（响应阶段） */
static void handleUpdateDone() {
  if (!g_otaAllowed) {
    server.send(403, F("text/plain; charset=utf-8"), F("403 源 IP 不在允许的局域网网段内"));
    return;
  }
  bool ok = !Update.hasError();
  server.sendHeader(F("Connection"), F("close"));
  server.send(200, F("text/plain; charset=utf-8"),
              ok ? F("OK, 刷机成功，设备正在重启...") : F("FAIL, 刷机失败，原固件未被替换"));
  if (ok) {
    Serial.println(F("[OTA] success, rebooting"));
    delay(400);
    ESP.restart();
  } else {
    Serial.println(F("[OTA] failed"));
  }
}

/* 上传数据流（写入 flash 阶段） */
static void handleUpdateUpload() {
  HTTPUpload &up = server.upload();
  if (up.status == UPLOAD_FILE_START) {
    g_otaAllowed = isLocalClient() && otaTokenOk();
    if (!g_otaAllowed) {
      Serial.printf("[OTA] rejected from %s\n", server.client().remoteIP().toString().c_str());
      return;                                   /* 不写 flash，丢弃数据 */
    }
    uint32_t maxSketch = (ESP.getFreeSketchSpace() - 0x1000) & 0xFFFFF000;
    Serial.printf("[OTA] start '%s'  maxSketchSpace=%u\n", up.filename.c_str(), maxSketch);
    if (!Update.begin(maxSketch, U_FLASH)) Update.printError(Serial);
  } else if (!g_otaAllowed) {
    return;                                     /* 丢弃非白名单来源的数据 */
  } else if (up.status == UPLOAD_FILE_WRITE) {
    if (Update.write(up.buf, up.currentSize) != up.currentSize) Update.printError(Serial);
  } else if (up.status == UPLOAD_FILE_END) {
    if (Update.end(true)) {
      Serial.printf("[OTA] received %u bytes\n", up.totalSize);
    } else {
      Update.printError(Serial);
    }
  }
}

static void registerRoutes() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/", HTTP_POST, handleSaveWifi);      /* 原固件的保存方式 */
  server.on("/config", HTTP_GET, handleConfigPage);
  server.on("/scan", HTTP_GET, handleScan);
  server.on("/save", HTTP_POST, handleSaveWifi);  /* 兼容表单提交 */
  server.on("/reset", HTTP_GET, handleClearWifi);
  server.on("/api", HTTP_GET, handleApi);
  server.on("/api/on", HTTP_GET, handleApi);
  server.on("/api/off", HTTP_GET, handleApi);
  server.on("/api/restart", HTTP_GET, handleApi);
  server.on("/api/status", HTTP_GET, handleStatus);
#if OTA_ENABLE
  server.on("/update", HTTP_GET, handleUpdatePage);
  server.on("/update", HTTP_POST, handleUpdateDone, handleUpdateUpload);
#endif
  server.onNotFound(handleNotFound);
  server.begin();
  server.enableCORS(true);
}

/* ------------------------------------------------------------------ */
/* 模式切换                                                             */
/* ------------------------------------------------------------------ */
static void startPortal() {
  g_portal = true;
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP_STA);            /* AP_STA：既能开热点，也能扫描 WiFi */
  char ap[40];
  snprintf(ap, sizeof(ap), AP_SSID_PREFIX "%06X", ESP.getChipId());
  const char *apPass = (g_cfg.extra.ap_pass[0] != 0) ? g_cfg.extra.ap_pass : nullptr;
  WiFi.softAP(ap, apPass);
  delay(200);
  dns.setErrorReplyCode(DNSReplyCode::NoError);
  dns.start(53, "*", WiFi.softAPIP());
  Serial.printf("[AP] ssid=%s  ip=%s\n", ap, WiFi.softAPIP().toString().c_str());
  snprintf(g_lastMsg, sizeof(g_lastMsg), "配网模式，请连接热点 %s", ap);
  g_lastStaTry = millis();
}

static void startStation() {
  g_portal = false;
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.hostname(HOSTNAME);
  WiFi.begin(g_cfg.ssid, g_cfg.pass);
  Serial.printf("[STA] connecting to %s ...\n", g_cfg.ssid);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - t0) < T_STA_CONNECT) {
    delay(200);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[STA] failed -> config portal"));
    startPortal();
    return;
  }
  Serial.printf("[STA] connected  ip=%s  rssi=%d\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
  snprintf(g_lastMsg, sizeof(g_lastMsg), "已连接 %s", WiFi.SSID().c_str());
}

/* ------------------------------------------------------------------ */
/* 上电时序：复刻原固件 setup() 里的引脚初始化，并识别配网按钮            */
/* ------------------------------------------------------------------ */
static bool g_forceConfig = false;   /* 上电时配网按钮是否按下 */

static void hardwareBoot() {
  pinMode(PIN_LED,   OUTPUT); digitalWrite(PIN_LED, LED_OFF);
  pinMode(PIN_PWR,   OUTPUT); digitalWrite(PIN_PWR, PWR_IDLE);
  pinMode(PIN_RST,   OUTPUT); digitalWrite(PIN_RST, RST_IDLE);
  pinMode(PIN_STATE, INPUT);
  pinMode(PIN_SENSE2, INPUT_PULLUP);
  delay(10);

  /* 配网按钮 = GPIO4（内部上拉），低电平表示按下。
     原固件 function A(0x402039EC) 开头就是 digitalRead(4)：
       GPIO4==0 → 进入 "Wait for Webconfig" 配网流程
       GPIO4==1 → return -1，跳过配网走正常联网
     所以"按住按钮再上电"就是原厂的进配网方式，这里保持同样的行为。 */
  g_forceConfig = (digitalRead(PIN_SENSE2) == LOW);

  /* 原固件：digitalWrite(5,HIGH) → 等 GPIO4 变低 → digitalWrite(5,LOW)
     实测 GPIO4 常态为高，原厂这里是"等按钮按下"；为避免没按按钮时卡死，
     最多等 T_BOOT_SENSE 毫秒。等待期间按下也认定为要进配网。 */
#if BOOT_USE_RST_HOLD
  digitalWrite(PIN_RST, RST_ACTIVE);
  uint32_t t0 = millis();
  while (digitalRead(PIN_SENSE2) == HIGH && (millis() - t0) < T_BOOT_SENSE) {
    delay(10);
    yield();
  }
  if (digitalRead(PIN_SENSE2) == LOW) g_forceConfig = true;
  digitalWrite(PIN_RST, RST_IDLE);
#else
  digitalWrite(PIN_RST, RST_IDLE);
#endif
}

/* ------------------------------------------------------------------ */
void setup() {
  Serial.begin(SERIAL_BAUD);
  Serial.println();
  Serial.println(F("===== ES12F local firmware " ES12F_VERSION " ====="));
  Serial.printf("chipId=0x%06X  flash=%uKB  freeHeap=%u\n",
                ESP.getChipId(), ESP.getFlashChipRealSize() / 1024, ESP.getFreeHeap());

  hardwareBoot();
  cfgLoad();

  registerRoutes();

  Serial.printf("[BOOT] config-button(GPIO4)=%s\n", g_forceConfig ? "按下 -> 进配网" : "未按下");
  if (g_forceConfig || !cfgHasWifi()) startPortal();
  else                                startStation();

  Serial.printf("[MODE] %s  ip=%s\n",
                g_portal ? "CONFIG-AP" : "NORMAL-STA",
                g_portal ? WiFi.softAPIP().toString().c_str()
                         : WiFi.localIP().toString().c_str());
}

/* ------------------------------------------------------------------ */
void loop() {
  if (g_portal) {
    dns.processNextRequest();
    /* 配网模式下如果已经存过 WiFi，每 30 秒后台重试一次，
       一旦连上就自动切到正常模式（不用重新上电）。 */
    if (cfgHasWifi() && WiFi.status() != WL_CONNECTED && (millis() - g_lastStaTry) > 30000UL) {
      g_lastStaTry = millis();
      WiFi.begin(g_cfg.ssid, g_cfg.pass);
    }
    if (cfgHasWifi() && WiFi.status() == WL_CONNECTED) {
      Serial.println(F("[STA] connected from portal mode, switching"));
      g_portal = false;
      dns.stop();
      WiFi.softAPdisconnect(true);   /* 关掉热点，保留已建立的 STA 连接 */
      snprintf(g_lastMsg, sizeof(g_lastMsg), "已连接 %s", WiFi.SSID().c_str());
    }
  }

  server.handleClient();

  /* 电源动作：非阻塞推进，期间 Web 服务照常响应 */
  actService();

  /* 配网模式：慢闪提示；正常模式：执行中亮灯，其余熄灭（与原固件一致） */
  if (g_portal) {
    if (millis() - g_ledBlinkAt > LED_BLINK_MS) {
      g_ledBlinkAt = millis();
      g_ledState = !g_ledState;
      digitalWrite(PIN_LED, g_ledState ? LED_ON : LED_OFF);
    }
  } else {
    digitalWrite(PIN_LED, actBusy() ? LED_ON : LED_OFF);
  }

  if (g_rebootAt && (int32_t)(millis() - g_rebootAt) >= 0) {
    Serial.println(F("[SYS] rebooting"));
    delay(50);
    ESP.restart();
  }

  delay(2);
}
