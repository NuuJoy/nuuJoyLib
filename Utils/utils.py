#!/usr/bin/python3


import os
import sys
import time
import random
import string
import statistics
import collections
from configparser import ConfigParser
import subprocess
from io import BytesIO

try: # tkinter import exception for using in Pythonista
    import tkinter
    import tkinter.filedialog
except ModuleNotFoundError:
    print('Fail importing tkinter')


__version__ = (2024,2,29,'beta')


class logFileGen(object):
    '''
    Simple Log-File generator
        Purpose:
            Making and writing simple row-base log file
        Example:
            def blackbox(val): return (2.0*val-17.0)**-2.0
            with logFileGen(columns=('test','input','output',),activelyReport=True) as mylog:
                for testname,testval in {'testA':(1,2,3,4,5),'testB':(-1,-2,-3,-4,-5)}.items():
                    for testinput in testval:
                        mylog['test']   = testname
                        mylog['input']  = testinput
                        mylog['output'] = blackbox(testinput)
                        mylog.saveRow()
            print(mylog)
    '''
    def __init__(self,columns,activelyReport=False,printOut=False,logFilePath=None):
        self._keys = collections.OrderedDict()
        for name in columns:
            if isinstance(name,str):
                self._keys.update({name:None})
        self._report   = []
        self._actvRprt = activelyReport
        self._printOut = printOut
        if logFilePath: self.setSaveFilePath(logFilePath)
    def __setitem__(self,name,value):
        if name in self._keys:
            self._keys[name] = value
    def __getitem__(self,name):
        return self._keys[name]
    def __repr__(self):
        return self.header + '\n' + '\n'.join(self._report)
    def __enter__(self):
        return self
    def __exit__(self ,type, value, traceback):
        if not(self._actvRprt) and hasattr(self,'logFilePath'): self._outputAllReport()
    def _outputAllReport(self):
        with open(self._logFilePath,'a') as file:
            file.write('\n'.join(self._report)+'\n')
    @property
    def header(self):
       return 'dateTime,' + ', '.join([key for key in self._keys.keys()])
    @property
    def curTime(self):
        return time.strftime('%Y%m%d-%H:%M:%S',time.localtime())
    def setSaveFilePath(self,logFilePath):
        self._logFilePath = logFilePath
        if not os.path.exists(self._logFilePath):
            if not os.path.exists(os.path.dirname(self._logFilePath)):
                os.makedirs(os.path.dirname(self._logFilePath))
            with open(self._logFilePath,'w') as file:
                file.write(self.header+'\n')
    def saveRow(self):
        reportStr = self.curTime + ', ' + ', '.join([str(val) for val in self._keys.values()])
        if self._actvRprt:
            self._report = [reportStr]
            with open(self._logFilePath,'a') as file:
                file.write(self._report[-1]+'\n')
        else:
            self._report.append(reportStr)
        if self._printOut: print(self._report[-1])


