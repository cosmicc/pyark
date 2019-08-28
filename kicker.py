from modules.dbhelper import dbquery, dbupdate
from modules.servertools import serverexec
from time import sleep
from loguru import logger as log


@log.catch
def kicker(inst, dtime):
    log.debug(f'starting kicklist kicker thread for {inst}')
    while True:
        try:
            kicked = dbquery("SELECT * FROM kicklist WHERE instance = '%s'" % (inst,), fetch='one')
            if kicked:
                log.log('KICK', f'Kicking user [{kicked[1].title()}] from server [{inst.title()}] on kicklist')
                serverexec(['arkmanager', 'rconcmd', f'kickplayer {kicked[1]}', f'@{inst}'], nice=10, null=True)
                dbupdate("DELETE FROM kicklist WHERE steamid = '%s'" % (kicked[1],))
        except:
            log.exception('Critical Error in kick watcher!')
        sleep(dtime)
