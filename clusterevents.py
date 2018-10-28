import time, logging, socket, sqlite3
from configreader import sqldb, instance

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


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
    inevent = c4.fetchone()
    c4.close()
    conn4.close()


def stopserverevent(inst):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('UPDATE instances SET inevent = 0 WHERE name = ?', (inst,))
    inevent = c4.fetchone()
    c4.close()
    conn4.close()


def eventwatcher():
    log.info(f'Starting server event coordinator')
    while True:
        try:
            for eachinst in instance:
                if iseventtime() and currentserverevent(eachinst['name']) == 0:
                    startserverevent(eachinst['name'])
                elif not iseventtime() and currentserverevent(eachinst['name']) != 0:
                    stopserverevent(eachinst['name'])
        except:
            log.critical(f'Critical error in event coordinator', exc_info=True)
        time.sleep(60)
