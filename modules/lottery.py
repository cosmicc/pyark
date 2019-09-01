from datetime import datetime
from datetime import time as dt
from datetime import timedelta
from random import choice
from time import sleep

from loguru import logger as log
from modules.dbhelper import asyncdbquery, dbquery, dbupdate
from modules.timehelper import Now, Secs, datetimeto, elapsedTime, estshift
from numpy import argmax
from numpy.random import randint, seed, shuffle
from timebetween import is_time_between


def writediscord(msg, tstamp, server='generalchat', name='ALERT'):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (server, name, msg, tstamp))


def writeglobal(inst, whos, msg):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, Now()))


def getlastlotteryinfo():
    return dbquery("SELECT * FROM lotteryinfo WHERE completed = True ORDER BY id desc", fetch='one', fmt='dict')


async def asyncgetlastlotteryinfo():
    return await asyncdbquery("SELECT * FROM lotteryinfo WHERE completed = True ORDER BY id desc", 'dict', 'one')


def isinlottery():
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False")
    if linfo:
        return True
    else:
        return False


def getlottowinnings(pname):
    pwins = dbquery("SELECT payout FROM lotteryinfo WHERE winner = '%s'" % (pname,))
    totpoints = 0
    twins = 0
    for weach in pwins:
        totpoints = totpoints + int(weach[0])
        twins += 1
    return twins, totpoints


def getlotteryplayers(fmt):
    linfo = dbquery("SELECT playername FROM lotteryplayers", fmt=fmt)
    return linfo


def totallotterydeposits(steamid):
    linfo = dbquery("SELECT points, givetake FROM lotterydeposits where steamid = '%s'" % (steamid, ))
    tps = 0
    if linfo is not None:
        for each in linfo:
            if each[1] == 1:
                tps += each[0]
            elif each[1] == 0:
                tps -= each[0]
    return tps


def getlotteryendtime():
    linfo = dbquery("SELECT startdate, days from lotteryinfo WHERE completed = False", fetch='one')
    return estshift(linfo[0] + timedelta(days=linfo[1]))


def determinewinner(linfo):
    log.debug('Lottery time has ended. Determining winner.')
    winners = []
    picks = []
    adjpicks = []
    wins = []
    lottoers = dbquery("SELECT * FROM lotteryplayers")
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE id = '%s'" % (linfo['id'],), fetch='one', fmt='dict')
    if len(lottoers) >= 3:
        try:
            for eachn in lottoers:
                winners.append(eachn[0])
            seed(randint(100))
            shuffle(winners)
            seed(randint(100))
            for eachw in range(len(winners)):
                picks.append(randint(100))
                lwins = dbquery("SELECT lottowins FROM players WHERE steamid = '%s'" % (winners[eachw],), fetch='one')
                wins.append(lwins[0])
                if wins[eachw] > 10:
                    adjj = 10
                else:
                    adjj = wins[eachw]
                adjpicks.append(picks[eachw] - adjj * 5)
            winneridx = argmax(adjpicks)
            winnersid = winners[winneridx]
            lwinner = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (winnersid,), fetch='one')
            dbupdate("UPDATE lotteryinfo SET winner = '%s', completed = True WHERE id = '%s'" % (lwinner[1], linfo['id']))
            log.log('LOTTO', f'Lottery ended, winner is: {lwinner[1].upper()} for {linfo["payout"]} points, win #{lwinner[18]+1}')
            winners.remove(winnersid)
            log.debug(f'queuing up lottery deposits for {winners}')
            for ueach in winners:
                kk = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (ueach,), fetch='one')
                dbupdate("INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                           ('%s', '%s', '%s', '%s', '%s')" % (kk[0], kk[1], Now(), linfo['buyin'], 0))
            bcast = f"""<RichColor Color="0,1,0,1"> </>\n<RichColor Color="0,1,0,1">                The current lottery has ended, and the winner is...</>\n<RichColor Color="1,1,0,1">                                  {lwinner[1].upper()}!</>\n                      {lwinner[1].capitalize()} has won {linfo["payout"]} Reward Points!\n\n                         Next lottery begins in 1 hour."""
            writeglobal('ALERT', 'LOTTERY', bcast)
            writediscord(f'{lwinner[1].title()}', Now(), name=f'{linfo["payout"]}', server='LOTTOEND')
            dbupdate("INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                       ('%s', '%s', '%s', '%s', '%s')" % (lwinner[0], lwinner[1], Now(), linfo['payout'], 1))
            if lwinner[19] is None:
                lwin = 0
            else:
                lwin = int(lwinner[19])
            nlw = lwin + int(linfo['payout'])
            dbupdate("UPDATE players SET lottowins = '%s', lotterywinnings = '%s' WHERE steamid = '%s'" % (int(lwinner[18]) + 1, nlw, lwinner[0]))
        except:
            log.exception('Critical Error Lottery Winner determination!')
    else:
        log.log('LOTTO', f'Lottery has ended. Not enough players: ({len(lottoers)}/3)')
        dbupdate("UPDATE lotteryinfo SET winner = 'None', completed = True WHERE id = %s" % (linfo["id"],))
        msg = f'Lottery has ended. Not enough players have participated.  Requires at least 3 players.\nNo points will be withdrawn from any participants.\nNext lottery begins in 1 hour.'
        writediscord(f'NONE', Now(), name=f'{len(lottoers)}', server='LOTTOEND')
        writeglobal('ALERT', 'ALERT', msg)


