#!/usr/bin/env python3.6

import socket
from loguru import logger as log
from datetime import datetime
from time import sleep
import argparse
from os import _exit
import sys
from ansi2html import Ansi2HTMLConverter


class LogClient():
    def __init__(self, lines, argsdebug, argstrace, argsextend, argsstartexit, argscommands, argsvotes, argsjoinleave, argsfollow, argsadmin, showonly, server, html):
        HEADER = 5
        self.HEADERSIZE = HEADER * 4 + 4
        self.PORT = 11024
        self.IP = '172.31.250.115'
        self.first_time = True
        self.retrycount = 1
        self.timeout_timer = int(datetime.now().timestamp())
        self.lines = lines
        self.debug = argsdebug
        self.trace = argstrace
        self.extend = argsextend
        self.startexit = argsstartexit
        self.commands = argscommands
        self.votes = argsvotes
        self.joinleave = argsjoinleave
        self.follow = argsfollow
        self.admin = argsadmin
        self.showonly = showonly
        self.server = server
        self.html = html
        self.full_msg = ''
        self.new_msg = True
        if self.html:
            self.ansiconverter = Ansi2HTMLConverter()

    def htmlheaders(self):
            return self.ansiconverter.produce_headers()

    def close(self):
        self.sock.close()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cnt = False
        while not cnt:
            try:
                self.sock.connect((self.IP, self.PORT))
                cnt = True
            except ConnectionRefusedError:
                if self.retrycount == 1:
                    self.retrycount = 2
                    log.warning('Connection to log server lost. Reconnecting...')
                sleep(5)
        log.success(f'Connected to log server {self.IP}:{self.PORT}')
        self.sock.setblocking(False)
        self.retrycount = 1
        self.showonly = f'{self.showonly:<8}!'
        self.server = f'{self.server:<5}'
        if self.first_time:
            plines = self.lines
        else:
            plines = 0
        head = f'!{plines:>3}!{self.debug}!{self.trace}!{self.extend}!{self.admin}!{self.startexit}!{self.commands}!{self.votes}!{self.joinleave}!{self.follow}!{self.server}!{self.showonly}'
        log.debug(f'Header: {head}')
        self.sock.send(bytes(head, "utf-8"))
        self.timeout_timer = int(datetime.now().timestamp())
        self.first_time = False

    def getline(self):
        while True:
            try:
                header = self.sock.recv(self.HEADERSIZE)
                log.debug(header)
                log.debug(header.decode("utf-32"))
                msgsize = int(header.decode("utf-32"))
                msg = self.sock.recv(msgsize)
                log.debug(f'reported size: {msgsize}  actual size: {len(msg)}')
                decodedmsg = msg.decode("utf-32")
                log.debug(f'decoded size: {len(decodedmsg)}')
                self.timeout_timer = int(datetime.now().timestamp())
                self.new_msg = True
                self.full_msg = ''
                if msgsize == 8:
                        if decodedmsg == '!':
                            log.debug('HEARTBEAT Recieved')
                            self.timeout_timer = int(datetime.now().timestamp())
                            self.full_msg = ''
                            self.new_msg = True
                elif msgsize == 16:
                        if decodedmsg == '##':
                            log.debug('Recieved closing signal from server')
                            self.full_msg = ''
                            self.new_msg = True
                            self.sock.close()
                            if __name__ == '__main__':
                                _exit(2)
                            else:
                                return None
                        if decodedmsg == '#!':
                            log.info('Recieved a reconnect signal from log server. Reconnecting...')
                            self.full_msg = ''
                            self.new_msg = True
                            self.sock.close()
                            sleep(10)
                            self.connect()
                else:
                        if self.html:
                            return self.ansiconverter.convert(decodedmsg, full=False, ensure_trailing_newline=False)
                        else:
                            return decodedmsg
                if int(datetime.now().timestamp()) - self.timeout_timer > 61:
                    log.warning('Connection heartbeat timeout. Reconnecting...')
                    self.retry_count = 2
                    self.sock.close()
                    sleep(5)
                    self.connect()
                sleep(.01)
            except BlockingIOError:
                pass
            except ValueError:
                log.exception(f'Dead connection detected. Reconnecting')
                self.retry_count = 2
                self.sock.close()
                sleep(5)
                self.connect()
            except KeyboardInterrupt:
                self.sock.close()
                _exit(0)
            except:
                log.exception('FUCK!')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('lines', action='store', help='number of lines in log history to show')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose (client debug)')
    parser.add_argument('--html', action='store_true', help='html output')
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

    argsdebug = 1 if args.debug else 0
    argstrace = 1 if args.trace else 0
    argsextend = 1 if args.extend else 0
    argsstartexit = 1 if args.startexit else 0
    argscommands = 1 if args.commands else 0
    argsvotes = 1 if args.votes else 0
    argsjoinleave = 1 if args.joinleave else 0
    argsfollow = 1 if args.nofollow else 0
    argsadmin = 1 if args.noadmin else 0

    if args.showonly != 'ALL':
        argsshowonly = f'{args.showonly:<8}!'
    else:
        argsshowonly = f'ALL     !'
    if args.server != 'ALL':
        argsserver = f'{args.server:<5}'
    else:
        argsserver = f'ALL   '
    logwatch = LogClient(args.lines, argsdebug, argstrace, argsextend, argsstartexit, argscommands, argsvotes, argsjoinleave, argsfollow, argsadmin, argsshowonly, argsserver, args.html)
    # logwatch.connect()
    logwatch.connect()
    while True:
        try:
            print(logwatch.getline())
        except KeyboardInterrupt:
            logwatch.close()
            _exit(0)
        else:
            sleep(.05)


if __name__ == '__main__':
    main()
