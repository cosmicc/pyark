import asyncio
import globvars
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.players import isplayeradmin
from modules.redis import redis
from modules.servertools import removerichtext
from modules.timehelper import Now
from modules.tribes import asyncgettribeinfo, asyncputplayerintribe, asyncremoveplayerintribe
from time import time


def checkgamelog(record):
    if record['level'] == 'TRAP' or record['level'] == 'ADMIN' or record['level'] == 'DEATH' or record['level'] == 'TAME' or record['level'] == 'DECAY' or record['level'] == 'DEMO' or record['level'] == 'TRIBE' or record['level'] == 'CLAIM' or record['level'] == 'RELEASE':
        return True
    else:
        return False


@log.catch
async def addredisloghistory(rlog, max, line):
    count = int(redis.zcard(rlog))
    if count >= max:
        await redis.zremrangebyrank(rlog, 0, max - count)
        await redis.zadd(rlog, line, time(), nx=True)


@log.catch
async def asyncprocessgamelog():
    globvars.gamelogger = True
    count = await redis.zcard('gamelog')
    for each in range(count):
        sline = await redis.zpopmin('gamelog', 1)
        if sline:
            line = sline[0].decode().split('||')
            await _processgameline(line[0], line[1], line[2])
    await asyncio.sleep(.1)
    globvars.gamelogger = False


