from modules.dbhelper import dbupdate, dbquery, statsupdate
from modules.players import getplayersonline, getactiveplayers, getnewplayers, gethitnruns
from modules.timehelper import Secs, Now
from timebetween import is_time_between
from datetime import datetime
from datetime import time as dt
from time import time, sleep
from loguru import logger as log


def checkiftableexists(inst):
    dbupdate("CREATE TABLE IF NOT EXISTS %s (date timestamp, value smallint)" % (inst,), db='statsdb')


def addvalue(inst, value):
    statsupdate(inst, value)


def flushold(tinst):  # not implimented
    aweek = int(time()) - Secs['week']
    dbupdate("DELETE FROM %s WHERE date < '%s'" % (tinst, aweek), db='statsdb')


@log.catch
def oscollect(dtime):
    log.debug(f'starting online stats collectors')
    stinst = dbquery('SELECT name FROM instances', fmt='list', single=True)
    for each in stinst:
        checkiftableexists(each)
    while True:
        try:
            t, s, e = datetime.now(), dt(9, 0), dt(9, 5)  # 9:00am GMT (5:00AM EST)
            dailycollect = is_time_between(t, s, e)
            if dailycollect:
                dbupdate("INSERT INTO clusterstats (timestamp, dailyactive, weeklyactive, monthlyactive, dailyhnr, dailynew) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (Now(fmt='dt'), len(getactiveplayers(Secs['day'])), len(getactiveplayers(Secs['week'])), len(getactiveplayers(Secs['month'])), len(gethitnruns(Secs['day'])), len(getnewplayers(Secs['day']))), db='statsdb')
            for each in stinst:
                addvalue(each, getplayersonline(each, fmt='count'))
        except:
            log.exception('Critical Error in Online Stat Collector!')
        sleep(dtime)
