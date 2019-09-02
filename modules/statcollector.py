from datetime import datetime
from datetime import time as dt
from time import sleep, time

from loguru import logger as log
from timebetween import is_time_between

from modules.dbhelper import dbquery, dbupdate, statsupdate
from modules.players import getactiveplayers, gethitnruns, getnewplayers, getplayersonline
from modules.timehelper import Now, Secs


def stopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Statcollector thread has ended')
            exit(0)
        sleep(1)


def addvalue(inst, value):
    statsupdate(inst, value)


def flushold(tinst):  # not implimented
    aweek = int(time()) - Secs['week']
    dbupdate("DELETE FROM %s WHERE date < '%s'" % (tinst, aweek), db='statsdb')


@log.catch
def statcollector_thread(dtime, stop_event):
    log.debug(f'Statcollector thread is starting')
    stinst = dbquery('SELECT name FROM instances', fmt='list', single=True)
    while not stop_event.is_set():
        t, s, e = datetime.now(), dt(9, 0), dt(9, 5)  # 9:00am GMT (5:00AM EST)
        dailycollect = is_time_between(t, s, e)
        if dailycollect:
            dbupdate("INSERT INTO clusterstats (timestamp, dailyactive, weeklyactive, monthlyactive, dailyhnr, dailynew) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (Now(fmt='dt'), len(getactiveplayers(Secs['day'])), len(getactiveplayers(Secs['week'])), len(getactiveplayers(Secs['month'])), len(gethitnruns(Secs['day'])), len(getnewplayers(Secs['day']))), db='statsdb')
        for each in stinst:
            addvalue(each, getplayersonline(each, fmt='count'))
        stopsleep(dtime, stop_event)
    log.debug('Statcollector thread has ended')
    exit(0)
