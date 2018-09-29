#!/usr/bin/python3

import time, logging, sqlite3, subprocess, socket, random
from datetime import datetime
from configreader import *
from timehelper import estshift

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

def writediscord(msg,tstamp):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', ('generalchat','ALERT',msg,tstamp))
    conn4.commit()
    c4.close()
    conn4.close()

def writeglobal(inst,whos,msg):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,time.time()))
    conn.commit()
    c.close()
    conn.close()


def determinewinner(linfo):
    log.info('Lottery time has ended. Determining winner.')
    winners = []
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('SELECT * FROM lotteryplayers')
    lottoers = c4.fetchall()
    c4.close()
    conn4.close()
    print(lottoers)
    if len(lottoers) > 0:   ### change back to 3
        for eachn in lottoers:
            winners.append(eachn[0])
        winnersid = random.choice(list(enumerate(winners)))
        conn4 = sqlite3.connect(sqldb)
        c4 = conn4.cursor()
        c4.execute('SELECT * FROM players WHERE steamid = ?', (winnersid[1],))
        lwinner = c4.fetchone()
        c4.execute('UPDATE lotteryinfo SET winner = ?', (lwinner[1],))
        conn4.commit()
        c4.close()
        conn4.close()
        log.info(f'Lottery winner is: {lwinner[1]}')
        winners.remove(winnersid[1])
        log.info(f'queuing up lottery deposits for {winners}')
        for ueach in winners:
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            c4.execute('SELECT playername FROM players WHERE steamid = ?', (ueach,))
            kk = c4.fetchone()
            c4.execute('INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES (?, ?, ?, ?, ?)', (kk[0],kk[1],time.time(),linfo[4],0))
            conn4.commit()
            c4.close()
            conn4.close()
        msg = f'The lottery has ended, and the winner is {lwinner[1].upper()}!'
        writediscord(msg,time.time())
        if linfo[1] == 'points': 
            msg = f'{lwinner[1].capitalize()} has won {linfo[2]} ARc Reward Points'
            writediscord(msg,time.time())
            conn4 = sqlite3.connect(sqldb)
            c4 = conn4.cursor()
            ku = c4.fetchone()
            c4.execute('INSERT INTO lotterydeposits (steamid, playername, timestamp, points, givetake) VALUES (?, ?, ?, ?, ?)', (lwinner[0],lwinner[1],time.time(),linfo[2],1))
            c4.execute('UPDATE players SET lottowins = ? WHERE steamid = ?', (int(lwinner[18])+1,lwinner[0]))
            conn4.commit()
            c4.close()
            conn4.close()

        else:
            msg = f'{lwinner[1].capitalize()} has won a {linfo[2]}'
            writediscord(msg,time.time())

    else:
        log.info(f'Lottery has ended. Not enough players: {len(lottoers)}')
        conn4 = sqlite3.connect(sqldb)
        c4 = conn4.cursor()
        c4.execute('UPDATE lotteryinfo SET winner = "None" WHERE winner = "Incomplete"')
        conn4.commit()
        c4.close()
        conn4.close()
        msg = f'Lottery has ended. Not enough players have participated.  Requires at least 4.'
        writediscord(msg,time.time())
        msg = f'No points will be withdawn from any participants.'
        writediscord(msg,time.time())



def lotteryloop():
    log.debug('clearing lotteryplayers table')
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('DELETE FROM lotteryplayers')
    c4.execute('SELECT * FROM lotteryinfo WHERE winner = "Incomplete"')
    conn4.commit()
    linfo = c4.fetchone()
    c4.close()
    conn4.close()
    inlottery = True
    log.info('starting lottery wait loop')
    while inlottery:
        time.sleep(60)
        #tdy = float(linfo[3])+(84600*int(linfo[5])
        tdy = float(linfo[3])+300*int(linfo[5])
        if time.time() >= tdy:
            determinewinner(linfo)
            inlottery = False
    log.info(f'Lottery loop has completed')

    

def startlottery(lottoinfo):
    if lottoinfo[1] == 1:
        lottotype = 'Points'
        litm = 'ARc reward points accumulated pot'
    else:
        lottotype = 'Item'
        litm = lottoinfo[2]
    lottostart = estshift(datetime.fromtimestamp(float(lottoinfo[3])+(86400*int(lottoinfo[5])))).strftime('%a, %b %d %I:%M%p')

    log.info(f'New lottery has started. Type: {lottotype} Payout: {lottoinfo[2]} Buyin: {lottoinfo[4]} Days: {lottoinfo[5]}')
    msg = f'A new {lottotype} lottery has started! Cost to enter: {lottoinfo[4]} ARc Points'
    writediscord(msg,time.time())
    msg = f'Winning prize: {litm}'
    writediscord(msg,time.time())
    msg = f'Type !lottery or !lotto for more information'
    writediscord(msg,time.time())

    msg = f'A new {lottotype} lottery has started! Cost to enter: {lottoinfo[4]} ARc Points'
    writeglobal('ALERT','ALERT',msg)
    msg = f'Winning prize: {litm}'
    writeglobal('ALERT','ALERT',msg)
    msg = f'Type !lottery or !lotto for more information'
    writeglobal('ALERT','ALERT',msg)

    lotteryloop()

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
            try:
                if c4 in vars():
                    c4.close()
            except:
                pass
            try:
                if conn4 in vars():
                    conn4.close()
            except:
                pass

