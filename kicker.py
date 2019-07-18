from modules.dbhelper import dbquery, dbupdate
from time import sleep
from loguru import logger as log
import subprocess


@log.catch
def kicker(inst):
    log.debug(f'starting kicklist kicker thread for {inst}')
    while True:
        try:
            kicked = dbquery("SELECT * FROM kicklist WHERE instance = '%s'" % (inst,), fetch='one')
            if kicked:
                log.info(f'kicking user {kicked[1]} from server {inst} on kicklist')
                subprocess.run("""arkmanager rconcmd 'kickplayer %s' @%s""" % (kicked[1], inst), shell=True)
                dbupdate("DELETE FROM kicklist WHERE steamid = '%s'" % (kicked[1],))
        except:
            log.exception('Critical Error in kick watcher!')
        sleep(5)
