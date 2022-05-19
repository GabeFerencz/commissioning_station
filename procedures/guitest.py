# coding: utf-8
from collections import OrderedDict
import os
import time
import threading
import traceback
import binascii

title = 'GUI Test 1.0'

class TestThread(threading.Thread):
    def __init__(self, parent):
        super(TestThread, self).__init__()
        self.daemon = True
        self.parent = parent
        self.log = self.parent.log

        self.state = 'pending' #'running', 'pass', 'fail'
        self.data = ''
        
        # The test should set these parameters in its init
        # self.id = ''
        # self.trans = ('','')

    def run(self):
        try:
            callback = self.parent.test_callback
            if self.id == 'verify':
                callback = self.parent.verify_callback
            self.state = 'running'
            callback(self)
            self.test_procedure()
            callback(self)
        except Exception as e:
            self.state = 'fail'
            self.parent.thread_exception(self, e)

    def test_procedure(self):
        # Threads cannot be killed cleanly in Python, so the timeout will 
        # have to be internal to the thread (unless we switch from threads
        # to multiprocessing.Process, but then we no longer have a shared
        # memory space)
        pass

    def fail(self, message = '', exit = True):
        if message != '':
            self.log(message)
        self.state = 'fail'
        if exit:
            # Abort the rest of the tests when this fails
            self.parent.stop()

class Verify(TestThread):
    def __init__(self, parent, pass_test = True):
        super(Verify, self).__init__(parent)
        self.id = 'verify'
        self.trans = ('Verify Fixture','夹具检验')
        self.name = self.trans[0]
        self.message = ''
        self.pass_test = pass_test
    
    def test_procedure(self):
        get = self.parent.config.get
        # Add a delay to allow the power to stabilize
        time.sleep(1)
        self.message = 'Demo Commissioning Test PASS'
        if self.pass_test:
            self.state = 'pass'
        else:
            self.state = 'fail'

class PassTest(TestThread):
    def __init__(self, parent):
        super(PassTest, self).__init__(parent)
        self.id = 'passtest'
        self.trans = ('Pass Test','通过测试')
        self.exp_time = 0.1
        self.name = self.trans[0]
        self.message = ''
    
    def test_procedure(self):
        time.sleep(0.1)
        self.state = 'pass'

class FailTest(TestThread):
    def __init__(self, parent):
        super(FailTest, self).__init__(parent)
        self.id = 'failtest'
        self.trans = ('Fail Test','未通过测试')
        self.exp_time = 0.1
        self.name = self.trans[0]
        self.message = ''
    
    def test_procedure(self):
        time.sleep(1)
        self.fail()

class FailContinueTest(TestThread):
    def __init__(self, parent):
        super(FailContinueTest, self).__init__(parent)
        self.id = 'failcontinuetest'
        self.trans = ('Fail Continuation Test','无法继续测试')
        self.exp_time = 0.1
        self.name = self.trans[0]
        self.message = ''
    
    def test_procedure(self):
        time.sleep(0.1)
        self.fail('Failed test', exit = False)

class UserTest(TestThread):
    def __init__(self, parent):
        super(UserTest, self).__init__(parent)
        self.id = 'user'
        self.trans = ('User Test','用户测试')
        self.name = self.trans[0]
    
    def test_procedure(self):
        self.message = ('Manually choose whether product passes or fails.', 
                        '手动选择产品是通过还是失败')
        self.done = False
        self.parent.pass_fail_query(self)
        while not self.done:
            # Wait for the user response
            pass

    def user_response(self, resp):
        if resp == 'pass':
            self.state = 'pass'
        else:
            self.state = 'fail'
        self.done = True

