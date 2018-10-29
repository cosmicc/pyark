import time, logging, subprocess, socket, sqlite3
from configreader import sqldb

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def setmotd(inst, motd=None, cancel=False):
    if not cancel:
        subprocess.run("""/usr/local/bin/arkmanager rconcmd "SetMessageOfTheDay '%s'" @%s""" % (motd, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    elif cancel:
        subprocess.run("""/usr/local/bin/arkmanager rconcmd "SetMessageOfTheDay ''" @%s""" % (inst,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


def iseventtime():
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM events WHERE completed == 0 AND starttime < ?', (time.time(),))
    inevent = c4.fetchone()
    c4.close()
    conn4.close()
    if inevent:
        return True
    else:
        return False


def getcurrenteventid():
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT id FROM events WHERE completed == 0 AND starttime < ?', (time.time(),))
    inevent = c4.fetchone()
    c4.close()
    conn4.close()
    return inevent[0]


def getcurrenteventinfo():
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM events WHERE completed == 0 AND starttime < ?', (time.time(),))
    inevent = c4.fetchone()
    c4.close()
    conn4.close()
    return inevent


def getlasteventinfo():
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM events WHERE completed == 1 ORDER BY id DESC LIMIT 1')
    inevent = c4.fetchone()
    c4.close()
    conn4.close()
    return inevent


def getnexteventinfo():
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM events WHERE completed == 0 AND starttime > ?', (time.time(),))
    inevent = c4.fetchone()
    c4.close()
    conn4.close()
    return inevent


def currentserverevent(inst):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT inevent FROM instances WHERE name == ?', (inst,))
    inevent = c4.fetchone()
    c4.close()
    conn4.close()
    return inevent[0]


def startserverevent(inst):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('UPDATE instances SET inevent = ? WHERE name = ?', (getcurrenteventid(), inst))
    conn4.commit()
    c4.close()
    conn4.close()
    eventinfo = getcurrenteventinfo()
    log.info(f'Starting {eventinfo[4]} Event on instance {inst.capitalize()}')
    msg = f"\n\n\n                      {eventinfo[4]} Event is Active!\n\n                   {eventinfo[5]}"
    setmotd(inst, motd=msg)


def stopserverevent(inst):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('UPDATE instances SET inevent = 0 WHERE name = ?', (inst,))
    conn4.commit()
    c4.close()
    conn4.close()
    log.info(f'Ending event on instance {inst.capitalize()}')
    setmotd(inst, cancel=True)


def checkifeventover():
    curevent = getcurrenteventinfo()
    if curevent or curevent is not None:
        if curevent[3] < time.time():
            log.info(f'Event {curevent[5]} has passed end time. Ending Event')
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            c4.execute('UPDATE events SET completed = 1 WHERE id = ?', (curevent[0],))
            conn4.commit()
            c4.close()
            conn4.close()


def eventwatcher(inst):
    log.debug(f'Starting server event coordinator for {inst}')
    while True:
        checkifeventover()
        try:
            if iseventtime() and currentserverevent(inst) == 0:
                startserverevent(inst)
            elif not iseventtime() and currentserverevent(inst) != 0:
                stopserverevent(inst)
        except:
            log.critical(f'Critical error in event coordinator', exc_info=True)
        time.sleep(60)
