#!/usr/bin/python3


import socket
from nuuJoyLib.nuuJoySocket.tcpipv4 import server_socket
from nuuJoyLib.nuuJoySocket.utils import user_socket,getHostMACAddress


__version__ = (2021,1,26,'beta')


class bluetooth_server(server_socket):
    '''
    Bluetooth socket server
    Purpose:
        initial server-side using bluetooth connection
    '''
    def __init__(self,addr=None,port=(3,4,5,6,7,),backlog=1,size=1024):
        if not(addr):
            self.hostMACAddress = getHostMACAddress()
        else:
            self.hostMACAddress = addr
        self._port    = port
        if not(isinstance(self._port,(tuple,list,))): self._port = (self._port,)
        self._useport = None
        self.backlog  = backlog
        self.size     = size
    def __enter__(self):
        self._soc = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        portflag = False
        for self._useport in self._port:
            print('starting server with MACAddr {}, port:{} ...'.format(self.hostMACAddress,self._useport))
            try:
                self._soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._soc.bind((self.hostMACAddress,self.port))
                portflag = True
                break
            except OSError as e:
                print(e)
                print('MACAddr {}, port:{} fail, retrying...'.format(self.hostMACAddress,self._useport))
        if not(portflag): raise(OSError('Can\'t find available port'))
        print('MACAddr and Port bound')
        self._soc.listen(self.backlog)
        print('listen for connection')
        return self


class bluetooth_client(user_socket):
    '''
    Bluetooth socket client
        Purpose:
            simply start client, make a request, recieve data, then disconnect
    '''
    def __init__(self,addr=None,port=(3,4,5,6,7,)):
        super(bluetooth_client,self).__init__(IPAddr='nouse',port=port)
        if not(addr):
            self.hostMACAddress = getHostMACAddress()
        else:
            self.hostMACAddress = addr
    def __enter__(self):
        self._soc = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        portflag = False
        for self._useport in self._port:
            print('connecting to server MACAddr {}, port:{} ...'.format(self.hostMACAddress,self._useport))
            try:
                self._soc.connect((self.hostMACAddress, self.port))
                portflag = True
                break
            except OSError:
                print('MACAddr:{}, port:{} fail, retrying...'.format(self.hostMACAddress,self._useport))

        if not(portflag): raise(OSError('Can\'t find server'))
        print('server connected')
        return self
    def __exit__(self,*args):
        self._soc.close()

