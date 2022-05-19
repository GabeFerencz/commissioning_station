#!/usr/bin/python -u
import serial
import socket
# This works with Sirit 510/610 and Motorola FX9500 and connects over 
# serial port (if name has COM in it) or ethernet

class Reader(object):
    def __init__(self, address, username, password, timeout=10):
        self.is_live = False
        self.is_serial = 'COM' in address
        self.address = address
        if not self.is_serial:
            try:
                self.comm = socket.socket()
                self.comm.settimeout(timeout)
            except Exception as e:
                raise self.ConnectionError(e)
        self.address = address
        self.block_write_enabled = False
        self.open()
        resp = self.send('reader.login(%s,%s)'%(username, password))
        if resp[:2] != 'ok':
            raise self.LoginError(resp)
        self.send('modem.protocol.isoc.control.use_block_write=False')

    def open(self):
        if not self.is_live:
            if self.is_serial:
                self.comm = serial.Serial(self.address, 115200)
                self.comm.timeout = 0
                self.send = self.send_serial
                self.send('')
            else:
                self.comm.connect((self.address, 50007))
                self.send = self.send_socket
            self.is_live = True;
    
    def send_socket(self, command):
        self.comm.send(command + '\r\n')
        data = ''
        while '\r\n\r\n' not in data:
            data = data + self.comm.recv(4096)
        return data.strip()

    def send_serial(self, command):
        # It may be worth looking into com.serial.rawmode, which removes 
        # some of the silliness I hack out here and it may be slightly faster
        # Enter the command and wait for the echo to come back
        self.comm.write(command)
        resp = ''
        while 1:
            resp += self.comm.read(4096)
            # Compare a whitespace-stripped version of the command because 
            # the terminal tries to be fancy with automatic line wrapping
            if ''.join(command.split()) in ''.join(resp.split()):
                break
        # Now execute the command
        # Note: sending /r/n will yield double prompts
        self.comm.write('\n')
        # Collect data, ensuring it ends in a new prompt
        data = ''
        while 1:
            data += self.comm.read(4096)
            if (data.endswith('>>> ')):
                break
        # Strip off the prompt and any whitespace before returning
        data = data.replace('>>> ', '')
        return data.strip()

    def get(self, config):
        data = self.send(config)
        if data[:2] == 'ok':
            return data[2:].strip()
        else:
            if 'error.tag.no_tag_in_field' in data:
                raise self.TagNotFoundError(data)
            raise self.ReaderError(data)

    def close(self):
        if self.is_live:
            try:
                self.comm.close()
                self.is_live = False
            except Exception as e:
                raise self.ConnectionError(e)

    def block_write_enable(self, enable = True):
        cmd = 'modem.protocol.isoc.control.use_block_write = '
        enable = bool(enable)
        self.send(cmd + str(enable))
        self.block_write_enabled = enable

    def tag_read(self, epc, bank, word_ptr, len):
        '''Returns hex string without leading 0x on success'''
        arg_str = ','.join(['tag_id=' + epc, 'mem_bank=' + hex(bank), 
                        'word_ptr=' + hex(word_ptr), 'word_count=' + hex(len)])
        cmd_str = 'modem.protocol.isoc.read(%s)'%arg_str
        response = self.get(cmd_str)
        resp_data = response.replace('data = 0x','')
        try:
            int(resp_data, 16)
        except:
            raise self.ReaderError('Invalid read response: %s'%response)
        return resp_data

    def tag_write(self, epc, bank, word_ptr, data):
        '''Returns empty string on success'''
        arg_str = ','.join(['tag_id=' + epc, 'mem_bank=' + hex(bank), 
                        'word_ptr=' + hex(word_ptr), 'data=' + data])
        cmd_str = 'modem.protocol.isoc.write(%s)'%arg_str
        return self.get(cmd_str)

    def write_epc(self, epc_str):
        '''Write a new EPC to the first tag found'''
        cmd_str = 'tag.write_id(new_tag_id=%s)'%epc_str
        resp = self.get(cmd_str)

    def find_tag(self):
        '''Returns the EPC of the first tag found'''
        arg_str = 'mem_bank=1,word_ptr=2,word_count=6'
        cmd_str = 'modem.protocol.isoc.read(%s)'%arg_str
        epc_str = None
        # Block until a tag is found
        while epc_str == None:
            try:
                epc_str = self.get(cmd_str).replace('data = 0x','')
            except self.TagNotFoundError as e:
                pass
        return epc_str

    def find_tags(self, milliseconds = 2000):
        self.get('tag.reporting.taglist_fields = tag_id')
        self.get('tag.db.purge()')
        db = self.get('tag.db.scan_tags(%d)'%milliseconds).split('\r\n')
        epcs = []
        for entry in db:
            entry = entry.strip().strip('()').split('=')
            if entry[0] == 'tag_id':
                epcs.append(entry[1].replace('0x',''))
        return epcs

    # Check for known/expected errors and raise the appropriate exception
    def reader_error_handler(self, string):
        if 'error.tag.no_tag_in_field' in string:
            string = string.replace('error.tag.no_tag_in_field','')
            raise self.TagNotFoundError(string)
        elif 'error.tag.protocol.isoc.memory_overrun' in string:
            raise self.TagMemoryError(string)
        else:
            raise self.ReaderError(string)

    class TagMemoryError(Exception):
        def __init__(self, string):
            self.string = string

        def __str__(self):
            return self.string

    class ConnectionError(Exception):
        def __init__(self, string):
            self.string = string

        def __str__(self):
            return self.string

    class TagNotFoundError(Exception):
        def __init__(self, string):
            self.string = string

        def __str__(self):
            return self.string

    class ReaderError(Exception):
        def __init__(self, string):
            self.string = string

        def __str__(self):
            return self.string

    class LoginError(Exception):
        def __init__(self, string):
            self.string = string

        def __str__(self):
            return self.string