import serial
from serial.tools import list_ports
#import time

class BarcodeReader(object):
    def __init__(self):
        self.connected = False
        self.name = 'Honeywell VuQuest 3310 Barcode Reader'

    def setup(self):
        # # Use the RS232 mode with /r/n
        # self.nvm_command('PAP232')
        # Sending this via the serial port causes serial write issues for the
        # next command if we don't insert a long delay
        # time.sleep(2)
        # Enable and set the activation character to 'a'
        self.nvm_command('HSTCEN1')
        self.nvm_command('HSTACH%02X'%ord('a'))
        # Enable and set the deactivation character to 'd'
        self.nvm_command('HSTDEN1')
        self.nvm_command('HSTDCH%02X'%ord('d'))
        # Turn off all barcode symbologies
        self.nvm_command('ALLENA0')
        # Enable just code 128
        self.nvm_command('128ENA1')
        # Only accept 16 character code128 barcodes
        self.nvm_command('128MIN16')
        self.nvm_command('128MAX16')

    def connect(self):
        ports = [p for p in list_ports.comports()]
        honeywell_id = 'Vuquest 3310 Area-Imaging Scanner'
        barcode_readers = [x for x in ports if honeywell_id in x[1]]
        try:
            reader_id = barcode_readers[0][0]
            self.comm = serial.Serial(reader_id, 115200, timeout = 1)
            self.connected = True
        except:
            self.comm = None
            self.connected = False
        return self.connected

    def disconnect(self):
        self.comm.close()
        self.connected = False

    def scan_barcode(self, timeout = 2):
        self.comm.timeout = timeout
        self.comm.flush()
        self.comm.write('a')
        data = self.comm.readline().strip()
        self.comm.write('d')
        return data

    def send_command(self, command):
        # Menu commands require a SYN M CR prefix
        self.comm.write(''.join(map(chr,[22, 77, 13])) + command)

    def nvm_command(self, command):
        self.send_command(command + '.')
        resp = self.comm.read(4096)
        # Ensure that the command is ACKd
        exp = command + '\x06.'
        assert exp == resp, 'expected: %s, received: %s'%(exp, resp)

if __name__ == '__main__':
    br = BarcodeReader()
    br.connect()
    print('Connected on port: ' + br.comm.port)
    br.setup()
    print(br.scan_barcode(timeout = 10))

    # br.setup()
    # br.comm.timeout = 1
    # br.comm.flush()
    # while True:
        # print repr(br.comm.read()),

    # br.comm.timeout = 0.1
    # while True:
        # br.send_command(raw_input())
        # print repr(br.comm.read(1024)),