import serial, time, sys

port = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
pat = bytes(range(0x41, 0x51))  # 'A'..'P'

for baud in (115200, 9600, 74880):
    try:
        s = serial.Serial(port, baud, timeout=1)
    except Exception as e:
        print(f'baud={baud} OPEN FAIL: {e}')
        break
    s.reset_input_buffer()
    s.reset_output_buffer()
    n = s.write(pat)
    s.flush()
    time.sleep(0.4)
    got = s.read(len(pat) + 8)
    print(f'baud={baud}: wrote {n} bytes {pat!r}')
    print(f'          read  {len(got)} bytes {got!r}')
    print(f'          LOOPBACK {"OK" if got[:len(pat)] == pat else "FAIL"}')
    s.close()
