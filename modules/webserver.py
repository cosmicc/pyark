#!/usr/bin/python3.6

from loguru import logger as log
from modules.configreader import hstname, webserver_ip, webserver_port
from web import socketio

log.configure(extra={'hostname': hstname, 'instance': 'MAIN'})


def webserv(app):
    log.log('START', f'Starting Web Server on IP: {webserver_ip} PORT: {webserver_port}')
    socketio.run(app, host=webserver_ip, port=webserver_port)
