from datetime import datetime
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import estshift, Secs, Now
from numpy import argmax
from numpy.random import seed, shuffle, randint
from time import sleep
import logging
import socket


hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def writediscord(msg, tstamp):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             ('generalchat', 'ALERT', msg, tstamp))


def writeglobal(inst, whos, msg):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             (inst, whos, msg, Now()))


def determinewinner(linfo):
    log.info('Lottery time has ended. Determining winner.')
    winners = []
    picks = []
    adjpicks = []
    wins = []
    lottoers = dbquery("SELECT * FROM lotteryplayers")
    linfo = dbquery("SELECT * FROM lotteryinfo WHERE id = '%s'" % (linfo[0],), fetch='one')
    if len(lottoers) >= 3:
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
        dbupdate("UPDATE lotteryinfo SET winner = '%s' WHERE id = '%s'" % (lwinner[1], linfo[0]))
        log.info(f'Lottery winner is: {lwinner[1]}')
        winners.remove(winnersid)
        log.info(f'queuing up lottery deposits for {winners}')
        for ueach in winners:
            kk = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (ueach,), fetch='one')
            dbupdate("INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                       ('%s', '%s', '%s', '%s', '%s')" % (kk[0], kk[1], Now(), linfo[4], 0))
        msg = f'The lottery has ended, and the winner is {lwinner[1].upper()}!\n'
        if linfo[1] == 'points':
            msg = msg + f'{lwinner[1].capitalize()} has won {linfo[2]} ARc Reward Points'
            writediscord(msg, Now())
            writeglobal('ALERT', 'ALERT', msg)
            dbupdate("INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                       ('%s', '%s', '%s', '%s', '%s')" % (lwinner[0], lwinner[1], Now(), linfo[2], 1))
            nlw = int(lwinner[19]) + int(linfo[2])
            dbupdate("UPDATE players SET lottowins = '%s', lotterywinnings = '%s' WHERE steamid = '%s'" % (int(lwinner[18]) + 1, nlw, lwinner[0]))
        else:
            msg = msg + f'{lwinner[1].capitalize()} has won a {linfo[2]}'
            writediscord(msg, Now())
            writeglobal('ALERT', 'ALERT', msg)
            dbupdate("UPDATE players SET lottowins = '%s' WHERE steamid = '%s'" % (int(lwinner[18]) + 1, lwinner[0]))
    else:
        log.info(f'Lottery has ended. Not enough players: {len(lottoers)}')
        dbupdate("UPDATE lotteryinfo SET winner = 'None' WHERE winner = 'Incomplete'")
        msg = f'Lottery has ended. Not enough players have participated.  Requires at least 3 players.'
        writediscord(msg, Now())
        writeglobal('ALERT', 'ALERT', msg)
        sleep(3)
        msg = f'No points will be withdrawn from any participants.'
        writediscord(msg, Now())
        writeglobal('ALERT', 'ALERT', msg)


def lotteryloop(linfo):
    if linfo[8] == 0 or linfo[8] is None:
        log.debug('clearing lotteryplayers table')
        dbupdate("UPDATE lotteryinfo SET announced = 1 WHERE id = '%s'" % (linfo[0],))
        dbupdate("DELETE FROM lotteryplayers")
    inlottery = True
    log.info('lottery loop has begun, waiting for lottery entries')
    while inlottery:
        sleep(Secs['1min'])
        try:
            tdy = float(linfo[3]) + (Secs['hour'] * int(linfo[5]))
        # tdy = float(linfo[3])+300*int(linfo[5]) ## quick 5 min for testing
            if Now() >= tdy:
                determinewinner(linfo)
                inlottery = False
        except:
            log.error('lottery loop error, ignoring')
    log.info(f'Lottery loop has completed')


def startlottery(lottoinfo):
    if lottoinfo[1] == 'points':
        lottotype = 'points'
        litm = 'ARc points lottery pool'
    else:
        lottotype = 'Item'
        litm = lottoinfo[2]
    lottoend = estshift(datetime.fromtimestamp(float(lottoinfo[3]) + (Secs['hour'] * int(lottoinfo[5])))).strftime('%a, %b %d %I:%M%p')
    if lottoinfo[8] == 0 or lottoinfo[8] is None:
        log.info(f'A lottery has started. Type: {lottotype} Payout: {lottoinfo[2]} Buyin: {lottoinfo[4]} \
Length: {lottoinfo[5]} Hours, Ends: {lottoend}')
        msg = f'A new {lottotype} lottery has started! {lottoinfo[4]} ARc Points to enter\nWinning prize: \
{litm}, Lottery Ends: {lottoend} - Type !lotto for more info'
        writeglobal('ALERT', 'ALERT', msg)
        writediscord(msg, Now())
        sleep(3.1)
    lotteryloop(lottoinfo)


def checkfornewlottery():
    lottoinfo = dbquery("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'", fetch='one')
    if lottoinfo:
        startlottery(lottoinfo)


def lotterywatcher():
    while True:
        try:
            checkfornewlottery()
            sleep(Secs['1min'])
        except:
            log.critical('Critical Error Lottery Watcher!', exc_info=True)
