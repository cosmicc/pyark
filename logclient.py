#!/usr/bin/env python3.6

import socket
from loguru import logger as log
from datetime import datetime
from time import sleep
import argparse

HEADERSIZE = 8

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--loglevel', action='store', default=0, help='loglevel')
parser.add_argument('-n', '--lines', action='store', default=20, help='number of lines in log history to show')

args = parser.parse_args()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
timeout_timer = int(datetime.now().timestamp())


def connect_to_server():
    global timeout_timer
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cnt = False
    while not cnt:
        try:
            sock.connect(('172.31.250.115', 1024))
            cnt = True
        except ConnectionRefusedError:
            log.error('Connection to log server refused. Retrying...')
            sleep(10)
    log.info(f'Connected to log server 172.31.250.115')
    sock.setblocking(0)
    head = f'!{args.lines:>3}!{args.loglevel}                          '
    print(head)
    sock.send(bytes(head, "utf-32"))
    timeout_timer = int(datetime.now().timestamp())


connect_to_server()
while True:
    full_msg = ''
    new_msg = True
    while True:
        try:
            msg = sock.recv(80)
            decodedmsg = msg.decode("utf-32")
            if new_msg:
                new_msg = False
                msglen = int(msg.decode("utf-32")[:HEADERSIZE])
                if msglen == 1:
                    log.trace('HEARTBEAT Recieved')
                    timeout_timer = int(datetime.now().timestamp())
                    full_msg = ''
                    new_msg = True
            if msglen != 1:
                full_msg += decodedmsg
            if len(full_msg) - HEADERSIZE == msglen:
                print(full_msg[HEADERSIZE:])
                new_msg = True
                full_msg = ''
            if int(datetime.now().timestamp()) - timeout_timer > 61:
                log.warning('Dead connection timeout.  Reconnecting...')
                sock.close()
                sleep(10)
                connect_to_server()
            sleep(.01)
        except BlockingIOError:
            pass
        except ValueError:
            log.exception(f'Dead connection detected. Reconnecting')
            sock.close()
            sleep(10)
            connect_to_server()
        except KeyboardInterrupt:
            exit(0)
        except:
            log.exception('FUCK!')
