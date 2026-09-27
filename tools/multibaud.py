import serial, time, sys

port = 'COM3'
out = r'C:\Users\Administrator\Desktop\es12f\tools\multibaud.log'
plan = [(74880, 20), (115200, 20), (9600, 10), (57600, 10)]

with open(out, 'a', encoding='utf-8', errors='replace') as f:
    f.write(f"\n=== multibaud capture {time.strftime('%H:%M:%S')} ===\n")
    f.flush()
    for baud, secs in plan:
        try:
            s = serial.Serial(port, baud, timeout=0.3)
        except Exception as e:
            f.write(f"baud {baud}: OPEN FAIL {e}\n"); f.flush(); continue
        buf = b''
        t = time.time()
        while time.time() - t < secs:
            try:
                d = s.read(4096)
            except Exception as e:
                f.write(f"baud {baud}: READ FAIL {e}\n"); f.flush(); break
            if d:
                buf += d
        s.close()
        txt = buf.decode('utf-8', errors='replace')
        printable = sum(1 for c in txt if 32 <= ord(c) < 127 or c in '\r\n')
        f.write(f"\n--- baud {baud}: {len(buf)} bytes, printable {printable} ---\n")
        f.write(repr(buf[:400]) + "\n")
        if printable > len(txt) * 0.7 and buf:
            f.write(">>> LOOKS LIKE TEXT AT THIS BAUD <<<\n")
        f.flush()
    f.write("=== done ===\n")
print('multibaud capture finished')
