import asyncio
import configparser
import logging
import random
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from datetime import time as dt
from os import chown
from pathlib import Path
from time import sleep

import uvloop
from loguru import logger as log
from timebetween import is_time_between

import globvars
from fsmonitor import FSMonitorThread
from modules.asyncdb import DB as db
from modules.clusterevents import asynciseventrebootday, getcurrenteventext, iseventtime
from modules.configreader import arkroot, hstname, instances, instr, is_arkupdater, maint_hour, numinstances, sharedpath
from modules.discordbot import asyncwritediscord
from modules.instances import (asyncgetlastrestart, asyncgetlastwipe,
                               asyncisinstanceenabled, asyncisinstanceup, asyncwipeit)
from modules.players import asyncgetplayersonline
from modules.pushover import pushover
from modules.servertools import (asyncserverbcast, asyncserverchat, asyncserverchatto, asyncserverexec,
                                 asyncservernotify, asynctimeit, serverexec, serverneedsrestart)
from modules.timehelper import Now, Secs, wcstamp

logging.basicConfig(level=logging.DEBUG)

confupdtimer = 0
dwtimer = 0
updgennotify = Now() - Secs['hour']

log.add(sink=sys.stdout, level=1, backtrace=True, diagnose=True, colorize=True)

def file_event(event):
    if event.action_name == 'modify':
        if event.name == globvars.gameini_baseconfig_file.name:
            asyncio.create_task(configupdatedetected('all'))
        elif event.name == globvars.gusini_baseconfig_file.name:
            asyncio.create_task(configupdatedetected('all'))
        else:
            for inst in instances:
                if event.name == globvars.gameini_customconfig_files[inst].name:
                    asyncio.create_task(configupdatedetected(inst))
                elif event.name == globvars.gusini_customconfig_files[inst].name:
                    asyncio.create_task(configupdatedetected(inst))


async def configupdatedetected(cinst):
    if cinst == 'all':
        cinst = instances
    for inst in cinst:
        if not isrebooting(inst):
            log.log('UPDATE', f'Config update detected for [{inst.title()}]')
            har = int(getcfgver(inst))
            setpendingcfgver(inst, har + 1)
        if getcfgver(inst) < getpendingcfgver(inst):
            maintrest = "configuration update"
            await asyncinstancerestart(inst, maintrest)


def pushoverthread(title, message):
    pushoverthread = threading.Thread(name='pushover', target=pushover, args=(title, message), daemon=True)
    pushoverthread.start()


@log.catch
async def asyncwritechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = await db.fetchone(f"SELECT * from players WHERE playername = '{whos}'")
    elif whos == "ALERT" or isindb:
        await db.update(f"INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('{inst}', '{whos}', '{msg}', '{tstamp}')")


@log.catch
def checkdirs(inst):
    for path in globvars.arkmanager_paths:
        if not path.exists():
            log.error(f'Log directory {str(path)} does not exist! creating')
            path.mkdir(mode=0o777, parents=True)
            chown(str(path), 1001, 1005)


@log.catch
async def asyncupdatetimer(inst, ctime):
    await db.update(f"UPDATE instances SET restartcountdown = '{ctime}' WHERE name = '{inst}'")


async def asyncsetcfgver(inst, cver):
    await db.update(f"UPDATE instances SET cfgver = {int(cver)} WHERE name = '{inst}'")


async def asyncsetpendingcfgver(inst, cver):
    await db.update(f"UPDATE instances SET pendingcfg = {int(cver)} WHERE name = '{inst}'")


async def ayncgetcfgver(inst):
    cfgver = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return int(cfgver['cfgver'])


async def asyncgetlastmaint(svr):
    lastmaint = await db.fetchone(f"SELECT * FROM lastmaintenance WHERE name = '{svr.upper()}'")
    return lastmaint['lastmaint']


async def asyncsetlastmaint(svr):
    await db.update(f"UPDATE lastmaintenance SET lastmaint = '{Now(fmt='dtd')}' WHERE name = 'svr.upper()'")


async def asyncgetpendingcfgver(inst):
    instdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return int(instdata['cfgver'])


async def getlastrestart(inst):
    dbdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return dbdata['lastrestart']


async def asyncresetlastrestart(inst):
    await db.update(f"UPDATE instances SET lastrestart = '{Now()}', needsrestart = 'False', cfgver = {await asyncgetpendingcfgver(inst)}, restartcountdown = 30 WHERE name = '{inst}'")


