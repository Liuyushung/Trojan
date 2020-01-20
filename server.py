# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 14:33:24 2020

@author: 劉又聖
"""

#server.py
import os
import socket
from netapi import NetAPI, save_file

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind(('127.0.0.1', 10732))
serverSocket.listen(5)

while True:
    conn, addr = serverSocket.accept()
    #conn.send(BANNER)
    handler = NetAPI(conn)
    while True:
        data = handler.recv_file()
        if not data:    break
        print('receive from', addr)
        print(data)
        save_file(data, os.path.join('..\\SaveFiles', addr[0]))
conn.close()

serverSocket.close()