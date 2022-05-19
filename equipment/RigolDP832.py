import pyvisa

class PowerSupply(object):
    def __init__(self):
        self.connected = False
        self.name = 'Rigol DP832 Power Supply'

    def connect(self):
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        id = '::0x1AB1::0x0E11::' #DP832 VID/PID
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
        self.comm.write(':APPL CH3,%f,%f'%(voltage, currentLimit))

    def enable(self):
        self.comm.write(':OUTP CH3,ON')

    def disable(self):
        self.comm.write(':OUTP CH3,OFF')

if __name__ == '__main__':  
    import time
    ps = PowerSupply()
    ps.connect()
    print(ps.get_id())
    ps.set_voltage()
    ps.enable()
    time.sleep(1)
    ps.disable()