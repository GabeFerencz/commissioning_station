# coding: utf-8
# These imports are built into Python
import os
import sys
import time
import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog
import configparser
import traceback
from glob import glob
from collections import OrderedDict
from importlib import import_module
import queue as Queue

# These imports are not built into Python:
try:
    import release
    version = release.version
except ImportError:
    version = 'INVALID RELEASE'

version_tuple = (f'Commissioning Station {version}', f'调试站 {version}')

langDict = {'lang':('english', 'chinese'),
            'nextlang':('简体中文', 'English'),
            'title':version_tuple,
            'config':('Configuration', '配置'),
            # 'opname':('Operator Name','操作员姓名'),
            # 'jobnum':('Job Number','工单号'),
            # 'shift':('Shift','班次'),
            'verify':('Verify Fixture','夹具检验'),
            'partnum':('Part Number', '部件号'),
            'endjob':('End Job', '作业结束'),
            'startjob':('Start Job', '作业开始'),
            'pending':('Pending','待定'),
            'running':('Running','执行'),
            'pass':('Pass','通过'),
            'fail':('Fail','失败'),
            'testframe':('Test Details','测试细节'),
            'commission':('Commission Product','佣金产品'),
            'continue':('Continue','继续'),
            }

class Translatable(tk.StringVar):
    '''A StringVar container that holds a translatable string. The language
    is based on the index of the translations tuple/list.'''
    def __init__(self, translations, lang_idx = 0):
        self.translations = translations
        tk.StringVar.__init__(self)
        # Set the StringVar to the default language
        self.translate(lang_idx)

    def translate(self, languageIndex = 0):
        self.set(self.translations[languageIndex])

class VarLabelFrame(ttk.LabelFrame):
    '''A ttk LabelFrame that supports a StringVar in the title. '''
    def __init__(self, parent, stringvar):
        ttk.LabelFrame.__init__(self, parent)
        # I guess LabelFrame doesn't support textvariables. Boo.
        #self.configure(textvariable = stringvar)
        # The following does what I wanted out of the line above (changes 
        #  the title when the dictionary gets translated):
        self.text_var_title = stringvar
        # Create a lambda function to update the title from the StringVar
        trans = lambda *args: self.configure(text = self.text_var_title.get())
        # Bind the lambda function to a write to the StringVar
        self.text_var_title.trace('w', trans)
        # Set the default title
        trans()

class VarLabelEntry(ttk.Frame):
    '''An entry box with a StringVar label west of the entry box.'''
    def __init__(self, parent, textvariable):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
    
        self.entry = ttk.Entry(self)
        self.label = ttk.Label(self, textvariable = textvariable)
        self.label.grid(row = 0, column = 0, sticky = tk.E)
        self.entry.grid(row = 0, column = 1)
        
        self.configure = self.entry.configure
        self.get = self.entry.get

    def set(self, data):
        self.entry.delete(0, 'end')
        self.entry.insert('end', data)

class VarLabelCombo(ttk.Frame):
    '''A read only combo box with a StringVar label west of the box.'''
    def __init__(self, parent, textvariable, values = ['']):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        
        self.label = ttk.Label(self, textvariable = textvariable)
        self.entry = ttk.Combobox(self, width = 17)
        self.set_values(values)
        self.entry.grid(row = 0, column = 1)
        self.label.grid(row = 0, column = 0, sticky = tk.E)
        
        self.get = self.entry.get

    def set_values(self, values):
        self.entry.configure(values = values)
        # If nothing is currently selected, try to select the first item
        if self.entry.get() == '':
            try:
                self.entry.current(0)
            except:
                pass

    def configure(self, **kwargs):
        self.entry.configure(kwargs)
        # When the state is 'normal', state() returns an empty tuple. We
        # want the enabled combobox to be 'readonly', so override 'normal'.
        if self.entry.state() == ():
            self.entry.configure(state = 'readonly')

class TestStepWidget(ttk.Frame):
    '''A StringVar name that has pending/running/pass/fail states.'''
    def __init__(self, parent, name):
        self.parent = parent
        self.translatables = parent.translatables
        ttk.Frame.__init__(self, parent)

        # Let the TestWidget grid these items so they can be aligned
        self.testLabel = ttk.Label(parent, textvariable = name)
        self.resultLabel = ttk.Label(parent)
        self.separator = ttk.Separator(parent)
        
        pendingStyle = ttk.Style()
        pendingStyle.configure('pending.Label', anchor = tk.EW)
        passStyle = ttk.Style()
        passStyle.configure('pass.Label', background = 'green', anchor = tk.EW)
        failStyle = ttk.Style()
        failStyle.configure('fail.Label', background = 'red', anchor = tk.EW)
        runningStyle = ttk.Style()
        runningStyle.configure('running.Label', background = 'yellow', 
                                anchor = tk.EW)

    def set_state(self, state):
        self.resultLabel.configure(style = state + '.Label')
        self.resultLabel.configure(textvariable = self.translatables[state])

