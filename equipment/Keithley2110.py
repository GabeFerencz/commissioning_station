import pyvisa
import time

class Multimeter(object):
    def __init__(self):
        self.connected = False
        self.name = 'Keithley 2110 Multimeter'

    def connect(self):
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        id = '::0x05E6::0x2110::' #2110 VID/PID
        inst = [x for x in resources if id in x]
        try:
            self.comm = rm.get_instrument(inst[0])
            self.get_id()
            self.connected = True
        except:
            self.comm = None
            self.connected = False
        return self.connected

    def disconnect(self):
        self.comm = None
        self.connected = False

    def get_id(self):
        return self.comm.ask('*IDN?').strip()

    def setup_current_read(self):
        self.comm.write(':CONF:CURR 0.1, MIN')
        self.comm.ask(':MEAS:CURR?')

    def read_current(self):
        return float(self.comm.ask(':READ?'))

    def current_sense_bypass(self):
        # Bypass the larger resistors used for the lower current measurement
        # ranges by setting the current range to MAX
        self.comm.write(':CONF:CURR MAX, MIN')

if __name__ == '__main__':
    start = time.time()
    print(start)
    mm = Multimeter()
    print('%.3f Multimeter'%(time.time() - start))
    mm.connect()
    print('%.3f connect'%(time.time() - start))
    print(mm.get_id())
    print('%.3f get_id'%(time.time() - start))
    print(mm.read_current())
    print('%.3f read_current'%(time.time() - start))