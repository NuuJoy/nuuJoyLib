#!/usr/bin/python3


import os
import sys
import time
import math
import random
import string
import imaplib
import smtplib


__version__ = (2020,12,1,'alpha')


'''
Note: Modules in this file was sometime tested on WinX64, sometimes on Ubuntu,
      sometimes on Python27, sometimes on Python38, sometimes on Python39, etc.
   *** PLEASE CAREFULLY TEST IT BY YOURSELF AGAIN AND USE IT ON YOUR OWN RISK ***

Content
    class 
        waveformData
        externalScope
        logFileGen
        statlist
        autologdict
        AFM_matFileReader
        saveOpen
        emailobject
        emailReader
        emailWriter
    function
        randomText
        userDialog
'''


class waveformData(object):
    '''
    Waveform data structure 
        Purpose:
            Add some basic criteria calculation of signal as class property
        Note:
            "self.rawdata" can be data from "dso.GetScaledWaveformWithTimes" module
    '''
    def __init__(self,rawdata):
        self.rawdata = rawdata
    @property
    def xaxis(self): return self.rawdata[0]
    @property
    def xLim(self): return (min(self.xaxis),max(self.xaxis))
    @property
    def xRange(self): return max(self.xaxis)-min(self.xaxis)
    @property
    def yaxis(self): return self.rawdata[1]
    @property
    def yLim(self): return (min(self.yaxis),max(self.yaxis))
    @property
    def yRange(self): return max(self.yaxis)-min(self.yaxis)
    @property
    def dataPoint(self): return len(self.yaxis)
    @property
    def samplingRate(self): return self.dataPoint/self.xRange
    @property
    def pointXY(self): return tuple((i,j) for (i,j) in zip(self.xaxis,self.yaxis))
    @property
    def mean(self): return sum(self.yaxis)/self.dataPoint
    @property
    def rms(self): return math.sqrt(sum(tuple(val**2 for val in self.yaxis))/self.dataPoint) if self.dataPoint else 0


