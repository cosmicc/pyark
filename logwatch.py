#!/usr/bin/python3

import time, sys
from datetime import datetime
from datetime import timedelta
import logging, sqlite3, threading, subprocess
from configparser import ConfigParser

log = logging.getLogger(__name__)

class ExtConfigParser(ConfigParser):
    def getlist(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.split(','))))

    def getlistint(self, section, option):
        return [int(x) for x in self.getlist(section, option)]

configfile = '/home/ark/pyark.cfg'

config = ExtConfigParser()
config.read(configfile)

sharedpath = config.get('general', 'shared')
sqldb = f'{sharedpath}/db/pyark.db'
arkroot = config.get('general', 'arkroot')

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

def elapsedTime(start_time, stop_time, lshort=False):
    diff_time = start_time - stop_time
    total_min = diff_time / 60
    minutes = int(total_min % 60)
    if minutes == 1:
        if lshort is False:
            minstring = 'minute'
        else:
            minstring = 'min'
    else:
        if lshort is False:
            minstring = 'minutes'
        else:
            minstring = 'mins'
    hours = int(total_min / 60)
    if hours == 1:
        if lshort is False:
            hourstring = 'hour'
        else:
            hourstring = 'hr'
    else:
        if lshort is False:
            hourstring = 'hours'
        else:
            hourstring = 'hrs'
    days = int(hours / 24)
    if days == 1:
        if lshort is False:
            daystring = 'day'
        else:
            daystring = 'day'
    else:
        if lshort is False:
            daystring = 'days'
        else:
            daystring = 'days'
    if days != 0:
        return('{} {}, {} {} ago'.format(days, daystring, hours, hourstring))
    elif hours != 0:
        return('{} {}, {} {} ago'.format(hours, hourstring, minutes, minstring))
    elif minutes > 1:
        return('{} {} ago'.format(minutes, minstring))
    elif minutes <= 1:
        return('now')
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

def playedTime(ptime):
    total_min = ptime / 60
    minutes = int(ptime % 60)
    if minutes == 1:
        minstring = 'Min'
    else:
        minstring = 'mins'
    hours = int(total_min / 60)
    if hours == 1:
        hourstring = 'hour'
    else:
        hourstring = 'hours'
    days = int(hours / 24)
    if days == 1:
        daystring = 'day'
    else:
        daystring = 'days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours-days*24, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes-hours, minstring))
    elif minutes != 0:
        return('{} {}'.format(minutes, minstring))
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

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
            pexist = c.fetchall()
            if not pexist:
                log.info(f'player {playername} with steamid {steamid} was not found. adding.')
                c.execute('INSERT INTO players (steamid, playername, lastseen, playedtime, rewardpoints, firstseen, connects) VALUES (?, ?, ?, ?, ?, ?, ?)', (steamid,playername,timestamp,playtime,rewardpoints,timestamp,1))
                conn.commit()
            elif steamid != '':
                log.debug(f'player {playername} with steamid {steamid} was found. updating.')
                c.execute('UPDATE players SET playername = ?, playedtime = ?, rewardpoints = ? WHERE steamid = ?', (playername,playtime,rewardpoints,steamid))
                conn.commit()
            c.close()
            conn.close()

def welcomenewplayer(steamid,inst):
    log.info(f'welcome message thread started for new player {steamid} on {inst}')
    #time.sleep(180)
    #mtxt = 'Welcome to the ultimate extinction core galaxy server cluster!'
    #subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
    #time.sleep(10)
    #mtxt = 'Public teleporters and crafting area is available, Rewards system points earned as you play. Build a rewards vault or find a public teleporter to access the rewards system.'
    #subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
    #time.sleep(10)
    #mtxt = 'There are free starter packs in the rewards vault, and the level 1 tent makes a quick starter shelter, and you get all your items back when you die (no corpses)'
    #subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
    #time.sleep(10)
    #mtxt = 'The engram menu is laggy, sorry. Admins & players in discord. Press F1 at anytime for help. Have Fun!'
    #subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
    #time.sleep(10)
    #mtxt = 'everyone welcome a new player to the cluster!'
    #subprocess.run("""arkmanager rconcmd 'ServerChat %s' @%s""" % (mtxt, inst), shell=True)
    #log.debug(f'welcome message thread complete for new player {steamid} on {inst}')


def serverisinrestart(steamid,inst,oplayer):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM instances WHERE name = ?', [inst])
    rbt = c.fetchone()
    if rbt[3] == "True":
        log.warning(f'{rbt[6]},{rbt[7]}')
        log.info(f'notifying player {oplayer[1]} that server {inst} will be restarting in {rbt[7]} min')

        #mtxt = f'WARNING: server is restarting in {rbt[7]} minutes'
        #subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
    

def onlineplayer(steamid,inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE steamid = ?', [steamid])
    oplayer = c.fetchone()
    timestamp=time.time()
    if not oplayer:
        log.info(f'steamid {steamid} was not found. adding new player to cluster!')
        c.execute('INSERT INTO players (steamid, playername, lastseen, server, playedtime, rewardpoints, firstseen, connects) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (steamid,'newplayer',timestamp,inst,'1',50,timestamp,1))
        conn.commit()
        c.close()
        conn.close()
        welcom = threading.Thread(name = '%s-welcomenewplayer' % inst, target=welcomenewplayer, args=(steamid,inst))
        welcom.start()
    elif len(oplayer) > 2:
        if float(oplayer[2]) + 300 > float(time.time()):
            log.debug(f'online player {oplayer[1]} with {steamid} was found. updating info.')
            c.execute('UPDATE players SET lastseen = ?, server = ? WHERE steamid = ?', (timestamp,inst,steamid))
        else:
            log.info(f"player {oplayer[1]} has joined {inst}, total player's connections {int(oplayer[7])+1}. updating info.")
            c.execute('UPDATE players SET lastseen = ?, server = ?, connects = ? WHERE steamid = ?', (timestamp,inst,int(oplayer[7])+1,steamid))
            laston = elapsedTime(float(time.time()),float(oplayer[2]))
            totplay = playedTime(float(oplayer[4].replace(',','')))
            mtxt = f'welcome back {oplayer[1]}, you have {oplayer[5]} reward points. you were last on {laston}, total time played {totplay}'
            subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (steamid, mtxt, inst), shell=True)
        if float(oplayer[2]) + 60 < float(time.time()):
            serverisinrestart(steamid,inst,oplayer)

        conn.commit()
        c.close()
        conn.close()


def onlineupdate(inst):
    log.info(f'starting online player watcher on {inst}')
    while True:
        #try:
            time.sleep(10)
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
                        nsteamid = rawline[1]
                        onlineplayer(nsteamid.strip(),inst)
            time.sleep(20)
        #except:
        #    e = sys.exc_info()[0]
        #    log.critical(e)

def logwatch(inst):
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
        try:
            for line in follow(following):
                processlogline(line,inst)
        except KeyboardInterrupt:
            pass
