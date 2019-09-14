import argparse
import fcntl
import subprocess
import threading
from pathlib import Path
from time import sleep

import configparser
import modules.logging
import psutil
import redis
from loguru import logger as log

from modules.configreader import hstname, redis_host, redis_port

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_true', help='verbose output (debug)')

pyarkpidfile = Path('/run/pyark.pid')
pyarklockfile = Path('/run/pyark.lock')
pyarkcfgfile = Path('/home/ark/pyark.cfg')

args = parser.parse_args()


def redislistener():
    r = redis.Redis(host=redis_host, port=redis_port, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe([f'{hstname.lower()}-commands'])
    for response in pubsub.listen():
        if response['type'] == 'message' and response['channel'].decode() == f'{hstname.lower()}-commands':
            log.debug(f'Recieved Server Command: {response["data"].decode()}')
            if response['data'].decode() == 'restart':
                subprocess.run(['systemctl', 'restart', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode() == 'stop':
                subprocess.run(['systemctl', 'stop', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode() == 'start':
                subprocess.run(['systemctl', 'start', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode() == 'gitpull':
                subprocess.run(['git', 'pull'], shell=True, cwd='/home/ark/pyark', capture_output=False)
            elif response['data'].decode() == 'restartwatchdog':
                subprocess.run(['systemctl', 'start', 'arkwatchdog'], shell=False, capture_output=False)
            elif response['data'].decode().startswith('loglevel'):
                loglevel = response['data'].decode().split(':')[1]
                config = configparser.RawConfigParser()
                config.optionxform = str
                config.read(pyarkcfgfile)
                if config.get('general', 'loglevel') != loglevel.upper():
                    log.debug(f"Changing pyark loglevel from [{config.get('general', 'loglevel')}] to [{loglevel.upper()}] on [{hstname}]")
                    config.set('general', 'loglevel', loglevel.upper())
                    with open(str(pyarkcfgfile), 'w') as configfile:
                        config.write(configfile)
                    sleep(1)
                    subprocess.run(['systemctl', 'restart', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode().startswith('setcfg'):
                respsplit = response['data'].decode().split(':')
                if len(respsplit) == 4:
                    section = respsplit[1]
                    key = respsplit[2]
                    value = respsplit[3]
                    config = configparser.RawConfigParser()
                    config.optionxform = str
                    config.read(pyarkcfgfile)
                    if config.has_section(section):
                        if config.get(section, key) is None:
                            log.info(f"Adding pyark config entry [{key}] in [{section}] from [{config.get(key)}] to [{value}] on [{hstname}]")
                            config.set(section, key, value)
                            with open(str(pyarkcfgfile), 'w') as configfile:
                                config.write(configfile)
                        elif config.get(section, key) != value:
                            log.info(f"Changing pyark config entry [{key}] in [{section}] from [{config.get(key)}] to [{value}] on [{hstname}]")
                            config.set(section, key, value)
                            with open(str(pyarkcfgfile), 'w') as configfile:
                                config.write(configfile)
                    else:
                        log.warning(f"Section [{section}] does not exist to add/change option [{key}] on [{hstname}]")

            elif response['data'].decode().startswith('delcfg'):
                respsplit = response['data'].decode().split(':')
                if len(respsplit) == 3:
                    section = respsplit[1]
                    key = respsplit[2]
                    config = configparser.RawConfigParser()
                    config.optionxform = str
                    config.read(pyarkcfgfile)
                    if config.has_section(section) and config.has_option(key):
                        if config.get(section, key) is None:
                            log.warning(f"Option [{key}] in [{section}] does not exist to remove on [{hstname}]")
                        elif config.get(section, key):
                            log.info(f"Removing pyark config entry [{key}] in [{section}] value [{config.get(key)}] on [{hstname}]")
                            config.set(section, key, value)
                            with open(str(pyarkcfgfile), 'w') as configfile:
                                config.write(configfile)
                    else:
                        log.warning(f"Option [{key}] or [{section}] does not exist to remove on [{hstname}]")


thread = threading.Thread(name='redislistener', target=redislistener, args=(), daemon=True)
log.debug('Starting redis command listener thread')
thread.start()

log.debug('Starting pyark process watch')
count = 1
while True:
    try:
        if not pyarkpidfile.is_file() or not pyarklockfile.is_file():
            if count == 1:
                log.warning('Pyark not running (pid and/or lock files missing)')
                count += 1
        else:
            pyarkpid = pyarkpidfile.read_text()
            if pyarkpid == '' or pyarkpid is None:
                if count == 1:
                    log.error(f'Pyark process is not running. (Empty pid found in pidfile)')
                count += 1
            else:
                if not psutil.pid_exists(int(pyarkpid)):
                    if count == 1:
                        log.error(f'Pyark process is not running. No process at pid [{pyarkpid}]')
                    count += 1
                else:
                    log.trace('pyark process passed pid check')

            try:
                lockhandle = open(str(pyarklockfile), 'w')
                fcntl.lockf(lockhandle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                log.trace('pyark process passed file lock check')
            else:
                fcntl.flock(lockhandle, fcntl.LOCK_UN)
                lockhandle.close()
                if count == 1:
                    log.error(f'Pyark process [{pyarkpid}] is not running. (Lockfile not locked)')
    except:
        if count == 1:
            log.exception(f'Error in arkwatchdog main loop!!')
            count += 1

    if count == 6:
        count = 1

    sleep(60)
