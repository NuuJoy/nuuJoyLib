

__version__ = (2023, 6, 22, 'alpha')


import pyvisa as visa


class tektronic_tds2024c():
    '''
    with tektronic_tds2024c(device_init_commands=[
        'DATa:SOUrce MATH',
        'WFMPre:ENCdg RIBinary',
    ]) as scope_ctrl:

        scope_ctrl.set_time_per_div(50e-9)
        scope_ctrl.set_time_position(8.0e-6)
        scope_ctrl.set_volt_position(-8.1e1, channel='CH1')
        scope_ctrl.set_volt_position(-8.3e1, channel='CH2')

        import time
        ref = time.time()
        waveform_values = scope_ctrl.capture_waveform()
    '''

    def __init__(self, device_init_commands=['WFMPre:ENCdg RIBinary']):
        self._rm = visa.ResourceManager()
        self._device_init_commands = device_init_commands

    def device_connect(self, device_indx=None, device_str=None):
        self._resources = self._rm.list_resources()
        if device_str is None:
            if device_indx is None:
                device_indx = 0
        else:
            for device_indx, device_label in enumerate(self._resources):
                if device_label.startswith(device_str):
                    break
        print('resources:', self._resources)
        assert self._resources, 'device not found'
        self._device = self._rm.open_resource(
            self._resources[device_indx],
            write_termination='\n'
        )
        self._device.timeout = 100000000
        for command in self._device_init_commands:
            self._device.write(command)

    def device_disconnect(self):
        try:
            self._device.close()
        except Exception:
            pass

    def __enter__(self, device_indx=0):
        self.device_connect(device_indx=device_indx)
        return self

    def __exit__(self, *args, **kwargs):
        self.device_disconnect()

    def run(self):
        self._device.write('ACQuire:STATE RUN')

    def stop(self):
        self._device.write('ACQuire:STATE STOP')

    def get_scope_iden(self):
        return self._device.query('*IDn?')

    def get_xaxs_info(self):
        str_list = self._device.query('HORizontal?').split(';')
        return {
            'time_per_div': float(str_list[2]),
            'time_offset': float(str_list[3]),
            'data_length': int(str_list[1]),
        }

    def get_time_position(self):
        return self.get_xaxs_info['time_offset']

    def get_time_per_div(self):
        return self.get_xaxs_info['time_per_div']

    def get_data_length(self):
        return self.get_xaxs_info['data_length']

    def get_volt_position(self, channel='MATH'):
        return float(self._device.query(f'{channel}?').split(';')[3])

    def get_volt_per_div(self, channel='MATH'):
        return float(self._device.query(f'{channel}?').split(';')[2])

    def set_time_position(self, sec):
        self._device.write(f'HORizontal:POSition {sec:0.3e}')

    def set_time_per_div(self, sec):
        self._device.write(f'HORizontal:SCAle {sec:0.3e}')

    def set_volt_position(self, volt, channel=('CH1', 'CH2')):
        if isinstance(channel, (str,)):
            channel = [channel]
        for ch in channel:
            self._device.write(f'{ch}:POSition {volt:0.3e}')

    def set_volt_per_div(self, volt, channel=('CH1', 'CH2')):
        if isinstance(channel, (str,)):
            channel = [channel]
        for ch in channel:
            self._device.write(f'{ch}:SCAle {volt:0.3e}')

    def capture_waveform(self):
        yscale = float(self._device.query('WFMPre:YMUlt?'))
        unscale_values = self._device.query_binary_values(message='CURVe?', datatype='b', is_big_endian=True)
        return [yscale * value for value in unscale_values]