async def asyncsetrestartbit(inst):
    await db.update(f"UPDATE instances SET needsrestart = 'True' WHERE name = '{inst}'")


async def asyncunsetstartbit(inst):
    await db.update(f"UPDATE instances SET needsrestart = 'False' WHERE name = '{inst}'")


async def asyncplayerrestartbit(inst):
    await db.update(f"UPDATE players SET restartbit = 1 WHERE server = '{inst}'")

@asynctimeit
@log.catch
async def asynccheckwipe(inst):
    global dwtimer
    lastwipe = await asyncgetlastwipe(inst)
    if Now() - lastwipe > Secs['12hour'] and await asyncisinstanceup(inst):
        if await asyncgetliveplayersonline(inst)['activeplayers'] == 0 and len(await asyncgetplayersonline()) == 0:
            log.log('WIPE', f'Dino wipe needed for [{inst.title()}], server is empty, wiping now')
            await asyncwritechat(inst, 'ALERT', f'### Empty server is over 12 hours since wild dino wipe. Wiping now.', wcstamp())
            asyncio.create_task(asyncwipeit(inst))
            dwtimer = 0
        else:
            if dwtimer == 0:
                log.log('WIPE', f'12 Hour dino wipe needed for [{inst.title()}], but players are online. Waiting...')
                bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="1,0.65,0,1">         It has been 12 hours since this server has had a wild dino wipe</>\n\n<RichColor Color="1,1,0,1">               Consider doing a</><RichColor Color="0,1,0,1">!vote </><RichColor Color="1,1,0,1">for fresh new dino selection</>\n\n<RichColor Color="0.65,0.65,0.65,1">     A wild dino wipe does not affect tame dinos that are already knocked out</>"""
                await asyncserverbcast(inst, bcast)
            dwtimer += 1
            if dwtimer == 24:
                dwtimer = 0
    elif Now() - lastwipe > Secs['day'] and await asyncsinstanceup(inst):
        log.log('WIPE', f'Dino wipe needed for [{inst.title()}], players online but forced, wiping now')
        bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="1,0.65,0,1">         It has been 24 hours since this server has had a wild dino wipe</>\n\n<RichColor Color="1,1,0,1">               Forcing a maintenance wild dino wipe in 10 seconds</>\n\n<RichColor Color="0.65,0.65,0.65,1">     A wild dino wipe does not affect tame dinos that are already knocked out</>"""
        await asyncserverbcast(inst, bcast)
        await asyncio.sleep(10)
        await asyncwritechat(inst, 'ALERT', f'### Server is over 24 hours since wild dino wipe. Forcing wipe now.', wcstamp())
        asyncio.create_task(wipeit(inst))
        dwtimer = 0
    else:
        log.trace(f'no dino wipe is needed for {inst}')


async def asyncstillneedsrestart(inst):
    instdata = db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if instdata['needsrestart'] == "True":
        return True
    else:
        return False


@log.catch
def installconfigs(inst):
    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(globvars.gusini_baseconfig_file)
    if inst in globvars.gusini_customconfig_files:
        gusbuildfile = globvars.gusini_customconfig_files[inst].read_text().split('\n')
        for each in gusbuildfile:
            a = each.split(',')
            if len(a) == 3:
                config.set(a[0], a[1], a[2])
    else:
        log.debug(f'No custom config found for {inst}')

    if iseventtime():
        eventext = getcurrenteventext()
        globvars.gusini_event_file = Path(f'{sharedpath}/config/GameUserSettings-{eventext.strip()}.ini')
        if globvars.gusini_event_file.exists():
            for each in globvars.gusini_event_file.read_text().split('\n'):
                a = each.split(',')
                if len(a) == 3:
                    config.set(a[0], a[1], a[2])
        else:
            log.error('Cannot find Event GUS config file to merge in')

    if globvars.gusini_tempconfig_file.exists():
        globvars.gusini_tempconfig_file.unlink()

    with open(str(globvars.gusini_tempconfig_file), 'w') as configfile:
            config.write(configfile)

    shutil.copy(globvars.gusini_tempconfig_file, globvars.gusini_final_file)
    globvars.gusini_tempconfig_file.unlink()
    if inst in globvars.gameini_customconfig_files:
        shutil.copy(globvars.gameini_customconfig_files[inst], globvars.gameini_final_file)
    else:
        shutil.copy(globvars.gameini_baseconfig_file, globvars.gameini_final_file)
    chown(str(globvars.gameini_final_file), 1001, 1005)
    chown(str(globvars.gusini_final_file), 1001, 1005)
    log.debug(f'Server {inst} built and updated config files')

