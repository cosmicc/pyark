import os, logging, subprocess, sqlite3, time, filecmp, threading, socket
from datetime import datetime
from datetime import time as dt
from timebetween import is_time_between
from timehelper import wcstamp
from configreader import sqldb, sharedpath, arkroot, numinstances, instance, instr, isupdater
from pushover import pushover

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

confupdtimer = 0
dwtimer = 0
updgennotify = time.time() - 2100


def writediscord(msg, tstamp):
    conn4 = sqlite3.connect(sqldb)
    c4 = conn4.cursor()
    c4.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)',
               ('generalchat', 'ALERT', msg, tstamp))
    conn4.commit()
    c4.close()
    conn4.close()


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


def playercount(inst):
    playercount = 0
    cmdpipe = subprocess.Popen('arkmanager rconcmd ListPlayers @%s' % inst, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        if line.startswith('Running command') or line.startswith('"') or line.startswith(' "'):
            pass
        else:
            if line.startswith('"No Players'):
                return 0
            else:
                playercount += 1
    return playercount


def updatetimer(inst, ctime):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('UPDATE instances SET restartcountdown = ? WHERE name = ?', (ctime, inst))
    conn.commit()
    c.close()
    conn.close()


def setcfgver(inst, cver):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    if inst == 'general':
        c.execute('UPDATE general SET cfgver = ?', [cver])
    else:
        c.execute('UPDATE instances SET cfgver = ? WHERE name = ?', (cver, inst))
    conn.commit()
    c.close()
    conn.close()


def getcfgver(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    if inst == 'general':
        c.execute('SELECT cfgver FROM general')
    else:
        c.execute('SELECT cfgver FROM instances WHERE name = ?', (inst, ))
    lastwipe = c.fetchone()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])


def getlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastdinowipe FROM instances WHERE name = ?', (inst, ))
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])


def resetlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET lastdinowipe = ? WHERE name = ?', (newtime, inst))
    conn.commit()
    c.close()
    conn.close()


