import pyvisa

class SpectrumAnalyzer(object):
    def __init__(self):
        self.connected = False
        self.name = 'Rigol DSA815 Spectrum Analyzer'

    def connect(self):
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        id = '::0x1AB1::0x0960::' #DSA815 VID/PID
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

    def get_carrier_stats(self):
        self.comm.write(':INIT:CONT ON')
        self.comm.write(':FREQ:CENT 433164000')
        # reject anything not seen on 
        self.comm.write(':FREQ:SPAN 50000')
        self.comm.write(':UNIT:POW DBM')
        # Set the input attenuation to 0dB
        self.comm.write(':POW:ATT 0')
        # Kyle used 0.65 in PSS command line
        #self.comm.write(':SENS:SWE:TIME 2.222200E-02')
        # Kyle used 300 in PSS command line
        self.comm.write(':BAND:RES 3000')
        self.comm.write(':CALC:MARK1:CPE ON')
        freq = int(self.comm.ask(':CALC:MARK1:X?'))
        power = float(self.comm.ask(':CALC:MARK1:Y?'))
        return (power, freq)

if __name__ == '__main__':
    sa = SpectrumAnalyzer()
    sa.connect()
    print(sa.get_id())
    (pwr, freq) = sa.get_carrier_stats()
    print(pwr)
    print(freq)