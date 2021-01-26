#!/usr/bin/python3


import time
import math
import LeCroyDSO


__version__ = (2021,1,26,'beta')


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
        self.channel   = []
        self.naptime   = 0.050
        self.IPAddr    = IPAddr
        self.dso       = LeCroyDSO.LeCroyDSO(connection=self.IPAddr,NewDSOSignals=None)
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
        else: raise LeCroyDSO.LeCroyDSOError('Cant connect to scope')
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

