import asyncio
from datetime import datetime
from datetime import time as dt
from datetime import timedelta

import aiohttp
import uvloop
from loguru import logger as log
from modules.apihelper import asyncfetchauctiondata, asyncwriteauctionstats, getauctionstats
from modules.asyncdb import DB as db
from modules.players import getactiveplayers, gethitnruns, getnewplayers, getplayersonline
from modules.servertools import removerichtext
from modules.timehelper import Now, Secs
from modules.tribes import gettribeinfo, putplayerintribe
from timebetween import is_time_between


@log.catch
class GameLogger():
    def __init__(self):
        self.db = db

    async def getlines(self):
        try:
            result = await self.db.fetchall("SELECT * FROM gamelog")
            for eline in result:
                await self.db.update(f"DELETE FROM gamelog WHERE id = {eline[0]}")
            return result
        except:
            log.error('Error in getlines() gamelog line retriever from db')

    async def process(self):
        lines = await self.getlines()
        if lines:
            for line in lines:
                await processgameline(line[1], line[2], line[3])

    def close(self):
        self.db.close()


async def asyncstopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Online monitor thread has ended')
            exit(0)
        asyncio.sleep(1)


@log.catch
async def gettotaldbconnections():
    result = await db.fetchone(f'SELECT count(*) FROM pg_stat_activity;')
    return int(result['count'])


async def addvalue(inst, value):
    await db.statsupdate(inst, value)


async def flushold(tinst):  # not implimented
    raise NotImplementedError
    # aweek = int(time()) - Secs['week']
    # await db.update("DELETE FROM %s WHERE date < '%s'" % (tinst, aweek))


@log.catch
async def processgameline(inst, ptype, line):
        clog = log.patch(lambda record: record["extra"].update(instance=inst))
        logheader = f'{Now(fmt="dt").strftime("%a %I:%M%p")}|{inst.upper():>8}|{ptype:<7}| '
        linesplit = removerichtext(line[21:]).split(", ")
        if ptype == 'TRAP':
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            msgsplit = linesplit[2][10:].split('trapped:')
            playername = msgsplit[0].strip()
            putplayerintribe(tribeid, playername)
            dino = msgsplit[1].strip().replace(')', '').replace('(', '')
            clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) has trapped [{dino}]')
        elif ptype == 'RELEASE':
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            msgsplit = linesplit[2][10:].split('released:')
            playername = msgsplit[0].strip()
            putplayerintribe(tribeid, playername)
            dino = msgsplit[1].strip().replace(')', '').replace('(', '')
            clog.log(ptype, f'{logheader}[{playername.title()}] of ({tribename}) has released [{dino}]')
        elif ptype == 'DEATH':
            clog.debug(f'{ptype} - {linesplit}')
            tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
            if tribename is None:
                deathsplit = removerichtext(line[21:]).split(" - ", 1)
                playername = deathsplit[0].strip()
                if deathsplit[1].find('was killed by') != -1:
                    killedby = deathsplit[1].split('was killed by')[1].strip()[:-1].replace('()', '').strip()
                    playerlevel = deathsplit[1].split('was killed by')[0].strip().replace('()', '')
                    clog.log(ptype, f'{logheader}[{playername.title()}] {playerlevel} was killed by [{killedby}]')
                elif deathsplit[1].find('killed!') != -1:
                    level = deathsplit[1].split(' was killed!')[0].strip('()')
                    clog.log(ptype, f'{logheader}[{playername.title()}] {level} has been killed')
                else:
                    log.warning(f'not found gameparse death: {deathsplit}')
            else:
                log.debug(f'deathskip: {linesplit}')
        elif ptype == 'TAME':
                clog.debug(f'{ptype} - {linesplit}')
                tribename, tribeid = gettribeinfo(linesplit, inst, ptype)
                if tribename is None:
                    tamed = linesplit[0].split(' Tamed ')[1].strip(')').strip('!')
                    clog.log(ptype, f'{logheader}A tribe has tamed [{tamed}]')
                else:
                    log.debug(f'TRIBETAME: {inst}, {linesplit}')
                    playername = linesplit[2][10:].split(' Tamed')[0].strip()
                    putplayerintribe(tribeid, playername)
                    tamed = linesplit[2].split(' Tamed')[1].strip(')').strip('!').strip()
                    if playername.title() == 'Your Tribe':
                        clog.log(ptype, f'{logheader}[{tribename}] tamed [{tamed}]')


@log.catch
async def asyncauctionapi(session):
        log.trace('Running auction api fetcher...')
        players = await db.fetchall(f"SELECT steamid, playername, auctionrefreshtime FROM players WHERE refreshauctions = True OR online = True")
        if players:
            log.trace(f'Found {len(players)} players for auctionapi to process {players}')
            for player in players:
                log.trace(f'processing player auctionapi [{player[1]}] ({player[0]})')
                refresh = False
                if player[2]:
                    if player[2] < Now(fmt='dt') - timedelta(hours=1):
                        log.trace(f'player [{player[1]}] is past auction refresh time')
                        refresh = True
                        rtime = Now(fmt='dt')
                    else:
                        rtime = player[2]
                else:
                    log.trace(f'no auctionrefreshtime found for player [{player[1]}]')
                    refresh = True
                    rtime = Now(fmt='dt')
                await db.update(f"UPDATE players SET refreshauctions = False, auctionrefreshtime = '{rtime}' WHERE steamid = '{player[0]}'")
                if refresh:
                    log.debug(f'retrieving auction information for player [{player[1]}] ({player[0]}]')
                    pauctions = await asyncfetchauctiondata(session, player[0])
                    totauctions, iauctions, dauctions = getauctionstats(pauctions)
                    await asyncwriteauctionstats(player[0], totauctions, iauctions, dauctions)
                    log.debug(f'retrieved auctions for player [{player[1]}] total: {totauctions}, items: {iauctions}, dinos: {dauctions}')



@log.catch
async def asyncstatcollector():
    log.trace('Running stat collector...')
    stinst = await db.fetchall('SELECT name FROM instances')
    t, s, e = datetime.now(), dt(9, 0), dt(9, 5)  # 9:00am GMT (5:00AM EST)
    dailycollect = is_time_between(t, s, e)
    if dailycollect:
        await db.update("INSERT INTO clusterstats (timestamp, dailyactive, weeklyactive, monthlyactive, dailyhnr, dailynew) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (Now(fmt='dt'), len(getactiveplayers(Secs['day'])), len(getactiveplayers(Secs['week'])), len(getactiveplayers(Secs['month'])), len(gethitnruns(Secs['day'])), len(getnewplayers(Secs['day']))), db='statsdb')
        for each in stinst:
            await addvalue(each, getplayersonline(each, fmt='count'))


async def asynccheckdbconnections():
    connections = await gettotaldbconnections()
    if connections > 60:
        log.warning(f'Database connections is high ({connections})')
    else:
        log.trace(f'Database connections normal ({connections})')


async def masterserverloop():
    global gl
    gl = GameLogger()
    async with aiohttp.ClientSession() as session:
        asyncio.create_task(asyncdblcheckonline())
        asyncio.create_task(asyncstatcollector())
        asyncio.create_task(gl.process())
        asyncio.create_task(asynccheckdbconnections())
        asyncio.create_task(asyncauctionapi(session))



def masterserver():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(masterserverloop())  # Async branch to main loop
