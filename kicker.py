#!/usr/bin/python3

import time, socket, logging, sqlite3, threading, subprocess
from datetime import datetime, timedelta
from configparser import ConfigParser
from configreader import *

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

numinstances = int(config.get('general', 'instances'))
global instance
instance = [dict() for x in range(numinstances)]

instr = ''
for each in range(numinstances):
    a = config.get('instance%s' % (each), 'name')
    b = config.get('instance%s' % (each), 'logfile')
    instance[each] = {'name':a,'logfile':b}
    if instr == '':
        instr = '%s' % (a)
    else:
        instr=instr + ', %s' % (a)

def kicker(inst):
    log.debug(f'starting kicklist kicker thread for {inst}')
    while True:
        try:
            conn2 = sqlite3.connect(sqldb)
            c2 = conn2.cursor()
            c2.execute('SELECT * FROM kicklist WHERE instance = ?', [inst])
            kicked = c2.fetchone()
            c2.close()
            conn2.close()
            if kicked:
                log.info(f'kicking user {kicked[1]} from server {inst} on kicklist')
                subprocess.run("""arkmanager rconcmd 'kickplayer %s' @%s""" % (kicked[1], inst), shell=True)
                conn2 = sqlite3.connect(sqldb)
                c2 = conn2.cursor()
                c2.execute('DELETE FROM kicklist WHERE steamid = ?', [kicked[1]])    
                conn2.commit()
                c2.close()
                conn2.close()
            time.sleep(2)
        except:
            log.critical('Critical Error in kick watcher!', exc_info=True)
            if c2 in vars():
                c2.close()
            if conn2 in vars():
                conn2.close()
