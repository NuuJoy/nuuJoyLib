#!/usr/bin/python3


import time
from utils import user_socket


__version__ = (2021,1,26,'beta')


class server_socket(user_socket):
    '''
    Server socket wrapper
    Purpose:
        initial server-side in data transfer.
    Note:
        - Client should connect, transfer data and then disconnect for stability
        - Start_server_XXX module is just for testing
    Example:
        if __name__ == '__main__':
        with server_socket() as server:
            server.start_echo_server()
    '''
    class client_conn(object):
        def __init__(self,conn):
            self._conn = conn
        def __enter__(self):
            return self._conn
        def __exit__(self,*args):
            self._conn.close()
    def __init__(self,addr=None,port=(13666,13667,13668,13669,13670,)):
        super(server_socket,self).__init__(addr,port)
    def __enter__(self):
        super(server_socket,self).__enter__()
        portflag = False
        for self._useport in self._port:
            print('starting server with IP:{}, port:{} ...'.format(self.IPAddr,self._useport))
            try:
                self._soc.bind((self.IPAddr,self.port))
                portflag = True
                break
            except OSError:
                print('IP:{}, port:{} fail, retrying...'.format(self.IPAddr,self._useport))
                pass
        if not(portflag): raise(OSError('Can\'t find available port'))
        print('IPAddr and Port bound')
        self._soc.listen(1) # backlog = 1
        print('listen for connection')
        return self
    def client_accept(self,timeout=None):
        print('waiting for client to connect ...')
        self._con, addr = self._soc.accept() # blocks and waits for an incoming connection
        if timeout: self._con.settimeout(timeout)
        print('client connected Addr {}, port:{}'.format(*addr))
        return self.client_conn(self._con)
    def start_echo_server(self,timeout=1.0,delay=0.0,reverse=False):
        while True:
            client_conn = self.client_accept()
            with client_conn as conn:
                print('start echo server ...')
                data = self.recv_rawb(conn=conn,timeout=timeout)
                if data:
                    print('server recieved {}'.format(data))
                    if reverse: data = data[::-1]
                    time.sleep(delay)
                    self.send_rawb(data,conn=conn)
                    print('server sent {}'.format(data))
                    time.sleep(delay)
            print('client disconnect ...')


class client_socket(user_socket):
    '''
    Client socket wrapper
        Purpose:
            simply start client, make a request, recieve data, then disconnect
        Example:
            if __name__ == '__main__':
            with client_socket() as client:
                client.send_data((','.join([str(num) for num in range(1000)])).encode())
                data = client.recv_data(buff=1024,timeout=10.0)
    '''
    def __init__(self,IPAddr=None,port=(13666,13667,13668,13669,13670,)):
        super(client_socket,self).__init__(IPAddr,port)
    def __enter__(self,addrprtc='IPv4',scktprtc='TCP'):
        super(client_socket,self).__enter__()
        portflag = False
        for self._useport in self._port:
            try:
                self._soc.connect((self.IPAddr, self._useport))
                portflag = True
                break
            except ConnectionRefusedError:
                print('IP:{}, port:{} fail, retrying...'.format(self.IPAddr,self._useport))
        if not(portflag): raise(OSError('Can\'t find server'))
        print('server connected')
        return self
