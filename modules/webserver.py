#!/usr/bin/python3.6

from modules.configreader import webserver_ip, webserver_port, hstname
from web import socketio
from loguru import logger as log

log.configure(extra={'hostname': hstname, 'instance': 'MAIN'})


def webserv(app):
    log.log('START', f'Starting Web Server on IP: {webserver_ip} PORT: {webserver_port}')
    socketio.run(app, host=webserver_ip, port=webserver_port)