class statlist(list):
    '''
    Statistic and opration extending list
        Purpose:
            add statistic-calculation and basic-array-operation to build-in list
        Note:
            - Elements in this list should be numerical, any tuple/list will be unziped to numeric
    '''
    @property
    def average(self):
        return statistics.mean(self) if len(self) >= 1 else None
    @property
    def median(self):
        return statistics.median(self) if len(self) >= 1 else None
    @property
    def mode(self):
        try:
            return statistics.mode(self) if len(self) >= 1 else None
        except statistics.StatisticsError:
            return None
    @property
    def stdev(self):
        return statistics.stdev(self) if len(self) >= 2 else None
    @property
    def variance(self): 
        return statistics.variance(self) if len(self) >= 2 else None
    @property
    def cov(self):
        return (self.stdev/self.average) if ((len(self) >= 2)and(self.average != 0)) else None
    @property
    def member(self):
        return super(statlist,self).__repr__()
    def append(self,val):
        if isinstance(val,(int,float,)):
            val = [val]
        for eachval in val:
            if isinstance(eachval,(int,float,))and not(type(eachval) is bool):
                super(statlist,self).append(eachval)
    def __str__(self):
        return 'count   : {}\n'.format(len(self))+\
               'mean    : {}\n'.format(self.average)+\
               'median  : {}\n'.format(self.median)+\
               'mode    : {}\n'.format(self.mode)+\
               'stdev   : {}\n'.format(self.stdev)+\
               'variance: {}\n'.format(self.variance)+\
               'cov     : {}\n'.format(self.cov)
    def __pos__(self):
        return statlist([eachSelf for eachSelf in self])
    def __neg__(self):
        return statlist([-eachSelf for eachSelf in self])
    def __add__(self,other,sub=False):
        if isinstance(other,(int,float,)):
            return statlist([eachSelf+(1 if not sub else -1 )*other for eachSelf in self])
        elif isinstance(other,(tuple,list,)):
            if len(self) == len(other):
                return statlist([eachSelf+(1 if not sub else -1 )*eachOther for eachSelf,eachOther in zip(self,other)])
            else:
                return ValueError('self,other must return equal __len__')
        else:
            return NotImplemented
    def __radd__(self,other):
        return self.__add__(other)
    def __iadd__(self,other):
        newVal = self.__add__(other)
        for i,eachVal in enumerate(newVal):
            self[i] = eachVal
        return True
    def __sub__(self,other):
        return self.__add__(other,sub=True)
    def __rsub__(self,other):
        return self.__add__(other,sub=True)
    def __isub__(self,other):
        newVal = self.__add__(other,sub=True)
        for i,eachVal in enumerate(newVal):
            self[i] = eachVal
        return True
    def __mul__(self,other):
        if isinstance(other,(int,float,)):
            return statlist([eachElement*other for eachElement in self])
        elif isinstance(other,(tuple,list,)):
            if len(self) == len(other):
                return statlist([eachSelf*eachOther for eachSelf,eachOther in zip(self,other)])
            else:
                return ValueError('self,other must return equal __len__')
        else:
            return NotImplemented
    def __rmul__(self,other):
        return self.__mul__(other)
    def __imul__(self,other):
        newVal = self.__mul__(other)
        for i,eachVal in enumerate(newVal):
            self[i] = eachVal
        return True
    def __getitem__(self,key):
        return statlist(super(statlist,self).__getitem__(key))


class saveOpen(object):
    '''
    Open log-file with folder-exist check
        Purpose:
            Open log-file with folder-exist check
    '''
    def __init__(self,filePath,mode,header):
        self._filePath = filePath
        self._mode     = mode
        if not os.path.exists(self._filePath):
            self._header = header + '\n'
            if not os.path.exists(os.path.dirname(self._filePath)):
                os.makedirs(os.path.dirname(self._filePath))
        else:
            self._header = None
    def __enter__(self):
        self._filehandle = open(self._filePath,self._mode)
        if self._header: self._filehandle.write(self._header)
        return self._filehandle
    def __exit__(self ,type, value, traceback):
        self._filehandle.close()


class stopWatch():
    '''
    minimal stop watch
        Purpose:
            loop time logging
        Example:
            mylog = stopWatch()
            mylog.start() # optional
            for _ in range(10):
                <<< Do something here >>>
                mylog.lap()
            print(mylog.fps)
    '''
    def __init__(self,buffer=0):
        self.buffer   = buffer
        self._timeref = None
        self._timelog = statlist()
    def start(self):
        self._timeref = time.time()
    def lap(self):
        if not self._timeref:
            self.start()
        else:
            self._timelog.append(time.time())
            if self.buffer:
                self._timelog = self._timelog[(-self.buffer):]
    @property
    def time_raw(self):
        return self._timelog - self._timeref
    @property
    def time_inc(self):
        return self.time_raw[1:] - self.time_raw[:-1]
    @property
    def fps(self):
        return statlist([1.0/(inc) for inc in self.time_inc])
    def __repr__(self):
        return 


