### 1. 芯片内已保存的配置（EEPROM 区 0xFB000，明文）

  +0x000  '<REDACTED>'                                                | hex: e8 a3 b8 e8 81 8a e6 8b 9b e5 ab 96 e9 83 bd e6 98 af e8 af 88 e9 aa 97 2d 32 34 00 00 00 00 00
  +0x020  '<REDACTED>'                                              | hex: 48 75 61 77 65 69 40 48 75 61 77 65 69 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  +0x060  '\r\n<REDACTED>'                                       | hex: 0d 0a 32 30 32 36 30 39 32 36 31 33 35 38 33 37 39 39 00 00 00 00 01 01 ff ff ff ff ff ff ff ff

### 2. 应用 EEPROM 副本（0xFD000 / 0xFE000）

  0xFD000+0x000  ff ff ff ff ff ff ff ff 01 00 ff ff 1b 00 00 00
  0xFD000+0x010  e8 a3 b8 e8 81 8a e6 8b 9b e5 ab 96 e9 83 bd e6
  0xFD000+0x020  98 af e8 af 88 e9 aa 97 2d 32 34 00 b8 0a 10 40
  0xFD000+0x030  03 05 03 00 03 00 00 48 75 61 77 65 69 40 48 75
  0xFD000+0x040  61 77 65 69 00 10 40 16 0d 10 40 64 00 00 00 01
  0xFD000+0x050  00 00 00 08 0d 10 40 08 00 00 00 14 17 ff 3f 15
  0xFD000+0x060  00 00 00 d0 01 10 40 f2 84 fe 3f 01 00 00 00 01
  0xFD000+0x070  00 00 00 ae ac 23 40 00 b5 9c e1 98 b5 22 4b a2
  0xFD000+0x080  ff 7d 05 e1 e4 fb 92 b2 66 a9 8b ca 96 1b cd c8
  0xFD000+0x090  59 50 31 dd c6 4f 0a bd ff ff ff ff ff ff ff ff
  0xFD000+0x0A0  ff ff ff ff ff ff ff ff ff 00 80 af ca a8 ed ec
  0xFD000+0x0B0  0a 00 00 00 57 65 62 5f 43 6f 6e 66 69 67 00 3f
  0xFD000+0x0C0  60 05 ff 3f 90 01 ff 3f 64 04 a8 c0 c0 a8 04 01
  0xFD000+0x0D0  01 04 a8 c0 00 b6 21 40 c0 a8 04 01 ff ff ff 00
  0xFD000+0x0E0  c0 a8 04 01 01 00 00 00 50 ff ff 3f 00 00 00 00
  0xFD000+0x0F0  d0 fe ff 3f ec 6e 21 40 5e aa 23 40 00 00 00 00
  0xFD000+0x100  d0 fe ff 3f 02 6b 21 40 55 a8 23 40 01 00 00 00
  0xFD000+0x110  01 00 00 00 00 ff ff ff ff ff ff ff ff ff ff ff
  0xFD000+0x130  ff ff ff ff ff 01 00 00 04 ff ff ff 01 00 ff ff
  0xFD000+0x140  1b 00 00 00 e8 a3 b8 e8 81 8a e6 8b 9b e5 ab 96
  0xFD000+0x150  e9 83 bd e6 98 af e8 af 88 e9 aa 97 2d 32 34 00
  0xFD000+0x160  b8 0a 10 40 48 75 61 77 65 69 40 48 75 61 77 65
  0xFD000+0x170  69 00 10 40 16 0d 10 40 64 00 00 00 01 00 00 00
  0xFD000+0x180  08 0d 10 40 08 00 00 00 14 17 ff 3f 15 00 00 00
  0xFD000+0x190  d0 01 10 40 f2 84 fe 3f 01 00 00 00 01 00 00 00
  0xFD000+0x1A0  ae ac 23 40 ff ff ff ff ff ff ff ff ff ff ff ff
  0xFE000+0x000  ff ff ff ff ff ff ff ff 03 00 ff ff 1b 00 00 00
  0xFE000+0x010  e8 a3 b8 e8 81 8a e6 8b 9b e5 ab 96 e9 83 bd e6
  0xFE000+0x020  98 af e8 af 88 e9 aa 97 2d 32 34 00 b8 0a 10 40
  0xFE000+0x030  03 05 03 00 03 00 00 48 75 61 77 65 69 40 48 75
  0xFE000+0x040  61 77 65 69 00 10 40 16 0d 10 40 64 00 00 00 01
  0xFE000+0x050  00 00 00 08 0d 10 40 08 00 00 00 14 17 ff 3f 15
  0xFE000+0x060  00 00 00 d0 01 10 40 f2 84 fe 3f 01 00 00 00 01
  0xFE000+0x070  00 00 00 ae ac 23 40 00 b5 9c e1 98 b5 22 4b a2
  0xFE000+0x080  ff 7d 05 e1 e4 fb 92 b2 66 a9 8b ca 96 1b cd c8
  0xFE000+0x090  59 50 31 dd c6 4f 0a bd ff ff ff ff ff ff ff ff
  0xFE000+0x0A0  ff ff ff ff ff ff ff ff ff 00 80 af ca a8 ed ec
  0xFE000+0x0B0  0a 00 00 00 57 65 62 5f 43 6f 6e 66 69 67 00 3f
  0xFE000+0x0C0  60 05 ff 3f 90 01 ff 3f 64 04 a8 c0 c0 a8 04 01
  0xFE000+0x0D0  01 04 a8 c0 00 b6 21 40 c0 a8 04 01 ff ff ff 00
  0xFE000+0x0E0  c0 a8 04 01 01 00 00 00 50 ff ff 3f 00 00 00 00
  0xFE000+0x0F0  d0 fe ff 3f ec 6e 21 40 5e aa 23 40 00 00 00 00
  0xFE000+0x100  d0 fe ff 3f 02 6b 21 40 55 a8 23 40 01 00 00 00
  0xFE000+0x110  01 00 00 00 00 ff ff ff ff ff ff ff ff ff ff ff
  0xFE000+0x130  ff ff ff ff ff 01 00 00 04 ff ff ff 01 00 ff ff
  0xFE000+0x140  1b 00 00 00 e8 a3 b8 e8 81 8a e6 8b 9b e5 ab 96
  0xFE000+0x150  e9 83 bd e6 98 af e8 af 88 e9 aa 97 2d 32 34 00
  0xFE000+0x160  b8 0a 10 40 48 75 61 77 65 69 40 48 75 61 77 65
  0xFE000+0x170  69 00 10 40 16 0d 10 40 64 00 00 00 01 00 00 00
  0xFE000+0x180  08 0d 10 40 08 00 00 00 14 17 ff 3f 15 00 00 00
  0xFE000+0x190  d0 01 10 40 f2 84 fe 3f 01 00 00 00 01 00 00 00
  0xFE000+0x1A0  ae ac 23 40 ff ff ff ff ff ff ff ff ff ff ff ff

### 3. 攻击能力关键词全镜像扫描（>=4 字符可打印串）

  [ieee80211] 8 处:
     0x45E60  ieee80211.c
     0x45EF0  ieee80211_hostap.c
     0x45F60  ieee80211_input.c
     0x45F80  ieee80211_output.c
     0x45FC0  ieee80211_scan.c
     0x46050  ieee80211_sta.c
  [disassoc] 1 处:
     0x46130  ap_probe_send over, rest wifi status to disassoc
  [payload] 1 处:
     0x48138  send payload failed

### 4. 固件中所有网络地址

  http://songguoyun.topwd.top
  http://songguoyun.topwd.top/Esp_OTA_Update/wifiBootUp
  mqtt.topwd.top

### 5. 传输安全相关

  https://               出现 0 次
  BEGIN CERTIFICATE      出现 0 次
  mbedtls                出现 0 次
  SSL                    出现 0 次
  bearssl                出现 1 次
  AES                    出现 0 次
  signature              出现 0 次
  Signature              出现 1 次
  md5                    出现 1 次
  MD5                    出现 2 次
  sha256                 出现 0 次
  SHA256                 出现 0 次