@asynctimeit
@log.catch
async def asyncrestartinstnow(inst, startonly=False):
    checkdirs(inst)
    if not startonly:
        await asyncwipeit(inst, extra=True)
        await asyncio.sleep(5)
        await asyncserverexec(['arkmanager', 'stop', '--saveworld', f'@{inst}'])
        log.log('UPDATE', f'Instance [{inst.title()}] has stopped, backing up world data...')
        await db.update(f"UPDATE instances SET isup = 0, isrunning = 0, islistening = 0 WHERE name = '{inst}'")
    await asyncserverexec(['arkmanager', 'backup', f'@{inst}'])
    if not await asyncisinstanceenabled(inst):
        log.log('UPDATE', f'Instance [{inst.title()}] remaining off because not enabled.')
        await asyncunsetstartbit(inst)
    elif serverneedsrestart() and inst != 'coliseum' and inst != 'crystal' and not startonly:
        await db.update(f"UPDATE instances SET restartserver = False WHERE name = '{inst.lower()}'")
        log.log('MAINT', f'REBOOTING Server [{hstname.upper()}] for maintenance server reboot')
        await asyncserverexec(['reboot'])
    else:
        log.log('UPDATE', f'Instance [{inst.title()}] has backed up world data, building config...')
        installconfigs(inst)
        log.log('UPDATE', f'Instance [{inst.title()}] is updating from staging directory')
        await asyncserverexec(['arkmanager', 'update', '--force', '--no-download', '--update-mods', '--no-autostart', f'@{inst}'])
        await db.update(f"UPDATE instances SET isrunning = 1 WHERE name = '{inst}'")
        log.log('UPDATE', f'Instance [{inst.title()}] is starting')
        await asyncresetlastrestart(inst)
        await asyncunsetstartbit(inst)
        await asyncplayerrestartbit(inst)
        await asyncserverexec(['arkmanager', 'start', f'@{inst}'])
        globvars.taskworkers.remove(f'{inst}-restarting')

