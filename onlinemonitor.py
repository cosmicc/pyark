import time, socket, logging, sqlite3, threading, subprocess
from timehelper import elapsedTime, playedTime, wcstamp
from configreader import sqldb
from auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

welcomthreads = []
greetthreads = []

global instance


def resetplayerbit(steamid):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('UPDATE players SET restartbit = 0 WHERE steamid = ?', (steamid,))
    conn.commit()
    c.close()
    conn.close()


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * from players WHERE playername = ?', (whos,))
        isindb = c.fetchone()
        c.close()
        conn.close()
    elif whos == "ALERT" or isindb:
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)',
                  (inst, whos, msg, tstamp))
        conn.commit()
        c.close()
        conn.close()


def welcomenewplayer(steamid, inst):
        global welcomthreads
        log.info(f'welcome message thread started for new player {steamid} on {inst}')
        time.sleep(180)
        mtxt = 'Welcome to the Ultimate Extinction Core Galaxy Server Cluster!'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        time.sleep(10)
        mtxt = 'ARc rewards points earned as you play. Public teleporters, crafting area, and auction house. Build \
or find a rewards vault, free starter items.'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        time.sleep(10)
        mtxt = 'You get all your items back when you die automatically, The engram menu is laggy, sorry. Admins and \
help in discord. Press F1 at anytime for help. Have Fun!'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        time.sleep(15)
        mtxt = 'Everyone welcome a new player to the cluster!'
        subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
        log.debug(f'welcome message thread complete for new player {steamid} on {inst}')
        welcomthreads[:] = [d for d in welcomthreads if d.get('steamid') != steamid]


def iswelcoming(steamid):
    for each in welcomthreads:
        if each['steamid'] == steamid:
            if each['sthread'].is_alive():
                return True
            else:
                return False


def isgreeting(steamid):
    for each in greetthreads:
        if each['steamid'] == steamid:
            if each['gthread'].is_alive():
                return True
            else:
                return False


def serverisinrestart(steamid, inst, oplayer):
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * FROM instances WHERE name = ?', [inst])
    rbt = c1.fetchone()
    c1.close()
    conn1.close()
    if rbt[3] == "True":
        log.info(f'notifying player {oplayer[1]} that server {inst} will be restarting in {rbt[7]} min')
        mtxt = f'WARNING: server is restarting in {rbt[7]} minutes'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)


def isinlottery(steamid):
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * FROM lotteryinfo WHERE winner = "Incomplete"')
    isinlotto = c1.fetchone()
    c1.close()
    conn1.close()
    if isinlotto:
        conn1 = sqlite3.connect(sqldb)
        c1 = conn1.cursor()
        c1.execute('SELECT * FROM lotteryplayers WHERE steamid = ?', (steamid,))
        isinlotto2 = c1.fetchone()
        c1.close()
        conn1.close()
        if isinlotto2:
            return True
        else:
            return False
    else:
        return True


def checklottodeposits(steamid, inst):
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * FROM lotterydeposits WHERE steamid = ?', (steamid,))
    lottocheck = c1.fetchall()
    c1.execute('SELECT * FROM players WHERE steamid = ?', (steamid,))
    elpinfo = c1.fetchone()
    c1.close()
    conn1.close()
    if lottocheck and inst == elpinfo[15]:
        log.warning(lottocheck)
        for weach in lottocheck:
            if weach[4] == 1:
                log.info(f'{weach[3]} points added to {elpinfo[1]} for a lottery win')
                msg = f'{weach[3]} ARc points have been deposited into your account for a lottery win!'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, msg, inst), shell=True)
                subprocess.run('arkmanager rconcmd "ScriptCommand TCsAR AddARcTotal %s %s" @%s' %
                               (steamid, weach[3], inst), shell=True)
            elif weach[4] == 0:
                log.info(f'{weach[3]} points removed from {elpinfo[1]} for a lottery entry')
                msg = f'{weach[3]} ARc points have been withdrawn from your account for a lottery entry'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, msg, inst), shell=True)
                subprocess.run('arkmanager rconcmd "ScriptCommand TCsAR SetARcTotal %s %s" @%s' %
                               (steamid, str(int(elpinfo[5]) - int(weach[3])), inst), shell=True)
        conn1 = sqlite3.connect(sqldb)
        c1 = conn1.cursor()
        c1.execute('DELETE FROM lotterydeposits WHERE steamid = ?', (steamid,))
        conn1.commit()
        c1.close()
        conn1.close()