def lotteryloop(linfo, stop_event):
    if linfo['announced'] is False:
        log.debug('clearing lotteryplayers table')
        dbupdate("DELETE FROM lotteryplayers")
    inlottery = True
    log.debug('lottery loop has begun, waiting for lottery entries')
    while inlottery:
        stopsleep(Secs['5min'], stop_event)
        tdy = linfo['startdate'] + timedelta(hours=linfo['days'])
        # tdy = linfo['startdate'] + timedelta(minutes=5)  # quick 5 min for testing
        if Now(fmt='dt') >= tdy:
            determinewinner(linfo)
            inlottery = False
    log.debug(f'Lottery loop has completed')


def startlottery(lottoinfo, stop_event):
    lend = elapsedTime(datetimeto(lottoinfo['startdate'] + timedelta(hours=lottoinfo['days']), fmt='epoch'), Now())
    if lottoinfo['announced'] is False:
        log.log('LOTTO', f'New lottery has started. Buyin: {lottoinfo["buyin"]} Starting: {lottoinfo["payout"]} Length: {lottoinfo["days"]}')
        bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="0,1,0,1">       A new points lottery has started! {lottoinfo['buyin']} points to enter in this lottery </>\n\n<RichColor Color="1,1,0,1">             Starting pot {lottoinfo['payout']} points and grows as players enter </>\n                   Lottery Ends in {lend}\n\n             Type !lotto for more info or !lotto enter to join"""

        writeglobal('ALERT', 'LOTTERY', bcast)
        writediscord(f'{lottoinfo["payout"]}', Now(), name=f'{lend}', server='LOTTOSTART')
        dbupdate("UPDATE lotteryinfo SET announced = True WHERE id = %s" % (lottoinfo["id"],))
    lotteryloop(lottoinfo, stop_event)


def generatelottery():
    amiinalotto = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
    if not amiinalotto:
        t, s, e = datetime.now(), dt(21, 0), dt(21, 10)  # Automatic Lottery 9:00pm GMT (5:00PM EST)
        lottotime = is_time_between(t, s, e)
        if lottotime:
            buyins = [25, 30, 20, 35]
            length = 23
            buyin = choice(buyins)
            litm = buyin * 25
            dbupdate("INSERT INTO lotteryinfo (payout,startdate,buyin,days,players,winner,announced,completed) VALUES ('%s','%s','%s','%s',0,'Incomplete',False,False)" % (litm, Now(fmt="dt"), buyin, length))


def checkfornewlottery(stop_event):
    lottoinfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
    if lottoinfo:
        startlottery(lottoinfo, stop_event)


def stopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Lotterywatcher thread has ended')
            exit(0)
        sleep(1)


@log.catch
def lotterywatcher_thread(dtime, stop_event):
    log.debug('Lotterywatcher thread is starting')
    while not stop_event.is_set():
        generatelottery()
        checkfornewlottery(stop_event)
        stopsleep(dtime, stop_event)
    log.debug('Lotterywatcher thread has ended')
    exit(0)