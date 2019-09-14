from datetime import time as dt
from datetime import datetime, timedelta
from random import choice
from modules.redis import Redis

import asyncio
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.dbhelper import dbquery
from modules.timehelper import Now, Secs, datetimeto, elapsedTime, estshift
from numpy import argmax
from numpy.random import randint, seed, shuffle
from timebetween import is_time_between

redis = Redis.redis


def isinlottery():
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False")
    if linfo:
        return True
    else:
        return False


async def asyncisinlottery():
    linfo = db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    if linfo:
        return True
    else:
        return False


async def getlottowinnings(pname):
    pwins = db.fetchone(f"SELECT payout FROM lotteryinfo WHERE winner = '{pname}'")
    totpoints = 0
    twins = 0
    for weach in pwins:
        totpoints = totpoints + int(weach[0])
        twins += 1
    return twins, totpoints


async def asyncwritediscord(msg, tstamp, server='generalchat', name='ALERT'):
    await db.update(f"INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('{server}', '{name}', '{msg}', '{tstamp}')")


async def asyncwriteglobal(inst, whos, msg):
    await db.update(f"INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('{inst}', '{whos}', '{msg}', '{Now()}')")


async def asyncgetlastlotteryinfo():
    return await db.fetchone(f"SELECT * FROM lotteryinfo WHERE completed = True ORDER BY id desc")


async def asyncgetlottowinnings(pname):
    pwins = await db.fetchone(f"SELECT payout FROM lotteryinfo WHERE winner = '{pname}'")
    totpoints = 0
    twins = 0
    for weach in pwins:
        totpoints = totpoints + int(weach[0])
        twins += 1
    return twins, totpoints


async def asyncgetlotteryplayers():
    lottoinfo = await db.fetchall("SELECT playername FROM lotteryplayers")
    return lottoinfo


async def asynctotallotterydeposits(steamid):
    lottoinfo = await db.fetchone(f"SELECT points, givetake FROM lotterydeposits where steamid = '{steamid}'")
    tps = 0
    if lottoinfo is not None:
        for each in lottoinfo:
            if each[1] == 1:
                tps += each[0]
            elif each[1] == 0:
                tps -= each[0]
    return tps


async def getlotteryendtime():
    lottoinfo = await db.fetchone(f"SELECT startdate, days from lotteryinfo WHERE completed = False")
    return estshift(lottoinfo[0] + timedelta(days=lottoinfo[1]))


async def asyncdeterminewinner(lottoinfo):
    log.debug('Lottery time has ended. Determining winner.')
    winners = []
    picks = []
    adjpicks = []
    wins = []
    lottoers = await db.fetchall("SELECT * FROM lotteryplayers")
    if len(lottoers) >= 3:
        try:
            for eachn in lottoers:
                winners.append(eachn[0])
            seed(randint(100))
            shuffle(winners)
            seed(randint(100))
            for eachw in range(len(winners)):
                picks.append(randint(100))
                lwins = await db.fetchone(f"SELECT lottowins FROM players WHERE steamid = '{winners[eachw]}'")
                wins.append(lwins[0])
                if wins[eachw] > 10:
                    adjj = 10
                else:
                    adjj = wins[eachw]
                adjpicks.append(picks[eachw] - adjj * 5)
            winneridx = argmax(adjpicks)
            winnersid = winners[winneridx]
            lwinner = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{winnersid}'")
            await db.update(f"UPDATE lotteryinfo SET winner = '{lwinner[1]}', completed = True WHERE id = '{lottoinfo['id']}'")
            log.log('LOTTO', f'Lottery ended, winner is: {lwinner[1].upper()} for {lottoinfo["payout"]} points, win #{lwinner[18]+1}')
            winners.remove(winnersid)
            log.debug(f'queuing up lottery deposits for {winners}')
            for ueach in winners:
                kk = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{ueach}'")
                await db.update(f"INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES ('{kk[0]}', '{kk[1]}', '{Now()}', '{lottoinfo['buyin']}', 0)")
            bcast = f"""<RichColor Color="0,1,0,1"> </>\n<RichColor Color="0,1,0,1">                The current lottery has ended, and the winner is...</>\n<RichColor Color="1,1,0,1">                                  {lwinner[1].upper()}!</>\n                      {lwinner[1].capitalize()} has won {lottoinfo["payout"]} Reward Points!\n\n                         Next lottery begins in 1 hour."""
            await asyncwriteglobal('ALERT', 'LOTTERY', bcast)
            await asyncwritediscord(f'{lwinner[1].title()}', Now(), name=f'{lottoinfo["payout"]}', server='LOTTOEND')
            await db.update(f"INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES ('{lwinner[0]}', '{lwinner[1]}', '{Now()}', '{lottoinfo['payout']}', 1)")
            if lwinner[19] is None:
                lwin = 0
            else:
                lwin = int(lwinner[19])
            nlw = lwin + int(lottoinfo['payout'])
            await db.update(f"UPDATE players SET lottowins = '{int(lwinner[18]) + 1}', lotterywinnings = '{nlw}' WHERE steamid = '{lwinner[0]}'")
        except:
            log.exception('Critical Error Lottery Winner determination!')
    else:
        log.log('LOTTO', f'Lottery has ended. Not enough players: ({len(lottoers)}/3)')
        await db.update(f"UPDATE lotteryinfo SET winner = 'None', completed = True WHERE id = {lottoinfo['id']}")
        msg = f'Lottery has ended. Not enough players have participated.  Requires at least 3 players.\nNo points will be withdrawn from any participants.\nNext lottery begins in 1 hour.'
        await asyncwritediscord(f'NONE', Now(), name=f'{len(lottoers)}', server='LOTTOEND')
        await asyncwriteglobal('ALERT', 'ALERT', msg)


