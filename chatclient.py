#!/usr/bin/env python3.6

import modules.tail
from loguru import logger as log
from datetime import datetime
from time import sleep
from modules.timehelper import estshift
import argparse
import os
import threading
from dateutil.parser import parse as dtparse
from os import _exit
from colored import fg
import sys

parser = argparse.ArgumentParser()
parser.add_argument('lines', action='store', help='number of lines in log history to show')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose (client debug)')
parser.add_argument('-s', '--server', action='store', default='ALL', help='show only chat from this server')

args = parser.parse_args()

chatlog = '/home/ark/shared/logs/pyark/clusterchat.log'

simplelogformat = '{message}'

log.remove()
llevel = 'DEBUG' if args.verbose else 'INFO'
log.add(sys.stderr, level=llevel, format=simplelogformat)

players = {}
pcolors = [45, 85, 105, 155, 225, 215, 195, 175, 115, 145, 185, 165, 205]
pcolorindex = 0


def chatwatcher():
    while True:
        count = 1
        if not os.path.isfile(chatlog):
            if count == 1 or count == 3600:
                log.warning('clusterchat.log not found. waiting for it..')
            sleep(1)
            count += 1
        else:
            tlog = modules.tail.Tail(chatlog)
            tlog.register_callback(processchatline)
            log.debug('clusterchat.log found. following it..')
            tlog.follow()


def processchatline(line):
    global players
    global pcolorindex
    linesplit = line.split("|")
    if len(linesplit) > 1:
        ctime = linesplit[0]
        cserver = linesplit[1].strip()
        cplayer = linesplit[2].strip()
        cmsg = linesplit[3].strip()
        cdt = estshift(dtparse(ctime))
        cdtf = cdt.strftime("%a %I:%M:%S%p")
        if cplayer not in players:
            ncolor = int(pcolors[pcolorindex])
            if pcolorindex == len(pcolors) - 1:
                pcolorindex = 0
            pcolorindex += 1
            players.update({cplayer: ncolor})
        else:
            ncolor = players[cplayer]
        newline = '%s%s [%s] %s - %s%s' % (fg(ncolor), cdtf, cserver.title(), cplayer, cmsg, fg(0))
        if args.server == 'ALL':
            log.info(newline)
        else:
            if args.server.lower() == cserver.lower():
                log.info(newline)


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
    chatwatch_thread = threading.Thread(target=chatwatcher)
    chatwatch_thread.start()
    try:
        f = open(chatlog)
        for line in endtail(f, lines=int(args.lines)):
            processchatline(line)
        f.close()
    except:
        log.exception('FUCK!')

    while True:
        sleep(.1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        _exit(0)
    except:
        log.exception('FUCK!!!')
