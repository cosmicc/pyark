from datetime import timedelta
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import estshift, Secs, Now, datetimeto, elapsedTime
from numpy import argmax
from numpy.random import seed, shuffle, randint
from time import sleep
import logging
import socket


hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def writediscord(msg, tstamp):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % ('generalchat', 'ALERT', msg, tstamp))


def writeglobal(inst, whos, msg):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, Now()))


def isinlottery():
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False")
    if linfo:
        return True
    else:
        return False


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
    log.info('Lottery time has ended. Determining winner.')
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
            log.info(f'Lottery winner is: {lwinner[1]}')
            winners.remove(winnersid)
            log.info(f'queuing up lottery deposits for {winners}')
            for ueach in winners:
                kk = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (ueach,), fetch='one')
                dbupdate("INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                           ('%s', '%s', '%s', '%s', '%s')" % (kk[0], kk[1], Now(), linfo['buyin'], 0))
            msg = f'The lottery has ended, and the winner is {lwinner[1].upper()}!\n{lwinner[1].capitalize()} has won {linfo["payout"]} ARc Reward Points'
            writediscord(msg, Now())
            writeglobal('ALERT', 'ALERT', msg)
            dbupdate("INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                       ('%s', '%s', '%s', '%s', '%s')" % (lwinner[0], lwinner[1], Now(), linfo['payout'], 1))
            nlw = int(lwinner[19]) + int(linfo['payout'])
            dbupdate("UPDATE players SET lottowins = '%s', lotterywinnings = '%s' WHERE steamid = '%s'" % (int(lwinner[18]) + 1, nlw, lwinner[0]))
        except:
            log.critical('Critical Error Lottery Winner determination!', exc_info=True)
    else:
        log.info(f'Lottery has ended. Not enough players: ({len(lottoers)}/3)')
        dbupdate("UPDATE lotteryinfo SET winner = 'None', completed = True WHERE id = %s" % (linfo["id"],))
        msg = f'Lottery has ended. Not enough players have participated.  Requires at least 3 players.\nNo points will be withdrawn from any participants.'
        writediscord(msg, Now())
        writeglobal('ALERT', 'ALERT', msg)


def lotteryloop(linfo):
    if linfo['announced'] is False:
        log.debug('clearing lotteryplayers table')
        dbupdate("DELETE FROM lotteryplayers")
    inlottery = True
    log.info('lottery loop has begun, waiting for lottery entries')
    while inlottery:
        sleep(Secs['5min'])
        tdy = linfo['startdate'] + timedelta(days=linfo['days'])
        # tdy = linfo['startdate'] + timedelta(minutes=5)  # quick 5 min for testing
        if Now(fmt='dt') >= tdy:
            determinewinner(linfo)
            inlottery = False
    log.info(f'Lottery loop has completed')


def startlottery(lottoinfo):
    # lottoend = estshift(lottoinfo['startdate'] + timedelta(days=lottoinfo['days']))
    lend = elapsedTime(datetimeto(lottoinfo['startdate'] + timedelta(days=lottoinfo['days']), fmt='epoch'), Now())
    if lottoinfo['announced'] is False:
        log.info(f'New lottery has started. Buy-in: {lottoinfo["buyin"]}, Starting pot: {lottoinfo["payout"]}, Length: {lottoinfo["days"]} Days, Ends in {lend}')
        msg = f'A new lottery has started! {lottoinfo["buyin"]} points to enter in this lottery.\nStarting pot {lottoinfo["payout"]} points and grows as players enter. '
        msg = msg + f'Lottery Ends in {lend}\nType !lotto for more info or !lotto enter to join'
        writeglobal('ALERT', 'ALERT', msg)
        writediscord(msg, Now())
        dbupdate("UPDATE lotteryinfo SET announced = True WHERE id = %s" % (lottoinfo["id"],))
        sleep(10)
    lotteryloop(lottoinfo)


def checkfornewlottery():
    lottoinfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
    if lottoinfo:
        startlottery(lottoinfo)


def lotterywatcher():
    while True:
        try:
            checkfornewlottery()
            sleep(Secs['3min'])
        except:
            log.critical('Critical Error Lottery Watcher!', exc_info=True)
            sleep(Secs['5min'])
