from dbhelper import dbquery, dbupdate
from time import sleep
from timehelper import Now
import logging
import socket
import subprocess

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def gchatrelay(inst):
    while True:
        try:
            cbuff = dbquery('SELECT * FROM globalbuffer')
            if cbuff:
                for each in cbuff:
                    if each[1] == 'ALERT' and each[2] == 'ALERT' and float(each[4]) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (each[3], inst), shell=True)
                    elif each[1] == inst and each[2] == 'ALERT' and float(each[4]) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (each[3], inst), shell=True)
                    elif each[1] != inst and each[2] != 'ALERT' and float(each[4]) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s@%s: %s" @%s'
                                       % (each[2].capitalize(), each[1].capitalize(), each[3], inst), shell=True)
                    if float(each[4]) < Now() - 10:
                        dbupdate('DELETE FROM globalbuffer WHERE id = "%s"' % (each[0],))
            sleep(3)
        except:
            log.critical('Critical Error in Global Chat Relayer!', exc_info=True)
