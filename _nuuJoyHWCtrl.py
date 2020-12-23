#!/usr/bin/python3


import time
import logging
import threading

import smbus


__version__ = (2020,12,23,'alpha')


'''
Note: Modules in this file was mainly tested on Raspberry Pi 4, SenseHat, etc.
   *** PLEASE CAREFULLY TEST IT BY YOURSELF AGAIN AND USE IT ON YOUR OWN RISK ***
Content
    class 
        constantRateAcquisition
        IMUSensor_MPU6050
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

    def __init__(self,func_list,output_list,rate_limit,stop_event=None,hw_lock=None,counter=0):
        self.func_list   = list(func_list) if isinstance(func_list,(list,tuple,)) else [func_list]
        self.output_list = list(output_list) if isinstance(output_list,(list,tuple,)) else [output_list]
        self.stop_event  = stop_event if stop_event else threading.Event()
        self.hw_lock     = hw_lock if hw_lock else threading.Lock()
        for i,output in enumerate(self.output_list):
            if not(output):
                self.output_list[i] = (self._nulloutput(),'null')
        self.time_limit  = 1.0/rate_limit
        
        self.counter     = counter

    def start_acquiring(self):
        previous_timestamp = time.time()
        auto_compensate    = 0.0
        while not(self.stop_event.is_set()):
            try:
                current_timestamp  = time.time()
                timeinc_error      = (current_timestamp-previous_timestamp)-self.time_limit
                auto_compensate   += timeinc_error
                previous_timestamp = current_timestamp
                
                for func,(output,attr) in zip(self.func_list,self.output_list):
                    with self.hw_lock:
                        setattr(output,attr,func())

                if self.counter:
                    self.counter -= 1
                    if not(self.counter):
                        break

                sleep_time = self.time_limit-(time.time()-current_timestamp)-auto_compensate
                time.sleep(max(0.0,sleep_time))
            except Exception as err:
                print('Exception detect: ', err)


class IMUSensor_MPU6050:

    '''
    This class was modified from https://github.com/m-rtijn/mpu6050/blob/master/mpu6050/mpu6050.py
    ---- Original script declaration ---
        This program handles the communication over I2C
        between a Raspberry Pi and a MPU-6050 Gyroscope / Accelerometer combo.
        Made by: MrTijn/Tijndagamer
        Released under the MIT License
        Copyright (c) 2015, 2016, 2017 MrTijn/Tijndagamer
    Also IMUSensor_MPU6050 class this script will leverage MIT License from original
    Purpose:
        MPU6050 sensor acquisition
    Example:
        print('Initial sensor ----')
        sensor = IMUSensor_MPU6050()
        sensor.accelerometer_mode = 'ACCL_16G' # set accelerometer mode
        sensor.gyroscope_mode     = 'GYRO_250DEG' # set gyroscope mode
        sensor.lowpassfilter_mode = 'ACCL_94HZ_GYRO_98HZ' # set low-pass filter
        print('accelerometer_mode: ',sensor.accelerometer_mode) # accelerometer getter
        print('gyroscope_mode    : ',sensor.gyroscope_mode) # gyroscope mode getter
        print('lowpassfilter_mode: ',sensor.lowpassfilter_mode) # low-pass filter mode getter
        print('temperature data read: ',sensor.get_temperature()) # temperature sensor data
        print('accelerometer data read: ',sensor.get_accl_data()) # accelerometer sensor data
        print('gyroscope data read: ',sensor.get_gyro_data()) # gyroscope sensor data
    '''

    def __init__(self,device_addr=0x68,
                      lowpass_mode='ACCL_184HZ_GYRO_188HZ',
                      accl_mode='ACCL_2G',
                      gyro_mode='GYRO_250DEG',):
        logging.debug('enter __init__')

        # Global Variables
        self.gravity_ms2 = 9.80665
        self.device_addr = device_addr
        self.bus         = smbus.SMBus(1)

        # Power config
        self.PWR_MGMT_1 = 0x6B
        self.PWR_MGMT_2 = 0x6C
        self.bus.write_byte_data(self.device_addr, self.PWR_MGMT_1, 0x00)
        self.bus.write_byte_data(self.device_addr, self.PWR_MGMT_2, 0x00)

        # Low-pass filter config
        self.lowpass_config_addr = 0x1A
        self.lowpass_bandwidth = {'ACCL_260HZ_GYRO_256HZ':{'regis':0x00},
                                  'ACCL_184HZ_GYRO_188HZ':{'regis':0x01},
                                  'ACCL_94HZ_GYRO_98HZ':{'regis':0x02},
                                  'ACCL_44HZ_GYRO_42HZ':{'regis':0x03},
                                  'ACCL_21HZ_GYRO_20HZ':{'regis':0x04},
                                  'ACCL_10HZ_GYRO_10HZ':{'regis':0x05},
                                  'ACCL_5HZ_GYRO_5HZ':{'regis':0x06},}
        # Gyroscope config
        self.gyro_config_addr = 0x1B
        self.gyro_mode = {'GYRO_250DEG': {'regis':0x00,'scale':131.0},
                          'GYRO_500DEG': {'regis':0x08,'scale':65.5},
                          'GYRO_1000DEG':{'regis':0x10,'scale':32.8},
                          'GYRO_2000DEG':{'regis':0x18,'scale':16.4},}
        # Accelerometer config
        self.accl_config_addr = 0x1C
        self.accl_mode = {'ACCL_2G': {'regis':0x00,'scale':16384.0},
                          'ACCL_4G': {'regis':0x08,'scale':8192.0},
                          'ACCL_8G': {'regis':0x10,'scale':4096.0},
                          'ACCL_16G':{'regis':0x18,'scale':2048.0},}
        # Sensor reading address
        self.TEMP_OUT    = (0x41,0x42,)
        self.GYRO_XOUT0  = (0x43,0x44,)
        self.GYRO_YOUT0  = (0x45,0x46,)
        self.GYRO_ZOUT0  = (0x47,0x48,)
        self.ACCEL_XOUT0 = (0x3B,0x3C,)
        self.ACCEL_YOUT0 = (0x3D,0x3E,)
        self.ACCEL_ZOUT0 = (0x3F,0x40,)
        # Get current setting
        self.accl_scale = self.accl_mode[self.accelerometer_mode]['scale']
        self.gyro_scale = self.gyro_mode[self.gyroscope_mode]['scale']

        # Perform self functional check
        if not(self._self_functional_check()):
            raise IOError('self functional check: Fail')

    def read_i2c_value(self, registers):
        logging.debug('enter read_i2c_value')
        high,low  = tuple(self.bus.read_byte_data(self.device_addr, regis) for regis in registers)
        value = (high << 8) + low
        return value if (value < 0x8000) else (-((65535-value) + 1))

    def _get_sensor_mode(self,config_addr,list_mode):
        logging.debug('enter _get_sensor_mode (addr 0x{:02x})'.format(config_addr))
        raw_data = self.bus.read_byte_data(self.device_addr, config_addr)
        mode = None
        for key,val in list_mode.items():
            if raw_data == val['regis']:
                mode = key
                break
        return mode

    def _set_sensor_mode(self,config_addr,regis_mode):
        logging.debug('enter _set_sensor_mode (addr 0x{:02x}, regis 0x{:02x})'.format(config_addr,regis_mode))
        self.bus.write_byte_data(self.device_addr, config_addr, 0x00)
        self.bus.write_byte_data(self.device_addr, config_addr, regis_mode)

    @property
    def accelerometer_mode(self):
        logging.debug('enter accelerometer_mode getter')
        return self._get_sensor_mode(self.accl_config_addr,self.accl_mode)
    @accelerometer_mode.setter
    def accelerometer_mode(self,mode):
        logging.debug('enter accelerometer_mode setter')
        self._set_sensor_mode(self.accl_config_addr, self.accl_mode[mode]['regis'])

    @property
    def gyroscope_mode(self):
        logging.debug('enter gyroscope_mode getter')
        return self._get_sensor_mode(self.gyro_config_addr,self.gyro_mode)
    @gyroscope_mode.setter
    def gyroscope_mode(self,mode):
        logging.debug('enter gyroscope_mode setter')
        self._set_sensor_mode(self.gyro_config_addr, self.gyro_mode[mode]['regis'])

    @property
    def lowpassfilter_mode(self):
        logging.debug('enter lowpassfilter_mode getter')
        return self._get_sensor_mode(self.lowpass_config_addr,self.lowpass_bandwidth)
    @lowpassfilter_mode.setter
    def lowpassfilter_mode(self,mode):
        logging.debug('enter lowpassfilter_mode setter')
        self._set_sensor_mode(self.lowpass_config_addr, self.lowpass_bandwidth[mode]['regis'])

    def get_temperature(self):
        logging.debug('enter get_temperature')
        raw_temp = self.read_i2c_value(self.TEMP_OUT)
        actual_temp = (raw_temp / 340.0) + 36.530001
        logging.debug('from get_temperature temp:{}'.format(actual_temp))
        return actual_temp

    def get_accl_data(self, g = False):
        logging.debug('enter get_accl_data')
        x = self.read_i2c_value(self.ACCEL_XOUT0)/self.accl_scale
        y = self.read_i2c_value(self.ACCEL_YOUT0)/self.accl_scale
        z = self.read_i2c_value(self.ACCEL_ZOUT0)/self.accl_scale
        logging.debug('from get_accl_data x:{}, y:{}, z:{}'.format(x,y,z))
        return {'x': x, 'y': y, 'z': z}

    def get_gyro_data(self, g = False):
        logging.debug('enter get_gyro_data')
        x = self.read_i2c_value(self.GYRO_XOUT0)/self.gyro_scale
        y = self.read_i2c_value(self.GYRO_YOUT0)/self.gyro_scale
        z = self.read_i2c_value(self.GYRO_ZOUT0)/self.gyro_scale
        logging.debug('from get_gyro_data x:{}, y:{}, z:{}'.format(x,y,z))
        return {'x': x, 'y': y, 'z': z}

    def _self_functional_check(self):
        try:
            orgn_fltr = self.lowpassfilter_mode
            orgn_gyro = self.gyro_mode
            orgn_accl = self.accl_mode
            success_flag = True
            for key in self.lowpass_bandwidth.keys():
                self.lowpassfilter_mode = key
                if (self.lowpassfilter_mode != key):
                    logging.error('lowpassfilter_mode {} set fail'.format(key))
                    success_flag = False
            for key in self.gyro_mode.keys():
                self.gyroscope_mode = key
                if (self.gyroscope_mode != key):
                    logging.error('gyroscope_mode {} set fail'.format(key))
                    success_flag = False
            for key in self.accl_mode.keys():
                self.accelerometer_mode = key
                if (self.accelerometer_mode != key):
                    logging.error('accelerometer_mode {} set fail'.format(key))
                    success_flag = False
            accldata = self.get_accl_data() 
            if accldata['x'] == accldata['y'] == accldata['z'] == 0.0:
                logging.error('accelerometer data acquiring fail')
                success_flag = False
            gyrodata = self.get_gyro_data() 
            if gyrodata['x'] == gyrodata['y'] == gyrodata['z'] == 0.0:
                logging.error('gyroscope data acquiring fail')
                success_flag = False
            tempdata = self.get_temperature
            if tempdata == 36.530001:
                logging.error('temperature data acquiring fail')
                success_flag = False
        except Exception as err:
            logging.error('Exception detected: functional check: {}'.format(err))
            return False
        finally:
            self.lowpassfilter_mode = orgn_fltr
            self.gyro_mode = orgn_gyro
            self.accl_mode = orgn_accl
            return success_flag

