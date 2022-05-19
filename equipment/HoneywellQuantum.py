import serial
from serial.tools import list_ports

class BarcodeReader(object):
    def __init__(self):
        self.connected = False
        self.name = 'Honeywell Quantum Barcode Reader'

    def connect(self):
        ports = [p for p in list_ports.comports()]
        honeywell_id = 'Honeywell Bidirectional Device'
        barcode_readers = [x for x in ports if honeywell_id in x[1]]
        count = len(barcode_readers)
        assert count == 1, 'Found %d Honeywell Quantums, expected 1'%count
        self.comm = serial.Serial(barcode_readers[0][0], 115200, timeout = 1)
        self.connected = True
        # Turn off the barcode reader's motor
        self.comm.write('O')

    def disconnect(self):
        self.comm.close()
        self.connected = False

    def scan_barcode(self, timeout = 2):
        self.comm.timeout = timeout
        self.comm.flush()
        # Turn on the barcode readers motor (Extra O is to prevent 
        # lockup caused by sending two M's)
        self.comm.write('OM')
        data = self.comm.readline().strip()
        # Turn off the barcode reader's motor
        self.comm.write('O')
        return data

if __name__ == '__main__':
    br = BarcodeReader()
    br.connect()
    print(br.scan_barcode(timeout = None))