#!/usr/bin/python3

import time, socket, logging, sqlite3, threading, subprocess
from datetime import datetime, timedelta
from timehelper import *
from auctionhelper import *
from configreader import *

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

welcomthreads = []

numinstances = int(config.get('general', 'instances'))
global instance
instance = [dict() for x in range(numinstances)]
instr = ''
for each in range(numinstances):
    a = config.get('instance%s' % (each), 'name')
    b = config.get('instance%s' % (each), 'logfile')
    instance[each] = {'name':a,'logfile':b}
    if instr == '':
        instr = '%s' % (a)
    else:
        instr=instr + ', %s' % (a)

def follow(stream):
    "Follow the live contents of a text file."
    line = ''
    for block in iter(lambda:stream.read(1024), None):
        if '\n' in block:
            for line in (line+block).splitlines(True)+['']:
                if line.endswith('\n'):
                    yield line
        elif not block:
            # Wait for data.
            time.sleep(1.0)

def writechat(inst,whos,msg,tstamp):
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
        c.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,tstamp))
        conn.commit()
        c.close()
        conn.close()

def processlogline(line,inst):
    if line.find('[TCsAR]') != -1:
        try:
            rawline = line.split('|')
            rawsteamid = rawline[2].split(':')
            steamid = rawsteamid[1].strip()
            rawname = rawline[3].split(':') 
            playername = rawname[1].strip()
            rawplaytime = rawline[8].split(':') 
            playtime = rawplaytime[1].strip()
            rawtimestamp = rawline[0].split(':')
            tstimestamp = rawtimestamp[0][1:]
            rawpoints = rawline[4].split(':')
            rewardpoints = rawpoints[1].strip()
            tsobj = datetime.strptime(tstimestamp, '%Y.%m.%d-%H.%M.%S')
            newts = tsobj
            timestamp = newts.timestamp()
            playername = playername.lower()
        except:
            log.debug(f'error processing TCsAR logline for instance {inst}')
            #log.error(line)
        else:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE steamid = ?', [steamid])
            pexist = c.fetchone()
            c.close()
            conn.close()
            if not pexist:
                if steamid != '':
                    log.info(f'player {playername} with steamid {steamid} was not found. adding.')
                    conn = sqlite3.connect(sqldb)
                    c = conn.cursor()
                    c.execute('INSERT INTO players (steamid, playername, lastseen, playedtime, rewardpoints, firstseen, connects, discordid, banned) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (steamid,playername,timestamp,playtime,rewardpoints,timestamp,1,'',''))
                    conn.commit()
                    c.close()
                    conn.close()
            elif steamid != '':
                log.debug(f'player {playername} with steamid {steamid} was found. updating.')
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('UPDATE players SET playername = ?, playedtime = ?, rewardpoints = ? WHERE steamid = ?', (playername,playtime,rewardpoints,steamid))
                conn.commit()
                c.close()
                conn.close()

def welcomenewplayer(steamid,inst):
        global welcomthreads
        log.info(f'welcome message thread started for new player {steamid} on {inst}')
        time.sleep(180)
        mtxt = 'Welcome to the Ultimate Extinction Core Galaxy Server Cluster!'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        time.sleep(10)
        mtxt = 'Public teleporters and crafting area, ARc rewards points earned as you play. Public auction house. Build a rewards vault, free starter items.'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        time.sleep(10)
        mtxt = 'You get all your items back when you die automatically, The engram menu is laggy, sorry. Admins and help in discord. Press F1 at anytime for help. Have Fun!'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        time.sleep(15)
        #imtxt = 'The engram menu is laggy, sorry. Admins & players in discord. Press F1 at anytime for help. Have Fun!'
        #subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        #time.sleep(20)
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


def serverisinrestart(steamid,inst,oplayer):
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * FROM instances WHERE name = ?', [inst])
    rbt = c1.fetchone()
    c1.close()
    conn1.close()
    if rbt[3] == "True":
        log.warning(f'{rbt[6]},{rbt[7]}')
        log.info(f'notifying player {oplayer[1]} that server {inst} will be restarting in {rbt[7]} min')
        mtxt = f'WARNING: server is restarting in {rbt[7]} minutes'
        subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)