class TestWidget(VarLabelFrame):
    '''Holds/displays the results and status of a running test.'''
    def __init__(self, parent):
        self.parent = parent
        self.translatables = parent.translatables
        VarLabelFrame.__init__(self, parent, 
                    stringvar = self.translatables['testframe'])

        self.row = 0
        # Add a manual go button at the top of the list (this may be replaced 
        # by the box open / box closed signal)
        self.runBtn = ttk.Button(self, command = self.test_running,
                                textvariable = self.translatables['commission'])
        self.runBtn.grid(row = self.row, column = 0, sticky = tk.W)
        # Simple indeterminate progress bar to show the user that the
        # program has not locked up
        self.progress = ttk.Progressbar(self, orient = 'horizontal', 
                                        length = 300, mode = 'indeterminate')
        self.progress.grid(row = self.row, column = 1)
        self.row += 1
        # Add a separator do split tests from controls
        sep = ttk.Separator(self)
        sep.grid(row = self.row, columnspan = 2, sticky = tk.EW)
        self.row += 1

        # Set up a dictionary to hold each of the individual tests defined
        # by the procedure
        self.test_widgets = {}

        # Queue to hold updates to tests
        self.testUpdateQueue = Queue.Queue()
        # Start looking for posted GUI updates
        self.after(10, self.update_check)

    def update_check(self):
        updates = []
        done = False
        while not done:
            try:
                updates.append(self.testUpdateQueue.get_nowait())
            except:
                done = True
        for (id,state) in updates:
            self.test_widgets[id].set_state(state)
        # Schedule another check for updates
        self.after(10, self.update_check)

    def set_config(self, config):
        self.config = config

    def reset_tests(self):
        for test in self.test_widgets.values():
            test.set_state('pending')

    def clear_tests(self):
        self.reset_tests()
        for test in self.test_widgets.values():
            test.testLabel.grid_remove()
            test.resultLabel.grid_remove()
            test.separator.grid_remove()

    def set_tests(self, tests):
        self.clear_tests()
        for n,(k,v) in enumerate(tests.items()):
            testKey = 'test%d'%n
            trans = Translatable(v, lang_idx = self.parent.lang_idx)
            self.translatables[testKey] = trans
            self.test_widgets[k] = TestStepWidget(self, trans)
            self.test_widgets[k].resultLabel.grid(row = self.row, column = 0, 
                                                sticky = tk.NSEW)
            self.test_widgets[k].testLabel.grid(row = self.row, column = 1, 
                                                sticky = tk.W)
            self.row += 1
            self.test_widgets[k].separator.grid(row = self.row, columnspan = 2, 
                                                sticky = tk.EW)
            self.row += 1

    def at_job_start(self):
        '''Actions to take when a job has started.'''
        self.reset_tests()
        # Display the widget
        self.grid()
        # Initialize with an open box, waiting for the box to close
        self.test_idle()

    def at_job_end(self):
        '''Actions to take when a job has ended.'''
        # Hide the widget from the user
        self.grid_remove()

    def test_idle(self):
        self.runBtn.configure(state = 'normal')
        # When the box is open, we're waiting on a board
        self.progress.stop()
        self.after(20, self.progress.grid_remove)

    def test_running(self):
        self.runBtn.configure(state = 'disabled')
        self.reset_tests()
        self.parent.clear_face()
        try:
            self.parent.procedure.test_start()
            # When the box is closed, we're waiting on a test procedure
            self.progress.configure(mode = 'indeterminate', maximum = 100)
            self.progress.start(10)
            self.progress.grid()
        except self.parent.procedure.EquipmentFailure as e:
            msg = 'Equipment failure:\n\t%s\n\t%s'%(e.name, e.message)
            mb = MessageBox(self, tk.StringVar(self.parent, msg))
            self.after(0, mb.create)
            self.parent.procedure.stop()
            self.test_idle()

