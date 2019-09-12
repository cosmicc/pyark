import subprocess
import threading
from time import sleep

import fcntl
import modules.logging
import psutil
import redis
from loguru import logger as log
from modules.configreader import hstname, redis_host, redis_port
from pathlib import Path

pyarkpidfile = Path('/run/pyark.pid')
pyarklockfile = Path('/run/pyark.lock')


def redislistener():
    r = redis.Redis(host=redis_host, port=redis_port, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe([f'{hstname.lower()}-commands'])
    for response in pubsub.listen():
        if response['type'] == 'message' and response['channel'].decode() == f'{hstname.lower()}-commands':
            if response['data'].decode() == 'restart':
                subprocess.run(['systemctl', 'restart', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode() == 'stop':
                subprocess.run(['systemctl', 'stop', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode() == 'start':
                subprocess.run(['systemctl', 'start', 'pyark'], shell=False, capture_output=False)
            elif response['data'].decode() == 'gitpull':
                subprocess.run(['git', 'pull'], shell=True, cwd='/home/ark/pyark', capture_output=False)
            elif response['data'].decode() == 'restartwatchdog':
                subprocess.run(['systemctl', 'start', 'arkwatchdog'], shell=True, cwd='/home/ark/pyark', capture_output=False)


thread = threading.Thread(name='redislistener', target=redislistener, args=(), daemon=True)
thread.start()

log.debug('Starting the pyark process watch')
while True:
    try:
        if pyarkpidfile.is_file() and pyarklockfile.is_file():
            pyarkpid = pyarkpidfile.read_text()
            if not psutil.pid_exists(int(pyarkpid)):
                log.error(f'Pyark process [{pyarkpid}] is not running. (No process at pid)')
            else:
                log.debug('pyark process passed pid check')
            try:
                lockhandle = open(str(pyarklockfile), 'w')
                fcntl.lockf(lockhandle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                log.debug('pyark process passed file lock check')
                pass
            else:
                fcntl.flock(lockhandle, fcntl.LOCK_UN)
                lockhandle.close()
                log.error(f'Pyark process [{pyarkpid}] is not running. (Lockfile not locked)')
        else:
            log.warning('Pyark not running (pid and/or lock files missing')
    except:
        log.exception(f'Error in arkwatchdog main loop!!')
    sleep(60)
