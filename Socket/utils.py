#!/usr/bin/python3


import time
import socket
import select
import subprocess
import uuid
import hashlib
# from cryptography.fernet import Fernet as fernet


__version__ = (2021,12,28,'beta')


def getHostMACAddress():
    try: # Linux
        try:
            resp = subprocess.run('hciconfig',capture_output=True)
        except:
            resp = subprocess.run('hciconfig',stdout=subprocess.PIPE)
        for line in resp.stdout.decode().split('\n'):
            if 'BD Address' in line:
                return line.split(' ')[2]
        raise
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
    def __new__(cls,rawmsg,syntax={'msgb':b'|msgb|','msge':b'|msge|'},*args,**kwargs):
        bgn_mrk,end_mrk = rawmsg.rfind(syntax['msgb']), rawmsg.rfind(syntax['msge'])
        if not ((bgn_mrk < 0) or (end_mrk < 0) or (end_mrk <= bgn_mrk)):
            return super(msgcls,cls).__new__(cls,*args,**kwargs)
    def __init__(self,rawmsg,syntax={'msgb':b'|msgb|','msge':b'|msge|',
                                     'dtab':b'|dtab|','dtae':b'|dtae|',
                                     'infb':b'|infb|','infe':b'|infe|',
                                     'hshb':b'|hshb|','hshe':b'|hshe|',
                                     'keyb':b'|keyb|','keye':b'|keye|'},*args,**kwargs):
        self._rawmsg = rawmsg
        self.syntax  = syntax
        bgn_mrk,end_mrk = self._rawmsg.rfind(self.syntax['msgb']), self._rawmsg.rfind(self.syntax['msge'])
        self._rfnmsg = self._rawmsg[bgn_mrk:(end_mrk+len(self.syntax['msge']))]
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
    def __init__(self,IPAddr=None,port=13666,msgb=None,msge=None,infb=None,infe=None,dtab=None,dtae=None,hshb=None,hshe=None,keyb=None,keye=None):
        self._address_protocol = {'IPv4':socket.AF_INET,'IPv6':socket.AF_INET6}
        self._socket_protocol  = {'TCP':socket.SOCK_STREAM,'UDP':socket.SOCK_DGRAM}
        # connection info
        if not IPAddr:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                self._IPAddr = s.getsockname()[0]
                s.close()
            except Exception as err:
                print('Exception: ',err)
                hostname = socket.gethostname()
                try:
                    self._IPAddr = socket.gethostbyname(hostname+'.local')
                except Exception as err:
                    print('Exception: ',err)
                    self._IPAddr = socket.gethostbyname(hostname)
        else:
            self._IPAddr = IPAddr
        self._port    = port
        if not(isinstance(self._port,(tuple,list,))): self._port = (self._port,)
        self._useport = None
        # syntax word
        self.syntax = {'msgb':b'|msgb|' if msgb is None else msgb,
                       'msge':b'|msge|' if msge is None else msge,
                       'dtab':b'|dtab|' if dtab is None else dtab,
                       'dtae':b'|dtae|' if dtae is None else dtae,
                       'infb':b'|infb|' if infb is None else infb,
                       'infe':b'|infe|' if infe is None else infe,
                       'hshb':b'|hshb|' if hshb is None else hshb,
                       'hshe':b'|hshe|' if hshe is None else hshe,
                       'keyb':b'|keyb|' if keyb is None else keyb,
                       'keye':b'|keye|' if keye is None else keye}
        # read buffer
        self.databuff = []
        self.dataresd = b''
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
    def conn_status(self):
        try:
            if self._soc.fileno() == -1:
                return False
            ready_to_read, ready_to_write, in_error = select.select([self._soc,], [self._soc,], [], 5)
            return bool(ready_to_write)
        except select.error:
            self._soc.shutdown(2)
            self._soc.close()
            return False
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
    def recv_msgsstrm(self,conn=None,timeout=1.0,buff=1024,takelastonly=False):
        if conn is None: conn = self._soc
        if timeout: conn.settimeout(timeout)
        if not(self.databuff):
            if not(self.syntax['msge'] in self.dataresd):
                self.dataresd += conn.recv(buff)
            while self.syntax['msge'] in self.dataresd:
                index = (self.dataresd.find(self.syntax['msge'])+len(self.syntax['msge']))
                self.databuff.append(msgcls(self.dataresd[:index],self.syntax))
                self.dataresd = self.dataresd[index:]
        if takelastonly:
            output = self.databuff[-1]
            self.databuff = []
            return output
        else:
            return self.databuff.pop(0) if self.databuff else None
    def send_msgsszbsstrm(self,inputdata,conn=None):
        if not conn: conn = self._soc
        if not(isinstance(inputdata,(tuple,list,))): inputdata = (inputdata,)
        for data in inputdata:
            self.send_msgs(str(len(data)).encode(),datainfo=b'szbsstrm',conn=conn)
            self.send_rawb(data,conn=conn)
    def recv_msgsszbsstrm(self,conn=None,timeout=1.0,buff=1024,takelastonly=False):
        if conn is None: conn = self._soc
        if timeout: conn.settimeout(timeout)
        if not(self.databuff):
            if not(self.syntax['msge'] in self.dataresd):
                self.dataresd += conn.recv(buff)
            while self.syntax['msge'] in self.dataresd:
                index = (self.dataresd.find(self.syntax['msge'])+len(self.syntax['msge']))
                header = msgcls(self.dataresd[:index],self.syntax)
                self.dataresd = self.dataresd[index:]
                if (header.info == b'szbsstrm'):
                    resbdata = int(header.data.decode())
                    timeout_ref = time.time()
                    while (len(self.dataresd) < resbdata) and (time.time()-timeout_ref < timeout):
                        readdata = conn.recv(min(buff,resbdata-len(self.dataresd)))
                        if readdata:
                            timeout_ref = time.time()
                            self.dataresd += readdata
                self.databuff.append(self.dataresd[:resbdata])
                self.dataresd = self.dataresd[resbdata:]
        if takelastonly:
            output = self.databuff[-1]
            self.databuff = []
            return output
        else:
            return self.databuff.pop(0) if self.databuff else None