class Config(configparser.ConfigParser):
    '''Container for reading/writing configuration files.'''
    def __init__(self, filename):
        configparser.ConfigParser.__init__(self)
        self.filename = filename
        self.read(filename)

    def save_to_file(self):
        cfgfile = open(self.filename,'w')
        self.write(cfgfile)
        cfgfile.close()

    def set_defaults(self, sect, optList):
        self.add_section(sect)
        for (opt, val) in optList:
            self.set(sect, opt, val)

class ConfigWidget(VarLabelFrame):
    '''Configuration input by the user before starting a job.'''
    def __init__(self, parent):
        self.parent = parent
        self.translatables = parent.translatables
        VarLabelFrame.__init__(self, parent, 
                    stringvar = self.translatables['config'])

        row = 0
        # Use an ordered dictionary so that we can lazily iterate the pack
        self.widgets = OrderedDict()
        # for key in ['opname', 'epcprefix', 'jobnum']:
            # self.widgets[key] = VarLabelEntry(self, self.translatables[key])
        # self.widgets['shift'] = VarLabelCombo(self, 
                                    # self.translatables['shift'])
        # self.widgets['shift'].set_values(('1', '2', '3'))
        
        self.widgets['partnum'] = VarLabelCombo(self, 
                                    self.translatables['partnum'])
        self.load_config_files()
        
        # Bind a part number change to a function to set the image
        self.widgets['partnum'].entry.bind('<<ComboboxSelected>>', 
                                    self.part_num_change)
        # Align the items on the east (labels are west and variable sized)
        for widget in self.widgets.values():
            widget.grid(row = row, sticky = tk.E, columnspan = 3)
            row += 1
        
        self.widgets['verify'] = ttk.Button(self, 
                    textvariable = self.translatables['verify'],
                    command = parent.verify)
        self.widgets['verify'].grid(row = row, column = 0)

        # # Set a default EPC prefix
        # self.widgets['epcprefix'].set('330832B4')

        # These buttons are not widgets because they aren't disabled on run
        self.runBtn = ttk.Button(self)
        self.runBtn.grid(row = row, column = 1)
        self.langBtn = ttk.Button(self,
                                textvariable = self.translatables['nextlang'],
                                command = self.parent.next_language)
        self.langBtn.grid(row = row, column = 2)
        
        self.enable()

    def load_config_files(self):
        self.configFiles = {}
        for configFilename in glob('config/*.ini'):
            configStr = os.path.basename(configFilename)[:-4]
            # try:
            if True:
                cfg = Config(configFilename)
                cfg.image = tk.PhotoImage(file = cfg.get('image', 'part'))
                # Only add the config file if it throws no exceptions above 
                # so that we don't break the program for a single broken 
                # configuration file.
                self.configFiles[configStr] = cfg
            # except:
                # pass
        self.widgets['partnum'].set_values(list(self.configFiles.keys()))
        self.part_num_change()

    def update_config_files(self):
        # Rescan the config files
        self.load_config_files()
        # Update the config files with the entered information
        cfg = self.configFiles[self.widgets['partnum'].get()]
        sect = 'uservars'
        cfg.add_section(sect)
        # for key in ['opname', 'epcprefix', 'jobnum', 'shift', 'partnum']:
        for key in ['partnum']:
            cfg.set(sect, key, self.widgets[key].get())
        # Give the procedure the updated configuration
        self.parent.procedure.update_config(cfg)

    def start_job(self):
        self.update_config_files()
        # Ensure that there is a valid procedure
        if not self.validProcedure:
            #TODO: indicate the part number box has a problem
            return
        # Disable the disable-able widgets
        self.disable()
        # Notify the GUI that we're starting a job
        self.parent.at_job_start()
        # Switch the context of the start button
        self.runBtn.configure(textvariable = self.translatables['endjob'], 
                            command = self.end_job)

    def end_job(self):
        # Request the parent to clear any pending tests (current test thread 
        # will continue until it ends)
        self.parent.procedure.stop()
        self.parent.procedure.end()
        # Enable the disable-able widgets
        self.enable()
        # Notify the GUI that we're ending a job
        self.parent.at_job_end()
        # Switch the context of the end button
        self.runBtn.configure(textvariable = self.translatables['startjob'], 
                            command = self.start_job)
        # Rescan the config files
        self.load_config_files()

    def part_num_change(self, *args):
        configName = self.widgets['partnum'].get()
        # Notify the GUI that the part number has changed
        # try:
        if True:
            self.parent.part_number_change(self.configFiles[configName])
            self.validProcedure = True
        # except KeyError:
            # self.validProcedure = False

    def enable(self):  
        for widget in self.widgets.values():
            widget.configure(state = 'normal')

    def disable(self):  
        for widget in self.widgets.values():
            widget.configure(state = 'disabled')

