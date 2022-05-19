import pyvisa

class PowerSupply(object):
    def __init__(self):
        self.connected = False
        self.name = 'Keithley 2200 Power Supply'

    def connect(self):
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        id = '::0x05E6::0x2200::'
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

    def set_voltage(self, voltage = 3.0, currentLimit = 0.5):
        self.comm.write(':VOLT %f'%voltage)

    def enable(self):
        self.comm.write(':OUTP ON')

    def disable(self):
        self.comm.write(':OUTP OFF')

if __name__ == '__main__':  
    import time
    ps = PowerSupply()
    ps.connect()
    print(ps.get_id())
    ps.set_voltage()
    ps.enable()
    time.sleep(1)
    ps.disable()