def playergreet(steamid, inst):
    global greetthreads
    gogo = 0
    xferpoints = 0
    global welcomthreads
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * FROM players WHERE steamid = ?', [steamid])
    oplayer = c1.fetchone()
    timestamp = time.time()
    c1.execute('SELECT * FROM players WHERE steamid = ? AND banned != ""', [steamid])
    poplayer = c1.fetchone()
    c1.execute('SELECT * FROM banlist WHERE steamid = ?', [steamid])
    bplayer = c1.fetchone()
    c1.close()
    conn1.close()
    timestamp = time.time()
    if poplayer:
        if not bplayer:
            log.error(f'banned player out of sync issue {steamid} on instance {inst}. not in banlist')
    if bplayer:
        if not poplayer:
            log.error(f'banned player out of sync issue {steamid} on instance {inst}. not banned in playerlist')
    if poplayer or bplayer:
        log.warning(f'banned player with steamid {steamid} has tried to connect or is online on {inst}.\
kicking and banning.')
        subprocess.run("""arkmanager rconcmd 'kickplayer %s' @%s""" % (steamid, inst), shell=True)
        subprocess.run("""arkmanager rconcmd 'banplayer %s' @%s""" % (steamid, inst), shell=True)
    else:
        log.debug(f'player {steamid} passed ban checks')
        if not oplayer:
            log.info(f'steamid {steamid} was not found. adding new player to cluster!')
            conn1 = sqlite3.connect(sqldb)
            c1 = conn1.cursor()
            c1.execute('INSERT INTO players (steamid, playername, lastseen, server, playedtime, rewardpoints, \
                       firstseen, connects, discordid, banned, totalauctions, itemauctions, dinoauctions, restartbit, \
                       primordialbit, homeserver, transferpoints, lastpointtimestamp, lottowins) VALUES \
                       (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (steamid, 'newplayer', timestamp, inst, '1', 50, timestamp, 1, '', '', 0, 0, 0,
                        0, 0, inst, 0, timestamp, 0))
            conn1.commit()
            c1.close()
            conn1.close()
            if not iswelcoming(steamid):
                welcom = threading.Thread(name='welcoming-%s' % steamid, target=welcomenewplayer, args=(steamid, inst))
                welcomthreads.append({'steamid': steamid, 'sthread': welcom})
                welcom.start()
            else:
                log.warning(f'welcome message thread already running for new player {steamid}')
            writechat(inst, 'ALERT', f'<<< A New player has joined the cluster!', wcstamp())
        elif len(oplayer) > 2:
            if oplayer[16] != 0 and oplayer[15] == inst:
                    xferpoints = int(oplayer[16])
                    log.info(f'transferring {xferpoints} non home server points into account for \
{oplayer[1]} on {inst}')
                    conn1 = sqlite3.connect(sqldb)
                    c1 = conn1.cursor()
                    c1.execute('UPDATE players SET transferpoints = 0 WHERE steamid = ?', (steamid,))
                    conn1.commit()
                    c1.close()
                    conn1.close()
                    subprocess.run('arkmanager rconcmd "ScriptCommand TCsAR AddARcTotal %s %s" @%s' %
                                   (steamid, xferpoints, inst), shell=True)
            if float(oplayer[2]) + 300 > float(time.time()):
                if oplayer[3] != inst:
                    gogo = 1
                    mtxt = f'{oplayer[1].capitalize()} has transferred here from {oplayer[3].capitalize()}'
                    subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
                    writechat(inst, 'ALERT', f'>><< {oplayer[1].capitalize()} has transferred from \
{oplayer[3].capitalize()} to {inst.capitalize()}', wcstamp())
                    log.info(f'player {oplayer[1].capitalize()} has transferred from {oplayer[3]} to {inst}')
                log.debug(f'online player {oplayer[1]} with {steamid} was found. updating info.')
                conn1 = sqlite3.connect(sqldb)
                c1 = conn1.cursor()
                c1.execute('UPDATE players SET lastseen = ?, server = ? WHERE steamid = ?', (timestamp, inst, steamid))
                conn1.commit()
                c1.close()
                conn1.close()
            else:
                log.info(f"player {oplayer[1]} has joined {inst}, total player's connections {int(oplayer[7])+1}. \
updating info.")
                conn1 = sqlite3.connect(sqldb)
                c1 = conn1.cursor()
                c1.execute('UPDATE players SET lastseen = ?, server = ?, connects = ? WHERE steamid = ?',
                           (timestamp, inst, int(oplayer[7]) + 1, steamid))
                conn1.commit()
                c1.close()
                conn1.close()
                laston = elapsedTime(float(time.time()), float(oplayer[2]))
                totplay = playedTime(float(oplayer[4].replace(',', '')))
                log.debug(f'fetching steamid {steamid} auctions from auction api website')
                pauctions = fetchauctiondata(steamid)
                totauctions, iauctions, dauctions = getauctionstats(pauctions)
                writeauctionstats(steamid, totauctions, iauctions, dauctions)
                time.sleep(3)
                newpoints = int(str(oplayer[5]).replace(',', '')) + xferpoints
                mtxt = f'Welcome back {oplayer[1]}, you have {newpoints} ARc reward points on \
{oplayer[15].capitalize()}, {totauctions} auctions, last online {laston} ago, total time played {totplay}'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
                time.sleep(1)
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM players WHERE server = ? AND steamid != ?', (inst, steamid))
                flast = c.fetchall()
                c.close()
                conn.close()
                pcnt = 0
                plist = ''
                potime = 40
                for row in flast:
                    chktme = time.time() - float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].capitalize())
                        else:
                            plist = plist + ', %s' % (row[1].capitalize())
                if pcnt != 0:
                    msg = f'There are {pcnt} other players online: {plist}'
                else:
                    msg = f'There are no other players are online on this server.'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, msg, inst), shell=True)
                time.sleep(2)
                if int(oplayer[14]) == 1 and int(oplayer[13]) == 1 and oplayer[3] == inst:
                    mtxt = f'WARNING: Server has restarted since you logged in, vivarium your primordials!'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
                    resetplayerbit(steamid)
                if oplayer[8] == '':
                    time.sleep(5)
                    mtxt = f'Your player is not linked with a discord account yet. type !linkme in global chat'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
                if not isinlottery(steamid):
                    time.sleep(3)
                    mtxt = f'A lottery you have not entered yet is underway. Type !lotto for more information'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)

            if xferpoints != 0:
                    time.sleep(2)
                    mtxt = f'{xferpoints} rewards points were transferred to you from other cluster servers'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" %
                                   (steamid, mtxt, inst), shell=True)
            checklottodeposits(steamid, inst)
            if float(oplayer[2]) + 60 < float(time.time()) and gogo == 0:
                mtxt = f'{oplayer[1].capitalize()} has joined the server'
                subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
                writechat(inst, 'ALERT', f'<<< {oplayer[1].capitalize()} has joined the server', wcstamp())
                serverisinrestart(steamid, inst, oplayer)
    greetthreads[:] = [d for d in greetthreads if d.get('steamid') != steamid]


