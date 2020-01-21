# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 14:39:40 2020

@author: 劉又聖
"""

#server.py
import socket
from netapi import NetAPI

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect(('127.0.0.1', 10732))
handler = NetAPI(clientSocket)
if handler.send_file('C:\\Users\\劉又聖\\Desktop\\大學課程\\大二(下) 課程\\PyTrojan\\Practice\\bigFile.txt'):
    print('Send success')
handler.close()