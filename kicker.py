from modules.dbhelper import dbquery, dbupdate
from modules.servertools import serverexec
from time import sleep
from loguru import logger as log


def stopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Kicker thread has ended')
            exit(0)
        sleep(1)


@log.catch
def kicker_thread(inst, dtime, stop_event):
    log.debug(f'Kicker thread starting for {inst}')
    while not stop_event.is_set():
        kicked = dbquery("SELECT * FROM kicklist WHERE instance = '%s'" % (inst,), fetch='one')
        if kicked:
            log.log('KICK', f'Kicking user [{kicked[1].title()}] from server [{inst.title()}] on kicklist')
            serverexec(['arkmanager', 'rconcmd', f'kickplayer {kicked[1]}', f'@{inst}'], nice=10, null=True)
            dbupdate("DELETE FROM kicklist WHERE steamid = '%s'" % (kicked[1],))
        stopsleep(dtime, stop_event)
    log.debug('Kicker thread has ended')
    exit(0)