class Procedure(object):
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config

        self.verify_callback = parent.verify_callback
        self.pass_fail_query = parent.pass_fail_query
        
        self.test_classes = [PassTest,
                            # FailContinueTest,
                            UserTest]
        self.equipment = {}

    def get_tests(self):
        test_names = OrderedDict()
        for TestClass in self.test_classes:
            test_class = TestClass(self)
            test_names[test_class.id] = test_class.trans
        return test_names

    def verify_start(self):
        self.connect_equipment()
        verify = Verify(self)
        verify.start()
        return verify

    def test_start(self):
        # Clear any leftover test data
        self.uid = ''
        self.test_log_buffer = ''
        self.start_time = time.time()
        self.no_failures = True
        # Log the test parameters
        self.param_dict = dict(self.config.items('uservars'))
        params = ['Part Number = %s'%self.param_dict['partnum']]
        self.log(self.parent.get_version_string())
        self.log(title)
        self.log(', '.join(params))
        # Ensure that the equipment is connected
        self.connect_equipment()
        # Load the tests to be performed
        self.pending_tests = self.test_classes
        # Start the first test
        self.pending_tests[0](self).start()

    def test_callback(self, test):
        self.parent.test_callback(test)
        # Ignore pending/running state updates
        if test.state in ['pass', 'fail']:
            # Log the state and any data
            log_data = '%s: %s'%(test.state.upper(), test.name)
            if test.data:
                log_data += ', data: ' + test.data
            self.log(log_data)
            if test.state == 'fail':
                self.no_failures = False
            # Start next test, callback when completed with all tests
            if len(self.pending_tests) > 1:
                self.pending_tests = self.pending_tests[1:]
                self.pending_tests[0](self).start()
            else:
                if self.no_failures:
                    exit_msg = 'PASS: All automated tests passed!'
                else:
                    exit_msg =  'FAIL: There were automated test failures!'
                self.log(exit_msg, force_file = True)
                self.parent.procedure_callback(self.no_failures)

    def update_config(self, config):
        self.config = config

    def manual_failure(self):
        self.no_failures = False
        self.log('FAIL: Manual test failure!')

    def thread_exception(self, test, e):
        print(traceback.format_exc())
        self.log('-'*71)
        self.log('Thread Exception in %s!'%test.trans[0])
        self.log(traceback.format_exc())
        self.log('-'*71)
        # Set the state to failed and execute the callback
        test.state = 'fail'
        self.stop()
        self.test_callback(test)

    def got_tag(self, tag):
        self.tag = tag

    def get_expected_time(self):
        return sum(c(self).exp_time for c in self.test_classes)

    def connect_equipment(self):
        for equipment in self.equipment.values():
            if not equipment.connected:
                try:
                    equipment.connect()
                except Exception as e:
                    raise self.EquipmentFailure(equipment, e)

    def disconnect_equipment(self):
        for equipment in self.equipment.values():
            try:
                equipment.disconnect()
            except Exception as e:
                print(e)

    def log(self, log_data, force_file = False):
        time_delta = time.time() - self.start_time
        self.test_log_buffer += '%07.03f '%time_delta + log_data + '\n'
        # Write the buffer to the file if we have a uid, or if we force 
        # the file (so that we can log failed uid scans)
        if self.uid != '' or force_file:
            start_time_local = time.localtime(self.start_time)
            time_str = time.strftime('%Y-%m-%d_%H-%M-%S', start_time_local)
            # Ensure that the logs directory exists
            dir = 'logs/%s_logs/'%self.param_dict['partnum']
            if not os.path.exists(dir):
                os.makedirs(dir)
            self.log_filename = dir + '%s_%s.log'%(self.uid, time_str)
            ofile = open(self.log_filename, 'a')
            ofile.write(self.test_log_buffer)
            ofile.close()
            # Clear the log buffer since we just wrote it to the file
            self.test_log_buffer = ''

    def stop(self):
        # A stop is a forced failure
        self.no_failures = False
        # Finish whatever test is running, then exit when on the callback
        try:
            self.pending_tests = [self.pending_tests[0]]
        except:
            self.pending_tests = []

    def end(self):
        pass

    class EquipmentFailure(Exception):
        def __init__(self, equipment, exception):
            self.name = equipment.name
            self.message = exception.message

if __name__ == '__main__':
    import ConfigParser
    config = ConfigParser.SafeConfigParser()
    config.read('config/guitest.ini')
    config.add_section('uservars')
    for (k,v) in [('opname', 'ManufacturingEngineer')]:
        config.set('uservars', k, v)
    
    tb = TestBed()
    proc = Procedure(tb, config)
    print([x[0] for x in proc.get_tests().values()])
    
    proc.test_start()
    while not tb.done:
        time.sleep(0.5)
    print(open(proc.log_filename, 'r').read())