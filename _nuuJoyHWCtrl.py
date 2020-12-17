#!/usr/bin/python3


import time


__version__ = (2020,12,17,'alpha')


'''
Note: Modules in this file was mainly tested on Raspberry Pi 4, SenseHat, etc.
   *** PLEASE CAREFULLY TEST IT BY YOURSELF AGAIN AND USE IT ON YOUR OWN RISK ***
Content
    class 
        constantRateAcquisition
'''


class constantRateAcquisition():

    '''
    Execute function with constant rate
    Purpose:
        Continouse acquire data from sensor, working with multiprocessing-share-value and threading-event
    Example:
        dataAcqs = constantRateAcquisition(func_list=(sense.get_accelerometer_raw,sense.get_gyroscope_raw,), # list of function
                                           output_list=(None,(shareValue,'value')), # list of share-value output (or other assignable object)
                                           rate_limit=100,  # 100 Hz
                                           stop_event=None, # no event stop used
                                           counter=loop)    # do acquisition with exact times
        dataAcqs.start_acquiring()
    '''

    class _nulloutput():
        def __setattr__(self,name,val):
            pass
    class _nullevent():
        def is_set(self):
            return False

    def __init__(self,func_list,output_list,rate_limit,stop_event=None,counter=0):
        self.func_list   = list(func_list) if isinstance(func_list,(list,tuple,)) else [func_list]
        self.output_list = list(output_list) if isinstance(output_list,(list,tuple,)) else [output_list]
        for i,output in enumerate(self.output_list):
            if not(output):
                self.output_list[i] = (self._nulloutput(),'null')
        self.time_limit  = 1.0/rate_limit
        self.stop_event  = stop_event if stop_event else self._nullevent()
        self.counter     = counter

    def start_acquiring(self):
        previous_timestamp = time.time()
        auto_compensate    = 0.0
        while not(self.stop_event.is_set()):
            current_timestamp  = time.time()
            timeinc_error      = (current_timestamp-previous_timestamp)-self.time_limit
            auto_compensate   += timeinc_error
            previous_timestamp = current_timestamp
            
            for func,(output,attr) in zip(self.func_list,self.output_list):
                setattr(output,attr,func())

            if self.counter:
                self.counter -= 1
                if not(self.counter):
                    break

            sleep_time = self.time_limit-(time.time()-current_timestamp)-auto_compensate
            time.sleep(max(0.0,sleep_time))