def resetlastrestart(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    newtime = time.time()
    c.execute('UPDATE instances SET lastrestart = ? WHERE name = ?', (newtime, inst))
    c.execute('UPDATE instances SET needsrestart = "False" WHERE name = ?', (inst, ))
    c.execute('UPDATE instances SET cfgver = ? WHERE name = ?', (getcfgver('general'), inst))
    c.execute('UPDATE instances SET restartcountdown = 30')
    conn.commit()
    c.close()
    conn.close()


def setrestartbit(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('UPDATE instances SET needsrestart = "True" WHERE name = ?', (inst, ))
    conn.commit()
    c.close()
    conn.close()


def unsetstartbit(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('UPDATE instances SET needsrestart = "False" WHERE name = ?', (inst, ))
    conn.commit()
    c.close()
    conn.close()


def restartbit(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('UPDATE players SET restartbit = 1 WHERE server = ?', (inst, ))
    conn.commit()
    c.close()
    conn.close()


def checkwipe(inst):
    global dwtimer
    lastwipe = getlastwipe(inst)
    if time.time() - float(lastwipe) > 86400:
        if playercount(inst) == 0:
            log.info(f'dino wipe needed for {inst}, 0 players connected, wiping now')
            writechat(inst, 'ALERT', f'### Empty server is over 24 hours since wild dino wipe. Wiping now.', wcstamp())
            subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True)
            dwtimer = 0
            resetlastwipe(inst)
        else:
            if dwtimer == 0:
                log.info(f'dino wipe needed for {inst}, but players are online. waiting')
            dwtimer += 1
            if dwtimer == 12:
                dwtimer = 0
    else:
        log.debug(f'no dino wipe is needed for {inst}')


def isrebooting(inst):
    for each in range(numinstances):
        if instance[each]['name'] == inst:
            if 'restartthread' in instance[each]:
                if instance[each]['restartthread'].is_alive():
                    return True
                else:
                    return False
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


def restartinstnow(inst):
    subprocess.run('arkmanager stop --saveworld @%s' % (inst), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, shell=True)
    log.info(f'server {inst} instance has stopped')
    subprocess.run('arkmanager backup @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    log.debug(f'server {inst} instance has backed up world data')
    subprocess.run('cp %s/config/Game.ini %s/ShooterGame/Saved/Config/LinuxServer' % (sharedpath, arkroot),
                   stdout=subprocess.DEVNULL, shell=True)
    subprocess.run('cp %s/config/GameUserSettings.ini %s/ShooterGame/Saved/Config/LinuxServer' % (sharedpath, arkroot),
                   stdout=subprocess.DEVNULL, shell=True)
    log.debug(f'server {inst} updated config files')
    log.info(f'server {inst} is updating from staging directory')
    subprocess.run('arkmanager update --no-download --update-mods --no-autostart @%s' % (inst),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    log.info(f'server {inst} instance is starting')
    subprocess.run('arkmanager start @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastrestart(inst)
    unsetstartbit(inst)


def restartloop(inst):
    log.debug(f'{inst} restart loop has started')
    setrestartbit(inst)
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT restartcountdown, restartreason from instances WHERE name = ?', (inst,))
    timeleftraw = c.fetchone()
    timeleft = int(timeleftraw[0])
    reason = timeleftraw[1]
    c.close()
    conn.close()
    if playercount(inst) == 0:
            log.info(f'server {inst} is empty and restarting now for a {reason}')
            writechat(inst, 'ALERT', f'!!! Empty server restarting now for a {reason.capitalize()}', wcstamp())
            message = f'server is restarting now for a {reason}'
            subprocess.run('arkmanager notify "%s" @%s' % (message, inst), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True)
            pushover('Instance Restart', message)
            restartinstnow(inst)
    else:
            if timeleft == 30:
                log.info(f'starting 30 min restart countdown for instance {inst} for a {reason}')
                writechat(inst, 'ALERT', f'!!! Server will restart in 30 minutes for a {reason.capitalize()}',
                          wcstamp())
            else:
                log.info(f'resuming {timeleft} min retart countdown for instance {inst} for a {reason}')
            gotime = False
            snr = stillneedsrestart(inst)
            while snr and not gotime:
                if timeleft == 30 or timeleft == 15 or timeleft == 10 or timeleft == 5 or timeleft == 1:
                    log.info(f'{timeleft} broadcast message sent to {inst}')
                    subprocess.run("""arkmanager rconcmd "broadcast
                                   '\n\n\n          The server will be restarting in %s minutes for a %s'" @%s""" %
                                   (timeleft, reason, inst), stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, shell=True)
                time.sleep(60)
                timeleft = timeleft - 1
                updatetimer(inst, timeleft)
                snr = stillneedsrestart(inst)
                if playercount(inst) == 0 or timeleft == 0:
                    gotime = True
            if stillneedsrestart(inst):
                log.info(f'server {inst} is restarting now for a {reason}')
                message = f'server is restarting now for a {reason}'
                subprocess.run("""arkmanager rconcmd "broadcast
                               '\n\n\n             The server is restarting NOW! for a %s'" @%s""" % (reason, inst),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                writechat(inst, 'ALERT', f'!!! Server restarting now for {reason.capitalize()}', wcstamp())
                subprocess.run('arkmanager notify "%s" @%s' % (message, inst), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, shell=True)
                pushover('Instance Restart', message)
                time.sleep(10)
                restartinstnow(inst)
            else:
                log.warning(f'server restart on {inst} has been canceled from forced cancel')
                subprocess.run("""arkmanager rconcmd "broadcast
                               '\n\n\n             The server restart for %s has been cancelled'" @%s""" %
                               (reason, inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                writechat(inst, 'ALERT', f'!!! Server restart for {reason.capitalize()} has been canceled', wcstamp())


def instancerestart(inst, reason):
    log.debug(f'instance restart verification starting for {inst}')
    global instance
    global confupdtimer
    t, s, e = datetime.now(), dt(11, 0), dt(11, 30)  # Maintenance reboot 11:00-11:30am GMT (7:00AM EST)
    inmaint = is_time_between(t, s, e)
    if inmaint:
                log.info(f'maintenance window reached, running server os maintenance')
                subprocess.run('apt update', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                subprocess.run('apt full-upgrade -y', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                time.sleep(3)
                if os.path.isfile('/var/run/reboot-required'):
                    log.warning(f'{inst} physical server needs a hardware reboot after package updates')
    if (inmaint and reason == "configuration update") \
       or (inmaint and reason == "maintenance restart") \
       or (reason != "configuration update" and reason != "maintenance restart"):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('UPDATE instances SET restartreason = ? WHERE name = ?', (reason, inst))
        conn.commit()
        c.close()
        conn.close()
        if not isrebooting(inst):
            for each in range(len(numinstances)):
                if instance[each]['name'] == inst:
                    instance[each]['restartthread'] = threading.Thread(name='%s-restart' % inst, target=restartloop,
                                                                       args=(inst, reason))
                    instance[each]['restartthread'].start()
        else:
            log.warning(f'instance {inst} is already running the restart thread')
    else:
        log.debug(f'instance restart posponed becuase not in maintenance window')


def checkconfig():
    if isupdater == "True":
        newcfg1 = f'{sharedpath}/config/Game.ini'
        oldcfg1 = f'{sharedpath}/stagedconfig/Game.ini'
        newcfg2 = f'{sharedpath}/config/GameUserSettings.ini'
        oldcfg2 = f'{sharedpath}/stagedconfig/GameUserSettings.ini'

        if not filecmp.cmp(newcfg1, oldcfg1) or not filecmp.cmp(newcfg2, oldcfg2):
            log.info('config file update detected. staging config files.')
            message = 'new configuration detected. signaling servers for update.'
            oldver = int(getcfgver('general'))
            setcfgver('general', str(oldver + 1))
            subprocess.run('cp %s/config/Game.ini %s/stagedconfig' % (sharedpath, sharedpath),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run('cp %s/config/GameUserSettings.ini %s/stagedconfig' % (sharedpath, sharedpath),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run('arkmanager notify "%s" @%s' % (message, instance[0]['name']), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True)
        else:
            log.debug('no config file updates detected')
    for each in range(numinstances):
        inst = instance[each]['name']
        if not isrebooting(inst):
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT lastrestart FROM instances WHERE name = ?', [inst])
            lstsv = c.fetchone()
            c.close()
            conn.close()
            t, s, e = datetime.now(), dt(11, 0), dt(11, 30)  # Maintenance reboot 11:00-11:30am GMT (7:00AM EST)
            inmaint = is_time_between(t, s, e)
            if float(time.time()) - float(lstsv[0]) > 432000 and inmaint:
                maintrest = "maintenance restart"
            else:
                maintrest = "configuration update"
            if (int(getcfgver('general')) > int(getcfgver(inst)) or maintrest == 'maintenance restart'):
                if not isrebooting(inst):
                    instancerestart(inst, maintrest)
            else:
                log.debug(f'no config changes detected for instance {inst}')


def isnewarkver(inst):
    isarkupd = subprocess.run('arkmanager checkupdate @%s' % (inst), stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, shell=True)
    for each in isarkupd.stdout.decode('utf-8').split('\n'):
        if each.find('Current version:') != -1:
            m = each.split(':')
            k = m[1].split(' ')
            curver = int((k[2]))
        elif each.find('Available version:') != -1:
            m = each.split(':')
            k = m[1].split(' ')
            avlver = int((k[2]))
    if curver == avlver:
        return False, curver, avlver
    else:
        return True, curver, avlver


def checkbackup():
    for seach in range(numinstances):
        sinst = instance[seach]['name']
        if not isrebooting(sinst):
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT lastrestart FROM instances WHERE name = ?', (sinst, ))
            lastrestr = c.fetchall()
            c.close()
            conn.close()
            lt = float(time.time()) - float(lastrestr[0][0])
            if (lt > 21600 and lt < 21900) or (lt > 43200 and lt < 43500) or (lt > 64800 and lt < 65100):
                log.info(f'performing a world data backup on {sinst}')
                subprocess.run('arkmanager backup @%s' % (sinst, ), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, shell=True)


def checkifalreadyrestarting(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT needsrestart FROM instances WHERE name = ?', (inst, ))
    lastwipe = c.fetchone()
    c.close()
    conn.close()
    ded = lastwipe[0]
    if ded == "True":
        if not isrebooting(inst):
            log.info(f'restart flag set for instance {inst}, starting restart loop')
            restartloop(inst)


def checkupdates():
    global ugennotify
    try:
        ustate, curver, avlver = isnewarkver(instance[0]['name'])
        if not ustate and time.time() - updgennotify > 2100:
            log.debug('ark update check found no ark updates available')
        else:
            log.info(f'ark update found ({curver}>{avlver}) downloading update.')
            if isupdater:
                subprocess.run('arkmanager update --downloadonly --update-mods @%s' % (instance[0]['name']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug('ark update downloaded to staging area')
                    msg = f'Ark update has been released. Servers will start a reboot countdown now.\n\
https://survivetheark.com/index.php?/forums/topic/166421-pc-patch-notes-client-283112-server-283112/'
                    writediscord(msg, time.time())
                    pushover('Ark Update', msg)
            else:
                time.sleep(60)
            for each in range(numinstances):
                inst = instance[each]['name']
                instancerestart(inst, 'ark game update')
    except:
        log.error(f'error in determining ark version')

    for each in range(numinstances):
        if not isrebooting(instance[each]['name']):
            ismodupd = subprocess.run('arkmanager checkmodupdate @%s' % (instance[each]['name']),
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
            ismodupd = ismodupd.stdout.decode('utf-8')
            modchk = 0
            ismodupd = ismodupd.split('\n')
            for teach in ismodupd:
                if teach.find('has been updated') != -1 or teach.find('needs to be applied') != -1:
                    modchk += 1
                    al = teach.split(' ')
                    modid = al[1]
                    modname = al[2]
            inst = instance[each]['name']
            if modchk != 0:
                ugennotify = time.time()
                log.info(f'ark mod update {modname} id {modid} detected for instance {instance[each]["name"]}')
                log.debug(f'downloading mod updates for instance {instance[each]["name"]}')
                subprocess.run('arkmanager update --downloadonly --update-mods @%s' % (instance[each]['name']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug(f'mod updates for instance {instance[each]["name"]} download complete')
                aname = f'{modname} mod update'
                if instance[each]["name"] == 'volcano':
                    msg = f'Mod {modname} has been updated. Servers will start a reboot countdown now.\n\
https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}'
                    writediscord(msg, time.time())
                    pushover('Mod Update', msg)
                for neo in range(numinstances):
                        instancerestart(instance[neo]['name'], aname)
        else:
            log.debug(f'no updated mods were found for instance {instance[each]["name"]}')


def arkupd():
    log.debug('arkupdater thread started')
    log.info(f'found {numinstances} ark server instances: {instr}')
    while True:
        try:
            for each in range(numinstances):
                if not isrebooting(instance[each]['name']):
                    checkifalreadyrestarting(instance[each]['name'])
                    checkwipe(instance[each]['name'])
            checkbackup()
            checkupdates()
            checkconfig()
            time.sleep(300)
        except:
            log.critical('Critical Error in Ark Updater!', exc_info=True)
