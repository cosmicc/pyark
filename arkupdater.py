from modules.configreader import hstname, sharedpath, arkroot, numinstances, instance, instr, is_arkupdater
import configparser
from datetime import datetime
from datetime import time as dt
from modules.dbhelper import dbquery, dbupdate
from modules.pushover import pushover
from modules.players import getliveplayersonline, getplayersonline
from modules.instances import getlastwipe, instancelist, isinstancerunning, isinstanceup
from timebetween import is_time_between
from modules.timehelper import wcstamp, Secs, Now
from time import sleep
from clusterevents import iseventtime, getcurrenteventext, iseventrebootday
from discordbot import writediscord
from loguru import logger as log
import os
import subprocess
import threading


confupdtimer = 0
dwtimer = 0
updgennotify = Now() - Secs['hour']


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,))
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


def updatetimer(inst, ctime):
    dbupdate("UPDATE instances SET restartcountdown = '%s' WHERE name = '%s'" % (ctime, inst))


def setcfgver(inst, cver):
    dbupdate("UPDATE instances SET cfgver = %s WHERE name = '%s'" % (int(cver), inst))


def setpendingcfgver(inst, cver):
    dbupdate("UPDATE instances SET pendingcfg = %s WHERE name = '%s'" % (int(cver), inst))


