from modules.configreader import hstname, sharedpath, arkroot, numinstances, instance, instr, is_arkupdater, maint_hour
import configparser
from datetime import datetime
from datetime import time as dt
from modules.dbhelper import dbquery, dbupdate
from modules.pushover import pushover
from modules.players import getliveplayersonline, getplayersonline
from modules.instances import getlastwipe, instancelist, isinstancerunning, isinstanceup, isinstanceenabled
from timebetween import is_time_between
from modules.timehelper import wcstamp, Secs, Now
from modules.servertools import serverexec, serverneedsrestart
from time import sleep
from clusterevents import iseventtime, getcurrenteventext, iseventrebootday
from discordbot import writediscord
from loguru import logger as log
import random
import os
import threading
import shutil
import subprocess

confupdtimer = 0
dwtimer = 0
updgennotify = Now() - Secs['hour']


@log.catch
def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,))
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


@log.catch
def checkdirs(inst):
    if not os.path.exists('/home/ark/shared/logs/arkmanager'):
        log.error(f'Log directory /home/ark/shared/logs/arkmanager does not exist! creating')
        os.mkdir('/home/ark/shared/logs/arkmanager', 0o777)
        os.chown('/home/ark/shared/logs/arkmanager', 1001, 1005)
    else:
        log.trace('Log directory /home/ark/shared/logs/arkmanager exists')
    if not os.path.exists(f'/home/ark/shared/logs/arkmanager/{inst}'):
        log.error(f'Log directory /home/ark/shared/logs/arkmanager/{inst} does not exist! creating')
        os.mkdir(f'/home/ark/shared/logs/arkmanager/{inst}', 0o777)
        os.chown(f'/home/ark/shared/logs/arkmanager/{inst}', 1001, 1005)
    else:
        log.trace(f'Log directory /home/ark/shared/logs/arkmanager/{inst} exists')


@log.catch
def updatetimer(inst, ctime):
    dbupdate("UPDATE instances SET restartcountdown = '%s' WHERE name = '%s'" % (ctime, inst))


def setcfgver(inst, cver):
    dbupdate("UPDATE instances SET cfgver = %s WHERE name = '%s'" % (int(cver), inst))


def setpendingcfgver(inst, cver):
    dbupdate("UPDATE instances SET pendingcfg = %s WHERE name = '%s'" % (int(cver), inst))


