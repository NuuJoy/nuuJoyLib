#!/usr/bin/python3


import time
import socket
import threading
import multiprocessing
import multiprocessing.managers
from nuuJoyLib.Socket.utils import user_socket


__version__ = (2021,12,27,'beta')


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
            server.start_echo_server(method='recv_msgsszbsstrm',silent=True)
    '''
    class client_conn(object):
        def __init__(self,conn):
            self._soc = self._conn = conn
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
        conn, addr = self._soc.accept() # blocks and waits for an incoming connection
        if timeout: conn.settimeout(timeout)
        print('client connected Addr {}, port:{}'.format(*addr))
        return self.client_conn(conn)
    def start_echo_server(self,method='recv_rawb',timeout=1.0,delay=0.0,reverse=False,silent=False):
        while True:
            connection = self.client_accept()
            with connection as conn:
                print('start echo server ...')
                timeout_ref = time.time()
                while time.time()-timeout_ref < timeout:
                    try:
                        data = getattr(self,method)(conn=conn,timeout=timeout)
                        if data:
                            print('server recieved {}'.format(data))
                            timeout_ref = time.time()
                            if not silent:
                                if reverse:
                                    data = data[::-1]
                                time.sleep(delay)
                                self.send_rawb(data,conn=conn)
                                print('server sent {}'.format(data))
                                time.sleep(delay)
                    except socket.timeout:
                        print('client timeout')
                        break
                    except BrokenPipeError:
                        print('client connection fail')
                        break
            print('client disconnect ...')
    def start_datarate_server(self,method='recv_rawb',timeout=1.0):
        while True:
            connection = self.client_accept()
            with connection as conn:
                print('start datarate server ...')
                timer   = None
                counter = 0
                timeout_ref = time.time()
                while time.time()-timeout_ref < timeout:
                    try:
                        data = getattr(self,method)(conn=conn,timeout=timeout)
                        if data:
                            if not timer:
                                timer = time.time()
                            counter += 1
                            timeout_ref = time.time()
                    except Exception as err:
                        print('some exception ignored: {}'.format(err))
                rate_hz = counter/(timeout_ref-timer)
                print('data receiving rate: {:0.2f} Hz ({} data)'.format(rate_hz,counter))
                            
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


class mySyncMngr(multiprocessing.managers.SyncManager,):
    def __init__(self,address=None,authkey=b'default',startserver=False,
                 queuename=('upstrm','dnstrm',),queuesize=(0,0,),managerQueue=False):
        if not(address):
            port = 13999
            try:
                ipaddr = socket.gethostbyname(socket.gethostname()+'.local')
            except:
                s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                s.connect(('128.128.128.128',port))
                ipaddr = s.getsockname()[0]
            self.initaddr = (ipaddr,port)
        else:
            self.initaddr = address
        self.authkey      = authkey
        self.startserver  = startserver
        self.queuename    = list(queuename) + ['null' for _ in range(8-len(list(queuename)))]
        self.queuesize    = list(queuesize) + [0 for _ in range(8-len(list(queuename)))]
        # portal registeration
        self.server_queue = {}    
        for qname,qsize in zip(self.queuename,self.queuesize):
            if managerQueue:
                self.server_queue.update({qname:multiprocessing.Manager().Queue(maxsize=qsize),})
            else:
                self.server_queue.update({qname:multiprocessing.Queue(maxsize=qsize),})
        mySyncMngr.register(self.queuename[0], callable=lambda:self.server_queue[self.queuename[0]])
        mySyncMngr.register(self.queuename[1], callable=lambda:self.server_queue[self.queuename[1]])
        mySyncMngr.register(self.queuename[2], callable=lambda:self.server_queue[self.queuename[2]])
        mySyncMngr.register(self.queuename[3], callable=lambda:self.server_queue[self.queuename[3]])
        mySyncMngr.register(self.queuename[4], callable=lambda:self.server_queue[self.queuename[4]])
        mySyncMngr.register(self.queuename[5], callable=lambda:self.server_queue[self.queuename[5]])
        mySyncMngr.register(self.queuename[6], callable=lambda:self.server_queue[self.queuename[6]])
        mySyncMngr.register(self.queuename[7], callable=lambda:self.server_queue[self.queuename[7]])
        # init super class
        super().__init__(self.initaddr,self.authkey)
    def __enter__(self):
        if self.startserver:
            print('Starting new server... {}'.format(self.initaddr))
            self.server_h = self.get_server()
            return self
        else:
            print('Connecting to server...{}'.format(self.initaddr))
            self.connect()
            return self
    def __exit__(self,*args):
        pass
    def serve_forever(self):
        self.server_h.serve_forever()
    def serve_forever_thread(self):
        thread = threading.Thread(target=self.serve_forever,daemon=True,)
        thread.start()
        return thread
    def serve_forever_process(self):
        process = multiprocessing.Process(target=self.serve_forever,daemon=True,)
        process.start()
        return process

