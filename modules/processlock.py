import os
import sys
import fcntl
from loguru import logger as log
import atexit
import socket

hstname = socket.gethostname()

ppid = str(os.getpid())


def cleanName(filename):
    filename = os.path.basename(filename)
    filename = filename.rsplit('.', 1)[0]
    return filename


def plock():
    def aquireLock():
        if not os.path.isfile(lockfile):
            os.mknod(lockfile, mode=0o600)
        try:
            fcntl.lockf(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            return False
        except:
            log.exception('General error trying to lock process to file {}. exiting.'.format(lockfile))
            exit(1)
        else:
            log.debug('Process has been locked to file {} with PID [{}]'.format(lockfile, ppid))
            return True
    if aquireLock():
        atexit.register(unlock)
        pidfile = f'{lpath}/{cleanName(sys.argv[0])}.pid'
        with open(pidfile, 'w') as pfile:
            pfile.write(ppid)
        return True
    else:
        log.error(f'Trying to start, but already running on pid {ppid}')
        exit(1)


def unlock():
    fcntl.flock(lock_handle, fcntl.LOCK_UN)
    lock_handle.close()
    if os.path.isfile(lockfile):
        os.remove(lockfile)


if os.access('/tmp', os.W_OK) and os.path.isdir('/tmp'):
    lpath = '/tmp'
else:
    log.critical('Cannot find a valid place to put the lockfile. Exiting')
    exit(1)

lockfile = f'{lpath}/{cleanName(sys.argv[0])}.lock'

lock_handle = open(lockfile, 'w')
