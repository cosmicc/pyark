#!/usr/bin/env python3.6

import argparse
import modules.tail
import json
import os
import socket
import pickle

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-d', '--debug', action='store_true', help='Debug Log')
parser.add_argument('-t', '--trace', action='store_true', help='Trace Log')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose')

args = parser.parse_args()

HEADERSIZE = 5


def sendmsg(msgg):
    msg = pickle.dumps(msgg)
    msg = bytes(f'{len(str(msg)):<{HEADERSIZE}}', "utf-8") + msg
    clientsocket.send(msg)


def endtail(f, lines=1, _buffer=4098):
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


def processlogline(line):
    try:
        line = line.strip('\x00')
        data = json.loads(line.strip(), strict=False)
        #print(f'##{data}')
        if not args.verbose and (data["record"]["level"]["name"] != "START" or data["record"]["level"]["name"] != "EXIT"):
            sendmsg(data)
        elif args.verbose:
            sendmsg(data)
    except json.decoder.JSONDecodeError:
        sendmsg(f'{repr(line)}')


def main():
    global clientsocket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 1024))
    s.listen(5)
    tlog = modules.tail.Tail('/home/ark/shared/logs/pyark/pyarklog.json')
    while True:
        clientsocket, address = s.accept()
        print(f"Connection from {address} has been established")
        startconnect()
        tlog.register_callback(processlogline)


def startconnect():
        #watchlog(False)
        logpath = f'/home/ark/shared/logs/pyark/pyarklog.json'
        with open(logpath) as f:
            lines = endtail(f, lines=50)
            for line in lines:
                processlogline(line)



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        os._exit(0)
