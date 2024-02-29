

__version__ = (2023, 7, 20, 'alpha')


import logging
import time
import socket
from io import BytesIO
import struct


def get_host_ipaddr():
    return socket.gethostbyname(socket.gethostname() + '.local')


class user_socket(object):
    READ_TIMEOUT = 0.1
    READ_BUFFSIZE = 1024
    SEND_DELAY = 0.1

    def __enter__(self):
        self._soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __exit__(self, exc_type, exc_value, traceback):
        self._soc.close()

    def send_rawb(self, data):
        self._soc.sendall(data)
        time.sleep(self.SEND_DELAY)

    def recv_rawb(self, block=False):
        if block:
            self._soc.settimeout(None)
            buffsize = 1
        else:
            self._soc.settimeout(self.READ_TIMEOUT)
            buffsize = self.READ_BUFFSIZE
        with BytesIO() as buff:
            try:
                while readbytes := self._soc.recv(buffsize):
                    if block:
                        self._soc.settimeout(self.READ_TIMEOUT)
                        buffsize = self.READ_BUFFSIZE
                    buff.write(readbytes)
            except socket.timeout:
                pass
            bytesdata = buff.getvalue()
        return bytesdata

    def recv_long(self, frmt='L'):
        with BytesIO() as buff:
            self._soc.settimeout(self.READ_TIMEOUT)
            bom = self._soc.recv(struct.calcsize(frmt))
            datalen = struct.unpack(frmt, bom)[0]
            ref = time.time()
            if self.READ_TIMEOUT is not None:
                time_limit = self.READ_TIMEOUT
            else:
                time_limit = 86400
            while time.time() - ref < time_limit:
                try:
                    buff.write(self._soc.recv(datalen))
                except socket.timeout:
                    pass
                bytesdata = buff.getvalue()
                if len(bytesdata) == datalen:
                    break
        return bytesdata

    def send_long(self, data, frmt='L'):
        bom = struct.pack(frmt, len(data))
        self._soc.sendall(bom + data)
        time.sleep(self.SEND_DELAY)


class server_socket(user_socket):
    def __init__(self, ipaddr, port, backlog=16):
        self._backlog = backlog
        if ipaddr is None:
            self.ipaddr = get_host_ipaddr()
        else:
            self.ipaddr = ipaddr
        self.port = port

    class connection(user_socket):
        def __init__(self, serv_soc):
            self._serv_soc = serv_soc

        def __enter__(self):
            self._soc, self._ipaddr = self._serv_soc.accept()
            return self

    def __enter__(self):
        super().__enter__()
        logging.debug(f'server binding to ipaddr: {self.ipaddr}, port: {self.port}')
        self._soc.bind((self.ipaddr, self.port))
        self._soc.listen(self._backlog)
        return self

    def accept_connection(self):
        self._curr_client = self.connection(self._soc)
        return self._curr_client

    def send_rawb(self, *args, **kwargs):
        self._curr_client.send_rawb(*args, **kwargs)

    def recv_rawb(self, *args, **kwargs):
        self._curr_client.recv_rawb(*args, **kwargs)

    def send_long(self, *args, **kwargs):
        self._curr_client.send_long(*args, **kwargs)

    def recv_long(self, *args, **kwargs):
        self._curr_client.recv_long(*args, **kwargs)


class client_socket(user_socket):
    def __init__(self, server_ipaddr, server_port):
        if server_ipaddr is None:
            self.server_ipaddr = get_host_ipaddr()
        else:
            self.server_ipaddr = server_ipaddr
        self.server_port = server_port

    def __enter__(self):
        super().__enter__()
        logging.debug(f'client connect to ipaddr: {self.server_ipaddr}, port: {self.server_port}')
        self._soc.connect((self.server_ipaddr, self.server_port))
        return self
