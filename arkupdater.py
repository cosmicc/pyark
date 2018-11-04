from modules.configreader import sharedpath, arkroot, numinstances, instance, instr, isupdater
from datetime import datetime
from datetime import time as dt
from modules.dbhelper import dbquery, dbupdate
from modules.pushover import pushover
from modules.players import getplayersonline
from modules.instances import getlastwipe
from timebetween import is_time_between
from modules.timehelper import wcstamp, Secs, Now
from time import sleep
import filecmp
import logging
import os
import socket
import subprocess
import threading

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

confupdtimer = 0
dwtimer = 0
updgennotify = Now() - Secs['hour']


def writediscord(msg, tstamp):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % ('generalchat', 'ALERT', msg, tstamp))


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,))
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


def updatetimer(inst, ctime):
    dbupdate("UPDATE instances SET restartcountdown = '%s' WHERE name = '%s'" % (ctime, inst))


def setcfgver(inst, cver):
    if inst == 'general':
        dbupdate("UPDATE general SET cfgver = '%s'" % (cver,))
    else:
        dbupdate("UPDATE instances SET cfgver = '%s' WHERE name = '%s'" % (cver, inst))


def getcfgver(inst):
    if inst == 'general':
        lastwipe = dbquery("SELECT cfgver FROM general", fetch='one')
    else:
        lastwipe = dbquery("SELECT cfgver FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return ''.join(lastwipe[0])


def resetlastwipe(inst):
    dbupdate("UPDATE instances SET lastdinowipe = '%s' WHERE name = '%s'" % (Now(), inst))


def resetlastrestart(inst):
    dbupdate("UPDATE instances SET lastrestart = '%s' WHERE name = '%s'" % (Now(), inst))
    dbupdate("UPDATE instances SET needsrestart = 'False' WHERE name = '%s'" % (inst, ))
    dbupdate("UPDATE instances SET cfgver = '%s' WHERE name = '%s'" % (getcfgver('general'), inst))
    dbupdate("UPDATE instances SET restartcountdown = 30")


def setrestartbit(inst):
    dbupdate("UPDATE instances SET needsrestart = 'True' WHERE name = '%s'" % (inst, ))


def unsetstartbit(inst):
    dbupdate("UPDATE instances SET needsrestart = 'False' WHERE name = '%s'" % (inst, ))


def restartbit(inst):
    dbupdate("UPDATE players SET restartbit = 1 WHERE server = '%s'" % (inst, ))


def checkwipe(inst):
    global dwtimer
    lastwipe = getlastwipe(inst)
    if Now() - lastwipe > Secs['day']:
        if getplayersonline(inst, fmt='count') == 0:
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
    lastwipe = dbquery("SELECT needsrestart FROM instances WHERE name = '%s'" % (inst,))
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
    timeleftraw = dbquery("SELECT restartcountdown, restartreason from instances WHERE name = '%s'" % (inst,), fetch='one')
    timeleft = int(timeleftraw[0])
    reason = timeleftraw[1]
    if getplayersonline(inst, fmt='count') == 0:
            log.info(f'server {inst} is empty and restarting now for a {reason}')
            writechat(inst, 'ALERT', f'!!! Empty server restarting now for a {reason.capitalize()}', wcstamp())
            message = f'server {inst.capitalize()} is restarting now for a {reason}'
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
                sleep(Secs['1min'])
                timeleft = timeleft - 1
                updatetimer(inst, timeleft)
                snr = stillneedsrestart(inst)
                if getplayersonline(inst, fmt='count') == 0 or timeleft == 0:
                    gotime = True
            if stillneedsrestart(inst):
                log.info(f'server {inst} is restarting now for a {reason}')
                message = f'server {inst.capitalize()} is restarting now for a {reason}'
                subprocess.run("""arkmanager rconcmd "broadcast
                               '\n\n\n             The server is restarting NOW! for a %s'" @%s""" % (reason, inst),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                writechat(inst, 'ALERT', f'!!! Server restarting now for {reason.capitalize()}', wcstamp())
                subprocess.run('arkmanager notify "%s" @%s' % (message, inst), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, shell=True)
                pushover('Instance Restart', message)
                sleep(10)
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
    t, s, e = Now(fmt='dt'), dt(11, 0), dt(11, 30)  # Maintenance reboot 11:00-11:30am GMT (7:00AM EST)
    inmaint = is_time_between(t, s, e)
    if inmaint:
                log.info(f'maintenance window reached, running server os maintenance')
                subprocess.run('apt update', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                subprocess.run('apt full-upgrade -y', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                subprocess.run('apt autoremove -y', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                sleep(3)
                if os.path.isfile('/var/run/reboot-required'):
                    log.warning(f'{inst} physical server needs a hardware reboot after package updates')
    if (inmaint and reason == "configuration update") \
       or (inmaint and reason == "maintenance restart") \
       or (reason != "configuration update" and reason != "maintenance restart"):
        dbupdate("UPDATE instances SET restartreason = '%s' WHERE name = '%s'" % (reason, inst))
        if not isrebooting(inst):
            for each in range(numinstances):
                if instance[each]['name'] == inst:
                    instance[each]['restartthread'] = threading.Thread(name='%s-restart' % inst, target=restartloop,
                                                                       args=(inst, ))
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
            lstsv = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (inst,), fetch='one')
            t, s, e = datetime.now(), dt(11, 0), dt(11, 30)  # Maintenance reboot 11:00-11:30am GMT (7:00AM EST)
            inmaint = is_time_between(t, s, e)
            if Now() - float(lstsv[0]) > 432000 and inmaint:
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
            lastrestr = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (sinst, ))
            lt = Now() - float(lastrestr[0][0])
            if (lt > 21600 and lt < 21900) or (lt > 43200 and lt < 43500) or (lt > 64800 and lt < 65100):
                log.info(f'performing a world data backup on {sinst}')
                subprocess.run('arkmanager backup @%s' % (sinst, ), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, shell=True)


def checkifalreadyrestarting(inst):
    lastwipe = dbquery("SELECT needsrestart FROM instances WHERE name = '%s'" % (inst, ), fetch='one')
    ded = lastwipe[0]
    if ded == "True":
        if not isrebooting(inst):
            log.info(f'restart flag set for instance {inst}, starting restart loop')
            restartloop(inst)


def checkupdates():
    global ugennotify
    try:
        ustate, curver, avlver = isnewarkver(instance[0]['name'])
        if not ustate and Now() - updgennotify > Secs['hour']:
            log.debug('ark update check found no ark updates available')
        else:
            if isupdater:
                log.info(f'ark update found ({curver}>{avlver}) downloading update.')
                subprocess.run('arkmanager update --downloadonly --update-mods @%s' % (instance[0]['name']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug('ark update downloaded to staging area')
                msg = f'Ark update has been released. Servers will start a reboot countdown now.\n\
https://survivetheark.com/index.php?/forums/topic/166421-pc-patch-notes-client-283112-server-283112/'
                writediscord(msg, Now())
                pushover('Ark Update', msg)
            for each in range(numinstances):
                instancerestart(instance[each]['name'], 'ark game update')
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
            if modchk != 0:
                ugennotify = Now()
                log.info(f'ark mod update {modname} id {modid} detected for instance {instance[each]["name"]}')
                log.debug(f'downloading mod updates for instance {instance[each]["name"]}')
                subprocess.run('arkmanager update --downloadonly --update-mods @%s' % (instance[each]['name']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug(f'mod updates for instance {instance[each]["name"]} download complete')
                aname = f'{modname} mod update'
                if instance[each]["name"] == 'volcano':
                    msg = f'Mod {modname} has been updated. Servers will start a reboot countdown now.\n\
https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}'
                    writediscord(msg, Now())
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
            sleep(Secs['5min'])
        except:
            log.critical('Critical Error in Ark Updater!', exc_info=True)
