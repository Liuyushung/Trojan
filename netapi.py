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
import socket
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
        self.savePath = 'D:\\PyTrojan\\SavedFiles'      # 存檔目錄
        self.maxSize = 2147483647                       # 最大檔案限制
        self.blockSize = 1024                           # 區塊大小
        
    def recv_file(self):    # API
        receiver = {
            FILE_NAME_TAG     :  self.recv_name,
            FILE_SIZE_TAG     :  self.recv_size,
            FILE_COONTENT_TAG :  self.recv_content,
            FILE_BLOCK_TAG    :  self.recv_blocks,
        }
        result = {}
        
        while True:
            tag = None
            #loggin.debug('wait for tag')
            try:
                data = self.recv_data()  # 無用資料
                #logging.warning('Catch unidentified data')
                if not data:    break    # 沒資料了，結束
                continue
            except InOutException as e:
                tag = e.args[0]         # 取得檔案標籤
            except socket.error as e:   # 網路的錯誤無法在這裡解決
                #loggin.error(f'Exception: {str(e)}')
                raise
            except Exception as e:
                #loggin.error(f'Exception: {str(e)}')
                print('Exception', str(e))
                break
            
            # logging.debug(f'Get tag: {tag}')
            if not tag:        # 不是標籤，重新取得
                continue
            elif tag == FILE_BEGIN_TAG: # 檔案傳送開始
                result= {}      # 檔案初始化
                self.send_success()
            elif tag == FILE_END_TAG:   # 檔案傳送結束
                self.send_success()
                break
            elif tag == FILE_ABORT_TAG:
                #logging.debug('abort')
                result = {}
                continue
            #self.send_success()  <-- ??
            
            try:
                #logging.debug('Wait for receive data')
                data = receiver.get(tag, (lambda:None))()     # 取得檔案資料
                if data is None:    break   # 沒資料就停止
                result[tag] = data      # 資料放進回傳值
                #logging.debug('Send success after receive data')
                #self.send_success()
                continue
            except InOutException as e:
                tag = e.args[0]         # 取得檔案標籤
                break                   # 這裡不該取得標籤，無論是甚麼，都中斷
            except socket.error as e:   # 網路的錯誤無法在這裡解決
                raise
            except Exception as e:
                #loggin.error(f'Exception: {str(e)}')
                print('Exception', str(e))
                break
        if not result:  # 客戶端如果結束，中斷連線，result 會是空的
            result = None
        else:
            if FILE_NAME_TAG not in result:     # 缺了檔名
                print('Name not found', result)
                reuslt = None
            elif FILE_SIZE_TAG not in result:   # 缺了檔案大小
                print('Size not found', result)
                reuslt = None
            elif FILE_COONTENT_TAG not in result \
                and FILE_BLOCK_TAG not in reuslt:   # 缺了檔案內容
                print('Content not found', result)
                reuslt = None
            response = FILE_SUCCESS_TAG if result else FILE_FAIL_TAG
            self.send_tag(response)     # 沒缺資料就傳送成功，否則傳送失敗

        # 設 flag 檢查收取的資料
        essential_flag = {
            FILE_NAME_TAG       : 1,
            FILE_SIZE_TAG       : 2,
            FILE_COONTENT_TAG   : 4,
            FILE_BLOCK_TAG      : 4,
        }
        flag = sum([ essential_flag.get(x) for x in result.keys() ])
        if flag != 7:   # 有缺少資料
            result = None
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