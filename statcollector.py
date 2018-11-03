from dbhelper import dbupdate, dbquery, getplayersonline
from time import time, sleep
from timehelper import Secs
import logging
import socket

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def checkiftableexists(inst):
    dbupdate("CREATE TABLE IF NOT EXISTS %s (date INT, value SMALLINT)" % (inst,), db='statsdb')


def addvalue(inst, value):
    ldate = int(time())
    dbupdate("INSERT INTO %s (date, value) VALUES ('%s', '%s')" % (inst, ldate, value), db='statsdb')


def flushold(tinst):  # not implimented
    aweek = int(time()) - Secs['week']
    dbupdate("DELETE FROM %s WHERE date < '%s'" % (tinst, aweek), db='statsdb')


def oscollect():
    log.debug(f'starting online stats collectors')
    stinst = dbquery('SELECT name FROM instances', fmt='list', single=True)
    for each in stinst:
        checkiftableexists(each)
    while True:
        try:
            for each in stinst:
                addvalue(each, getplayersonline(each, fmt='count'))
        except:
            log.critical('Critical Error in Online Stat Collector!', exc_info=True)
        sleep(Secs['5min'])
