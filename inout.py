# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 13:53:40 2020

@author: 劉又聖
"""
# inout.py
import io
import socket
import struct
from common import *

def InitIO(handle):
    # 可做更進階的討論
    readers = {
        bytes:          StringIO,
        io.IOBase:      FileIO,
        socket.socket:  NetworkIO,
    }
    return readers.get(type(handle), lambda n: None)(handle)

class InOutException(Exception):
    pass

class INOUT:            #父類別
    def __init__(self, handle):
        self.handle = handle
        self.exceptTag = b'\\'
    
    def data_to_nbyte(self, N, exceptFlag=False):     # 將資料加上基本標籤
        # 差別在哪 ?
        exceptTag = self.exceptTag if exceptFlag else b''
        exceptTag = {False: b'', True: self.exceptTag}.get(exceptFlag, b'')
        
        if isinstance(N, int):
            if N < (1 << 8):       tag = 'B'    # N < 2^8(256) bytes
            elif N < (1 << 16):    tag = 'H'    # N < 2^16(65536) bytes
            elif N < (1 << 32):    tag = 'L'    # N < 2^32(4G) bytes
            elif N < (1 << 64):    tag = 'Q'    # N < 2^64 bytes
            else:                  tag = 'U'
            
            if tag != 'U':
                nbyte = tag.encode('utf-8') + struct.pack('!'+tag, N)
            else:
                b     = bignum_to_bytes(N)
                nbyte = tag.encode('utf-8') + self.data_to_nbyte(len(b)) + b
        elif isinstance(N, bytes):
            tag, b = 's', N
            nbyte = tag.encode('utf-8') + self.data_to_nbyte(len(b)) + b
        elif isinstance(N, str):
            tag, b = 'c', N.encode('utf-8')
            N = N.encode('utf-8')
            nbyte = tag.encode('utf-8') + self.data_to_nbyte(len(b)) + b
        else:
            raise TypeError('Invaild Type: ' + type(tag))
        
        if exceptFlag:
            logging.debug(f'Send exception: {nbyte}')
        return exceptTag + nbyte
    # 1/20 改道這
    def nbyte_to_data(self):            # 將資料解開
        # Define the tags that mapping to size
        size_info = {'B':1, 'H':2, 'L':4, 'Q':8}
        
        btag = self.read_raw(1)         # 不管是特殊標籤還是基本標籤都只有一個 bytes
        if not btag:
            return None
        exceptFlag = False
        if btag == self.exceptTag:      # 如果是特殊標籤
            exceptFlag = True           # 設 flag 為 True
            btag = self.read_raw(1)     # 再讀一次為正常的基本標籤
        if not btag:                    # 沒讀到東西就是斷線了
            return None
        
        tag = btag.decode('utf-8')      # Btag to String
        
        if tag in size_info:
            size    = size_info[tag]
            bnum    = self.read_raw(size)
            result  = struct.unpack('!'+tag, bnum)[0]
        elif tag in ['s', 'c']:
            size    = self.nbyte_to_data()
            if size >= 65536:    raise ValueError('length too long: ' + str(size))
            bstr    = b''
            while len(bstr) < size:     #網路可能出問題，導致收到的比預期少
                bstr += self.read_raw(size - len(bstr))
            result  = bstr if tag == 's' else bstr.decode('utf-8')
        else:
            raise TypeError('Invaild type: ' + tag)
        if exceptFlag:
            # 是特別標籤時不用 return ， 而是用　raise exception
            # 有無特別標籤的差別僅是在於傳回資料的方法而已
            raise InOutException(result)
        return result
    
    def read(self): # 提供高級的存取介面
        return self.nbyte_to_data()
    def write(self, d): # 提供高級的存取介面
        byte_data = self.data_to_nbyte(d)
        self.write_raw(byte_data)
    def read_raw(self, n):
        return self.read_handle(n)
    def write_raw(self, d):
        return self.write_handle(d)
    def close(self):
        return self.handle.close()
    # 子類別需要定義的地方
    def read_handle(self, n):
        return b''
    def write_handle(self, d):
        print(d)
        return len(d)
    def close_handle(self):
        return self.handle

class NetworkIO(INOUT): #網路輸入輸出
    def read_handle(self, n):
        return self.handle.recv(n)  # sock.recv(n)
    def write_handle(self, d):
        return self.handle.send(d)  # sock.send(n)

class FileIO(INOUT):    #檔案輸出輸入
    def read_handle(self, n):
        return self.handle.read(n) # fp.read(n)
    def write_handle(self, d):
        return self.handle.write(d) #fp.write(d)

class StringIO(INOUT):  # 直接 bytes 測試用
    def read_handle(self, n):
        data, self.handle = self.handle[:n], self.handle[n:]
        return data
    def write_handle(self, d):
        self.handle += d

def bignum_to_bytes(n):
    result = b''
    while n > 0:
        b = n % 128              # 只取 7 bits
        n >>= 7                  # 位移 7 bits, 高位數移下來
        if n:
            b += 128            # 後面還有，位元組高位填 1
        result += bytes([b])    # 小於 256(1 byte) 的數字，可以直接轉成 bytes
    return result

def bytes_to_bignum(bs):
    result, exp = 0, 0
    for b in bs:                # 每次取出為 1 byte, 8 bit
        n = b % 128             # 從 byte 取出其中 7 bits
        result += n << exp      # 先傳的是低位，後面是高位, << 優先於 +=
        exp += 7
        if b & (1 << 7) == 0:   # 最高位是 0 結束
            break
    return result