def getcfgver(inst):
    lastwipe = dbquery("SELECT cfgver FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return int(lastwipe[0])


def getpendingcfgver(inst):
    lastwipe = dbquery("SELECT pendingcfg FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return int(lastwipe[0])


def resetlastwipe(inst):
    dbupdate("UPDATE instances SET lastdinowipe = '%s' WHERE name = '%s'" % (Now(), inst))


def resetlastrestart(inst):
    dbupdate("UPDATE instances SET lastrestart = '%s' WHERE name = '%s'" % (Now(), inst))
    dbupdate("UPDATE instances SET needsrestart = 'False' WHERE name = '%s'" % (inst, ))
    dbupdate("UPDATE instances SET cfgver = %s WHERE name = '%s'" % (getpendingcfgver(inst), inst))
    dbupdate("UPDATE instances SET restartcountdown = 30")


def setrestartbit(inst):
    dbupdate("UPDATE instances SET needsrestart = 'True' WHERE name = '%s'" % (inst, ))


def unsetstartbit(inst):
    dbupdate("UPDATE instances SET needsrestart = 'False' WHERE name = '%s'" % (inst, ))


def playerrestartbit(inst):
    dbupdate("UPDATE players SET restartbit = 1 WHERE server = '%s'" % (inst, ))


def wipeit(inst):
    subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    sleep(3)
    subprocess.run('arkmanager rconcmd "Destroyall BeeHive_C" @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastwipe(inst)
    log.log('WIPE', f'All wild dinos have been wiped from [{inst.title()}]')


def checkwipe(inst):
    global dwtimer
    lastwipe = getlastwipe(inst)
    if Now() - lastwipe > Secs['12hour'] and isinstanceup(inst):
        splayers, aplayers = getliveplayersonline(inst)
        if aplayers == 0 and int(getplayersonline(inst, fmt='count')) == 0:
            log.log('WIPE', f'Dino wipe needed for [{inst.title()}], server is empty, wiping now')
            writechat(inst, 'ALERT', f'### Empty server is over 12 hours since wild dino wipe. Wiping now.', wcstamp())
            wipeit(inst)
            dwtimer = 0
        else:
            if dwtimer == 0:
                log.log('WIPE', f'12 Hour dino wipe needed for [{inst.title()}], but players are online. Waiting...')
            dwtimer += 1
            if dwtimer == 24:
                dwtimer = 0
    elif Now() - lastwipe > Secs['day'] and isinstanceup(inst):
        log.log('WIPE', f'Dino wipe needed for [{inst.title()}], players online but forced, wiping now')
        subprocess.run("""arkmanager rconcmd "Broadcast '\n\n\nIts been over 24 hours since a wild dino wipe, forcing a maintenance wipe.  Wiping all wild dinos in 10 seconds.'" @%s""" % (inst,), shell=True)
        sleep(10)
        writechat(inst, 'ALERT', f'### Server is over 24 hours since wild dino wipe. Forcing wipe now.', wcstamp())
        wipeit(inst)
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


def restartinstnow(inst, ext='restart'):
    subprocess.run('arkmanager stop --saveworld @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    log.log('UPDATE', f'Instance [{inst.title()}] has stopped, backing up world data...')
    dbupdate("UPDATE instances SET isup = 0, isrunning = 0, islistening = 0 WHERE name = '%s'" % (inst,))
    subprocess.run('arkmanager backup @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    log.log('UPDATE', f'Instance [{inst.title()}] has backed up world data, building config...')
    buildconfig(inst)
    subprocess.run('cp %s/stagedconfig/Game-%s.ini %s/ShooterGame/Saved/Config/LinuxServer/Game.ini' % (inst, sharedpath, arkroot), stdout=subprocess.DEVNULL, shell=True)
    subprocess.run('chown ark.ark %s/ShooterGame/Saved/Config/LinuxServer/Game.ini' % (arkroot, ), stdout=subprocess.DEVNULL, shell=True)
    subprocess.run('cp %s/stagedconfig/GameUserSettings-%s.ini %s/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini' % (sharedpath, inst.lower(), arkroot), stdout=subprocess.DEVNULL, shell=True)
    log.debug(f'server {inst} built and updated config files')
    log.log('UPDATE', f'Instance [{inst.title()}] is updating from staging directory')
    subprocess.run('arkmanager update --force --no-download --update-mods --no-autostart @%s' % (inst),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    log.log('UPDATE', f'Instance [{inst.title()}] is starting')
    subprocess.run('arkmanager start @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastrestart(inst)
    unsetstartbit(inst)
    playerrestartbit(inst)
    dbupdate("UPDATE instances SET isrunning = 1 WHERE name = '%s'" % (inst,))
    # subprocess.run('systemctl start arkwatchdog', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


@log.catch
def restartloop(inst):
    log.debug(f'{inst} restart loop has started')
    timeleftraw = dbquery("SELECT restartcountdown, restartreason from instances WHERE name = '%s'" % (inst,), fetch='one')
    timeleft = int(timeleftraw[0])
    reason = timeleftraw[1]
    splayers, aplayers = getliveplayersonline(inst)
    if splayers == 0 and int(getplayersonline(inst, fmt='count')) == 0:
        setrestartbit(inst)
        log.log('UPDATE', f'Server [{inst.title()}] is empty and restarting now for a [{reason}]')
        writechat(inst, 'ALERT', f'!!! Empty server restarting now for a {reason.capitalize()}', wcstamp())
        message = f'server {inst.capitalize()} is restarting now for a {reason}'
        subprocess.run('arkmanager notify "%s" @%s' % (message, inst), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, shell=True)
        pushover('Instance Restart', message)
        restartinstnow(inst)
    elif reason != 'configuration update':
            setrestartbit(inst)
            if timeleft == 30:
                log.log('UPDATE', f'Starting 30 min restart countdown for [{inst.title()}] for a [{reason}]')
                writechat(inst, 'ALERT', f'!!! Server will restart in 30 minutes for a {reason.capitalize()}',
                          wcstamp())
            else:
                log.log('UPDATE', f'Resuming {timeleft} min retart countdown for [{inst.title()}] for a [{reason}]')
            gotime = False
            snr = stillneedsrestart(inst)
            while snr and not gotime:
                if timeleft == 30 or timeleft == 15 or timeleft == 10 or timeleft == 5 or timeleft == 1:
                    log.log('UPDATE', f'{timeleft} min broadcast message sent to [{inst.title()}]')
                    subprocess.run("""arkmanager rconcmd "broadcast
                                   '\n\n\n          The server will be restarting in %s minutes for a %s'" @%s""" %
                                   (timeleft, reason, inst), stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, shell=True)
                sleep(Secs['1min'])
                timeleft = timeleft - 1
                updatetimer(inst, timeleft)
                snr = stillneedsrestart(inst)
                splayers, aplayers = getliveplayersonline(inst)
                if (aplayers == 0 and int(getplayersonline(inst, fmt='count')) == 0) or timeleft == 0:
                    gotime = True
            if stillneedsrestart(inst):
                log.log('UPDATE', f'Server [{inst.title()}] is restarting now for a [{reason}]')
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
    else:
        log.debug(f'configuration restart skipped because {splayers} players and {aplayers} active players')


def checkmaintenance():
    t, s, e = datetime.now(), dt(9, 0), dt(9, 5)  # Maintenance reboot 9:00am GMT (5:00AM EST)
    inmaint = is_time_between(t, s, e)
    if inmaint:
        log.log('MAINT', f'Daily maintenance window has opened for server [{hstname.upper()}]...')
        for each in range(numinstances):
            inst = instance[each]['name']
            subprocess.run("""arkmanager rconcmd "Broadcast '\n\n\nServer maintenance has started. All dino mating will be temporarily stopped.  All unclaimed dinos will be cleared, and the server will also be performing updates and backups.'" @%s""" % (inst,), shell=True)
        log.log('MAINT', f'Running server os maintenance on [{hstname.upper()}]...')
        log.debug(f'OS update started for {hstname}')
        subprocess.run('apt update', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        log.debug(f'OS upgrade started for {hstname}')
        subprocess.run('apt upgrade -y', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        log.debug(f'OS autoremove started for {hstname}')
        subprocess.run('apt autoremove -y', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        for each in range(numinstances):
            inst = instance[each]['name']
            try:
                log.log('MAINT', f'Performing a world data save on [{inst.title()}]...')
                subprocess.run('arkmanager saveworld @%s' % (inst,), shell=True)
                log.log('MAINT', f'Backing up server instance [{inst.title()}]...')
                subprocess.run('arkmanager backup @%s' % (inst,), shell=True)
                log.log('MAINT', f'Archiving player and tribe data on [{inst.title()}]...')
                os.system('find /home/ark/ARK/ShooterGame/Saved/%s-data/ -maxdepth 1 -mtime +90 ! -path "*/ServerPaintingsCache/*" -path /home/ark/ARK/ShooterGame/Saved/%s-data/archive -prune -exec mv "{}" /home/ark/ARK/ShooterGame/Saved/%s-data/archive \;' % (inst, inst, inst))
                sleep(5)
                log.debug(f'Shutting down dino mating on {inst}...')
                subprocess.run('arkmanager rconcmd "ScriptCommand MatingOff_DS" @%s' % (inst,), shell=True)
                sleep(5)
                log.log('MAINT', f'Clearing all unclaimed dinos on [{inst.title()}]...')
                subprocess.run('arkmanager rconcmd "ScriptCommand DestroyUnclaimed_DS" @%s' % (inst,), shell=True)
                sleep(5)
                checkwipe(inst)
                lstsv = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (inst,), fetch='one')
                eventreboot = iseventrebootday()
                if eventreboot:
                    maintrest = f"{eventreboot}"
                    instancerestart(inst, maintrest)
                elif Now() - float(lstsv[0]) > Secs['3day'] or getcfgver(inst) < getpendingcfgver(inst):
                    maintrest = "maintenance restart"
                    instancerestart(inst, maintrest)
                else:
                    message = 'Server maintenance has ended. No restart needed. If you had dinos mating right now you will need to turn it back on.'
                    subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (message, inst), shell=True)
            except:
                log.exception(f'Error during {inst} instance daily maintenance')
        if os.path.isfile('/var/run/reboot-required'):
            log.warning(f'[{hstname.upper()}] server needs a hardware reboot after package updates')
        log.log('MAINT', f'Daily maintenance has ended for [{hstname.upper()}]')


def instancerestart(inst, reason):
    log.debug(f'instance restart verification starting for {inst}')
    global instance
    global confupdtimer
    dbupdate("UPDATE instances SET restartreason = '%s' WHERE name = '%s'" % (reason, inst))
    if not isrebooting(inst):
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['restartthread'] = threading.Thread(name='%s-restart' % inst, target=restartloop, args=(inst,))
                instance[each]['restartthread'].start()


def compareconfigs(config1, config2):
    if not os.path.isfile(config2):
        subprocess.run('touch "%s"' % (config2), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    try:
        f1 = open(config1)
        text1Lines = f1.readlines()
        f2 = open(config2)
        text2Lines = f2.readlines()
        set1 = set(text1Lines)
        set2 = set(text2Lines)
        diffList = (set1 | set2) - (set1 & set2)
        if diffList:
            return True
        else:
            return False
    except:
        log.critical('Problem comparing configs for build')
        return False


def buildconfig(inst):
    try:
        basecfgfile = f'{sharedpath}/config/GameUserSettings-base.ini'
        servercfgfile = f'{sharedpath}/config/GameUserSettings-{inst.lower()}.ini'
        newcfgfile = f'{sharedpath}/config/GameUserSettings-{inst.lower()}.tmp'
        stgcfgfile = f'{sharedpath}/stagedconfig/GameUserSettings-{inst.lower()}.ini'
        stggamefile = f'{sharedpath}/stagedconfig/Game-{inst.lower()}.ini'
        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(basecfgfile)

        if os.path.isfile(servercfgfile):
            with open(servercfgfile, 'r') as f:
                lines = f.readlines()
                for each in lines:
                    each = each.strip().split(',')
                    config.set(each[0], each[1], each[2])

        if iseventtime():
            eventext = getcurrenteventext()
            eventcfgfile = f'{sharedpath}/config/GameUserSettings-{eventext.lower()}.ini'
            if os.path.isfile(eventcfgfile):
                with open(eventcfgfile, 'r') as f:
                    lines = f.readlines()
                    for each in lines:
                        each = each.strip().split(',')
                        config.set(each[0], each[1], each[2])
            else:
                log.error('Cannot find Event GUS config file to merge in')

        with open(newcfgfile, 'w') as configfile:
            config.write(configfile)

        fname = f'{sharedpath}/config/Game-{inst.lower()}.ini'
        if os.path.isfile(fname):
            gamebasefile = f'{sharedpath}/config/Game-{inst.lower()}.ini'
        else:
            gamebasefile = f'{sharedpath}/config/Game-base.ini'

        if compareconfigs(newcfgfile, stgcfgfile) or compareconfigs(gamebasefile, stggamefile):
            subprocess.run('mv "%s" "%s"' % (newcfgfile, stgcfgfile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run('cp "%s" "%s"' % (gamebasefile, stggamefile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run('chown ark.ark "%s"' % (stgcfgfile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run('chown ark.ark "%s"' % (stggamefile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            return True
        else:
            subprocess.run('rm -f "%s"' % (newcfgfile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            return False
    except:
        log.exception(f'Problem building config for inst {inst}')
        return False


def checkconfig():
    for each in range(numinstances):
        inst = instance[each]['name']
        if not isrebooting(inst):
            if buildconfig(inst):
                log.log('UPDATE', f'Config update detected for [{inst.title()}]')
                har = int(getcfgver(inst))
                setpendingcfgver(inst, har + 1)
            if getcfgver(inst) < getpendingcfgver(inst):
                maintrest = "configuration update"
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


def performbackup(inst):
    log.log('MAINT', f'Performing a world data backup on [{inst.title()}]')
    subprocess.run('arkmanager backup @%s' % (inst, ), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


def checkbackup():
    for seach in range(numinstances):
        sinst = instance[seach]['name']
        if not isrebooting(sinst):
            lastrestr = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (sinst, ))
            lt = Now() - float(lastrestr[0][0])
            if (lt > 21600 and lt < 21900) or (lt > 43200 and lt < 43500) or (lt > 64800 and lt < 65100):
                performbackup(sinst)


def checkifenabled(inst):
    lastwipe = dbquery("SELECT enabled, isrunning FROM instances WHERE name = '%s'" % (inst, ), fetch='one')
    if lastwipe[0] and lastwipe[1] == 0:
        log.warning(f'Instance [{inst.title()}] is set to start (enabled). Starting server')
        restartinstnow(inst, ext='start')
    elif not lastwipe[0] and lastwipe[1] == 1:
        log.warning(f'Instance [{inst.title()}] is set to stop (disabled). Stopping server')
        instancerestart(inst, 'admin restart', ext='stop')


def checkifalreadyrestarting(inst):
    lastwipe = dbquery("SELECT needsrestart FROM instances WHERE name = '%s'" % (inst, ), fetch='one')
    ded = lastwipe[0]
    if ded == "True":
        if not isrebooting(inst):
            log.debug(f'restart flag set for instance {inst}, starting restart loop')
            restartloop(inst)


def checkupdates():
    global updgennotify
    global ugennotify
    if is_arkupdater == "True" and Now() - updgennotify > Secs['hour']:
        try:
            ustate, curver, avlver = isnewarkver('all')
            if not ustate:
                log.debug('ark update check found no ark updates available')
            else:
                updgennotify = Now()
                log.log('UPDATE', f'ARK update found ({curver}>{avlver}) downloading update.')
                subprocess.run('arkmanager update --downloadonly @%s' % (instance[0]['name']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug('ark update downloaded to staging area')
                # msg = f'Ark update has been released. Servers will begin restart countdown now.\n\
# https://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes/'
                writediscord('ARK Game Update', Now(), name='https://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes', server='UPDATE')
                # pushover('Ark Update', msg)
                log.log('UPDATE', f'ARK update download complete. Update is staged. Notifying servers')
                dbupdate(f"UPDATE instances set needsrestart = 'True', restartreason = 'ark game update'")
        except:
            log.exception(f'error in determining ark version')

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
                log.log('UPDATE', f'ARK mod update [{modname}] id [{modid}] detected for instance [{instance[each]["name"].title()}]')
                log.debug(f'downloading mod updates for instance {instance[each]["name"]}')
                subprocess.run('arkmanager update --downloadonly --update-mods @%s' % (instance[each]['name']),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                log.debug(f'mod updates for instance {instance[each]["name"]} download complete')
                aname = f'{modname} Mod Update'
                # msg = f'Mod {modname} has been updated. Servers will begin restart countdowns now.\n\
# https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}'
                writediscord(f'{modname} Mod Update', Now(), name=f'https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}', server='UPDATE')
                # pushover('Mod Update', msg)
                for neo in range(numinstances):
                        instancerestart(instance[neo]['name'], aname)
        else:
            log.debug(f'no updated mods were found for instance {instance[each]["name"]}')


def restartcheck():
    for each in range(numinstances):
        # checkifenabled(instance[each]['name'])
        if not isrebooting(instance[each]['name']):
            checkifalreadyrestarting(instance[each]['name'])


def arkupd():
    log.debug('arkupdater thread started')
    if numinstances > 0:
        log.debug(f'Found {numinstances} ARK server instances: [{instr}]')
    else:
        log.debug(f'No ARK game instances found, running as [Master Bot]')
    while True:
        try:
            checkconfig()
            restartcheck()
            sleep(30)
            restartcheck()
            sleep(30)
            checkupdates()
            restartcheck()
            sleep(30)
            restartcheck()
            sleep(30)
            checkmaintenance()
            restartcheck()
            sleep(30)
            restartcheck()
            sleep(30)
            checkbackup()
            restartcheck()
            sleep(30)
            restartcheck()
            sleep(30)
            for each in range(numinstances):
                if not isrebooting(instance[each]['name']):
                    checkwipe(instance[each]['name'])
            restartcheck()
            sleep(30)
            restartcheck()
            sleep(30)
        except:
            log.exception('Critical Error in Ark Updater!')
            sleep(60)
