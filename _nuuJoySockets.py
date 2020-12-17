#!/usr/bin/python3


import sys
import time
import socket
import subprocess
import uuid
from cryptography.fernet import Fernet as fernet
import hashlib


__version__ = (2020,12,10,'alpha')


'''
Note: Modules in this file was sometime tested on WinX64, sometimes on Ubuntu,
      sometimes on Python27, sometimes on Python38, sometimes on Python39, etc.
   *** PLEASE CAREFULLY TEST IT BY YOURSELF AGAIN AND USE IT ON YOUR OWN RISK ***

Content
    function
        getHostMACAddress
    class
        user_socket
        server_socket
        client_socket
        bluetooth_server
        bluetooth_client
'''


def getHostMACAddress():
    try: # Linux
        try:
            resp = subprocess.run('hciconfig',capture_output=True)
        except:
            resp = subprocess.run('hciconfig',stdout=subprocess.PIPE)
        for line in resp.stdout.decode().split('\n'):
            if 'BD Address' in line:
                return line.split(' ')[2]
        if not(hasattr(self,'hostMACAddress')):
            raise(ValueError)
    except: # Windows
        rawstr = hex(uuid.getnode()).upper()[2:]
        return ''.join([(char if i%2 == 0 else char+':') for i,char in enumerate(rawstr)])[:-1]


class ciphers():
    def __init__(self,key=None):
        self._key   = key if key else fernet.generate_key()
        self._suite = fernet(self._key)
    @property
    def key(self):
        return self._key
    @key.setter
    def key(self,newkey):
        self._suite = fernet(newkey)
        self._key   = newkey
    def encrypt(self,bytedata):
        return self._suite.encrypt(bytedata)
    def decrypt(self,ncypdata):
        return self._suite.decrypt(ncypdata)
def encrypt(bytedata,key=None):
    if not(key): key = fernet.generate_key()
    suite = fernet(key)
    return suite.encrypt(bytedata), key
def decrypt(bytedata,key):
    return fernet(key).decrypt(bytedata)



class msgcls(object):
    '''
    message pattern for user_socket
        Purpose:
            use predefined word as delimit for data block
    '''
    @staticmethod
    def _xtrct(data,bgn,end):
        if (bgn and end):
            bgn_mrk,end_mrk = data.rfind(bgn), data.rfind(end)
            if not ((bgn_mrk < 0) or (end_mrk < 0) or (end_mrk <= bgn_mrk)):
                return data[(bgn_mrk+len(bgn)):end_mrk]
    def __new__(cls,rawmsg,syntax,*args,**kwargs):
        bgn_mrk,end_mrk = rawmsg.rfind(syntax['msgb']), rawmsg.rfind(syntax['msge'])
        if not ((bgn_mrk < 0) or (end_mrk < 0) or (end_mrk <= bgn_mrk)):
            return super(msgcls,cls).__new__(cls,*args,**kwargs)
    def __init__(self,rawmsg,syntax,*args,**kwargs):
        self.syntax = syntax
        bgn_mrk,end_mrk = rawmsg.rfind(self.syntax['msgb']), rawmsg.rfind(self.syntax['msge'])
        self._rfnmsg = rawmsg[bgn_mrk:(end_mrk+len(self.syntax['msge']))]
    def __repr__(self):
        return str(self._rfnmsg)
    @property
    def info(self):
        return self._xtrct(self._rfnmsg,self.syntax['infb'],self.syntax['infe'])
    @property
    def hash(self):
        return self._xtrct(self._rfnmsg,self.syntax['hshb'],self.syntax['hshe'])
    @property
    def key(self):
        return self._xtrct(self._rfnmsg,self.syntax['keyb'],self.syntax['keye'])
    @property
    def data(self):
        return self._xtrct(self._rfnmsg,self.syntax['dtab'],self.syntax['dtae'])


class user_socket(object):
    '''
    Native Python socket wrapper
        Purpose:
            Abstract class that contain simple send/recieve protocol.
            mainly use as server_socket and client_socket parent
    '''
    def __init__(self,IPAddr=None,port=13666,msgb=b'|msgb|',msge=b'|msge|',
                                             infb=b'|infb|',infe=b'|infe|',
                                             dtab=b'|dtab|',dtae=b'|dtae|',
                                             hshb=b'|hshb|',hshe=b'|hshe|',
                                             keyb=b'|keyb|',keye=b'|keye|'):
        self._address_protocol = {'IPv4':socket.AF_INET,'IPv6':socket.AF_INET6}
        self._socket_protocol  = {'TCP':socket.SOCK_STREAM,'UDP':socket.SOCK_DGRAM}
        # connection info
        if not IPAddr:
            hostname     = socket.gethostname()
            self._IPAddr = socket.gethostbyname(hostname+'.local')
        else:
            self._IPAddr = IPAddr
        self._port    = port
        if not(isinstance(self._port,(tuple,list,))): self._port = (self._port,)
        self._useport = None
        # syntax word
        self.syntax = {'msgb':msgb,'msge':msge,
                       'dtab':dtab,'dtae':dtae,
                       'infb':infb,'infe':infe,
                       'hshb':hshb,'hshe':hshe,
                       'keyb':keyb,'keye':keye}
        # read buffer
        self.databuff = []
        self.dataresd = ''
        # encoder
        self._ciphers  = ciphers()
        self.encryptor = self._ciphers.encrypt
        self.decryptor = self._ciphers.decrypt
        #hasher
    @property
    def IPAddr(self):
        return self._IPAddr
    @property
    def port(self):
        return self._useport
    @property
    def secrkey(self):
        return self._ciphers.key
    def __enter__(self):
        self._soc = socket.socket(self._address_protocol['IPv4'],self._socket_protocol['TCP'])
    def __exit__(self,exc_type, exc_value, traceback):
        self._soc.close()
        print('socket port closed')
    def send_rawb(self,data,conn=None):
        if not conn: conn = self._soc
        conn.sendall(data)
    def recv_rawb(self,conn=None,timeout=1.0,buff=1024):
        if not conn: conn = self._soc
        if timeout: conn.settimeout(timeout)
        data = b''
        datapart = True
        while datapart:
            try:
                datapart = conn.recv(buff)
                if datapart: 
                    data += datapart
            except socket.timeout:
                datapart = None
            except ConnectionResetError:
                datapart = None
        return data
    def send_msgs(self,inputdata,datainfo=b'',datahash=False,conn=None):
        if not conn: conn = self._soc
        if not(isinstance(inputdata,(tuple,list,))): inputdata = (inputdata,)
        info_block = self.syntax['infb'] + datainfo + self.syntax['infe'] if datainfo else b''
        for data in inputdata:
            hash_block = self.syntax['hshb'] + hashlib.md5(data).digest() + self.syntax['hshe'] if datahash else b''
            data_block = self.syntax['dtab'] + data + self.syntax['dtae']
            conn.sendall(self.syntax['msgb'] + info_block + data_block + hash_block + self.syntax['msge'])
    def recv_msgs(self,conn=None,timeout=1.0,buff=1024):
        if not conn: conn = self._soc
        if timeout: conn.settimeout(timeout)
        data = b''
        datapart = True
        while datapart:
            try:
                datapart = conn.recv(buff)
                if datapart: 
                    data += datapart
                    if self.syntax['msge'] in data:
                        break
            except socket.timeout:
                datapart = None
        return msgcls(data,self.syntax)


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