class externalScope(object):
    '''
    Lecroy Scope Control
        Purpose:
            Work as wrapper of "LeCroyDSO" basic-function
        Example:
            with externalScope(scopeAddr,('C1','C2')) as scope:
                scope.setTimeScale(timeScale)
                scope.setVoltScale(voltScale)
                scope.setTrigger('AUTO','C1',0.0)
                scope.waitForScope()
                signalWaveform = scope.getWaveform('C2')
    '''
    def __init__(self,IPAddr,channel=('C1','C2','C3','C4')):
        self.LeCroyDSO = __import__('LeCroyDSO')
        self.channel   = []
        self.naptime   = 0.050
        self.IPAddr    = IPAddr
        self.dso       = self.LeCroyDSO.LeCroyDSO(connection=self.IPAddr,NewDSOSignals=None)
        for ch in ('C1','C2','C3','C4'):
            if ch in channel:
                self.channel.append(ch)
                self.dso.WriteString('{}:TRA ON'.format(ch))
            else:
                self.dso.WriteString('{}:TRA OFF'.format(ch))
            self.waitForScope()
        gridNum = ('SINGLE','DUAL','QUAD','QUAD')
        self.dso.WriteString('GRID {}'.format(gridNum[len(self.channel)-1]))
    def connect(self):
        if self.dso.dso.MakeConnection(self.IPAddr): self.dso.DeviceClear()
        else: raise self.LeCroyDSO.LeCroyDSOError('Cant connect to scope')
    def disconnect(self):
        self.dso.Disconnect()
    def waitForScope(self,naptime=0.1):
        time.sleep(naptime)
        self.dso.WriteString('*IDN?')
        self.dso.WriteString('*OPC?')
    def setTimeScale(self,sec_per_div):
        self.dso.WriteString('TIME_DIV {:0.12f}'.format(sec_per_div))
    def setVoltScale(self,volt_per_div):
        self.dso.WriteString('VOLT_DIV {:0.12f}'.format(volt_per_div))
    def setTrigger(self,*setinput):
        if not(isinstance(setinput,(tuple,list))): setinput = (setinput,)
        for eachInput in setinput:
            if eachInput in ('AUTO','NORM','SINGLE','STOP'):
                self.dso.WriteString('TRIG_MODE {}'.format(eachInput))
            elif eachInput in ('C1','C2','C3','C4'):
                self.dso.WriteString('TRIG_SELECT EDGE,SR,{}'.format(eachInput))
            elif isinstance(eachInput,(int,float,)):
                self.dso.WriteString('TRIG_LEVEL {}V'.format(eachInput))
    def getWaveform(self,channel):
        return waveformData(self.dso.GetScaledWaveformWithTimes(channel))
    def __enter__(self):
        self.connect()
        return self
    def __exit__(self ,type, value, traceback):
        self.disconnect()


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
        self._keys = OrderedDict()
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
            - "statistics" module is referred but if its not available, class will try to use "numpy" instead
    '''
    try:
        statistics = __import__('statistics')
        @property
        def average(self): return self.statistics.mean(self) if len(self) >= 1 else None
        @property
        def median(self): return self.statistics.median(self) if len(self) >= 1 else None
        @property
        def mode(self): return self.statistics.mode(self) if len(self) >= 1 else None
        @property
        def stdev(self): return self.statistics.stdev(self) if len(self) >= 2 else None
        @property
        def variance(self): return self.statistics.variance(self) if len(self) >= 2 else None
    except:
        try:
            numpy = __import__('numpy')
            @property
            def average(self): return self.numpy.mean(self) if len(self) >= 1 else None
            @property
            def median(self): return self.numpy.median(self) if len(self) >= 1 else None
            @property
            def mode(self): return None
            @property
            def stdev(self): return self.numpy.std(self,ddof=1) if len(self) >= 2 else None
            @property
            def variance(self): return self.numpy.var(self,ddof=1) if len(self) >= 2 else None
        except:
            pass
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
               'cov     : {}\n'.format(self.cov)+\
               'member  : {}'.format(self.member)
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


class autologdict(object):
    '''
    Auto logging "results" instance
        Purpose : 
            record wite-results-instance input, can replace 'results' instance at a beginning of script as...
            results = autologdict(results). Anyway, standalone-use is also available.
    '''
    def __init__(self,witeResults=None):
        self._keys = OrderedDict()
        self._witeResults = witeResults
    def __setitem__(self,name,value):
        if self._witeResults:
            self._witeResults[name] = value
        if not name in self._keys:
            self._keys.update({name:statlist()})
        self._keys[name].append(value)
    def __getitem__(self,name):
        return self._keys[name]
    def __repr__(self):
        outputString = ''
        for key,val in self._keys.items():
            outputString += '-------- key: {}\n'.format(key) + str(val) + '\n'
        return outputString[:-1]


class AFM_matFileReader(object):
    '''
    AFM-mat-file reader
        Purpose:
            Read AFM .mat file and extend form calculation
        Note:
            This class use "scipy.io" and "scipy.ndimage" for calculation
    '''
    def __init__(self,filepath):
        self.scipy_io      = __import__('scipy.io', fromlist=('object',))
        self.scipy_ndimage = __import__('scipy.ndimage', fromlist=('object',))
        self.numpy         = __import__('numpy', fromlist=('object',))
        self._matfile = self.scipy_io.loadmat(filepath)
        self._factor = [float(val) for val in self._matfile['matdata'][0][1:]]
        self._rawz = self._matfile['matdata'][0][0]
    def _genXYAxis(self):
        if not (hasattr(self,'_xaxis') and hasattr(self,'_yaxis')):
            self._xaxis = tuple(self.xFac*i for i in range(self.xNum))
            self._yaxis = tuple(self.yFac*i for i in range(self.yNum))
    def _genXYMesh(self):
        self._genXYAxis()
        if not (hasattr(self,'_xmesh') and hasattr(self,'_ymesh')):
            self._xmesh, self._ymesh = self.numpy.meshgrid(self._xaxis,self._yaxis)
    def selfFlip(self):
        self._genXYAxis()
        self._xaxis, self._yaxis = self._yaxis, self._xaxis
        self._rawz = self._rawz.transpose([1,0])
    @property
    def xNum(self):
        return self._matfile['matdata'][0][0].shape[0]
    @property
    def yNum(self):
        return self._matfile['matdata'][0][0].shape[1]
    @property
    def xFac(self):
        return max(self._factor) if self.xNum == min(self.xNum,self.yNum) else min(self._factor)
    @property
    def yFac(self):
        return max(self._factor) if self.yNum == min(self.xNum,self.yNum) else min(self._factor)
    @property
    def x_axis(self):
        self._genXYAxis()
        return self._xaxis
    @property
    def y_axis(self):
        self._genXYAxis()
        return self._yaxis
    @property
    def x_mesh(self):
        self._genXYMesh()
        return self._xmesh.copy()
    @property
    def y_mesh(self):
        self._genXYMesh()
        return self._ymesh.copy()
    def z_data(self,filter=None,filter_n=5):
        if filter=='median':
            return self.scipy_ndimage.median_filter(self._rawz,size=filter_n)
        elif filter=='gaussian':
            return self.scipy_ndimage.gaussian_filter(self._rawz,sigma=filter_n)
        else:
            return self._rawz.copy()


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


class emailobject():
    '''
    ***Many thing to revise for this stupid email scraping***
        Purpose:
            Scrap email data from plain text
    '''
    def __init__(self,rawmessage):
        print(rawmessage)
        self._rawmessage = rawmessage
        self.content = []
        contentStart = False
        for line in self._rawmessage.decode().split('\r\n'):
            if not(contentStart):
                if line.startswith('Date: '):
                    self.datetime = line.replace('Date: ','')
                elif line.startswith('Subject: '):
                    self.subject = line.replace('Subject: ','')
                elif line.startswith('From: '):
                    self.from_email = line.split('<')[-1].split('>')[0]
                elif line == '':
                    contentStart = True
            else:
                self.content.append(line)
        self.content = self.content[:-1]
    def __repr__(self):
        return 'From   : {}\n'.format(self.from_email) + \
               'Date   : {}\n'.format(self.datetime) + \
               'Subject: {}\n'.format(self.subject) + \
               '\n'.join(self.content)


class emailReader():
    '''
    Get all/unread email from server using 'imaplib'
        Purpose:
            Get email that its subject match 'mark' arrtribute, leave other unseen
        Example:
            mail_reader = emailReader('myemail@someprovider.com','mypassword',mark='identicaltext')
            for email in mail_reader.emailList:
                print(email)
    '''
    def __init__(self,user,psswrd,mailbox='unread',mark=''):
        self.emailList = []
        mailbox = {'all':'ALL','unread':'(UNSEEN)'}[mailbox]
        with imaplib.IMAP4_SSL('imap.gmail.com') as server:
            server.login(user,psswrd)
            server.select(mailbox='INBOX',readonly=(True if not(mark) else False))
            _, data = server.search(None,mailbox)
            for num in data[0].split():
                _, data = server.fetch(num,'(RFC822)')
                mailobj = emailObject(data[0][1])
                if mark in mailobj.subject:
                    self.emailList.append(mailobj)
                else:
                    server.store(num,'-FLAGS','(\\SEEN)')


class emailWriter():
    '''
    Send email using 'smtplib'
        Purpose:
            Send a minimal email body to server
        Example:
            with emailWriter('myemail@someprovider.com','mypassword') as mail_writer:
                mail_writer.sendmail('sendtosomeone@someprovider.com','mailsubject','mailbody')
                
    '''
    def __init__(self,user,psswrd):
        self.user   = user
        self.psswrd = psswrd
    def __enter__(self):
        self.server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        self.server.ehlo()
        self.server.login(self.user, self.psswrd)
        return self
    def __exit__(self,*args):
        self.server.close()
    def sendmail(self,to_email,subject,content):
        self.server.sendmail(self.user,to_email,'Subject: {}\n\n{}'.format(subject,content))


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
    if sys.version_info > (3,):
        tkinter    = __import__('tkinter', fromlist=('object',))
        filedialog = __import__('tkinter.filedialog', fromlist=('object',))
    else:
        tkinter    = __import__('Tkinter', fromlist=('object',))      # Python2
        filedialog = __import__('tkFileDialog', fromlist=('object',)) # Python2
    if not title:
        title = dialogType
    if not initialdir:
        initialdir = os.path.dirname(os.path.realpath(__file__)) if '__file__' in locals() else os.getcwd()
    root = tkinter.Tk()
    root.withdraw()
    if dialogType == 'openfile':
        return filedialog.askopenfilename(title=title,multiple=multiple,initialdir=initialdir,filetypes=filetypes,)
    elif dialogType == 'savefile':
        return filedialog.asksaveasfilename(title=title,initialdir=initialdir,filetypes=filetypes,)
    elif dialogType == 'opendir':
        return filedialog.askdirectory(title=title,initialdir=initialdir,)
    else:
        raise ValueError('Invalid [dialogType]')