@asynctimeit
@log.catch
async def asyncrestartloop(inst, startonly=False):
    checkdirs(inst)
    log.debug(f'{inst} restart loop has started')
    if startonly:
        await asyncrestartinstnow(inst, startonly=True)
    instdata = await db.fetchone(f"SELECT * from instances WHERE name = '{inst}'")
    timeleft = int(instdata['restartcountdown'])
    reason = instdata['restartreason']
    if instdata['connectingplayers'] == 0 and instdata['activeplayers'] == 0 and len(await asyncgetonlineplayers(inst)) == 0:
        await asyncsetrestartbit(inst)
        log.log('UPDATE', f'Server [{inst.title()}] is empty and restarting now for a [{reason}]')
        await asyncwritechat(inst, 'ALERT', f'!!! Empty server restarting now for a {reason.capitalize()}', wcstamp())
        message = f'server {inst.capitalize()} is restarting now for a {reason}'
        await asyncserverexec(['arkmanager', f'notify "{message}"', f'@{inst}'])
        pushoverthread('Instance Restart', message)
        await asyncrestartinstnow(inst)
    if reason != 'configuration update':
        await asyncsetrestartbit(inst)
        if timeleft == 30:
            log.log('UPDATE', f'Starting 30 min restart countdown for [{inst.title()}] for a [{reason}]')
            await asyncwritechat(inst, 'ALERT', f'!!! Server will restart in 30 minutes for a {reason.capitalize()}', wcstamp())
        else:
            log.log('UPDATE', f'Resuming {timeleft} min retart countdown for [{inst.title()}] for a [{reason}]')
        while await asyncstillneedsrestart(inst) and await len(await asyncgetplayersonline(inst)) != 0 and timeleft != 0 and await asyncgetliveplayersonline(inst)['activeplayers'] != 0:
            if timeleft == 30 or timeleft == 15 or timeleft == 10 or timeleft == 5 or timeleft == 1:
                log.log('UPDATE', f'{timeleft} min broadcast message sent to [{inst.title()}]')
                bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="1,0,0,1">                 The server has an update and needs to restart</>\n                       Restart reason: <RichColor Color="0,1,0,1">{reason}</>\n\n<RichColor Color="1,1,0,1">                   The server will be restarting in</><RichColor Color="1,0,0,1">{timeleft}</><RichColor Color="1,1,0,1"> minutes</>"""
                await asyncserverbcast(inst, bcast)
            await asyncio.sleep(Secs['1min'])
            timeleft = timeleft - 1
            await asyncupdatetimer(inst, timeleft)
        if await asyncstillneedsrestart(inst):
            log.log('UPDATE', f'Server [{inst.title()}] is restarting now for a [{reason}]')
            message = f'server {inst.capitalize()} is restarting now for a {reason}'
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="1,0,0,1">                 The server has an update and needs to restart</>\n                       Restart reason: <RichColor Color="0,1,0,1">Ark Game Update</>\n\n<RichColor Color="1,1,0,1">                     !! THE SERVER IS RESTARTING</><RichColor Color="1,0,0,1">NOW</><RichColor Color="1,1,0,1"> !!</>\n\n     The server will be back up in 10 minutes, you can check status in Discord"""
            await asyncserverbcast(inst, bcast)
            await asyncwritechat(inst, 'ALERT', f'!!! Server restarting now for {reason.capitalize()}', wcstamp())
            await asyncservernotify(inst, message)
            pushoverthread('Instance Restart', message)
            await asyncio.sleep(10)
            await asyncrestartinstnow(inst)
        else:
            log.warning(f'server restart on {inst} has been canceled from forced cancel')
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n\n<RichColor Color="1,1,0,1">                    The server restart has been cancelled!</>"""
            await asyncserverbcast(inst, bcast)
            await asyncwritechat(inst, 'ALERT', f'!!! Server restart for {reason.capitalize()} has been canceled', wcstamp())
    else:
        log.debug(f'configuration restart skipped because {splayers} players and {aplayers} active players')

@asynctimeit
@log.catch
async def asyncmaintenance():
    t, s, e = datetime.now(), dt(int(maint_hour), 0), dt(int(maint_hour) + 1, 0)
    inmaint = is_time_between(t, s, e)
    if inmaint and await asyncgetlastmaint(hstname) < Now(fmt='dtd') and f'{inst}-maintenance' not in globvars.taskworkers:
        globvars.taskworkers.append[f'{inst}-maintenance']
        await asyncsetlastmaint(hstname)
        log.log('MAINT', f'Daily maintenance window has opened for server [{hstname.upper()}]...')
        for inst in instances:
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="0,1,0,1">           Daily server maintenance has started (4am EST/8am GMT)</>\n\n<RichColor Color="1,1,0,1">    All dino mating will be toggled off, and all unclaimed dinos will be cleared</>\n<RichColor Color="1,1,0,1">            The server will also be performing updates and backups</>"""
            await asyncserverbcast(inst, bcast)
        log.log('MAINT', f'Running server os maintenance on [{hstname.upper()}]...')
        log.debug(f'OS update started for {hstname}')
        await asyncserverexec(['apt', 'update'])
        log.debug(f'OS upgrade started for {hstname}')
        await asyncserverexec(['apt', 'upgrade', '-y'])
        log.debug(f'OS autoremove started for {hstname}')
        await asyncserverexec(['apt', 'autoremove', '-y'])
        if serverneedsrestart():
            log.warning(f'[{hstname.upper()}] server needs a hardware reboot after package updates')
        for inst in instances:
            checkdirs(inst)
            if serverneedsrestart():
                await db.update(f"UPDATE instances SET restartserver = True WHERE name = '{inst.lower()}'")
            try:
                log.log('MAINT', f'Performing a world data save on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'saveworld', f'@{inst}'])
                await asyncio.sleep(30)
                log.log('MAINT', f'Backing up server instance and archiving old players [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'backup', f'@{inst}'])
                # sleep(30)
                # log.debug(f'Archiving player and tribe data on [{inst.title()}]...')
                # os.system('find /home/ark/ARK/ShooterGame/Saved/%s-data/ -maxdepth 1 -mtime +90 ! -path "*/ServerPaintingsCache/*" -path /home/ark/ARK/ShooterGame/Saved/%s-data/archive -prune -exec mv "{}" /home/ark/ARK/ShooterGame/Saved/%s-data/archive \;' % (inst, inst, inst))
                await asyncio.sleep(30)
                log.log('MAINT', f'Running all dino and map maintenance on server [{inst.title()}]...')
                log.debug(f'Shutting down dino mating on {inst}...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'ScriptCommand MatingOff_DS', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all unclaimed dinos on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'ScriptCommand DestroyUnclaimed_DS', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all wild wyvern eggs on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsWyvern_C', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all wild Deinonychus eggs on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsDeinonychus_C', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all wild drake eggs on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_RockDrake_NoPhysics_C', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all beehives on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'Destroyall BeeHive_C', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all wild Deinonychus eggs on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsDeinonychus_C', f'@{inst}'])
                await asyncio.sleep(30)
                log.debug(f'Clearing all beaver dams on [{inst.title()}]...')
                await asyncserverexec(['arkmanager', 'rconcmd', 'destroyall BeaverDam_C', f'@{inst}'])
                await asyncio.sleep(30)
                await asynccheckwipe(inst)
                lstsv = await asyncgetlastrestart(inst)
                eventreboot = await asynciseventrebootday()
                if eventreboot:
                    maintrest = f"{eventreboot}"
                    globvars.taskworkers.remove(f'{inst}-maintenance')
                    await asyncinstancerestart(inst, maintrest)
                elif Now() - float(lstsv) > Secs['3day'] or await asyncgetcfgver(inst) < await asyncgetpendingcfgver(inst):
                    maintrest = "maintenance restart"
                    globvars.taskworkers.remove(f'{inst}-maintenance')
                    await asyncinstancerestart(inst, maintrest)
                else:
                    message = 'Server maintenance has ended. No restart needed. If you had dinos mating right now you will need to turn it back on.'
                    globvars.taskworkers.remove(f'{inst}-maintenance')
                    await asyncserverchat(inst, message)
            except:
                log.exception(f'Error during {inst} instance daily maintenance')
                globvars.taskworkers.remove(f'{inst}-maintenance')
        log.log('MAINT', f'Daily maintenance has ended for [{hstname.upper()}]')

@asynctimeit
@log.catch
async def asyncinstancerestart(inst, reason, startonly=False):
    checkdirs(inst)
    log.debug(f'instance restart verification starting for {inst}')
    if f'{inst}-restarting' not in globvars.taskworkers:
        await db.update(f"UPDATE instances SET restartreason = '{reason}' WHERE name = '{inst}'")
        globvars.taskworkers.append(f'{inst}-restarting')
        asyncio.create_task(restartloop(inst, startonly))
    else:
        log.debug(f'skipping start/restart for {inst} because restart thread already running')

@log.catch
async def asyncisnewarkver(inst):
    try:
        isarkupd = await asyncserverexec(['arkmanager', 'checkupdate', f'@{inst}'], wait=True)
        for each in isarkupd['stdout'].decode('utf-8').split('\n'):
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
    except:
        return False, False, False

@asynctimeit
@log.catch
async def asyncperformbackup(inst):
    await asyncio.sleep(random.randint(1, 5) * 6)
    log.log('MAINT', f'Performing a world data backup on [{inst.title()}]')
    await asyncserverexec(['arkmanager', 'backup', f'@{inst}'])

@asynctimeit
@log.catch
async def asynccheckbackup():
    for inst in instances:
        checkdirs(inst)
        if f'{inst}-restarting' not in globvars.taskworkers:
            lastrestart = await asyncgetlastrestart(inst)
            lt = Now() - float(lastrestart)
            if (lt > 21600 and lt < 21900) or (lt > 43200 and lt < 43500) or (lt > 64800 and lt < 65100):
                asyncio.create_task(asyncperformbackup(inst))


@log.catch
async def asynccheckifenabled(inst):
    instdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if serverneedsrestart():
        await db.update(f"UPDATE instances SET restartserver = True WHERE name = '{inst.lower()}'")
    if instdata['enabled'] and instdata['isrunning'] == 0 and f'{inst}-restarting' not in globvars.taskworkers:
        log.log('MAINT', f'Instance [{inst.title()}] is set to [enabled]. Starting server')
        restartinstnow(inst, startonly=True)
    elif not instdata['enabled'] and instdata['isrunning'] == 1:
        if f'{inst}-restarting' not in globvars.taskworkers:
            log.warning(f'Instance [{inst.title()}] is set to [disabled]. Stopping server')
            await asyncinstancerestart(inst, 'admin restart')


@log.catch
async def asynccheckifalreadyrestarting(inst):
    instdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if instdata['needsrestart'] == "True":
        if f'{inst}-restarting' not in globvars.taskworkers:
            log.debug(f'restart flag set for instance {inst}, starting restart loop')
            globvars.append[f'{inst}-restarting']
            asyncio.create_task(restartloop(inst))


@asynctimeit
@log.catch
async def asynccheckupdates():
    global updgennotify
    if is_arkupdater == "True" and Now() - updgennotify > Secs['hour']:
        try:
            ustate, curver, avlver = await asyncisnewarkver('all')
            if not ustate:
                log.debug('ark update check found no ark updates available')
            else:
                updgennotify = Now()
                log.log('UPDATE', f'ARK update found ({curver}>{avlver}) downloading update.')
                await asyncserverexec(['arkmanager', 'update', '--downloadonly', f'@{instances[0]}'])
                log.debug('ark update downloaded to staging area')
                # msg = f'Ark update has been released. Servers will begin restart countdown now.\n\
# https://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes/'
                await asyncwritediscord('ARK Game Update', Now(), name='https://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes', server='UPDATE')
                msg = f'Ark Game Updare Released\nhttps://survivetheark.com/index.php?/forums/forum/5-changelog-patch-notes'
                log.log('UPDATE', f'ARK update download complete. Update is staged. Notifying servers')
                await db.update(f"UPDATE instances set needsrestart = 'True', restartreason = 'ark game update'")
                pushoverthread('Ark Update', msg)
        except:
            log.exception(f'error in determining ark version')

    for inst in instances:
        checkdirs(inst)
        if f'{inst}-restarting' not in globvars.taskworkers:
            ismodupdd = await asyncserverexec(['arkmanager', 'checkmodupdate', f'@{inst}'], wait=True)
            ismodupd = ismodupdd['stdout'].decode('utf-8')
            modchk = 0
            ismodupd = ismodupd.split('\n')
            for teach in ismodupd:
                if teach.find('has been updated') != -1 or teach.find('needs to be applied') != -1:
                    modchk += 1
                    al = teach.split(' ')
                    modid = al[1]
                    modname = al[2]
            if modchk != 0:
                log.log('UPDATE', f'ARK mod update [{modname}] id [{modid}] detected for instance [{inst.title()}]')
                log.debug(f'downloading mod updates for instance {inst}')
                await asyncserverexec(['arkmanager', 'update', '--downloadonly', '--update-mods', f'@{inst}'])
                log.debug(f'mod updates for instance {inst} download complete')
                aname = f'{modname} Mod Update'
                await asyncwritediscord(f'{modname} Mod Update', Now(), name=f'https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}', server='UPDATE')
                msg = f'{modname} Mod Update\nhttps://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}'
                pushoverthread('Mod Update', msg)
                await asyncinstancerestart(inst, aname)
        else:
            log.debug(f'no updated mods were found for instance {inst}')


@asynctimeit
@log.catch
async def asyncrestartcheck():
    for inst in instances:
        await asynccheckifenabled(inst)
        await asynccheckifalreadyrestarting(inst)


@log.catch
async def asyncupdaterloop():
    if len(instances) > 0:
        log.info(f'Found {len(instances)} ARK server instances: [{instr}]')
        global file_event_notifier
        #file_watch_manager = FSMonitorThread(callback=file_event)
        #file_watch_manager.add_dir_watch("/home/ark/shared/config")
    else:
        log.info(f'No ARK game instances found, running as [Master Bot]')

    while True:
        await asyncio.sleep(10)
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asyncrestartcheck()
        await asyncio.sleep(10)
        asyncio.create_task(asynccheckupdates())
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asyncmaintenance()
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asynccheckbackup()
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asyncrestartcheck()
        await asyncio.sleep(10)
        for inst in instances:
            if f'{inst}-restarting' not in globvars.taskworkers:
                await asynccheckwipe(inst)
        await asyncrestartcheck()
        await asyncio.sleep(10)
        await asyncrestartcheck()
    exit(0)


def main():
    print('start')
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(asyncupdaterloop(), debug=True)  # Async branch to main loop


main()