def str_to_num(valStr):
    if valStr.lower().startswith('0x'):
        val = int(valStr, 16)
    else:
        val = int(valStr)
    return val

class CommissioningStation(ttk.Frame):
    '''Main GUI window and message passer. Delegates to widgets.'''
    def __init__(self, parent = None):
        # Save the English translation in self.version_string
        self.version_string = version_tuple[0]
        
        self.parent = parent
        ttk.Frame.__init__(self, parent)
        
        self.grid()
        self.pass_image = tk.PhotoImage(file='images/GreenSmiley.gif')
        self.fail_image = tk.PhotoImage(file='images/RedFrowny.gif')
        self.translatables = {k:Translatable(v) for (k,v) in langDict.items()}
        # Default to English
        self.lang_idx = 0
        self.lang_idx_max = len(self.translatables['lang'].translations) - 1
        
        self.face_canvas = tk.Canvas(self, width = self.pass_image.width(), 
                                height = self.pass_image.height())
        self.part_canvas = tk.Canvas(self)
        self.test_widget = TestWidget(self)
        self.config_widget = ConfigWidget(self)
        
        self.config_widget.grid(row = 0, column = 0, sticky = tk.N)
        self.part_canvas.grid(row = 1, column = 0, columnspan = 2)
        self.face_canvas.grid(row = 0, column = 1)
        self.test_widget.grid(row = 0, column = 2, rowspan = 2, 
                                    sticky = tk.N)
        self.test_widget.grid_remove()

        # Set the default part image
        self.config_widget.part_num_change()

        # The root title doesn't support a StringVar, so we'll do it this way 
        # (See VarLabelFrame for explanation):
        text_var_title = self.translatables['title']
        trans = lambda *args: parent.title(text_var_title.get())
        text_var_title.trace('w', trans)
        trans()
        # Initialize in stopped mode
        self.config_widget.end_job()

    def get_version_string(self):
        return self.version_string

    def next_language(self):
        self.lang_idx += 1
        if self.lang_idx > self.lang_idx_max:
            self.lang_idx = 0
        for tr in self.translatables.values():
            tr.translate(self.lang_idx)

    def at_job_end(self):
        '''Actions to take when a job has ended.'''
        # Notify the test widget that we're ending a job.
        self.test_widget.at_job_end()
        # Clean up the GUI after the job
        self.clear_face()

    def at_job_start(self):
        '''Actions to take when a job has started.'''
        # Notify the test widget that we're starting a job.
        self.test_widget.at_job_start()
        # Clean up the GUI before the job
        self.clear_face()

    # Now thread safe
    def test_error(self, test, message):
        msg = 'Test Error:\n%s'%(message)
        mb = MessageBox(self, tk.StringVar(self.parent, msg))
        self.after(0, mb.create)
        self.after(0, self.test_widget.test_idle)

    # Now thread safe
    def test_callback(self, test):
        self.test_widget.testUpdateQueue.put((test.id, test.state))

    # Now thread safe
    def procedure_callback(self, noFailures):
        # Use the after method to make calls thread safe
        if noFailures:
            self.after(0, self._procedure_callback_pass)
        else:
            self.after(0, self._procedure_callback_fail)

    def _procedure_callback_pass(self):
        self._set_smiley()
        self.test_widget.test_idle()

    def _procedure_callback_fail(self):
        self._set_frowny()
        self.test_widget.test_idle()

    def _set_smiley(self):
        self._clear_face()
        img = self.pass_image
        self.face_canvas.create_image(0, 0, image = img, anchor = tk.NW)

    def _set_frowny(self):
        self._clear_face()
        img = self.fail_image
        self.face_canvas.create_image(0, 0, image = img, anchor = tk.NW)

    def clear_face(self):
        # Use the after method to make this call thread safe
        self.after(0, self._clear_face)

    def _clear_face(self):
        # Clear the old pass/fail image
        for x in self.face_canvas.find_all():
            self.face_canvas.delete(x)

    def part_number_change(self, config):
        img = config.image
        # Delete anything on the canvas
        for x in self.part_canvas.find_all():
            self.part_canvas.delete(x)
        self.part_canvas.create_image(0, 0, image = img, anchor = tk.NW)
        self.part_canvas.configure(width = img.width(), height = img.height())
        self.clear_face()
        proc = import_module('procedures.' + config.get('procedure', 'commissioning'))
        self.procedure = proc.Procedure(self, config)
        self.test_widget.set_tests(self.procedure.get_tests())

    def verify(self):
        self.config_widget.update_config_files()
        self.config_widget.disable()
        self._clear_face()
        try:
            self.procedure.verify_start()
        except self.procedure.EquipmentFailure as e:
            msg = 'Equipment failure:\n\t%s\n\t%s'%(e.name, e.message)
            mb = MessageBox(self, tk.StringVar(self, msg))
            self.after(0, mb.create)
            # Clean up after the failure
            self._clear_face()
            img = self.fail_image
            self.face_canvas.create_image(0, 0, image = img, anchor = tk.NW)
            self.config_widget.enable()

    def verify_callback(self, test):
        self.clear_face()
        if test.state in ['running', 'pending']:
            return
        if test.state == 'pass':
            self.after(0, self._set_smiley)
        else:
            self.after(0, self._set_frowny)
        self.after(0, self.config_widget.enable)
        # Display the results to the user
        mb = MessageBox(self, tk.StringVar(self, test.message))
        self.after(0, mb.create)

    def pass_fail_query(self, test):
        self.pfq_test = test
        pfq = PassFailBox(self, tk.StringVar(self, test.message[self.lang_idx]),
                                self.pass_fail_query_callback)
        self.after(0, pfq.create)

    def pass_fail_query_callback(self, status):
        self.pfq_test.user_response(status)

