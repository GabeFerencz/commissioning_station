import serial
from serial.tools import list_ports
from equipment.RfidReader import Reader
from binascii import hexlify, unhexlify

class RfidReader(Reader):
    def __init__(self):
        self.connected = False
        self.name = 'Motorola FX9500 RFID Reader'
        self.ip_addr = None

    def connect(self, username = 'admin', password = 'change', ip_addr = None):
        # If we're given an IP address, try using that first.
        if ip_addr is not None:
            try:
                Reader.__init__(self, ip_addr, username, password)
                self.connected = True
                self.ip_addr = ip_addr
                return True
            except:
                pass
        # If we have an IP address from a previous connection, try using that
        if self.ip_addr is not None:
            try:
                Reader.__init__(self, self.ip_addr, username, password)
                self.connected = True
                self.ip_addr = ip_addr
                return True
            except:
                pass
        # If we didn't just connect using the methods above, try to get the IP
        # address via the serial port, then connect over the faster network
        # connection.
        self.get_ip_from_serial_port(username, password)
        try:
            Reader.__init__(self, self.ip_addr, username, password)
            self.connected = True
            return True
        except:
            pass
        # If we've gotten here, we've run out of things to try, so return False
        return False

    def get_ip_from_serial_port(self, username, password):
        ports = [p for p in list_ports.comports()]
        fx9500_id = 'VID:PID=0525:A4A7'
        inst = [x for x in ports if fx9500_id in x[2]]
        try:
            addr = inst[0][0]
            # Connect to the serial port to get the ip address
            serialReader = Reader(addr, username, password)
            self.ip_addr = serialReader.get('com.network.1.ip_address')
            serialReader.close()
        except:
            self.ip_addr = None

if __name__ == '__main__':
    rr = RfidReader()
    rr.connect()
    tags = rr.find_tags(500)
    print(tags)
    if len(tags) != 1:
        print('Tags in Field: exp 1, got %d'%len(tags))
        #assert False, 'Tags in Field: exp 1, got %d'%len(tags)
    #print rr.tag_read(tags[0], 1, 0, 10)
    #print rr.tag_read(tags[0], 3, 0, 14)
