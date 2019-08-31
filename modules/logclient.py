import socket
from datetime import datetime
from os import _exit
from time import sleep

from ansi2html import Ansi2HTMLConverter
from loguru import logger as log
from modules.instances import instancelist


def loggerchat(chatline):
    from modules.instances import serverchat
    cmd = chatline.split(' ')[0][:1].strip()
    who = chatline.split(' ')[0][1:].strip().lower()
    cmdremove = len(who) + 1
    msg = chatline[cmdremove:].strip()
    if (cmd == '@' and who == 'all') or (cmd == '#' and who == 'all'):
        serverchat(msg, inst='ALL', whosent='Admin', private=False, broadcast=False)
    elif cmd == '#':
        serverchat(msg, inst=who, whosent='Admin', private=False, broadcast=False)
    elif cmd == '@':
        if who in instancelist():
            serverchat(msg, inst=who, whosent='Admin', private=False, broadcast=False)
        else:
            serverchat(msg, inst='ALL', whosent=who, private=True, broadcast=False)
    elif cmd == '!':
        serverchat(msg, inst=who, whosent='Admin', private=False, broadcast=True)


class LogClient():
    def __init__(self, lines, argsdebug, argstrace, argsextend, argsstartexit, argscommands, argserrorsonly, argsjoinleave, argsfollow, argserrors, showonly, server, html):
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
        self.errorsonly = argserrorsonly
        self.joinleave = argsjoinleave
        self.follow = argsfollow
        self.errors = argserrors
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
        log.debug(f'Connected to log server {self.IP}:{self.PORT}')
        self.sock.setblocking(False)
        self.retrycount = 1
        self.showonly = f'{self.showonly:<8}!'
        self.server = f'{self.server:<5}'
        if self.first_time:
            plines = self.lines
        else:
            plines = 0
        head = f'!{plines:>3}!{self.debug}!{self.trace}!{self.extend}!{self.errors}!{self.startexit}!{self.commands}!{self.errorsonly}!{self.joinleave}!{self.follow}!{self.server}!{self.showonly}'
        log.trace(f'Header: {head}')
        self.sock.send(bytes(head, "utf-8"))
        self.timeout_timer = int(datetime.now().timestamp())
        self.first_time = False

    def getline(self):
        try:
            header = self.sock.recv(self.HEADERSIZE)
            log.trace(header)
            log.trace(header.decode("utf-32"))
            msgsize = int(header.decode("utf-32"))
            msg = self.sock.recv(msgsize)
            log.trace(f'reported size: {msgsize}  actual size: {len(msg)}')
            decodedmsg = msg.decode("utf-32")
            log.trace(f'decoded size: {len(decodedmsg)}')
            self.timeout_timer = int(datetime.now().timestamp())
            self.new_msg = True
            self.full_msg = ''
            if msgsize == 8:
                    if decodedmsg == '!':
                        log.trace('HEARTBEAT Recieved')
                        self.timeout_timer = int(datetime.now().timestamp())
                        self.full_msg = ''
                        self.new_msg = True
            elif msgsize == 12:
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
        except BlockingIOError:
            sleep(.01)
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
