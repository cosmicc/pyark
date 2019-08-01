#!/usr/bin/env python3.6

import modules.tail
import json
import os
import socket
import threading
import argparse
import sys
from datetime import datetime
from queue import Queue
from time import sleep
from loguru import logger as log
from sh import tail as tailer

HEADERSIZE = 8
log_file = '/home/ark/shared/logs/pyark/logserver.log'

log_queue = Queue()
log.remove()
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='count', default=0)
args = parser.parse_args()

if args.verbose == 0:
    log.add(sink=sys.stderr, level=50, backtrace=False, diagnose=False, colorize=True)
elif args.verbose == 3:
    log.add(sink=sys.stdout, level=5, backtrace=True, diagnose=True, colorize=True)
elif args.verbose == 2:
    log.add(sink=sys.stdout, level=10, backtrace=True, diagnose=True, colorize=True)
elif args.verbose == 1:
    log.add(sink=sys.stdout, level=20, backtrace=True, diagnose=True, colorize=True)
else:
    log.add(sink=sys.stderr, level=50, backtrace=False, diagnose=False, colorize=True)

log.add(sink=log_file, level=20, enqueue=False, backtrace=True, diagnose=True, serialize=False, colorize=False)


def checkconnections():
    for client in client_threads:
        if not client['thread'].is_alive():
            log.info(f'Dead thread detected. Removing: {client["address"]}')
            client_threads.remove(client)


def logwatcher():
    tlog = modules.tail.Tail('/home/ark/shared/logs/pyark/pyarklog.json')
    tlog.register_callback(processlogline)
    tlog.follow()


def clientloop(clientsocket, addr):
    log.debug(f'New thread started for client: {addr}')
    for client in client_threads:
        if client['address'] == addr:
            thisqueue = client['queue']
            log.trace(f'found queue: {thisqueue}')
    now = int(datetime.now().timestamp())
    header = clientsocket.recv(32).decode("utf-32")
    linerequest = int(header.split('!')[1])
    loglevel = int(header.split('!')[2])
    newdict = {}
    for num, client in enumerate(client_threads):
        if client['address'] == addr:
            newdict = {'address': client['address'], 'thread': client['thread'], 'queue': client['queue'], 'loglevel': loglevel}
            client_threads.pop(num)
            client_threads.append(newdict)
    log.debug(f'Requested playback of {linerequest} lines and loglevel {loglevel}')
    try:
        for line in tailer(f"-n {linerequest}", "/home/ark/shared/logs/pyark/pyarklog.json", _iter=True):
            processlogline(line.strip(), single=addr)
    except:
        log.exception('SHIT')
    log.debug('main loop started')
    while True:
        exitwatch = True
        for client in client_threads:
            if client['address'] == addr:
                exitwatch = False
        if exitwatch:
            log.debug(f'Ending thread for port {addr}')
            exit(0)
        if int(datetime.now().timestamp()) - now >= 15:
            sendmsg(clientsocket, addr, '!')
            now = int(datetime.now().timestamp())

        if not thisqueue.empty():
            logline = thisqueue.get()
            log.trace(f'got from queue: {logline}')
            sendmsg(clientsocket, addr, logline)
        else:
            sleep(.01)


def sendmsg(clientsocket, addr, logline):
    global client_threads
    try:
        if logline == '!':
            msg = f'{len(logline):<{HEADERSIZE}}' + logline
            clientsocket.send(bytes(msg, "utf-32"))
        else:
            msg = logline.strip()
            msg = f'{len(msg):<{HEADERSIZE}}' + msg
            log.trace(f'sending: {len(msg)} {msg}')
            clientsocket.send(bytes(msg, "utf-32"))
        sleep(.1)
    except BrokenPipeError:
        for num, client in enumerate(client_threads):
            if int(client['address']) == int(addr):
                log.warning(f'Dead connection detected. Removing: {client["address"]}')
                client_threads.pop(num)


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


def processlogline(line, single=False):
    try:
        line = line.strip('\x00')
        data = json.loads(line.strip(), strict=False)
        log.trace(f'Got from log: {data["text"]}')
        if data["record"]["level"]["name"] != "START" and data["record"]["level"]["name"] != "EXIT":
            for client in client_threads:
                if not single or single == client['address']:
                    if client['loglevel'] > 0:
                        msgapp = f' \u001b[38;5;109m{data["record"]["module"]}:{data["record"]["function"]}:{data["record"]["line"]}'
                        data["text"] = data["text"].strip() + msgapp
                    log.trace(f'putting in queue for {client["address"]}')
                    client["queue"].put(data["text"].strip())
        else:
            for client in client_threads:
                if client['loglevel'] > 0:
                    if not single or single == client['address']:
                        if client['loglevel'] > 0:
                            msgapp = f' \u001b[38;5;109m{data["record"]["module"]}:{data["record"]["function"]}:{data["record"]["line"]}'
                            data["text"] = data["text"].strip() + msgapp
                        log.debug(f'putting in queue for {client["address"]}')
                        client["queue"].put(data["text"].strip())
    except json.decoder.JSONDecodeError:
        log.exception(f'DECODE ERROR: {repr(line)}')


def main():
    global client_threads
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('172.31.250.115', 1024))
    log.debug('Starting log tail thread')
    logwatch_thread = threading.Thread(target=logwatcher)
    logwatch_thread.start()
    client_threads = []
    cleanup_thread = threading.Thread(target=checkconnections)
    cleanup_thread.start()
    log.info('Server started, waiting for clients...')
    s.listen(3)
    while True:
        clientsocket, address = s.accept()
        log.info(f"Connection from {address[0]}:{address[1]} has been established")
        nthread = threading.Thread(target=clientloop, args=(clientsocket, address[1]))
        client_threads.append({'address': address[1], 'thread': nthread, 'queue': Queue(), 'loglevel': 0})
        log.trace(client_threads)
        nthread.start()

    s.close()


def startconnect():
        # watchlog(False)
        logpath = f'/home/ark/shared/logs/pyark/pyarklog.json'
        with open(logpath) as f:
            lines = endtail(f, lines=1)
            for line in lines:
                processlogline(line)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        for client in client_threads:
            client_threads.remove(client)
        sleep(2)
        os._exit(0)
