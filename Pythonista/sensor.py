

import time
import motion
import objc_util
from ctypes import Structure, c_double


__version__ = (2021,2,2,'beta')


class motion_sensor():
    class CMRotationRate (Structure):
        _fields_ = [('x', c_double), ('y', c_double), ('z', c_double)]
    def __init__(self):
        self.gyromgr = objc_util.ObjCClass('CMMotionManager').alloc().init()
    def __enter__(self):
        self.start_updates()
        self.gyromgr.startGyroUpdates()
        time.sleep(0.05) # wait for sensor initialize
        return self
    def __exit__(self,*args):
        self.stop_updates()
        self.gyromgr.stopGyroUpdates()
        self.gyromgr.release()
    def start_updates(self):
        motion.start_updates()
    def stop_updates(self):
        motion.stop_updates()
    @property
    def gravity(self):
        return {key:val for key,val in zip(('x','y','z'),motion.get_gravity())}
    @property
    def acceleration(self):
        return {key:val for key,val in zip(('x','y','z'),motion.get_user_acceleration())}
    @property
    def accelerometer(self):
        return {key:(grvt+user) for key,grvt,user in zip(('x','y','z'),self.gravity.values(),self.acceleration.values())}
    @property
    def gyroscope(self):
        gyro_data = self.gyromgr.gyroData()
        if not gyro_data:
            return {'x':0.0,'y':0.0,'z':0.0}
        rate = gyro_data.rotationRate(argtypes=[], restype=self.CMRotationRate)
        return {'x':rate.x,'y':rate.y,'z':rate.z}
    @property
    def magnetometer(self):
        return {key:val for key,val in zip(('x','y','z','accu'),motion.get_magnetic_field())}
    @property
    def attitude(self):
        return {key:val for key,val in zip(('roll','pitch','yaw'),motion.get_attitude())}
    @property
    def allsensor(self):
        output = {}
        output.update({('grvt_'+key):val for key,val in self.gravity.items()})
        output.update({('user_'+key):val for key,val in self.acceleration.items()})
        output.update({('accl_'+key):val for key,val in self.accelerometer.items()})
        output.update({('gyro_'+key):val for key,val in self.gyroscope.items()})
        output.update({('mgnt_'+key):val for key,val in self.magnetometer.items()})
        output.update({('attd_'+key):val for key,val in self.attitude.items()})
        return output

