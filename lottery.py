#!/usr/bin/python3

import time, logging, sqlite3, socket
from datetime import datetime
from numpy.random import seed, shuffle, randint
from numpy import argmax
from configreader import sqldb
from timehelper import estshift

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def writediscord(msg, tstamp):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)',
               ('generalchat', 'ALERT', msg, tstamp))
    conn4.commit()
    c4.close()
    conn4.close()


def writeglobal(inst, whos, msg):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)',
              (inst, whos, msg, time.time()))
    conn.commit()
    c.close()
    conn.close()


def determinewinner(linfo):
    log.info('Lottery time has ended. Determining winner.')
    winners = []
    picks = []
    adjpicks = []
    wins = []
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM lotteryplayers')
    lottoers = c4.fetchall()
    c4.execute('SELECT * FROM lotteryinfo WHERE id = ?', (linfo[0],))
    linfo = c4.fetchone()
    c4.close()
    conn4.close()
    if len(lottoers) >= 3:
        for eachn in lottoers:
            winners.append(eachn[0])
        seed(randint(100))
        shuffle(winners)
        seed(randint(100))
        for eachw in range(len(winners)):
            picks.append(randint(100))
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            c4.execute('SELECT lottowins FROM players WHERE steamid = ?', (winners[eachw],))
            lwins = c4.fetchone()
            c4.close()
            conn4.close()
            wins.append(lwins[0])
            if wins[eachw] > 10:
                adjj = 10
            else:
                adjj = wins[eachw]
            adjpicks.append(picks[eachw] - adjj * 5)
        winneridx = argmax(adjpicks)
        winnersid = winners[winneridx]
        conn4 = sqlite3.connect(sqldb)
        c4 = conn4.cursor()
        c4.execute('SELECT * FROM players WHERE steamid = ?', (winnersid,))
        lwinner = c4.fetchone()
        c4.execute('UPDATE lotteryinfo SET winner = ? WHERE id = ?', (lwinner[1], linfo[0]))
        conn4.commit()
        c4.close()
        conn4.close()
        log.info(f'Lottery winner is: {lwinner[1]}')
        winners.remove(winnersid)
        log.info(f'queuing up lottery deposits for {winners}')
        for ueach in winners:
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            c4.execute('SELECT * FROM players WHERE steamid = ?', (ueach,))
            kk = c4.fetchone()
            c4.execute('INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                       (?, ?, ?, ?, ?)', (kk[0], kk[1], time.time(), linfo[4], 0))
            conn4.commit()
            c4.close()
            conn4.close()
        msg = f'The lottery has ended, and the winner is {lwinner[1].upper()}!\n'
        if linfo[1] == 'points':
            msg = msg + f'{lwinner[1].capitalize()} has won {linfo[2]} ARc Reward Points'
            writediscord(msg, time.time())
            writeglobal('ALERT', 'ALERT', msg)
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            c4.execute('INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES \
                       (?, ?, ?, ?, ?)', (lwinner[0], lwinner[1], time.time(), linfo[2], 1))
            nlw = int(lwinner[19]) + int(linfo[2])
            c4.execute('UPDATE players SET lottowins = ?, lotterywinnings = ? WHERE steamid = ?', (int(lwinner[18]) + 1, nlw, lwinner[0]))
            conn4.commit()
            c4.close()
            conn4.close()
        else:
            msg = msg + f'{lwinner[1].capitalize()} has won a {linfo[2]}'
            writediscord(msg, time.time())
            writeglobal('ALERT', 'ALERT', msg)
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            c4.execute('UPDATE players SET lottowins = ? WHERE steamid = ?', (int(lwinner[18]) + 1, lwinner[0]))
            conn4.commit()
            c4.close()
            conn4.close()
    else:
        log.info(f'Lottery has ended. Not enough players: {len(lottoers)}')
        conn4 = sqlite3.connect(sqldb)
        c4 = conn4.cursor()
        c4.execute('UPDATE lotteryinfo SET winner = "None" WHERE winner = "Incomplete"')
        conn4.commit()
        c4.close()
        conn4.close()
        msg = f'Lottery has ended. Not enough players have participated.  Requires at least 3 players.'
        writediscord(msg, time.time())
        writeglobal('ALERT', 'ALERT', msg)
        time.sleep(3)
        msg = f'No points will be withdrawn from any participants.'
        writediscord(msg, time.time())
        writeglobal('ALERT', 'ALERT', msg)


def lotteryloop(linfo):
    if linfo[8] == 0 or linfo[8] is None:
        log.debug('clearing lotteryplayers table')
        conn4 = sqlite3.connect(sqldb)
        c4 = conn4.cursor()
        c4.execute('UPDATE lotteryinfo SET announced = 1 WHERE id = ?', (linfo[0],))
        c4.execute('DELETE FROM lotteryplayers')
        conn4.commit()
        c4.close()
        conn4.close()
    inlottery = True
    log.info('lottery loop has begun, waiting for lottery entries')
    while inlottery:
        time.sleep(60)
        try:
            tdy = float(linfo[3]) + (3600 * int(linfo[5]))
        # tdy = float(linfo[3])+300*int(linfo[5]) ## quick 5 min for testing
            if time.time() >= tdy:
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
    lottoend = estshift(datetime.fromtimestamp(float(lottoinfo[3]) + (3600 * int(lottoinfo[5])))).strftime('%a, %b %d %I:%M%p')
    if lottoinfo[8] == 0 or lottoinfo[8] is None:
        log.info(f'A lottery has started. Type: {lottotype} Payout: {lottoinfo[2]} Buyin: {lottoinfo[4]} \
Length: {lottoinfo[5]} Hours, Ends: {lottoends}')
        msg = f'A new {lottotype} lottery has started! {lottoinfo[4]} ARc Points to enter\nWinning prize: \
{litm}, Lottery Ends: {lottoend} - Type !lotto for more info'
        writeglobal('ALERT', 'ALERT', msg)
        writediscord(msg, time.time())
        time.sleep(3.1)
    lotteryloop(lottoinfo)


def checkfornewlottery():
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM lotteryinfo WHERE winner == "Incomplete"')
    lottoinfo = c4.fetchone()
    c4.close()
    conn4.close()
    if lottoinfo:
        startlottery(lottoinfo)


def lotterywatcher():
    while True:
        try:
            checkfornewlottery()
            time.sleep(60)
        except:
            log.critical('Critical Error Lottery Watcher!', exc_info=True)
