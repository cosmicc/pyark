from time import sleep
import subprocess
from loguru import logger as log
from modules.configreader import maint_hour
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import Now, Secs
from datetime import datetime
from datetime import time as dt


def writediscord(msg, mtype, tstamp):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (mtype, 'ALERT', msg, tstamp))


def d2dt_maint(dtme):
    tme = dt(int(maint_hour) - 1, 55)
    return datetime.combine(dtme, tme)


def iseventrebootday():
    startday = dbquery("SELECT title FROM events WHERE starttime = '%s'" % (Now(fmt='dtd'),), fmt='string', fetch='one')
    endday = dbquery("SELECT title FROM events WHERE endtime = '%s'" % (Now(fmt='dtd'),), fmt='string', fetch='one')
    if startday:
        return f'{startday} Event Start'
    elif endday:
        return f'{startday} Event End'


def iseventtime():
    inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fmt='dict', fetch='one')
    if inevent:
        stime = d2dt_maint(inevent['starttime'])
        etime = d2dt_maint(inevent['endtime'])
        now = Now(fmt='dt')
        if now > stime and now < etime:
            return True
        else:
            return False
    else:
        return False


def getcurrenteventext():
    inevent = dbquery("SELECT cfgfilesuffix FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
    if inevent:
        return inevent[0]


def getcurrenteventtitle():
    inevent = dbquery("SELECT title FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
    if inevent:
        return inevent[0]


def getcurrenteventinfo():
    if iseventtime():
        inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent
        else:
            return None
    else:
        return None


def getlasteventinfo():
    inevent = dbquery("SELECT * FROM events WHERE completed = 1 ORDER BY id DESC", fetch='one')
    return inevent


def getnexteventinfo():
    inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND starttime > '%s' ORDER BY id DESC" % (Now(fmt='dtd'),), fetch='one')
    return inevent


def currentserverevent(inst):
    inevent = dbquery("SELECT inevent FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return inevent[0]


def startserverevent(inst):
    dbupdate("UPDATE instances SET inevent = '%s' WHERE name = '%s'" % (getcurrenteventext(), inst))
    eventinfo = getcurrenteventinfo()
    log.info(f'Starting {eventinfo[4]} Event on instance {inst.capitalize()}')
    msg = f"\n\n                      {eventinfo[4]} Event is Starting Soon!\n\n                        {eventinfo[5]}"
    subprocess.run("""arkmanager rconcmd "broadcast '%s' " @%s""" % (msg, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


def stopserverevent(inst):
    dbupdate("UPDATE instances SET inevent = 0 WHERE name = '%s'" % (inst,))
    log.info(f'Ending event on instance {inst.capitalize()}')
    eventinfo = getlasteventinfo()
    msg = f"\n\n                      {eventinfo[4]} Event is Ending Soon!"
    subprocess.run("""arkmanager rconcmd "broadcast '%s' " @%s""" % (msg, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


def checkifeventover():
    curevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (endtime < '%s' OR endtime = '%s') ORDER BY endtime ASC" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
    if curevent and not iseventtime():
        log.info(f'Event {curevent[4]} is over. Closing down event')
        msg = f"{curevent[0]}"
        writediscord(msg, 'EVENTEND', Now())
        dbupdate("UPDATE events SET completed = 1 WHERE id = '%s'" % (curevent[0],))


def checkifeventstart():
    curevent = dbquery("SELECT * FROM events WHERE completed = 0 AND announced = False AND (starttime < '%s' OR starttime = '%s') ORDER BY endtime ASC" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
    if curevent and iseventtime():
        log.info(f'Event {curevent[4]} has begun. Starting event')
        msg = f"{curevent[0]}"
        writediscord(msg, 'EVENTSTART', Now())
        dbupdate("UPDATE events SET announced = True WHERE id = '%s'" % (curevent[0],))


def eventwatcher(inst):
    log.debug(f'Starting server event coordinator for {inst}')
    while True:
        checkifeventover()
        checkifeventstart()
        try:
            if iseventtime() and currentserverevent(inst) == '0':
                startserverevent(inst)
            elif not iseventtime() and currentserverevent(inst) != '0':
                stopserverevent(inst)
        except:
            log.exception(f'Critical error in event coordinator')
        sleep(Secs['1min'])
