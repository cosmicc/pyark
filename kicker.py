#!/usr/bin/python3

import time, socket, logging, sqlite3, subprocess
from configreader import sqldb

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


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
