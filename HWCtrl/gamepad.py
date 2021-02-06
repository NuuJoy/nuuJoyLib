#!/usr/bin/python3


import os
import array
import struct
import fcntl
import threading
import multiprocessing


__version__ = (2021,1,26,'beta')


class gamepad_controller():
    '''
    GamePad controller input
    Purpose:
        Continuously read axes and button status of controller
    Example:
        jspad = gamepad_controller()
        jspad.keep_update(mode='process')
        state,lock,event = jspad.shareval,jspad.sharelock,jspad.stopevent
    Note:
        This class based from jdb's unlicense-code
        https://gist.github.com/rdb/8864666
    '''
    @staticmethod
    def get_device_name(fn):
        # Get the device name.
        with open(fn, 'rb') as jsdev:
            buf = array.array('B', [0] * 64)
            fcntl.ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
            js_name = buf.tobytes().rstrip(b'\x00').decode('utf-8')
        return js_name
    def __init__(self,device_name=None,shareval=None,sharelock=None,stopevent=None):
        # Pre-define joypad axes and button name mapping (itype,number)
        # Ipega9023, 
        mapping = {'ipega Extending Game controller':{(1, 0): 'a_button',
                                                      (1, 1): 'b_button',
                                                      (1, 3): 'x_button',
                                                      (1, 4): 'y_button',
                                                      (1, 6): 'trigL1_button',
                                                      (1, 7): 'trigR1_button',
                                                      (1, 8): 'trigL2_button',
                                                      (1, 9): 'trigR2_button',
                                                      (1,10): 'select_button',
                                                      (1,11): 'start_button',
                                                      (1,13): 'analogL_button',
                                                      (1,14): 'analogR_button',
                                                      (2, 0): 'analogL_xAxs',
                                                      (2, 1): 'analogL_yAxs',
                                                      (2, 2): 'analogR_xAxs',
                                                      (2, 3): 'analogR_yAxs',
                                                      (2, 4): 'trigR2_zAxs',
                                                      (2, 5): 'trigL2_zAxs',
                                                      (2, 6): 'digitPad_xAxs',
                                                      (2, 7): 'digitPad_yAxs',}}
        for fn in os.listdir('/dev/input'):
            if fn.startswith('js'):
                buff = '/dev/input/{}'.format(fn)
                name = self.get_device_name(buff)
                if ((name == device_name) if device_name else (name in mapping)):
                    self.device, self.devmap = buff, mapping[name]
                    break
        if not(hasattr(self,'device')):
            raise IOError('Device not found')
        self.shareval  = shareval if shareval else multiprocessing.Manager().dict()
        self.sharelock = sharelock if sharelock else multiprocessing.Lock()
        self.stopevent = stopevent if stopevent else multiprocessing.Event()
    def _keep_update_func(self):
        with open(self.device, 'rb') as jsdev:
            while not(self.stopevent.is_set()):
                time, value, itype, number = struct.unpack('IhBB', jsdev.read(8)) # <<<< script will be blocked here
                itype = itype%128
                if (itype,number) in self.devmap:
                    if (itype == 2):
                        value = value/32767.0
                    with self.sharelock:
                        self.shareval[self.devmap[(itype,number)]] = value
                        self.shareval['timestamp'] = time
    def keep_update(self,mode='normal'):
        if mode == 'normal':
            self._keep_update_func()
        elif mode == 'thread':
            thread = threading.Thread(target=self._keep_update_func,daemon=True,)
            thread.start()
            return thread
        elif mode == 'process':
            process = multiprocessing.Process(target=self._keep_update_func,daemon=True,)
            process.start()
            return process
        else:
            raise ValueError('Invalid input mode')