def randomText(length=8):
    '''
    Return random n length of string
    '''
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def userDialog(dialogType,title=None,multiple=False,initialdir=None,filetypes=(('all files','*.*'),)):
    '''
    File choosing dialog
    Purpose:
        Wrapper of tkinter open-file, save-file, open-dir for easier using
    '''
    if not title:
        title = dialogType
    if not initialdir:
        initialdir = os.path.dirname(os.path.realpath(__file__)) if '__file__' in locals() else os.getcwd()
    root = tkinter.Tk()
    root.withdraw()
    if dialogType == 'openfile':
        return tkinter.filedialog.askopenfilename(title=title,multiple=multiple,initialdir=initialdir,filetypes=filetypes,)
    elif dialogType == 'savefile':
        return tkinter.filedialog.asksaveasfilename(title=title,initialdir=initialdir,filetypes=filetypes,)
    elif dialogType == 'opendir':
        return tkinter.filedialog.askdirectory(title=title,initialdir=initialdir,)
    else:
        raise ValueError('Invalid [dialogType]')


class config_reader(dict):
    class _none_dict(dict):
        def __missing__(self, misskey):
            for key in self.keys():
                if key.casefold() == misskey.casefold():
                    return self[key]
            return None

    @staticmethod
    def _strip(text):
        try:
            text = text[:text.index(';')].strip()  # remove inline comment
        except ValueError:
            pass
        return text

    @staticmethod
    def _tryeval(text):
        try:
            text = eval(text)
        except Exception:
            pass
        return text

    def __init__(self, filepath='config.ini', tryeval=False, strip=True, case=False):
        cnfg = ConfigParser()
        if case:
            cnfg.optionxform = str
        cnfg.read(filepath)
        _tryeval = self._tryeval if tryeval else lambda x: x
        _strip = self._strip if strip else lambda x: x

        super().__init__({
            section: self._none_dict({
                key: _tryeval(_strip(val))
                for key, val in cnfg[section].items()
            }) for section in cnfg.sections()
        })

    def __missing__(self, misskey):
        for key in self.keys():
            if key.casefold() == misskey.casefold():
                return self[key]
        return self._none_dict()

    def __str__(self):
        output = ''
        for section in self.keys():
            output += f'{section}\n'
            for key, val in self[section].items():
                output += f'    {key}: {val} <{val.__class__.__name__}>\n'
        return output


class with_retry():
    '''
    note: thisdecorator need to invoke __call__ at initial,
    alway decorate with initial argument(s), DONT decorate with bare function

    example:

    @with_retry(retry_max=3)
    def my_func():
        ...run something...

    class mycls():
        @with_retry(retry_max=3)
        def my_method():
            ...run something...
    '''
    def __init__(self, retry_max, delay=0.0, exceptions=(Exception,)):
        self._retry_max = retry_max
        self._delay = delay
        self._exceptions = exceptions

    def __call__(self, *args):
        def inner_func(inst=None, *args, **kwargs):
            for retry in range(1, self._retry_max + 1):
                try:
                    if inst is None:
                        return self._func(*args, **kwargs)
                    else:
                        return self._func(inst, *args, **kwargs)
                except self._exceptions as err:
                    if retry >= self._retry_max:
                        raise err
                    time.sleep(self._delay)
        self._func = args[0]
        return inner_func


class CLI_Popen():
    def __init__(self, target, cwd=None):
        self._target = target
        if cwd is None:
            cwd = os.path.dirname(self._target)
        self._cwd = cwd

    def __enter__(self):
        self.proc = subprocess.Popen(self._target, cwd=self._cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        while self.proc.poll() is None:
            self.proc.terminate()

    def read_until(self, expect):
        with BytesIO() as buff:
            while not (output := buff.getvalue()).endswith(expect):
                buff.write(self.proc.stdout.read(1))
        return output

    def write(self, bytesdata):
        self.proc.stdin.write(bytesdata)
        self.proc.stdin.write(b'\n')
        self.proc.stdin.flush()