@log.catch
async def _processgameline(inst, ptype, line):
    clog = log.patch(lambda record: record["extra"].update(instance=inst))
    logheader = f'{Now(fmt="dt").strftime("%a %I:%M%p")}|{inst.upper():>8}|{ptype:<7}| '
    linesplit = removerichtext(line[21:]).split(", ")
    if ptype == 'TRAP':
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        msgsplit = linesplit[2][10:].split('trapped:')
        playername = msgsplit[0].strip()
        await asyncputplayerintribe(tribeid, playername)
        dino = msgsplit[1].strip().replace(')', '').replace('(', '')
        line = f'{logheader}[{playername.title()}] of ({tribename}) has trapped [{dino}]'
        clog.log(ptype, line)
        await addredisloghistory('glhistory', 50, line)
    elif ptype == 'RELEASE':
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        msgsplit = linesplit[2][10:].split('released:')
        playername = msgsplit[0].strip()
        await asyncputplayerintribe(tribeid, playername)
        dino = msgsplit[1].strip().replace(')', '').replace('(', '')
        line = f'{logheader}[{playername.title()}] of ({tribename}) has released [{dino}]'
        clog.log(ptype, line)
        await addredisloghistory('glhistory', 50, line)
    elif ptype == 'DEATH':
        # clog.debug(f'{ptype} - {linesplit}')
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        if tribename is None:
            deathsplit = removerichtext(line[21:]).split(" - ", 1)
            playername = deathsplit[0].strip()
            if deathsplit[1].find('was killed by') != -1:
                killedby = deathsplit[1].split('was killed by')[1].strip()[:-1].replace('()', '').strip()
                playerlevel = deathsplit[1].split('was killed by')[0].strip().replace('()', '')
                line = f'{logheader}[{playername.title()}] {playerlevel} was killed by [{killedby}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            elif deathsplit[1].find('killed!') != -1:
                level = deathsplit[1].split(' was killed!')[0].strip('()')
                line = f'{logheader}[{playername.title()}] {level} has been killed'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            else:
                log.warning(f'not found gameparse death: {deathsplit}')
        else:
            pass
            # log.debug(f'deathskip: {linesplit}')
    elif ptype == 'TAME':
            # clog.debug(f'{ptype} - {linesplit}')
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        if tribename is None:
            tamed = linesplit[0].split(' Tamed ')[1].strip(')').strip('!')
            line = f'{logheader}A tribe has tamed [{tamed}]'
            clog.log(ptype, line)
            await addredisloghistory('glhistory', 50, line)
        else:
            # log.debug(f'TRIBETAME: {inst}, {linesplit}')
            playername = linesplit[2][10:].split(' Tamed')[0].strip()
            await asyncputplayerintribe(tribeid, playername)
            tamed = linesplit[2].split(' Tamed')[1].strip(')').strip('!').strip()
            if playername.title() == 'Your Tribe':
                line = f'{logheader}[{tribename}] tamed [{tamed}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            else:
                line = f'{logheader}[{playername.title()}] of ({tribename}) tamed [{tamed}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
    elif ptype == 'DEMO':
        # clog.debug(f'{ptype} - {linesplit}')
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        if tribename is None:
            pass
            # clog.log(ptype, f'{logheader}SINGLDEMO: [{linesplit}]')
        else:
            # log.debug(f'TRIBEDEMO: {inst}, {linesplit}')
            playername = linesplit[2][10:].split(' demolished a ')[0].strip()
            await asyncputplayerintribe(tribeid, playername)
            if len(linesplit[2].split(' demolished a ')) > 0 and linesplit[2].find(' demolished a ') != -1:
                demoitem = linesplit[2].split(' demolished a ')[1].replace("'", "").strip(')').strip('!').strip()
                line = f'{logheader}[{playername.title()}] of ({tribename}) demolished a [{demoitem}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
    elif ptype == 'ADMIN':
        # clog.debug(f'{ptype} - {linesplit}')
        steamid = linesplit[2].strip()[9:].strip(')')
        pname = linesplit[0].split('PlayerName: ')[1]
        cmd = linesplit[0].split('AdminCmd: ')[1].split(' (PlayerName:')[0].upper()
        if not isplayeradmin(steamid):
            clog.warning(f'{logheader}Admin command [{cmd}] executed by NON-ADMIN [{pname.title()}] !')
            await db.update("INSERT INTO kicklist (instance,steamid) VALUES ('%s','%s')" % (inst, steamid))
            await db.update("UPDATE players SET banned = 'true' WHERE steamid = '%s')" % (steamid, ))
        else:
            line = f'{logheader}[{pname.title()}] executed admin command [{cmd}] '
            clog.log(ptype, line)
            await addredisloghistory('glhistory', 50, line)
    elif ptype == 'DECAY':
        # clog.debug(f'{ptype} - {linesplit}')
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        decayitem = linesplit[2].split("'", 1)[1].split("'")[0]
        # decayitem = re.search('\(([^)]+)', linesplit[2]).group(1)
        line = f'{logheader}Tribe ({tribename}) auto-decayed [{decayitem}]'
        clog.log(ptype, line)
        await addredisloghistory('glhistory', 50, line)
        # wglog(inst, removerichtext(line[21:]))
    elif ptype == 'CLAIM':
        # log.debug(f'{ptype} : {linesplit}')
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        if tribename:
            if linesplit[2].find(" claimed '") != -1:
                playername = linesplit[2][10:].split(' claimed ')[0].strip()
                await asyncputplayerintribe(tribeid, playername)
                claimitem = linesplit[2].split("'", 1)[1].split("'")[0]
                line = f'{logheader}[{playername}] of ({tribename}) has claimed [{claimitem}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            elif linesplit[2].find(" unclaimed '") != -1:
                playername = linesplit[2][10:].split(' claimed ')[0].strip()
                await asyncputplayerintribe(tribeid, playername)
                claimitem = linesplit[2].split("'", 1)[1].split("'")[0]
                line = f'{logheader}[{playername}] of ({tribename}) has un-claimed [{claimitem}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
        else:
            pass
            # clog.log(ptype, f'{logheader} SINGLECLAIM: {linesplit}')
    elif ptype == 'TRIBE':
        # clog.debug(f'{ptype} - {linesplit}')
        tribename, tribeid = await asyncgettribeinfo(linesplit, inst, ptype)
        if tribeid is not None:
            if linesplit[2].find(' was added to the Tribe by ') != -1:
                playername = linesplit[2][10:].split(' was added to the Tribe by ')[0].strip()
                playername2 = linesplit[2][10:].split(' was added to the Tribe by ')[1].strip().strip(')').strip('!')
                await asyncputplayerintribe(tribeid, playername)
                await asyncputplayerintribe(tribeid, playername2)
                line = f'[{playername.title()}] was added to Tribe ({tribename}) by [{playername2.title()}]'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            elif linesplit[2].find(' was removed from the Tribe!') != -1:
                playername = linesplit[2][10:].split(' was removed from the Tribe!')[0].strip()
                await asyncremoveplayerintribe(tribeid, playername)
                line = f'[{playername.title()}] was removed from Tribe ({tribename})'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            elif linesplit[2].find(' was added to the Tribe!') != -1:
                playername = linesplit[2][10:].split(' was added to the Tribe!')[0].strip()
                await asyncputplayerintribe(tribeid, playername)
                line = f'[{playername.title()}] was added to the Tribe ({tribename})'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
            elif linesplit[2].find(' set to Rank Group ') != -1:
                playername = linesplit[2][10:].split(' set to Rank Group ')[0].strip()
                await asyncputplayerintribe(tribeid, playername)
                rankgroup = linesplit[2][10:].split(' set to Rank Group ')[1].strip().strip('!')
                line = f'[{playername.title()}] set to rank group [{rankgroup}] in Tribe ({tribename})'
                clog.log(ptype, line)
                await addredisloghistory('glhistory', 50, line)
        else:
            clog.log(ptype, f'{logheader}{linesplit}')
    else:
        log.debug(f'UNKNOWN {ptype} - {linesplit}')
        line = f'{linesplit}'
        clog.log(ptype, line)
        await addredisloghistory('glhistory', 50, line)
