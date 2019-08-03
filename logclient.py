#!/usr/bin/env python3.6

import socket
from loguru import logger as log
from datetime import datetime
from time import sleep
import argparse
from os import _exit
import sys

HEADERSIZE = 30
RECVSIZE = 1024
PORT = 11024

parser = argparse.ArgumentParser()
parser.add_argument('lines', action='store', help='number of lines in log history to show')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose (client debug)')
parser.add_argument('-s', '--server', action='store', default='ALL', help='show only this log type')
parser.add_argument('-d', '--debug', action='store_true', help='show debug log')
parser.add_argument('-t', '--trace', action='store_true', help='show trace log')
parser.add_argument('-e', '--extend', action='store_true', help='show extended info lines')
parser.add_argument('--showonly', action='store', default='ALL', help='show only this log type')
parser.add_argument('-nf', '--nofollow', action='store_false', help='dont follow continuous log')
parser.add_argument('-ra', '--noadmin', action='store_false', help='remove admin entries')
parser.add_argument('-rs', '--startexit', action='store_false', help='remove start/exit entries')
parser.add_argument('-rc', '--commands', action='store_false', help='remove command entries')
parser.add_argument('-rv', '--votes', action='store_false', help='remove vote entries')
parser.add_argument('-rj', '--joinleave', action='store_false', help='remove join/leave entries')

args = parser.parse_args()

simplelogformat = '<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level> | <level>LOGGR</level> | <level>{level: <7}</level> | <level>{message}</level>'

log.remove()
llevel = 'DEBUG' if args.verbose else 'INFO'
log.add(sys.stderr, level=llevel, format=simplelogformat)


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
timeout_timer = int(datetime.now().timestamp())

argsdebug = 1 if args.debug else 0
argstrace = 1 if args.trace else 0
argsextend = 1 if args.extend else 0
argsstartexit = 1 if args.startexit else 0
argscommands = 1 if args.commands else 0
argsvotes = 1 if args.votes else 0
argsjoinleave = 1 if args.joinleave else 0
argsfollow = 1 if args.nofollow else 0
argsadmin = 1 if args.noadmin else 0

first_time = True
retrycount = 1


def connect_to_server():
    global timeout_timer
    global sock
    global first_time
    global retrycount
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cnt = False
    while not cnt:
        try:
            sock.connect(('172.31.250.115', PORT))
            cnt = True
        except ConnectionRefusedError:
            if retrycount == 1:
                retrycount = 2
                log.warning('Connection to log server lost. Reconnecting...')
            sleep(5)
    log.success(f'Connected to log server 172.31.250.115:{PORT}')
    sock.setblocking(0)
    retrycount = 1
    if args.showonly != 'ALL':
        argsshowonly = f'{args.showonly:<8}!'
    else:
        argsshowonly = f'ALL     !'
    if args.server != 'ALL':
        argsserver = f'{args.server:<5}'
    else:
        argsserver = f'ALL   '
    if first_time:
        plines = args.lines
    else:
        plines = 0
    head = f'!{plines:>3}!{argsdebug}!{argstrace}!{argsextend}!{argsadmin}!{argsstartexit}!{argscommands}!{argsvotes}!{argsjoinleave}!{argsfollow}!{argsserver}!{argsshowonly}'
    log.debug(f'Header: {head}')
    sock.send(bytes(head, "utf-8"))
    timeout_timer = int(datetime.now().timestamp())
    first_time = False


connect_to_server()
while True:
    full_msg = ''
    new_msg = True
    while True:
        try:
            msg = sock.recv(RECVSIZE)
            decodedmsg = msg.decode("utf-32")
            if new_msg:
                new_msg = False
                msglen = int(msg.decode("utf-32")[:HEADERSIZE])
                log.debug(f'msg recieved length {msglen}')
                if msglen == 1:
                    if decodedmsg[HEADERSIZE:] == '!':
                        log.debug('HEARTBEAT Recieved')
                        timeout_timer = int(datetime.now().timestamp())
                        full_msg = ''
                        new_msg = True
                if msglen == 2:
                    if decodedmsg[HEADERSIZE:] == '##':
                        log.debug('Recieved closing signal from server')
                        full_msg = ''
                        new_msg = True
                        sock.close()
                        _exit(2)
                    if decodedmsg[HEADERSIZE:] == '#!':
                        log.info('Recieved a reconnect signal from log server. Reconnecting...')
                        full_msg = ''
                        new_msg = True
                        sock.close()
                        sleep(10)
                        connect_to_server()

            full_msg += decodedmsg
            if len(full_msg) - HEADERSIZE == msglen:
                if msglen > 2:
                    print(full_msg[HEADERSIZE:])
                timeout_timer = int(datetime.now().timestamp())
                new_msg = True
                full_msg = ''
            if int(datetime.now().timestamp()) - timeout_timer > 61:
                log.warning('Connection heartbeat timeout. Reconnecting...')
                retry_count = 2
                sock.close()
                sleep(5)
                connect_to_server()
        except BlockingIOError:
            pass
        except ValueError:
            log.warning(f'Dead connection detected. Reconnecting')
            retry_count = 2
            sock.close()
            sleep(5)
            connect_to_server()
        except KeyboardInterrupt:
            sock.close()
            _exit(0)
        except:
            log.exception('FUCK!')
        try:
            sleep(.01)
        except KeyboardInterrupt:
            sock.close()
            _exit(0)
