import logging, subprocess, sqlite3, time, filecmp, threading
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
            minstring = 'Minute'
        else:
            minstring = 'Min'
    else:
        if lshort is False:
            minstring = 'Minutes'
        else:
            minstring = 'Mins'
    hours = int(total_min / 60)
    if hours == 1:
        if lshort is False:
            hourstring = 'Hour'
        else:
            hourstring = 'Hr'
    else:
        if lshort is False:
            hourstring = 'Hours'
        else:
            hourstring = 'Hrs'
    days = int(hours / 24)
    if days == 1:
        if lshort is False:
            daystring = 'Day'
        else:
            daystring = 'Day'
    else:
        if lshort is False:
            daystring = 'Days'
        else:
            daystring = 'Days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes, minstring))
    elif minutes != 0:
        return('{} {}'.format(minutes, minstring))
    elif minutes == 0:
        return('now')
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

def playercount(instance):
    playercount = 0
    cmdpipe = subprocess.Popen('arkmanager rconcmd ListPlayers @%s' % instance, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        if line.startswith('Running command') or line.startswith('"') or line.startswith(' "') or line.startswith('Error:'):
            pass
        else:
            if line.startswith('"No Players'):
                return 0
            else:
                playercount+=1
    return playercount

def setcfgver(inst,cver):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    if inst == 'general':
        c.execute('UPDATE general SET cfgver = ?', [cver])
    else:
        c.execute('UPDATE instances SET cfgver = ? WHERE name = ?', [cver,inst])
    conn.commit()
    c.close()
    conn.close()

def getcfgver(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    if inst == 'general'
        c.execute('SELECT cfgver FROM general')
    else:
        c.execute('SELECT cfgver FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchone()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def getlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastdinowipe FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def resetlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET lastdinowipe = ? WHERE name = ?', [newtime,inst])
    conn.commit()
    c.close()
    conn.close()

def resetlastrestart(inst,reason):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET lastrestart = ? WHERE name = ?', [newtime,inst])
    c.execute('UPDATE instances SET lastdinowipe = ? WHERE name = ?', [newtime,inst])
    c.execute('UPDATE instances SET needsrestart = "False" WHERE name = ?', [inst])
    c.execute('UPDATE instances SET restartreason = ? WHERE name = ?', [reason,inst])
    c.execute('UPDATE instances SET cfgver = ? WHERE name = ?', [getcfgver('general'),inst])
    conn.commit()
    c.close()
    conn.close()

def setrestartbit(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET needsrestart = "True" WHERE name = ?', [inst])
    conn.commit()
    c.close()
    conn.close()

def unsetstartbit(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET needsrestart = "False" WHERE name = ?', [inst])
    conn.commit()
    c.close()
    conn.close()

def checkwipe(inst):
    #log.debug(f'running dinowipe check for {inst}')
    lastwipe = getlastwipe(inst)
    if time.time()-float(lastwipe) > 86400:
        if playercount(inst) == 0:
            log.info(f'dino wipe needed for {inst}, 0 players connected, wiping now')
            subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            resetlastwipe(inst)            
        else:
            log.debug(f'dino wipe needed for {inst}, but players are online. waiting..')
    else:
        log.debug(f'no dino wipe is needed for {inst}')

def isrebooting(inst):
    for each in range(numinstances):
        if instance[each]['name'] == inst and 'restartthread' in instance[each]:
            if instance[each]['restartthread'].is_alive():
                return True
            else:
                return False

def stillneedsrestart(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT needsrestart FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    ded = ''.join(lastwipe[0])
    if ded == "True":
        return True
    else:
        return False

def instancerestart(inst, reason):
    log.debug(f'instance restart thread starting for {inst}')
    setrestartbit(inst)
    if playercount(inst) == 0:
        log.info(f'instance {inst} is empty and restarting now due to {reason}')
        message = f'server is restarting because of a {reason}'
        subprocess.run('arkmanager notify "%s" @%s' % (message, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        subprocess.run('arkmanager stop --saveworld @%s' % (inst),stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        log.info(f'instance {inst} server has stopped')
        subprocess.run('arkmanager backup @%s' % (inst),stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        log.info(f'instance {inst} server has backed up world')
        subprocess.run('cp %s/config/Game.ini %s/ShooterGame/Saved/Config/LinuxServer' % (sharedpath,arkroot), stdout=subprocess.DEVNULL, shell=True)
        subprocess.run('cp %s/config/GameUserSettings.ini %s/ShooterGame/Saved/Config/LinuxServer' % (sharedpath,arkroot), stdout=subprocess.DEVNULL, shell=True)
        log.debug(f'instance {inst} server updated config files')
        subprocess.run('arkmanager start --alwaysrestart @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        log.info(f'instance {inst} server is starting')
        resetlastrestart(inst, reason)
    else:
        if reason != "configuration update":
            log.info(f'starting 30 min restart countdown for instance {inst} due to {reason}')
            timeleft = 30
            gotime = False
            countstart = time.time()
            snr = stillneedsrestart(inst)
            log.warning(snr)
            while snr and not gotime:
                if timeleft == 30 or timeleft == 15 or timeleft == 10 or timeleft == 5 or timeleft == 1:
                    log.info(f'{timeleft} broadcast message sent to {inst}')
                    subprocess.run("""arkmanager rconcmd "broadcast '\n\n\n          The server will be restarting in %s minutes for a %s'" @%s""" % (timeleft,reason,inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                time.sleep(60)
                timeleft = timeleft - 1
                snr = stillneedsrestart(inst)
                if playercount(inst) == 0 or timeleft == 0:
                    gotime = True
            if snr:
                log.info(f'instance {inst} is restarting now due to {reason}')
                message = f'server is restarting because of a {reason}'
                subprocess.run("""arkmanager rconcmd "broadcast '\n\n\n             The server is restarting NOW! for a %s'" @%s""" % (reason,inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                time.sleep(30)
                subprocess.run('arkmanager notify "%s" @%s' % (message, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                subprocess.run('arkmanager stop --saveworld @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.info(f'instance {inst} server has stopped')
                subprocess.run('arkmanager backup @%s' % (inst),stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.info(f'instance {inst} server has backed up world')
                subprocess.run('cp %s/config/Game.ini %s/ShooterGame/Saved/Config/LinuxServer' % (sharedpath,arkroot), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                subprocess.run('cp %s/config/GameUserSettings.ini %s/ShooterGame/Saved/Config/LinuxServer' % (sharedpath,arkroot), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug(f'instance {inst} server updated config files')
                subprocess.run('arkmanager start --alwaysrestart @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.info(f'instance {inst} server is starting')
                resetlastrestart(inst, reason)
            else:
                log.warning(f'server restart on {inst} has been canceled from forced cancel')
                subprocess.run("""arkmanager rconcmd "broadcast '\n\n\n             The server restart for %s has been cancelled'" @%s""" % (reason,inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        else:
            unsetstartbit(inst)
            log.info(f'waiting on configuration update for {inst} because players are online')


def checkconfig():
    newcfg1 = f'{sharedpath}/config/Game.ini'
    oldcfg1 = f'{sharedpath}/stagedconfig/Game.ini'
    newcfg2 = f'{sharedpath}/config/GameUserSettings.ini'
    oldcfg2 = f'{sharedpath}/stagedconfig/GameUserSettings.ini'

    if not filecmp.cmp(newcfg1,oldcfg1) or not filecmp.cmp(newcfg2,oldcfg2):
        log.info('config file update detected')
        oldver = getcfgver('general')
        setcfgver('general',oldver+1)
        subprocess.run('cp %s/config/Game.ini %s/stagedconfig' % (sharedpath,sharedpath), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        subprocess.run('cp %s/config/GameUserSettings.ini %s/stagedconfig' % (sharedpath,arkroot), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)

    for each in range(numinstances):
        inst = instance[each]['name']
        if getcfgver('general') > getcfgver(inst) and not isrebooting(inst):
                instance[each]['restartthread'] = threading.Thread(name = '%s-restart' % inst, target=instancerestart, args=(inst,"configuration update"))
                instance[each]['restartthread'].start()

        time.sleep(10)

    else:
        log.debug('no config file updates detected')


def checkupdates():
    pendingupdates = False
    arkupdate = False
    modupdate = False
    isarkupd = subprocess.run('arkmanager checkupdate @%s' % (instance[0]['name']), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    if isarkupd.returncode == 1:
        log.debug('ark update check found no ark updates available')

        for each in range(numinstances):
            ismodupd = subprocess.run('arkmanager checkmodupdate @%s' % (instance[each]['name']), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            if ismodupd.returncode == 0 and not isrebooting(instance[each]['name']):
                log.info(f'ark mod update detected for instance {instance[each]["name"]}')
                log.debug(f'downloading mod updates for instance {instance[each]["name"]}')
                subprocess.run('arkmanager update --downloadonly --update-mods @%s' % (instance[each]['name']), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug(f'mod updates for instance {instance[each]["name"]} download complete')
                instance[each]['restartthread'] = threading.Thread(name = '%s-restart' % inst, target=instancerestart, args=(inst,"ark mod update"))
                instance[each]['restartthread'].start()
            else:
                log.debug(f'no updated mods were found for instance {instance[each]["name"]}')

    elif isarkupd.returncode == 0:
        log.info('ark update found. downloading update.')
        pendingupdates = True
        arkupdate = True
        subprocess.run('arkmanager update --downloadonly --update-mods @all', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        log.debug('ark update downloaded to staging area')
        for each in range(numinstances):
            inst = instance[each]['name']
            if not isrebooting(inst):
                instance[each]['restartthread'] = threading.Thread(name = '%s-restart' % inst, target=instancerestart, args=(inst,"ark game update"))
                instance[each]['restartthread'].start()

def checkpending(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT needsrestart FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    ded = ''.join(lastwipe[0])
    if ded == "True":
        if not isrebooting(inst):
            log.info(f'detected admin forced instance restart for instance {inst}')
            for each in range(numinstances):
                if instance[each]['name'] == inst:
                    instance[each]['restartthread'] = threading.Thread(name = '%s-restart' % inst, target=instancerestart, args=(inst,"admin restart"))
                    instance[each]['restartthread'].start()

def arkupd(): 
    log.info('arkupdater thread started')

    log.info(f'found {numinstances} instances: {instr}')

    while True:
        checkupdates()
        checkconfig()
        for each in range(numinstances):
            checkwipe(instance[each]['name'])
            checkpending(instance[each]['name'])

        time.sleep(300)
        print(threading.enumerate())

    

    
