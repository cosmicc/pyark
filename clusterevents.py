from time import sleep
from loguru import logger as log
from modules.configreader import maint_hour
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import Now, Secs
from modules.instances import instancelist, serverchat
from datetime import datetime, timedelta
from datetime import time as dt


def writediscord(msg, mtype, tstamp):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (mtype, 'ALERT', msg, tstamp))


def d2dt_maint(dtme):
    tme = dt(int(maint_hour) - 1, 55)
    return datetime.combine(dtme, tme)


def autoschedevolution():
    if not getnexteventinfo():
        now = Now(fmt='dt')
        while now.strftime('%a') != 'Fri':
            now += timedelta(1)
        enddt = now + timedelta(days=3)
        enddate = enddt.date()
        startdate = now.date()

        einfo = dbquery("SELECT * FROM autoevents WHERE title = 'Evolution Weekend'", fmt='dict', fetch='one')
        dbupdate("INSERT INTO events (completed, starttime, endtime, title, description, cfgfilesuffix, announced) VALUES (0, '%s', '%s', '%s', '%s', '%s      ', False)" % (startdate, enddate, einfo['title'], einfo['description'], einfo['cfgfilesuffix']))

        log.log('EVENTS', f'Scheduling next Evolution Weekend Event {startdate} - {enddate}')
    else:
        log.log('EVENTS', f'Skipping auto-schedule of next Evo weekend to do existing next event')


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
    if iseventtime():
        inevent = dbquery("SELECT cfgfilesuffix FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent[0]


def getcurrenteventtitle():
    if iseventtime():
        inevent = dbquery("SELECT title FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent[0]


def getcurrenteventtitleabv():
    if iseventtime():
        inevent = dbquery("SELECT cfgfilesuffix FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent[0]


def getcurrenteventinfo():
    if iseventtime():
        inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent


def replacerates(event):
    try:
        if event == 'default':
            newrates = dbquery("SELECT * FROM rates WHERE type = 'default'", fetch='one', fmt='dict')
        else:
            newrates = dbquery("SELECT * FROM autoevents WHERE title = '%s'" % (event,), fetch='one', fmt='dict')
        dbupdate(f"UPDATE rates set breed = {newrates['breed']}, tame = {newrates['tame']}, harvest = {newrates['harvest']}, mating = {newrates['mating']}, matingint = {newrates['matingint']}, hatch = {newrates['hatch']}, playerxp = {newrates['playerxp']}, tamehealth = {newrates['tamehealth']}, playerhealth = {newrates['playerhealth']}, playersta = {newrates['playersta']}, foodwater = {newrates['foodwater']}, pph = {newrates['pph']}, pphx = {newrates['pphx']} WHERE type = 'current'")
        log.log('EVENTS', f'Replaced event rates with rates from {event}')
    except:
        log.exception('Error replacing rates')


def getlasteventinfo():
    inevent = dbquery("SELECT * FROM events WHERE completed = 1 ORDER BY id DESC", fetch='one')
    return inevent


def getnexteventinfo():
    inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND starttime > '%s' or starttime = '%s' ORDER BY starttime ASC" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='all')
    if inevent:
        if inevent[0][2] == (Now(fmt='dtd')) and not iseventtime():
            return inevent[0]
        elif inevent[0][2] == (Now(fmt='dtd')) and iseventtime():
            if len(inevent) > 1:
                return inevent[1]
        elif inevent[0][2] > (Now(fmt='dtd')):
            return inevent[0]


def currentserverevent(inst):
    inevent = dbquery("SELECT inevent FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return inevent[0]


def startserverevent(inst):
    dbupdate("UPDATE instances SET inevent = '%s' WHERE name = '%s'" % (getcurrenteventext(), inst))
    eventinfo = getcurrenteventinfo()
    log.log('EVENTS', f'Starting {eventinfo[4]} Event on instance {inst.capitalize()}')
    msg = f"\n\n                      {eventinfo[4]} Event is Starting Soon!\n\n                        {eventinfo[5]}"
    serverchat(msg, inst=inst, broadcast=True)


def stopserverevent(inst):
    dbupdate("UPDATE instances SET inevent = 0 WHERE name = '%s'" % (inst,))
    log.log('EVENTS', f'Ending event on instance {inst.capitalize()}')
    eventinfo = getlasteventinfo()
    msg = f"\n\n                      {eventinfo[4]} Event is Ending Soon!"
    serverchat(msg, inst=inst, broadcast=True)


def checkifeventover():
    curevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (endtime < '%s' OR endtime = '%s') ORDER BY endtime ASC" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
    if curevent and not iseventtime():
        log.log('EVENTS', f'Event {curevent[4]} is over. Closing down event')
        msg = f"{curevent[0]}"
        writediscord(msg, 'EVENTEND', Now())
        dbupdate("UPDATE events SET completed = 1 WHERE id = '%s'" % (curevent[0],))
        replacerates('default')
        autoschedevolution()


def checkifeventstart():
    curevent = dbquery("SELECT * FROM events WHERE completed = 0 AND announced = False AND (starttime < '%s' OR starttime = '%s') ORDER BY endtime ASC" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one', fmt='dict')
    if curevent and iseventtime():
        log.log('EVENTS', f'Event {curevent["title"]} has begun. Starting event')
        msg = f"{curevent['id']}"
        writediscord(msg, 'EVENTSTART', Now())
        dbupdate("UPDATE events SET announced = True WHERE id = '%s'" % (curevent['id'],))
        replacerates(curevent['title'])
        autoschedevolution()


def eventwatcher():
    log.debug(f'Starting cluster server event coordinator')
    instances = instancelist()
    while True:
        try:
            checkifeventover()
            checkifeventstart()
            for inst in instances:
                if iseventtime() and currentserverevent(inst) == '0':
                    startserverevent(inst)
                elif not iseventtime() and currentserverevent(inst) != '0':
                    stopserverevent(inst)
        except:
            log.exception(f'Critical error in event coordinator')
        sleep(Secs['1min'])
