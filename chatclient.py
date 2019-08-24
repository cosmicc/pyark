#!/usr/bin/env python3.6

import modules.tail
from loguru import logger as log
from time import sleep
from modules.timehelper import estshift
import argparse
import os
import threading
from dateutil.parser import parse as dtparse
from os import _exit
from colored import fg
import sys
from ansi2html import Ansi2HTMLConverter


class ChatClient():
    def __init__(self, server, lines, html):
        self.chatlog = '/home/ark/shared/logs/pyark/clusterchat.log'
        self.players = {}
        self.pcolors = [45, 85, 105, 155, 225, 215, 195, 175, 115, 145, 185, 165, 205]
        self.pcolorindex = 0
        self.server = server
        self.lines = lines
        self.messages = []
        self.html = html
        if self.html:
            self.ansiconverter = Ansi2HTMLConverter()

    def start(self):
        self.thread = threading.Thread(target=self.chatwatcherthread)
        self.thread.start()

    def gettail(self):
        f = open(self.chatlog)
        for line in endtail(f, lines=int(self.lines)):
            self.processchatline(line)
        f.close()

    def getline(self):
        if len(self.messages) > 0:
            msg = self.messages[0]
            self.messages.remove(msg)
            return msg
        else:
            return None

    def chatwatcherthread(self):
        self.gettail()
        while True:
            count = 1
            if not os.path.isfile(self.chatlog):
                if count == 1 or count == 3600:
                    log.warning('clusterchat.log not found. waiting for it..')
                sleep(1)
                count += 1
            else:
                tlog = modules.tail.Tail(self.chatlog)
                tlog.register_callback(self.processchatline)
                log.debug('clusterchat.log found. following it..')
                tlog.follow()

    def processchatline(self, line):
        linesplit = line.split("|")
        if len(linesplit) > 1:
            ctime = linesplit[0]
            cserver = linesplit[1].strip()
            cplayer = linesplit[2].strip()
            cmsg = linesplit[3].strip()
            cdt = estshift(dtparse(ctime))
            cdtf = cdt.strftime("%a %I:%M%p")
            if cplayer not in self.players:
                ncolor = int(self.pcolors[self.pcolorindex])
                if self.pcolorindex == len(self.pcolors) - 1:
                    self.pcolorindex = 0
                self.pcolorindex += 1
                self.players.update({cplayer: ncolor})
            else:
                ncolor = self.players[cplayer]
            newline = '%s%s [%s] %s: %s%s' % (fg(ncolor), cdtf, cserver.title(), cplayer.title(), cmsg, fg(0))
            if self.server == 'ALL':
                if self.html:
                    self.messages.append(self.ansiconverter.convert(newline, full=False, ensure_trailing_newline=False))
                else:
                    self.messages.append(newline)
            else:
                if self.server.lower() == cserver.lower():
                    if self.html:
                        self.messages.append(self.ansiconverter.convert(newline, full=False, ensure_trailing_newline=False))
                    else:
                        self.messages.append(newline)


def endtail(f, lines=1, _buffer=12288):
    """Tail a file and get X lines from the end"""
    lines_found = []
    block_counter = -1
    while len(lines_found) < lines:
        try:
            f.seek(block_counter * _buffer, os.SEEK_END)
        except IOError:  # either file is too small, or too many lines requested
            f.seek(0)
            lines_found = f.readlines()
            break

        lines_found = f.readlines()
        block_counter -= 1

    return lines_found[-lines:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('lines', action='store', help='number of lines in log history to show')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose (client debug)')
    parser.add_argument('-s', '--server', action='store', default='ALL', help='show only chat from this server')

    args = parser.parse_args()

    simplelogformat = '{message}'

    log.remove()
    llevel = 'DEBUG' if args.verbose else 'INFO'
    log.add(sys.stderr, level=llevel, format=simplelogformat)
    chatwatch = ChatClient(args.server, args.lines, False)
    chatwatch.start()
    while True:
        msg = chatwatch.getline()
        if msg is not None and msg != 'None':
            print(msg)
        sleep(.1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        _exit(0)
    except:
        log.exception('FUCK!!!')
