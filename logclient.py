#!/usr/bin/env python3.6

import socket
import pickle

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 1024))

HEADERSIZE = 8


while True:
    full_msg = b''
    new_msg = True
    while True:
        msg = s.recv(24)
        if new_msg:
            # print(f'new msg length: {msg[:HEADERSIZE]}')
            msglen = int(msg[:HEADERSIZE])
            new_msg = False
        # print(msg)
        full_msg += msg
        if len(full_msg) - HEADERSIZE == msglen:
            # print('full msg recieved')
            # print(full_msg[HEADERSIZE:])
            d = pickle.loads(full_msg[HEADERSIZE:])
            print(d)
            new_msg = True
            full_msg = b''
