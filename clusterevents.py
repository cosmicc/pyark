from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import Now, Secs
from time import sleep
from datetime import datetime, time
import logging
import socket
import subprocess

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def setmotd(inst, motd=None, cancel=False):
    if not cancel:
        subprocess.run("""/usr/local/bin/arkmanager rconcmd "SetMessageOfTheDay '%s'" @%s""" % (motd, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    elif cancel:
        subprocess.run("""/usr/local/bin/arkmanager rconcmd "SetMessageOfTheDay ''" @%s""" % (inst,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


def iseventtime():
    inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'),Now(fmt='dtd')), fmt='dict', fetch='one')
    if inevent:
        tme = time(10, 59)
        stime = datetime.combine(inevent['starttime'], tme)
        etime = datetime.combine(inevent['endtime'], tme)
        now = Now(fmt='dt')
        if now > stime and now < etime:
            return True
        else:
            return False
    else:
        return False


def getcurrenteventext():
    inevent = dbquery("SELECT cfgfilesuffix FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'),Now(fmt='dtd')), fetch='one')
    if inevent:
        return inevent[0]


def getcurrenteventtitle():
    inevent = dbquery("SELECT title FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'),Now(fmt='dtd')), fetch='one')
    if inevent:
        return inevent[0]


def getcurrenteventinfo():
    if iseventtime():
        inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'),Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent
        else:
            return False
    else:
        return False


def getlasteventinfo():
    inevent = dbquery("SELECT * FROM events WHERE completed = 1 ORDER BY endtime DESC", fetch='one')
    return inevent


def getnexteventinfo():
    inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND endtime < '%s' ORDER BY starttime ASC" % (Now(fmt='dtd'),), fetch='one')
    return inevent


def currentserverevent(inst):
    inevent = dbquery("SELECT inevent FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return inevent[0]


def startserverevent(inst):
    dbupdate("UPDATE instances SET inevent = '%s' WHERE name = '%s'" % (getcurrenteventext(), inst))
    eventinfo = getcurrenteventinfo()
    log.info(f'Starting {eventinfo[4]} Event on instance {inst.capitalize()}')
    msg = f"\n\n                      {eventinfo[4]} Event is Active!\n\n                   {eventinfo[5]}"
    setmotd(inst, motd=msg)


def stopserverevent(inst):
    dbupdate("UPDATE instances SET inevent = 0 WHERE name = '%s'" % (inst,))
    log.info(f'Ending event on instance {inst.capitalize()}')
    setmotd(inst, cancel=True)


def checkifeventover():
    if not iseventtime():
        curevent = getcurrenteventinfo()
        log.warning(curevent)
        if curevent:
            log.info(f'Event {curevent[5]} has passed end time. Ending Event')
            dbupdate("UPDATE events SET completed = 1 WHERE endtime = '%s'" % (curevent[3],))


def eventwatcher(inst):
    log.debug(f'Starting server event coordinator for {inst}')
    while True:
        checkifeventover()
        try:
            if iseventtime() and currentserverevent(inst) == '0':
                startserverevent(inst)
            elif not iseventtime() and currentserverevent(inst) != '0':
                stopserverevent(inst)
        except:
            log.critical(f'Critical error in event coordinator', exc_info=True)
        sleep(Secs['1min'])