def onlineupdate(inst):
    global greetthreads
    log.debug(f'starting online player watcher on {inst}')
    while True:
        try:
            cmdpipe = subprocess.Popen('arkmanager rconcmd ListPlayers @%s' % inst, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, shell=True)
            b = cmdpipe.stdout.read().decode("utf-8")
            for line in iter(b.splitlines()):
                if line.startswith('Running command') or line.startswith('"') or line.startswith(' "') \
                   or line.startswith('Error:'):
                    pass
                else:
                    if line.startswith('"No Players'):
                        pass
                    else:
                        rawline = line.split(',')
                        log.debug(rawline)
                        if len(rawline) > 1:
                            nsteamid = rawline[1].strip()
                            if f'greet-{nsteamid}' not in greetthreads:
                                if not isgreeting(nsteamid):
                                    gthread = threading.Thread(name='greet-%s' % nsteamid, target=playergreet,
                                                               args=(nsteamid, inst))
                                    greetthreads.append({'steamid': nsteamid, 'gthread': gthread})
                                    gthread.start()
                                else:
                                    log.debug(f'online player greeting aleady running for {nsteamid}')
                            else:
                                log.debug(f'greeting already running for {nsteamid}')
                        else:
                            log.error(f'problem with parsing online player - {rawline}')
            time.sleep(10)
        except:
            log.critical('Critical Error in Online Updater!', exc_info=True)