async def asynclotteryloop(lottoinfo):
    if lottoinfo['announced'] is False:
        log.debug('clearing lotteryplayers table')
        await db.update("DELETE FROM lotteryplayers")
    redis.set('inlottery', 1)
    log.debug('lottery loop has begun, waiting for lottery entries')
    while redis.get('inlottery') == 1:
        await asyncio.sleep(Secs['5min'])
        tdy = lottoinfo['startdate'] + timedelta(hours=lottoinfo['days'])
        # tdy = lottoinfo['startdate'] + timedelta(minutes=5)  # quick 5 min for testing
        if Now(fmt='dt') >= tdy:
            await asyncdeterminewinner(lottoinfo)
            redis.set('inlottery', 1)
    log.debug(f'Lottery loop has completed')


async def asyncstartlottery(lottoinfo):
    lend = elapsedTime(datetimeto(lottoinfo['startdate'] + timedelta(hours=lottoinfo['days']), fmt='epoch'), Now())
    if lottoinfo['announced'] is False:
        log.log('LOTTO', f'New lottery has started. Buyin: {lottoinfo["buyin"]} Starting: {lottoinfo["payout"]} Length: {lottoinfo["days"]}')
        bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="0,1,0,1">       A new points lottery has started! {lottoinfo['buyin']} points to enter in this lottery </>\n\n<RichColor Color="1,1,0,1">             Starting pot {lottoinfo['payout']} points and grows as players enter </>\n                   Lottery Ends in {lend}\n\n             Type !lotto for more info or !lotto enter to join"""

        await asyncwriteglobal('ALERT', 'LOTTERY', bcast)
        await asyncwritediscord(f'{lottoinfo["payout"]}', Now(), name=f'{lend}', server='LOTTOSTART')
        await db.update(f"UPDATE lotteryinfo SET announced = True WHERE id = {lottoinfo['id']}")
    asyncio.create_task(asynclotteryloop(lottoinfo))


async def asyncgeneratelottery():
    log.debug('Generate new lottery check')
    lottodata = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    if not lottodata:
        t, s, e = datetime.now(), dt(21, 0), dt(21, 10)  # Automatic Lottery 9:00pm GMT (5:00PM EST)
        lottotime = is_time_between(t, s, e)
        if lottotime:
            buyins = [25, 30, 20, 35]
            length = 23
            buyin = choice(buyins)
            litm = buyin * 25
            await db.update(f"""INSERT INTO lotteryinfo (payout,startdate,buyin,days,players,winner,announced,completed) VALUES ('{litm}','{Now(fmt="dt")}','{buyin}','{length}',0,'Incomplete',False,False)""")


async def asynccheckforlottery():
    log.debug('Running lottery check')
    lottoinfo = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    if lottoinfo:
        await asyncstartlottery(lottoinfo)


async def asynclotterywatcher():
    await asyncgeneratelottery()
    await asynccheckforlottery()
