# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 12:28:06 2020

@author: 劉又聖
"""

#import io
import os
#import sys
import time
import shutil
#from config import *
#from common import *
from inout import InitIO, InOutException
from path import split_path

FILE_BEGIN_TAG = b'FILEBEG0'
FILE_END_TAG = b'FILEEND0'
FILE_SIZE_TAG = b'FILESIZE'
FILE_NAME_TAG = b'FILENAME'
FILE_COONTENT_TAG = b'FILEDATA'
FILE_BLOCK_TAG = b'FILEBLKS'

FILE_SUCCESS_TAG = b'FILEGOOD'
FILE_FAIL_TAG = b'FILEFAIL'
FILE_ABORT_TAG = B'FILEABRT'
FILE_TAG_SIZE = len(FILE_BEGIN_TAG)

# netapi.py
class NetAPI:
    """
    handle.send_file('test.txt')    # 傳送單一檔案所有檔案資訊
    fileInfo = handle.recv_file()   # 收取單一檔案所有的資訊
    """
    def __init__(self, iHandle=None, oHandle=None):
        if not iHandle:
            iHandle = b''
        if not oHandle:
            oHandle = iHandle
        self.iHandle = InitIO(iHandle)
        self.oHandle = InitIO(oHandle)
        self.savePath = 'D:\\PyTrojan\\SavedFiles'     # 存檔目錄
        self.maxSize = 2147483647                       # 最大檔案限制
        self.blockSize = 1024                           # 區塊大小
        
    def recv_file(self):    # API
        result = {}
        while True:
            tag = self.recv_tag()
            if not tag or tag in [FILE_END_TAG, FILE_ABORT_TAG]: break
            
            if tag == FILE_BLOCK_TAG:   # 如果是傳區塊，用讀區塊的方式讀取
                data = self.recv_blocks()
            else:                       # 用一般方式讀取
                data = self.recv_data()
                if not data: break
            
            if tag == FILE_NAME_TAG:
                namelist = data.split('\t')
                if '..' in namelist:
                    raise ValueError('Dangerous path')
                data = os.path.join(*namelist)
                
            result[tag] = data
        return result
    
    def send_file(self, path):    # API
        fileName = '\t'.join(split_path(path))
        fileSize = os.path.getsize(path)
        fileData = open(path, 'rb').read()
        try:
            self.send_tag(FILE_NAME_TAG)
            self.send_data(fileName)
            self.send_tag(FILE_SIZE_TAG)
            self.send_data(fileSize)
            if fileSize > self.blockSize:   # 比區塊大，用區塊傳
                self.send_tag(FILE_BLOCK_TAG)
                self.send_blocks(path)
            else:                           # 比區塊小，直接傳內容
                self.send_tag(FILE_COONTENT_TAG)
                self.send_conntent(fileData)
            self.send_tag(FILE_END_TAG)
            return True
        except Exception as e:
            print(str(e))
            self.send_tag(FILE_ABORT_TAG)
            return False

    def send_blocks(self, fileName):    # API
        fp        = open(fileName, 'rb')
        blockID   = 0
        totalSize = 0
        
        while True:
            block      = fp.read(self.blockSize)    # 讀檔案
            if not block:   break                   # 沒資料就是結束
            blockID   += 1                          # 區塊編號
            self.send_data(blockID)                 # 送出區塊編號
            self.send_data(block)                   # 送出檔案區塊
            totalSize += len(block)
        self.send_data(0)                           # 送出結束編號
        return totalSize
        
    def recv_blocks(self):            # API
        totalSize = 0
        lastBlockID = 0
        fileTmpName = os.path.abspath(os.path.join(self.savePath, f'TEMP{int(time.time())}'))  #決定暫存檔名
        dirname = os.path.dirname(fileTmpName)
        if not os.path.exists(dirname):
            os.makedirs(dirname)    # 產生目錄
        with open(fileTmpName, 'wb') as fp:
            while True:
                blockID = self.recv_data()
                if not isinstance(blockID, int):
                    raise TypeError(f'Invalid type of block id {type(blockID)}')
                if blockID == 0:    break                   # 結束編號
                if lastBlockID + 1 != blockID:              # 比對編號是否正確
                    raise ValueError(f'Block ID error last: {lastBlockID} current: {blockID}')
                lastBlockID = blockID                       # 記下現在的編號
                block = self.recv_data()                    # 收取資料
                if not isinstance(block, bytes):            # 資料應該是 bytes
                    raise TypeError(f'Invalid type of block {type(block)}')
                if len(block) + totalSize > self.maxSize:   # 收取資料總數太大
                    raise RuntimeError('Exceed max file size limit')
                fp.write(block)                             # 寫進暫存檔
        return fileTmpName

    def recv_tag(self):               return self.iHandle.read()
    def recv_data(self):              return self.iHandle.read()
    def send_tag(self, tag):          return self.oHandle.write(tag)
    def send_data(self, data):        return self.oHandle.write(data)

    def send_size(self, n):           return self.send_data(n)
    def send_name(self, s):           return self.send_data(s)
    def send_conntent(self, d):       return self.send_data(d)
    
    def recv_size(self):           
        size = self.recv_data()
        if not isinstance(size, int): # 判斷是否為 int
            raise TypeError('Invalid size type {}'.format(type(size)))
        return size
    def recv_name(self):
        path = self.recv_data()
        if not isinstance(path, str): # 判斷是否為 str
            raise TypeError('Invalid name type {}'.format(type(path)))
        namelist = path.split('\t')
        if '..' in namelist:
            raise ValueError('Dangerous path')
        name = os.path.join(*namelist)
        return name
    def recv_content(self):           return self.recv_data()
    
    def send_success(self):  pass
    def send_fail(self):     pass
    def send_abort(self, n): pass

def save_file(fileInfo, target):
    fileName = fileInfo.get(FILE_NAME_TAG)
    fileSize = fileInfo.get(FILE_SIZE_TAG)
    content = fileInfo.get(FILE_COONTENT_TAG)
    tempFile = fileInfo.get(FILE_BLOCK_TAG)
    
    if not fileName or not fileSize:
        return False
    if content or tempFile:         # 有檔案內容或暫存檔
        fullName = os.path.join(target, fileName)
        dirName = os.path.dirname(fullName)
        if not os.path.exists(dirName): # 建立存檔目錄
            os.mkdir(dirName)
        if content:                     # 如果是 content 就存到檔名
            if len(content) != fileSize:
                raise RuntimeError('Size unmatched')
            with open(fullName, 'wb') as fp:
                fp.write(content)
        else:   # 如果是暫存檔，將暫存檔名改成真正檔名
            if os.path.getsize(tempFile) != fileSize:
                raise RuntimeError('Size unmatched')
            shutil.move(tempFile, fullName)
        return True
    else:
        return False