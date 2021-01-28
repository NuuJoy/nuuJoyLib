#!/usr/bin/python3


import time
import queue
import threading
import multiprocessing
import multiprocessing.queues


__version__ = (2021,1,26,'beta')


class constantRateAcquisition():

    '''
    Execute function with constant rate
    Purpose:
        Continouse acquire data from sensor, working with multiprocessing-share-value and threading-event
    Example:
        dataAcqs = constantRateAcquisition(func_list=(sense.get_accelerometer_raw,sense.get_gyroscope_raw,), # list of function
                                           output_list=(None,(shareValue,'value'),(shareValue,None)), # list of share-value output (or other assignable object)
                                           rate_limit=100,  # 100 Hz
                                           stop_event=None, # no event stop used
                                           counter=loop)    # do acquisition with exact times
        dataAcqs.start_acquiring()
    '''

    class _nulloutput():
        def __setattr__(self,name,val):
            pass

    def __init__(self,func_list,output_list,rate_limit,stop_event=None,hw_lock=None,sv_lock=None,counter=None):
        if isinstance(func_list,(list,tuple,)):
            self.func_list = list(func_list)
        else:
            raise ValueError('"func_list should be "list" or "tuple"')
        if isinstance(output_list,(list,tuple,)):
            self.output_list = list(output_list)
        else:
            raise ValueError('"output_list should be "list" or "tuple"')
        self.stop_event  = stop_event if stop_event else multiprocessing.Event()
        self.hw_lock     = hw_lock if hw_lock else multiprocessing.Lock() # hardware lock
        self.sv_lock     = sv_lock if sv_lock else multiprocessing.Lock() # share-value lock
        for i,output in enumerate(self.output_list):
            if output is None:
                self.output_list[i] = (self._nulloutput(),'null')
            elif len(output) != 2:
                raise ValueError('Invalid "output_list", sholde be "None" or "2-element List"')
        print(self.output_list)
        self.time_limit  = 1.0/rate_limit
        
        self.counter     = counter

    def start_acquiring(self):
        previous_timestamp = time.time()
        auto_compensate    = 0.0
        while not(self.stop_event.is_set()):
            try:
                if not(self.counter is None):
                    if self.counter:
                        self.counter -= 1
                    else:
                        break
                current_timestamp  = time.time()
                timeinc_error      = (current_timestamp-previous_timestamp)-self.time_limit
                auto_compensate   += timeinc_error
                previous_timestamp = current_timestamp
                for func,(output,attr) in zip(self.func_list,self.output_list):
                    with self.hw_lock:
                        func_output = func()
                    with self.sv_lock:
                        if isinstance(output,(multiprocessing.queues.Queue,)):
                            if attr:
                                output.put({attr:func_output})
                            elif isinstance(func_output,(dict,)):
                                for key,val in func_output.items():
                                    if output.full():
                                        output.get()
                                    output.put({key:val},False)
                            else:
                                raise ValueError('Invalid output_list: "func_output" should be dict if "attr" is None')
                        else:
                            if attr:
                                setattr(output,attr,func_output)
                            elif isinstance(func_output,(dict,)):
                                for key,val in func_output.items():
                                    if not key in output:
                                        output[key] = []
                                    output[key] += [val]
                            else:
                                raise ValueError('Invalid output_list: "func_output" should be dict if "attr" is None')
                sleep_time = self.time_limit-(time.time()-current_timestamp)-auto_compensate
                time.sleep(max(0.0,sleep_time))
            except Exception as err:
                print('Exception detect: ', err)

    def start_acquiring_thread(self):
        thread = threading.Thread(target=self.start_acquiring,daemon=True,)
        thread.start()
        return thread

    def start_acquiring_multiprocess(self):
        process = multiprocessing.Process(target=self.start_acquiring,daemon=True,)
        process.start()
        return process

