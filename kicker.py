#!/usr/bin/python3

import socket, logging, subprocess
from time import sleep
from dbhelper import dbquery, dbupdate

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def kicker(inst):
    log.debug(f'starting kicklist kicker thread for {inst}')
    while True:
        try:
            kicked = dbquery('SELECT * FROM kicklist WHERE instance = "%s"' % (inst,), fetch='one')
            if kicked:
                log.info(f'kicking user {kicked[1]} from server {inst} on kicklist')
                subprocess.run("""arkmanager rconcmd 'kickplayer %s' @%s""" % (kicked[1], inst), shell=True)
                dbupdate('DELETE FROM kicklist WHERE steamid = "%s"' % (kicked[1],))
        except:
            log.critical('Critical Error in kick watcher!', exc_info=True)
        sleep(5)