def onlineplayer(steamid,inst):
    global welcomthreads
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * FROM players WHERE steamid = ?', [steamid])
    oplayer = c1.fetchone()
    timestamp=time.time()
    c1.execute('SELECT * FROM players WHERE steamid = ? AND banned != ""', [steamid])
    poplayer = c1.fetchone()
    c1.execute('SELECT * FROM banlist WHERE steamid = ?', [steamid])
    bplayer = c1.fetchone()
    c1.close()
    conn1.close()
    timestamp=time.time()
    if poplayer:
        if not bplayer:
            log.error(f'banned player out of sync issue {steamid} on instance {inst}. not in banlist')
    if bplayer:
        if not poplayer:
            log.error(f'banned player out of sync issue {steamid} on instance {inst}. not banned in playerlist')
    if poplayer or bplayer:
        log.warning(f'banned player with steamid {steamid} has tried to connect or is online on {inst}. kicking and banning.')
        subprocess.run("""arkmanager rconcmd 'kickplayer %s' @%s""" % (steamid, inst), shell=True)
        subprocess.run("""arkmanager rconcmd 'banplayer %s' @%s""" % (steamid, inst), shell=True)
    else:
        log.debug(f'player {steamid} passed ban checks')
        if not oplayer:
            log.info(f'steamid {steamid} was not found. adding new player to cluster!')
            conn1 = sqlite3.connect(sqldb)
            c1 = conn1.cursor()
            c1.execute('INSERT INTO players (steamid, playername, lastseen, server, playedtime, rewardpoints, firstseen, connects, discordid, banned) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (steamid,'newplayer',timestamp,inst,'1',50,timestamp,1,'',''))
            conn1.commit()
            c1.close()
            conn1.close()
            if not iswelcoming(steamid):
                welcom = threading.Thread(name = 'welcoming-%s' % steamid, target=welcomenewplayer, args=(steamid,inst))
                welcomthreads.append({'steamid':steamid,'sthread':welcom})
                welcom.start()
            else:
                log.warning(f'welcome message thread already running for new player {steamid}')
            writechat(inst,'ALERT',f'<<< A New player has joined the cluster!',wcstamp())
        elif len(oplayer) > 2:
            if float(oplayer[2]) + 300 > float(time.time()):
                if oplayer[3] != inst:
                    writechat(inst,'ALERT',f'>><< {oplayer[1].capitalize()} has transferred from {oplayer[3].capitalize()} to {inst.capitalize()}',wcstamp())
                    log.info(f'player {oplayer[1].capitalize()} has transferred from {oplayer[3]} to {inst}')
                log.debug(f'online player {oplayer[1]} with {steamid} was found. updating info.')
                conn1 = sqlite3.connect(sqldb)
                c1 = conn1.cursor()
                c1.execute('UPDATE players SET lastseen = ?, server = ? WHERE steamid = ?', (timestamp,inst,steamid))
                conn1.commit()
                c1.close()
                conn1.close()
            else:
                log.info(f"player {oplayer[1]} has joined {inst}, total player's connections {int(oplayer[7])+1}. updating info.")
                conn1 = sqlite3.connect(sqldb)
                c1 = conn1.cursor()
                c1.execute('UPDATE players SET lastseen = ?, server = ?, connects = ? WHERE steamid = ?', (timestamp,inst,int(oplayer[7])+1,steamid))
                conn1.commit()
                c1.close()
                conn1.close()
                laston = elapsedTime(float(time.time()),float(oplayer[2]))
                totplay = playedTime(float(oplayer[4].replace(',','')))
                
                log.debug(f'fetching steamid {steamid} auctions from auction api website')
                pauctions = fetchauctiondata(steamid)
                totauctions, iauctions, dauctions = getauctionstats(pauctions)
                writeauctionstats(steamid,totauctions,iauctions,dauctions)
                time.sleep(3)

                mtxt = f'Welcome back {oplayer[1]}, you have {oplayer[5]} ARc reward points, {totauctions} auctions, last online {laston} ago, total time played {totplay}'
                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
                if oplayer[8] == '':
                    time.sleep(8)
                    mtxt = f'Your player is not linked with a discord account yet. type !linkme in global chat'
                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
            if float(oplayer[2]) + 60 < float(time.time()):
                writechat(inst,'ALERT',f'<<< {oplayer[1].capitalize()} has joined the server',wcstamp())
                serverisinrestart(steamid,inst,oplayer)

def onlineupdate(inst):
    log.debug(f'starting online player watcher on {inst}')
    while True:
        try:
            cmdpipe = subprocess.Popen('arkmanager rconcmd ListPlayers @%s' % inst, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            b = cmdpipe.stdout.read().decode("utf-8")
            for line in iter(b.splitlines()):
                if line.startswith('Running command') or line.startswith('"') or line.startswith(' "') or line.startswith('Error:'):
                    pass
                else:
                    if line.startswith('"No Players'):
                        pass
                    else:
                        rawline = line.split(',')
                        if len(rawline) > 1:
                            nsteamid = rawline[1]
                            mumu = threading.Thread(name = '%s-greeting' % inst, target=onlineplayer, args=(nsteamid.strip(),inst))
                            mumu.start()
                        else:
                            log.error(f'problem with parsing online player - {rawline}')
            time.sleep(10)
        except:
            log.critical('Critical Error in Online Updater!', exc_info=True)
            try:
                if c1 in vars():
                    c1.close()
            except:
                pass
            try:
                if conn1 in vars():
                    conn1.close()
            except:
                pass
            try:
                if c in vars():
                    c.close()
            except:
                pass
            try:
                if conn in vars():
                    conn.close()
            except:
                pass


def logwatch(inst):
    try:
        log.debug(f'starting logwatch thread for instance {inst}')
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                weebo = threading.Thread(name = '%s-onlineupdater' % inst, target=onlineupdate, args=(inst,))
                weebo.start()

                logfile = instance[each]['logfile']
                logpath = f'{arkroot}/ShooterGame/Saved/Logs/{logfile}'
                log.debug(f'watching log {logpath} for instance {inst}')
        with open(logpath, 'rt') as following:
            following.seek(0, 0)
            for line in follow(following):
                processlogline(line,inst)
    except:
        log.critical('Critical Error in Log Watcher!', exc_info=True)
        try:
            if c in vars():
                c.close()
        except:
            pass
        try:
            if conn in vars():
                conn.close()
        except:
            pass
        try:
            if c1 in vars():
                c1.close()
        except:
            pass
        try:
            if conn1 in vars():
                conn1.close()
        except:
            pass

