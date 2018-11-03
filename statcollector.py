from dbhelper import dbupdate, getplayersonline, db_getvalue
from time import time, sleep
from timehelper import Secs
import logging
import socket

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def checkiftableexists(inst):
    dbupdate("CREATE TABLE IF NOT EXISTS '%s' (date INT, value SMALLINT)" % (inst,), sdb='statsdb')


def addvalue(inst, value):
    ldate = int(time())
    dbupdate("INSERT INTO '%s' (date, value) VALUES ('%s', '%s')" % (inst, ldate, value), sdb='statsdb')


def flushold(tinst):  # not implimented
    aweek = int(time()) - Secs['week']
    dbupdate("DELETE FROM '%s' WHERE date < '%s'" % (tinst, aweek), sdb='statsdb')


def oscollect():
    log.debug(f'starting online stats collector for instances {statinst}')
    for each in db_getvalue('name', 'instance')
        checkiftableexists(each)
    while True:
        try:
            for each in statinst:
                addvalue(each, getplayersonline(each, qtype='count'))
        except:
            log.critical('Critical Error in Online Stat Collector!', exc_info=True)
        sleep(Secs['5min'])