def write_error_file(*args):
        # Ensure that the logs directory exists
        dir = 'logs/'
        if not os.path.exists(dir):
            os.makedirs(dir)
        time_str = time.strftime('%Y-%m-%d %H:%M:%S')
        err_file = open(dir + 'ProgramError.log', 'a')
        err_file.write('-'*79 + '\n' + time_str + '\n' + '-'*79 + '\n')
        err_file.write(traceback.format_exc())
        err_file.close()
        sys.exit()

class MessageBox(tkinter.simpledialog.Dialog):
    def __init__(self, parent, varMsg):
        '''Override the init so we can create the window after config.'''
        self.parent = parent
        self.message = varMsg

    def create(self):
        # Create the dialog window (blocking)
        tkinter.simpledialog.Dialog.__init__(self, self.parent)

    def buttonbox(self):
        box = tk.Frame(self)
        button = ttk.Button(box, command = self.ok, default = tk.ACTIVE,
                textvariable = self.parent.translatables['continue'])
        button.pack()
        self.bind("<Return>", self.ok)
        box.pack()

    def body(self, master):
        ttk.Label(master, textvariable = self.message).pack()

class PassFailBox(tkinter.simpledialog.Dialog):
    def __init__(self, parent, varMsg, callback):
        '''Override the init so we can create the window after config.'''
        self.parent = parent
        self.message = varMsg
        self.status = 'fail'
        self.callback = callback

    def create(self):
        # Create the dialog window (blocking)
        tkinter.simpledialog.Dialog.__init__(self, self.parent)
        self.callback(self.status)

    def buttonbox(self):
        box = tk.Frame(self)
        button1 = ttk.Button(box, command = self.ok, default = tk.ACTIVE,
                textvariable = self.parent.translatables['pass'])
        button1.pack(side = tk.LEFT, padx = 5, pady = 5)
        button2 = ttk.Button(box, command = self.cancel, default = tk.ACTIVE,
                textvariable = self.parent.translatables['fail'])
        button2.pack(side = tk.LEFT, padx = 5, pady = 5)
        #self.bind("<Return>", self.ok)
        box.pack()

    def body(self, master):
        ttk.Label(master, textvariable = self.message).pack()

    def apply(self):
        self.status = 'pass'

if __name__ == '__main__':
    try:
        root = tk.Tk()
        # Write any exceptions to an error file and exit the program
        tk.Tk.report_callback_exception = write_error_file
        # Load the icon
        root.wm_iconbitmap('images/CommissioningStation.ico')
        # Don't allow the window to be resized
        root.resizable(0,0)
        # Initialize the application
        app = CommissioningStation(root)
    except Exception as e:
        # Write any exceptions to an error file and exit the program
        write_error_file(e)
    # Start the main loop, catching and logging any unhandled exceptions
    try:
        app.mainloop()
    except Exception as e:
        # Write any exceptions to an error file and exit the program
        write_error_file(e)
