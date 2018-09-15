#!/usr/bin/python3

import time
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

def follow(stream):
    "Follow the live contents of a text file."
    line = ''
    for block in iter(lambda:stream.read(1024), None):
        if '\n' in block:
            # Only enter this block if we have at least one line to yield.
            # The +[''] part is to catch the corner case of when a block
            # ends in a newline, in which case it would repeat a line.
            for line in (line+block).splitlines(True)+['']:
                if line.endswith('\n'):
                    yield line
            # When exiting the for loop, 'line' has any remaninig text.
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
            tsobj = datetime.strptime(tstimestamp, '%Y.%m.%d-%H.%M.%S')
            newts = tsobj
            timestamp = newts.timestamp()
            playername = playername.lower()
        except:
            log.error(f'error processing TCsAR logline for instance {inst}')
            log.error(line)
        else:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE steamid = ?', [steamid])
            pexist = c.fetchall()
            if not pexist:
                log.info(f'player {playername} with steamid {steamid} was not found. adding.')
                c.execute('INSERT INTO players (steamid, playername, playedtime) VALUES (?, ?, ?, ?, ?)', (steamid,playername,playtime))
                conn.commit()
            else:
                log.debug(f'player {playername} with steamid {steamid} was found. updating.')
                c.execute('UPDATE players SET playername = ?, playedtime = ? WHERE steamid = ?', (playername,playtime,steamid))
                conn.commit()
            c.close()
            conn.close()

def onlineplayer(steamid,inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE steamid = ?', [steamid])
    pexist = c.fetchall()
    timestamp=time.time()
    if not pexist:
        log.info(f'steamid {steamid} was not found. adding.')
        c.execute('INSERT INTO players (steamid, playername, lastseen, server, playedtime) VALUES (?, ?, ?, ?, ?)', (steamid,'newplayer',timestamp,inst,'0'))
        conn.commit()
    else:
        log.debug(f'steamid {steamid} was found. updating.')
        c.execute('UPDATE players SET lastseen = ?, server = ? WHERE steamid = ?', (timestamp,inst,steamid))
        conn.commit()
        c.close()
        conn.close()


def onlineupdate(inst):
    log.info(f'starting online player watcher on {inst}')
    while True:
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
        time.sleep(60)



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