def getcfgver(inst):
    lastwipe = dbquery("SELECT cfgver FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return int(lastwipe[0])


def getlastmaint(svr):
    lastmaint = dbquery("SELECT lastmaint FROM lastmaintenance WHERE name = '%s'" % (svr.upper(),), fetch='one', single=True)
    return lastmaint[0]


def setlastmaint(svr):
    dbupdate("UPDATE lastmaintenance SET lastmaint = '%s' WHERE name = '%s'" % (Now(fmt='dtd'), svr.upper()))


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


@log.catch
def wipeit(inst, extra=False):
    checkdirs(inst)
    if extra:
        serverexec(['arkmanager', 'rconcmd', f'ScriptCommand MatingOff_DS', f'@{inst}'], nice=0, null=True)
        sleep(3)
        serverexec(['arkmanager', 'rconcmd', f'ScriptCommand DestroyUnclaimed_DS', f'@{inst}'], nice=0, null=True)
        sleep(3)
    resetlastwipe(inst)
    serverexec(['arkmanager', 'rconcmd', 'DestroyWildDinos', f'@{inst}'], nice=0, null=True)
    sleep(3)
    serverexec(['arkmanager', 'rconcmd', 'Destroyall BeeHive_C' f'@{inst}'], nice=0, null=True)
    log.log('WIPE', f'All wild dinos have been wiped from [{inst.title()}]')


@log.catch
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
                bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="1,0.65,0,1">         It has been 12 hours since this server has had a wild dino wipe</>\n\n<RichColor Color="1,1,0,1">               Consider doing a</><RichColor Color="0,1,0,1">!vote </><RichColor Color="1,1,0,1">for fresh new dino selection</>\n\n<RichColor Color="0.65,0.65,0.65,1">     A wild dino wipe does not affect tame dinos that are already knocked out</>"""
                subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
            dwtimer += 1
            if dwtimer == 24:
                dwtimer = 0
    elif Now() - lastwipe > Secs['day'] and isinstanceup(inst):
        log.log('WIPE', f'Dino wipe needed for [{inst.title()}], players online but forced, wiping now')
        bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="1,0.65,0,1">         It has been 24 hours since this server has had a wild dino wipe</>\n\n<RichColor Color="1,1,0,1">               Forcing a maintenance wild dino wipe in 10 seconds</>\n\n<RichColor Color="0.65,0.65,0.65,1">     A wild dino wipe does not affect tame dinos that are already knocked out</>"""
        subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
        sleep(10)
        writechat(inst, 'ALERT', f'### Server is over 24 hours since wild dino wipe. Forcing wipe now.', wcstamp())
        wipeit(inst)
        dwtimer = 0
    else:
        log.trace(f'no dino wipe is needed for {inst}')


@log.catch
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


@log.catch
def restartinstnow(inst, startonly=False):
    checkdirs(inst)
    if not startonly:
        wipeit(inst, extra=True)
        sleep(5)
        serverexec(['arkmanager', 'stop', '--saveworld', f'@{inst}'], nice=0, null=True)
        log.log('UPDATE', f'Instance [{inst.title()}] has stopped, backing up world data...')
        dbupdate("UPDATE instances SET isup = 0, isrunning = 0, islistening = 0 WHERE name = '%s'" % (inst,))
    serverexec(['arkmanager', 'backup', f'@{inst}'], nice=0, null=True)
    if not isinstanceenabled(inst):
        log.log('UPDATE', f'Instance [{inst.title()}] remaining off because not enabled.')
        unsetstartbit(inst)
    elif serverneedsrestart() and inst != 'coliseum' and inst != 'crystal'and not startonly:
        dbupdate(f"UPDATE instances SET restartserver = False WHERE name = '{inst.lower()}'")
        log.log('MAINT', f'REBOOTING Server [{hstname.upper()}] for maintenance server reboot')
        serverexec(['reboot'], nice=0, null=True)
    else:
        log.log('UPDATE', f'Instance [{inst.title()}] has backed up world data, building config...')
        buildconfig(inst)
        shutil.copy(f'{sharedpath}/stagedconfig/Game-{inst.lower()}.ini', f'{arkroot}/ShooterGame/Saved/Config/LinuxServer/Game.ini')
        subprocess.run('chown ark.ark %s/ShooterGame/Saved/Config/LinuxServer/Game.ini' % (arkroot, ), stdout=subprocess.DEVNULL, shell=True)
        shutil.copy(f'{sharedpath}/stagedconfig/GameUserSettings-{inst.lower()}.ini', f'{arkroot}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini')
        log.debug(f'server {inst} built and updated config files')
        log.log('UPDATE', f'Instance [{inst.title()}] is updating from staging directory')
        serverexec(['arkmanager', 'update', '--force', '--no-download', '--update-mods', '--no-autostart', f'@{inst}'], nice=0, null=True),
        log.log('UPDATE', f'Instance [{inst.title()}] is starting')
        resetlastrestart(inst)
        unsetstartbit(inst)
        playerrestartbit(inst)
        os.nice(-19)
        serverexec(['arkmanager', 'start', f'@{inst}'], nice=-10, null=True)
        dbupdate("UPDATE instances SET isrunning = 1 WHERE name = '%s'" % (inst,))
        os.nice(10)


@log.catch
def restartloop(inst, startonly=False):
    checkdirs(inst)
    log.debug(f'{inst} restart loop has started')
    if startonly:
        restartinstnow(inst, startonly=True)
    timeleftraw = dbquery("SELECT restartcountdown, restartreason from instances WHERE name = '%s'" % (inst,), fetch='one')
    timeleft = int(timeleftraw[0])
    reason = timeleftraw[1]
    splayers, aplayers = getliveplayersonline(inst)
    if splayers == 0 and int(getplayersonline(inst, fmt='count')) == 0:
        setrestartbit(inst)
        log.log('UPDATE', f'Server [{inst.title()}] is empty and restarting now for a [{reason}]')
        writechat(inst, 'ALERT', f'!!! Empty server restarting now for a {reason.capitalize()}', wcstamp())
        message = f'server {inst.capitalize()} is restarting now for a {reason}'
        serverexec(['arkmanager', f'notify "{message}"', f'@{inst}'], nice=19, null=True)
        pushover('Instance Restart', message)
        restartinstnow(inst)
    elif reason != 'configuration update':
            setrestartbit(inst)
            if timeleft == 30:
                log.log('UPDATE', f'Starting 30 min restart countdown for [{inst.title()}] for a [{reason}]')
                writechat(inst, 'ALERT', f'!!! Server will restart in 30 minutes for a {reason.capitalize()}', wcstamp())
            else:
                log.log('UPDATE', f'Resuming {timeleft} min retart countdown for [{inst.title()}] for a [{reason}]')
            gotime = False
            snr = stillneedsrestart(inst)
            while snr and not gotime:
                if timeleft == 30 or timeleft == 15 or timeleft == 10 or timeleft == 5 or timeleft == 1:
                    log.log('UPDATE', f'{timeleft} min broadcast message sent to [{inst.title()}]')
                    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="1,0,0,1">                 The server has an update and needs to restart</>\n                       Restart reason: <RichColor Color="0,1,0,1">{reason}</>\n\n<RichColor Color="1,1,0,1">                   The server will be restarting in</><RichColor Color="1,0,0,1">{timeleft}</><RichColor Color="1,1,0,1"> minutes</>"""
                    subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)

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
                bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="1,0,0,1">                 The server has an update and needs to restart</>\n                       Restart reason: <RichColor Color="0,1,0,1">Ark Game Update</>\n\n<RichColor Color="1,1,0,1">                     !! THE SERVER IS RESTARTING</><RichColor Color="1,0,0,1">NOW</><RichColor Color="1,1,0,1"> !!</>\n\n     The server will be back up in 10 minutes, you can check status in Discord"""
                subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
                writechat(inst, 'ALERT', f'!!! Server restarting now for {reason.capitalize()}', wcstamp())
                serverexec(['arkmanager', f'notify "{message}"', f'@{inst}'], nice=19, null=True)
                pushover('Instance Restart', message)
                sleep(10)
                restartinstnow(inst)
            else:
                log.warning(f'server restart on {inst} has been canceled from forced cancel')
                bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\n\n\n<RichColor Color="1,1,0,1">                    The server restart has been cancelled!</>"""
                subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
                writechat(inst, 'ALERT', f'!!! Server restart for {reason.capitalize()} has been canceled', wcstamp())
    else:
        log.debug(f'configuration restart skipped because {splayers} players and {aplayers} active players')


@log.catch
def maintenance():
    t, s, e = datetime.now(), dt(int(maint_hour), 0), dt(int(maint_hour) + 1, 0)
    inmaint = is_time_between(t, s, e)
    if inmaint and getlastmaint(hstname) < Now(fmt='dtd'):
        setlastmaint(hstname)
        log.log('MAINT', f'Daily maintenance window has opened for server [{hstname.upper()}]...')
        for each in range(numinstances):
            inst = instance[each]['name']
            bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="0,1,0,1">           Daily server maintenance has started (4am EST/8am GMT)</>\n\n<RichColor Color="1,1,0,1">    All dino mating will be toggled off, and all unclaimed dinos will be cleared</>\n<RichColor Color="1,1,0,1">            The server will also be performing updates and backups</>"""
            subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
        log.log('MAINT', f'Running server os maintenance on [{hstname.upper()}]...')
        log.debug(f'OS update started for {hstname}')
        serverexec(['apt', 'update'], nice=5, null=True)
        log.debug(f'OS upgrade started for {hstname}')
        serverexec(['apt', 'upgrade', '-y'], nice=5, null=True)
        log.debug(f'OS autoremove started for {hstname}')
        serverexec(['apt', 'autoremove', '-y'], nice=5, null=True)
        if serverneedsrestart():
            log.warning(f'[{hstname.upper()}] server needs a hardware reboot after package updates')
        for each in range(numinstances):
            inst = instance[each]['name']
            checkdirs(inst)
            if serverneedsrestart():
                dbupdate(f"UPDATE instances SET restartserver = True WHERE name = '{inst.lower()}'")
            try:
                log.log('MAINT', f'Performing a world data save on [{inst.title()}]...')
                serverexec(['arkmanager', 'saveworld', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.log('MAINT', f'Backing up server instance and archiving old players [{inst.title()}]...')
                serverexec(['arkmanager', 'backup', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Archiving player and tribe data on [{inst.title()}]...')
                os.system('find /home/ark/ARK/ShooterGame/Saved/%s-data/ -maxdepth 1 -mtime +90 ! -path "*/ServerPaintingsCache/*" -path /home/ark/ARK/ShooterGame/Saved/%s-data/archive -prune -exec mv "{}" /home/ark/ARK/ShooterGame/Saved/%s-data/archive \;' % (inst, inst, inst))
                sleep(30)
                log.log('MAINT', f'Running all dino and map maintenance on server [{inst.title()}]...')
                log.debug(f'Shutting down dino mating on {inst}...')
                serverexec(['arkmanager', 'rconcmd', 'ScriptCommand MatingOff_DS', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all unclaimed dinos on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'ScriptCommand DestroyUnclaimed_DS', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all wild wyvern eggs on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsWyvern_C', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all wild Deinonychus eggs on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsDeinonychus_C', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all wild drake eggs on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_RockDrake_NoPhysics_C', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all beehives on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'Destroyall BeeHive_C', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all wild Deinonychus eggs on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsDeinonychus_C', f'@{inst}'], nice=0, null=True)
                sleep(30)
                log.debug(f'Clearing all beaver dams on [{inst.title()}]...')
                serverexec(['arkmanager', 'rconcmd', 'destroyall BeaverDam_C', f'@{inst}'], nice=0, null=True)
                sleep(30)
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
                    serverexec(['arkmanager', 'rconcmd', f'ServerChat {message}', f'@{inst}'], nice=19, null=True)
            except:
                log.exception(f'Error during {inst} instance daily maintenance')
        log.log('MAINT', f'Daily maintenance has ended for [{hstname.upper()}]')


@log.catch
def instancerestart(inst, reason, startonly=False):
    checkdirs(inst)
    log.debug(f'instance restart verification starting for {inst}')
    global instance
    global confupdtimer
    if not isrebooting(inst):
        dbupdate("UPDATE instances SET restartreason = '%s' WHERE name = '%s'" % (reason, inst))
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['restartthread'] = threading.Thread(name='%s-restart' % inst, target=restartloop, args=(inst, startonly))
                instance[each]['restartthread'].start()
    else:
        log.debug(f'skipping start/restart for {inst} because restart thread already running')


@log.catch
def compareconfigs(config1, config2):
    if not os.path.isfile(config2):
        serverexec(['touch', '{config2}'], nice=15, null=True)
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


@log.catch
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
            eventcfgfile = f'{sharedpath}/config/GameUserSettings-{eventext.strip()}.ini'
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
            shutil.move(newcfgfile, stgcfgfile)
            shutil.copy(gamebasefile, stggamefile)
            subprocess.run('chown ark.ark "%s"' % (stgcfgfile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run('chown ark.ark "%s"' % (stggamefile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            return True
        else:
            subprocess.run('rm -f "%s"' % (newcfgfile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            return False
    except:
        log.exception(f'Problem building config for inst {inst}')
        return False


@log.catch
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
                log.trace(f'no config changes detected for instance {inst}')


@log.catch
def isnewarkver(inst):
    isarkupd = serverexec(['arkmanager', 'checkupdate', f'@{inst}'], nice=19, null=False)
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


@log.catch
def performbackup(inst):
    sleep(random.randint(1, 5) * 6)
    log.log('MAINT', f'Performing a world data backup on [{inst.title()}]')
    serverexec(['arkmanager', 'backup', f'@{inst}'], nice=19, null=True)


@log.catch
def checkbackup():
    for seach in range(numinstances):
        sinst = instance[seach]['name']
        checkdirs(sinst)
        if not isrebooting(sinst):
            lastrestr = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (sinst, ))
            lt = Now() - float(lastrestr[0][0])
            if (lt > 21600 and lt < 21900) or (lt > 43200 and lt < 43500) or (lt > 64800 and lt < 65100):
                performbackup(sinst)


@log.catch
def checkifenabled(inst):
    lastwipe = dbquery("SELECT enabled, isrunning FROM instances WHERE name = '%s'" % (inst, ), fetch='one')
    if serverneedsrestart():
        dbupdate(f"UPDATE instances SET restartserver = True WHERE name = '{inst.lower()}'")
    if lastwipe[0] and lastwipe[1] == 0:
        log.log('MAINT', f'Instance [{inst.title()}] is set to [enabled]. Starting server')
        restartinstnow(inst, startonly=True)
    elif not lastwipe[0] and lastwipe[1] == 1:
        for each in range(numinstances):
            if not isrebooting(instance[each]['name']):
                if instance[each]['name'] == inst:
                    checkifalreadyrestarting(instance[each]['name'])
                    log.warning(f'Instance [{inst.title()}] is set to [disabled]. Stopping server')
                    instancerestart(inst, 'admin restart')


@log.catch
def checkifalreadyrestarting(inst):
    global instance
    lastwipe = dbquery("SELECT needsrestart FROM instances WHERE name = '%s'" % (inst, ), fetch='one')
    ded = lastwipe[0]
    if ded == "True":
        if not isrebooting(inst):
            log.debug(f'restart flag set for instance {inst}, starting restart loop')
            for each in range(numinstances):
                if instance[each]['name'] == inst:
                    instance[each]['restartthread'] = threading.Thread(name='%s-restart' % inst, target=restartloop, args=(inst,))
                    instance[each]['restartthread'].start()


@log.catch
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
                serverexec(['arkmanager', 'update', '--downloadonly', f'@{instance[0]["name"]}'], nice=0, null=True)
                log.debug('ark update downloaded to staging area')
                # msg = f'Ark update has been released. Servers will begin restart countdown now.\n\
# https://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes/'
                writediscord('ARK Game Update', Now(), name='https://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes', server='UPDATE')
                msg = f'Ark Game Updare Released\nhttps://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes'
                log.log('UPDATE', f'ARK update download complete. Update is staged. Notifying servers')
                dbupdate(f"UPDATE instances set needsrestart = 'True', restartreason = 'ark game update'")
                pushover('Ark Update', msg)
        except:
            log.exception(f'error in determining ark version')

    for each in range(numinstances):
        checkdirs(instance[each]['name'])
        if not isrebooting(instance[each]['name']):
            ismodupdd = serverexec(['arkmanager', 'checkmodupdate', f'@{instance[each]["name"]}'], nice=19, null=False)
            ismodupd = ismodupdd.stdout.decode('utf-8')
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
                serverexec(['arkmanager', 'update', '--downloadonly', '--update-mods', f'@{instance[each]["name"]}'], nice=0, null=True)
                log.debug(f'mod updates for instance {instance[each]["name"]} download complete')
                aname = f'{modname} Mod Update'
                writediscord(f'{modname} Mod Update', Now(), name=f'https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}', server='UPDATE')
                msg = f'{modname} Mod Update\nhttps://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}'
                pushover('Mod Update', msg)
                for neo in range(numinstances):
                        instancerestart(instance[neo]['name'], aname)
        else:
            log.debug(f'no updated mods were found for instance {instance[each]["name"]}')


@log.catch
def restartcheck():
    for each in range(numinstances):
        checkifenabled(instance[each]['name'])
        if not isrebooting(instance[each]['name']):
            checkifalreadyrestarting(instance[each]['name'])


@log.catch
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
            maintenance()
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
