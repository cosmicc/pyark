from datetime import datetime
from datetime import time as dt
from datetime import timedelta

from loguru import logger as log

from modules.asyncdb import DB as db
from modules.redis import globalvar
from modules.configreader import maint_hour
from modules.dbhelper import dbquery, dbupdate
from modules.instances import asyncserverchat
from modules.timehelper import Now


async def asyncwritediscord(msg, mtype, tstamp):
    await db.update("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (mtype, 'ALERT', msg, tstamp))


def d2dt_maint(dtme):
    tme = dt(int(maint_hour) - 1, 55)
    return datetime.combine(dtme, tme)


async def asyncschedholidayevent(startdate, enddate):
    if not await asyncgetnexteventinfo():
        einfo = dbquery("SELECT * FROM autoevents WHERE title = 'Holiday'", fmt='dict', fetch='one')
        dbupdate("INSERT INTO events (completed, starttime, endtime, title, description, cfgfilesuffix, announced) VALUES (0, '%s', '%s', '%s', '%s', '%s', False)" % (startdate, enddate, einfo['title'], einfo['description'], einfo['cfgfilesuffix']))
        log.log('EVENTS', f'Scheduling next Evolution Weekend Event {startdate} - {enddate}')
    else:
        log.log('EVENTS', f'Skipping auto-schedule of next Evo weekend to do existing next event')


async def asyncautoschedevolution():
    if not await asyncgetnexteventinfo():
        now = Now(fmt='dt')
        while now.strftime('%a') != 'Fri':
            now += timedelta(1)
        enddt = now + timedelta(days=3)
        enddate = enddt.date()
        startdate = now.date()
        einfo = await db.fetchone(f"SELECT * FROM autoevents WHERE title = 'Evolution Weekend'")
        await db.update("INSERT INTO events (completed, starttime, endtime, title, description, cfgfilesuffix, announced) VALUES (0, '%s', '%s', '%s', '%s', '%s', False)" % (startdate, enddate, einfo['title'], einfo['description'], einfo['cfgfilesuffix']))
        log.log('EVENTS', f'Scheduling next Evolution Weekend Event {startdate} - {enddate}')
    else:
        log.log('EVENTS', f'Skipping auto-schedule of next Evo weekend to do existing next event')


async def asynciseventrebootday():
    startday = await db.fetchone(f"SELECT title FROM events WHERE starttime = '{Now(fmt='dtd')}'")
    endday = await db.fetchone(f"SELECT title FROM events WHERE endtime = '{Now(fmt='dtd')}'")
    if startday:
        return f'{startday["title"]} Event Start'
    elif endday:
        return f'{startday["title"]} Event End'


async def asynciseventtime():
    inevent = await db.fetchone(f"""SELECT * FROM events WHERE completed = 0 AND (starttime < '{Now(fmt="dtd")}' OR starttime = '{Now(fmt="dtd")}')""")
    if inevent:
        stime = d2dt_maint(inevent['starttime'])
        etime = d2dt_maint(inevent['endtime'])
        now = Now(fmt='dt')
        if now > stime and now < etime:
            return inevent
        else:
            return False
    else:
        return False


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


async def asyncgetcurrenteventext():
    if await asynciseventtime():
        inevent = await db.fetchone("SELECT cfgfilesuffix FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent['cfgfilesuffix']


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


async def asyncgetcurrenteventinfo():
    if await asynciseventtime():
        inevent = await db.fetchone("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent


def getcurrenteventinfo():
    if iseventtime():
        inevent = dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime < '%s' OR starttime = '%s')" % (Now(fmt='dtd'), Now(fmt='dtd')), fetch='one')
        if inevent:
            return inevent


async def asyncreplacerates(event):
    try:
        if event == 'default':
            newrates = await db.fetchone(f"SELECT * FROM rates WHERE type = 'default'")
        else:
            newrates = await db.fetchone(f"SELECT * FROM autoevents WHERE title = '{event}'")
        await db.update(f"UPDATE rates set breed = {newrates['breed']}, tame = {newrates['tame']}, harvest = {newrates['harvest']}, mating = {newrates['mating']}, matingint = {newrates['matingint']}, hatch = {newrates['hatch']}, playerxp = {newrates['playerxp']}, tamehealth = {newrates['tamehealth']}, playerhealth = {newrates['playerhealth']}, playersta = {newrates['playersta']}, foodwater = {newrates['foodwater']}, pph = {newrates['pph']}, pphx = {newrates['pphx']} WHERE type = 'current'")
        log.log('EVENTS', f'Replaced event rates with rates from {event}')
    except:
        log.exception('Error replacing rates')


async def asyncgetlasteventinfo():
    inevent = await db.fetchone(f"SELECT * FROM events WHERE completed = 1 ORDER BY id DESC")
    return inevent


async def asyncgetnexteventinfo():
    inevent = await db.fetchall(f"""SELECT * FROM events WHERE completed = 0 AND starttime > '{Now(fmt="dtd")}' or starttime = '{Now(fmt="dtd")}' ORDER BY starttime ASC""")
    if inevent:
        if inevent[0][2] == (Now(fmt='dtd')) and not await asynciseventtime():
            return inevent[0]
        elif inevent[0][2] == (Now(fmt='dtd')) and await asynciseventtime():
            if len(inevent) > 1:
                return inevent[1]
        elif inevent[0][2] > (Now(fmt='dtd')):
            return inevent[0]


async def asynccurrentserverevent(inst):
    inevent = await db.fetchone(f"SELECT inevent FROM instances WHERE name = '{inst}'")
    return inevent['inevent']


async def asyncstartserverevent(inst):
    await db.update(f"UPDATE instances SET inevent = '{await asyncgetcurrenteventext()}' WHERE name = '{inst}")
    eventinfo = await asyncgetcurrenteventinfo()
    log.log('EVENTS', f'Starting {eventinfo[4]} Event on instance {inst.capitalize()}')
    msg = f"\n\n                      {eventinfo[4]} Event is Starting Soon!\n\n                        {eventinfo[5]}"
    await asyncserverchat(msg, inst=inst, broadcast=True)


async def asyncstopserverevent(inst):
    await db.update(f"UPDATE instances SET inevent = 0 WHERE name = '{inst}'")
    log.log('EVENTS', f'Ending event on instance {inst.capitalize()}')
    eventinfo = await asyncgetlasteventinfo()
    msg = f"\n\n                      {eventinfo[4]} Event is Ending Soon!"
    await asyncserverchat(msg, inst=inst, broadcast=True)


async def asynccheckifeventover():
    curevent = await db.fetchone(f"""SELECT * FROM events WHERE completed = 0 AND (endtime < '{Now(fmt="dtd")}' OR endtime = '{Now(fmt="dtd")}' ORDER BY endtime ASC""")
    if curevent and not await asynciseventtime():
        log.log('EVENTS', f'Event {curevent[4]} is over. Closing down event')
        msg = f"{curevent[0]}"
        await asyncwritediscord(msg, 'EVENTEND', Now())
        await db.update(f"UPDATE events SET completed = 1 WHERE id = '{curevent[0]}'")
        await asyncreplacerates('default')
        await asyncautoschedevolution()


async def asynccheckifeventstart():
    curevent = await db.fetchone(f"""SELECT * FROM events WHERE completed = 0 AND announced = False AND (starttime < '{Now(fmt="dtd")}' OR starttime = '{Now(fmt="dtd")}') ORDER BY endtime ASC""")
    if curevent and await asynciseventtime():
        log.log('EVENTS', f'Event {curevent["title"]} has begun. Starting event')
        msg = f"{curevent['id']}"
        await asyncwritediscord(msg, 'EVENTSTART', Now())
        await db.update(f"""UPDATE events SET announced = True WHERE id = '{curevent["id"]}'""")
        await asyncreplacerates(curevent['title'])
        await asyncautoschedevolution()


async def asynceventwatcher():
    await asynccheckifeventover()
    await asynccheckifeventstart()
    for inst in await globalvar.getlist('allinstances'):
        if await asynciseventtime() and await asynccurrentserverevent(inst) == '0':
            await asyncstartserverevent(inst)
        elif not await asynciseventtime() and await asynccurrentserverevent(inst) != '0':
            await asyncstopserverevent(inst)
