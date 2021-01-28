#!/usr/bin/python3


import socket
import subprocess
import uuid
# from cryptography.fernet import Fernet as fernet
import hashlib


__version__ = (2021,1,26,'beta')


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


# class ciphers():
#     def __init__(self,key=None):
#         self._key   = key if key else fernet.generate_key()
#         self._suite = fernet(self._key)
#     @property
#     def key(self):
#         return self._key
#     @key.setter
#     def key(self,newkey):
#         self._suite = fernet(newkey)
#         self._key   = newkey
#     def encrypt(self,bytedata):
#         return self._suite.encrypt(bytedata)
#     def decrypt(self,ncypdata):
#         return self._suite.decrypt(ncypdata)
# def encrypt(bytedata,key=None):
#     if not(key): key = fernet.generate_key()
#     suite = fernet(key)
#     return suite.encrypt(bytedata), key
# def decrypt(bytedata,key):
#     return fernet(key).decrypt(bytedata)


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
        # self._ciphers  = ciphers()
        # self.encryptor = self._ciphers.encrypt
        # self.decryptor = self._ciphers.decrypt
        #hasher
    @property
    def IPAddr(self):
        return self._IPAddr
    @property
    def port(self):
        return self._useport
    # @property
    # def secrkey(self):
    #     return self._ciphers.key
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
