import asyncio
import configparser
import random
import shutil
from datetime import datetime
from datetime import time as dt
from functools import partial
from os import chown

from loguru import logger as log
from timebetween import is_time_between

import globvars
from modules.asyncdb import DB as db
from modules.clusterevents import asynciseventrebootday, asyncgetcurrenteventext, asynciseventtime
from modules.configreader import hstname, is_arkupdater, maint_hour, sharedpath
from modules.discordbot import asyncwritediscord
from modules.instances import asyncgetlastrestart, asyncgetlastwipe, asyncisinstanceenabled, asyncwipeit
from modules.players import asyncgetliveplayersonline, asyncgetplayersonline
from modules.pushover import pushover
from modules.redis import instancestate, instancevar
from modules.servertools import (asyncserverbcast, asyncserverchat, asyncserverexec,
                                 asyncservernotify, serverneedsrestart)
from modules.timehelper import Now, Secs, wcstamp

# from fsmonitor import FSMonitorThread

confupdtimer = 0
updgennotify = Now() - Secs['hour']


"""
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
        await redis.sadd(f'{inst}-states', 'cfgupdate')
        if f'{inst}-restarting' not in redis.smembers(f'{inst}-states'):
            log.log('UPDATE', f'Config update detected for [{inst.title()}]')
            har = int(getcfgver(inst))
            setpendingcfgver(inst, har + 1)
        if getcfgver(inst) < getpendingcfgver(inst):
            maintrest = "configuration update"
            await asyncinstancerestart(inst, maintrest)
"""


async def pushoversend(title, message):
    asyncloop = asyncio.get_running_loop()
    await asyncloop.run_in_executor(None, partial(pushover, title, message))


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


async def asyncupdatetimer(inst, ctime):
    await db.update(f"UPDATE instances SET restartcountdown = '{ctime}' WHERE name = '{inst}'")


async def asyncsetcfgver(inst, cver):
    await db.update(f"UPDATE instances SET cfgver = {int(cver)} WHERE name = '{inst}'")


async def asyncsetpendingcfgver(inst, cver):
    await db.update(f"UPDATE instances SET pendingcfg = {int(cver)} WHERE name = '{inst}'")


async def asyncgetcfgver(inst):
    cfgver = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return int(cfgver['cfgver'])


async def asyncgetlastmaint(svr):
    lastmaint = await db.fetchone(f"SELECT * FROM lastmaintenance WHERE name = '{svr.upper()}'")
    return lastmaint['lastmaint']


async def asyncsetlastmaint(svr):
    await db.update(f"UPDATE lastmaintenance SET lastmaint = '{Now(fmt='dtd')}' WHERE name = '{svr.upper()}'")


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


async def asynccheckwipe(instances):
    global dwtimer
    for inst in instances:
        log.trace(f'running checkwipe for {inst}')
        lastwipe = await asyncgetlastwipe(inst)
        if Now() - lastwipe > Secs['12hour'] and await instancevar.getbool(inst, 'islistening'):
            oplayers = await asyncgetliveplayersonline(inst)
            if oplayers['activeplayers'] == 0 and len(await asyncgetplayersonline(inst)) == 0:
                log.log('WIPE', f'Dino wipe needed for [{inst.title()}], server is empty, wiping now')
                await asyncwritechat(inst, 'ALERT', f'### Empty server is over 12 hours since wild dino wipe. Wiping now.', wcstamp())
                asyncio.create_task(asyncwipeit(inst))
                await instancevar.set(inst, 'last12hourannounce', Now())
            else:
                if Now() - await instancevar.getint(inst, 'last12hourannounce') > 3600:
                    await instancevar.set(inst, 'last12hourannounce', Now())
                    log.log('WIPE', f'12 Hour dino wipe needed for [{inst.title()}], but players are online. Waiting...')
                    bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="1,0.65,0,1">         It has been 12 hours since this server has had a wild dino wipe</>\n\n<RichColor Color="1,1,0,1">               Consider doing a</><RichColor Color="0,1,0,1">!vote </><RichColor Color="1,1,0,1">for fresh new dino selection</>\n\n<RichColor Color="0.65,0.65,0.65,1">     A wild dino wipe does not affect tame dinos that are already knocked out</>"""
                    await asyncserverbcast(inst, bcast)
        elif Now() - lastwipe > Secs['day'] and await instancevar.getbool(inst, 'islistening'):
            log.log('WIPE', f'Dino wipe needed for [{inst.title()}], players online but forced, wiping now')
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="1,0.65,0,1">         It has been 24 hours since this server has had a wild dino wipe</>\n\n<RichColor Color="1,1,0,1">               Forcing a maintenance wild dino wipe in 10 seconds</>\n\n<RichColor Color="0.65,0.65,0.65,1">     A wild dino wipe does not affect tame dinos that are already knocked out</>"""
            await asyncserverbcast(inst, bcast)
            await asyncio.sleep(10)
            await asyncwritechat(inst, 'ALERT', f'### Server is over 24 hours since wild dino wipe. Forcing wipe now.', wcstamp())
            asyncio.create_task(asyncwipeit(inst))
            dwtimer = 0
        else:
            log.trace(f'no dino wipe is needed for {inst}')


async def asyncstillneedsrestart(inst):
    instdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if instdata['needsrestart'] == "True":
        return True
    else:
        return False


@log.catch
async def installconfigs(inst):
    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(globvars.gusini_baseconfig_file)
    if globvars.gusini_customconfig_files[inst].exists():
        gusbuildfile = globvars.gusini_customconfig_files[inst].read_text().split('\n')
        for each in gusbuildfile:
            a = each.split(',')
            if len(a) == 3:
                config.set(a[0], a[1], a[2])
    else:
        log.debug(f'No custom config found for {inst}')

    if await asynciseventtime():
        globvars.gusini_event_file = sharedpath / 'config/GameUserSettings-{eventext.strip()}.ini'
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
    if globvars.gameini_customconfig_files[inst].exists():
        shutil.copy(globvars.gameini_customconfig_files[inst], globvars.gameini_final_file)
    else:
        shutil.copy(globvars.gameini_baseconfig_file, globvars.gameini_final_file)
    chown(str(globvars.gameini_final_file), 1001, 1005)
    chown(str(globvars.gusini_final_file), 1001, 1005)
    log.debug(f'Server {inst} built and updated config files')


@log.catch
async def asyncrestartinstnow(inst, startonly=False):
    checkdirs(inst)
    if not startonly:
        await asyncwipeit(inst)
        await asyncio.sleep(5)
        await asyncserverexec(['arkmanager', 'stop', '--saveworld', f'@{inst}'], _wait=True)
        log.log('UPDATE', f'Instance [{inst.title()}] has stopped, backing up world data...')
        await db.update(f"UPDATE instances SET isup = 0, isrunning = 0, islistening = 0 WHERE name = '{inst}'")
    await asyncserverexec(['arkmanager', 'backup', f'@{inst}'], _wait=True)
    if not await asyncisinstanceenabled(inst):
        log.log('UPDATE', f'Instance [{inst.title()}] remaining off because not enabled.')
        await asyncunsetstartbit(inst)
    elif serverneedsrestart() and inst != 'coliseum' and inst != 'crystal' and not startonly:
        await db.update(f"UPDATE instances SET restartserver = False WHERE name = '{inst.lower()}'")
        log.log('MAINT', f'REBOOTING Server [{hstname.upper()}] for maintenance server reboot')
        await instancestate.set(inst, 'restarting')
        await instancestate.unset(inst, 'updating', 'updatewaiting', 'restartwaiting', 'cfgupdate', 'maintenance')
        await instancevar.mset(inst, {'isrunning': 0, 'isonline': 0, 'islistening': 0})
        await asyncserverexec(['reboot'])
    else:
        log.log('UPDATE', f'Instance [{inst.title()}] has backed up world data, building config...')
        await installconfigs(inst)
        log.log('UPDATE', f'Instance [{inst.title()}] is updating from staging directory')
        await asyncserverexec(['arkmanager', 'update', '--force', '--no-download', '--update-mods', '--no-autostart', f'@{inst}'], _wait=True)
        await db.update(f"UPDATE instances SET isrunning = 1 WHERE name = '{inst}'")
        await asyncio.sleep(1)
        await asyncserverexec(['arkmanager', 'start', f'@{inst}'], _wait=True)
        log.log('UPDATE', f'Instance [{inst.title()}] is starting')
        await instancestate.set(inst, 'restarting')
        await instancestate.unset(inst, 'updating', 'updatewaiting', 'restartwaiting', 'cfgupdate', 'maintenance')
        await instancevar.mset(inst, {'isrunning': 1, 'isonline': 0, 'islistening': 0})
        await asyncresetlastrestart(inst)
        await asyncunsetstartbit(inst)
        await asyncplayerrestartbit(inst)
        await db.update(f"UPDATE instances SET isrunning = 1 WHERE name = '{inst}'")


@log.catch
async def asyncrestartloop(inst, startonly=False):
    checkdirs(inst)
    if not await instancestate.check(inst, 'restartwaiting') and not await instancestate.check(inst, 'restarting'):
        log.debug(f'{inst} restart loop has started')
        if startonly:
            asyncio.create_task(asyncrestartinstnow(inst, startonly=True))
        asyncio.sleep(1)
        if not await instancestate.check(inst, 'restartwaiting') and not await instancestate.check(inst, 'restarting'):
            instdata = await db.fetchone(f"SELECT * from instances WHERE name = '{inst}'")
            timeleft = int(instdata['restartcountdown'])
            reason = instdata['restartreason']
            if await instancevar.getint(inst, 'playersconnected') == 0 and await instancevar.getint(inst, 'playersactive') == 0 and await instancevar.getint(inst, 'playersonline') == 0:
                await instancestate.set(inst, 'restartwaiting')
                await asyncsetrestartbit(inst)
                log.log('UPDATE', f'Server [{inst.title()}] is empty and restarting now for a [{reason}]')
                await asyncwritechat(inst, 'ALERT', f'!!! Empty server restarting now for a {reason.capitalize()}', wcstamp())
                message = f'server {inst.capitalize()} is restarting now for a {reason}'
                await asyncserverexec(['arkmanager', f'notify "{message}"', f'@{inst}'])
                await pushoversend('Instance Restart', message)
                asyncio.create_task(asyncrestartinstnow(inst))
                await asyncio.sleep(1)
            if reason != 'configuration update' and not await instancestate.check(inst, 'restartwaiting') and not await instancestate.check(inst, 'restarting'):
                await asyncsetrestartbit(inst)
                if timeleft == 30:
                    log.log('UPDATE', f'Starting 30 min restart countdown for [{inst.title()}] for a [{reason}]')
                    await asyncwritechat(inst, 'ALERT', f'!!! Server will restart in 30 minutes for a {reason.capitalize()}', wcstamp())
                else:
                    log.log('UPDATE', f'Resuming {timeleft} min retart countdown for [{inst.title()}] for a [{reason}]')
                await instancestate.set(inst, 'restartwaiting')
                while await asyncstillneedsrestart(inst) and await instancevar.getint(inst, 'playersactive') != 0 and timeleft != 0 and await instancevar.getint(inst, 'playersonline') != 0:
                    if timeleft == 30 or timeleft == 15 or timeleft == 10 or timeleft == 5 or timeleft == 1:
                        log.log('UPDATE', f'{timeleft} min broadcast message sent to [{inst.title()}]')
                        bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="1,0,0,1">                 The server has an update and needs to restart</>\n                       Restart reason: <RichColor Color="0,1,0,1">{reason}</>\n\n<RichColor Color="1,1,0,1">                   The server will be restarting in</><RichColor Color="1,0,0,1">{timeleft}</><RichColor Color="1,1,0,1"> minutes</>"""
                        await asyncserverbcast(inst, bcast)
                    await asyncio.sleep(Secs['1min'])
                    timeleft = timeleft - 1
                    if await instancevar.getint(inst, 'playersonline') == 0 and await instancevar.getint(inst, 'playersactive') == 0:
                        timeleft = 0
                    await asyncupdatetimer(inst, timeleft)
                if await asyncstillneedsrestart(inst):
                    log.log('UPDATE', f'Server [{inst.title()}] is restarting now for a [{reason}]')
                    message = f'server {inst.capitalize()} is restarting now for a {reason}'
                    bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="1,0,0,1">                 The server has an update and needs to restart</>\n                       Restart reason: <RichColor Color="0,1,0,1">Ark Game Update</>\n\n<RichColor Color="1,1,0,1">                     !! THE SERVER IS RESTARTING</><RichColor Color="1,0,0,1">NOW</><RichColor Color="1,1,0,1"> !!</>\n\n     The server will be back up in 10 minutes, you can check status in Discord"""
                    await asyncserverbcast(inst, bcast)
                    await asyncwritechat(inst, 'ALERT', f'!!! Server restarting now for {reason.capitalize()}', wcstamp())
                    await asyncservernotify(inst, message)
                    await pushoversend('Instance Restart', message)
                    await asyncio.sleep(10)
                    asyncio.create_task(asyncrestartinstnow(inst))
                else:
                    log.warning(f'server restart on {inst} has been canceled from forced cancel')
                    bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n\n<RichColor Color="1,1,0,1">                    The server restart has been cancelled!</>"""
                    await instancestate.unset(inst, 'restartwaiting')
                    await asyncserverbcast(inst, bcast)
                    await asyncwritechat(inst, 'ALERT', f'!!! Server restart for {reason.capitalize()} has been canceled', wcstamp())
            elif reason == 'configuration update' and not await instancestate.check(inst, 'restartwaiting') and not await instancestate.check(inst, 'restarting'):
                log.debug(f'configuration restart skipped because of active players')


@log.catch
async def asynccheckmaint(instances):
    t, s, e = datetime.now(), dt(int(maint_hour), 0), dt(int(maint_hour) + 1, 0)
    inmaint = is_time_between(t, s, e)
    maint = False
    for inst in instances:
        if inmaint and await asyncgetlastmaint(hstname) < Now(fmt='dtd') and not await instancestate.check(inst, 'maintenance'):
            log.log('MAINT', f'Daily maintenance window has opened for server [{hstname.upper()}]...')
            maint = True
    if maint:
        for inst in instances:
            await instancestate.set(inst, 'maintenance')
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n\n<RichColor Color="0,1,0,1">           Daily server maintenance has started (4am EST/8am GMT)</>\n\n<RichColor Color="1,1,0,1">    All dino mating will be toggled off, and all unclaimed dinos will be cleared</>\n<RichColor Color="1,1,0,1">            The server will also be performing updates and backups</>"""
            await asyncserverbcast(inst, bcast)
        await asyncsetlastmaint(hstname)
        log.log('MAINT', f'Running server os maintenance on [{hstname.upper()}]...')
        log.debug(f'OS update started for {hstname}')
        await asyncserverexec(['apt', 'update'], _wait=True)
        log.debug(f'OS upgrade started for {hstname}')
        await asyncserverexec(['apt', 'upgrade', '-y'], _wait=True)
        log.debug(f'OS autoremove started for {hstname}')
        await asyncserverexec(['apt', 'autoremove', '-y'], _wait=True)
        for inst in instances:
            if await instancevar.getbool(inst, 'islistening'):
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
                    await asyncwipeit(inst, dinos=False, eggs=True, dams=True, mating=True, bees=False)
                    await asyncio.sleep(30)
                    lstsv = await asyncgetlastrestart(inst)
                    eventreboot = await asynciseventrebootday()
                    if eventreboot:
                        maintrest = f"{eventreboot}"
                        await asyncinstancerestart(inst, maintrest)
                    elif Now() - int(lstsv) > Secs['3day'] or await asyncgetcfgver(inst) < await asyncgetpendingcfgver(inst):
                        maintrest = "maintenance restart"
                        await asyncinstancerestart(inst, maintrest)
                    else:
                        message = 'Server maintenance has ended. No restart needed. If you had dinos mating right now you will need to turn it back on.'
                        await asyncserverchat(inst, message)
                except:
                    log.exception(f'Error during {hstname} instance daily maintenance')
                finally:
                    await instancestate.unset(inst, 'maintenance')
        await asynccheckwipe(instances)
        if serverneedsrestart():
            log.warning(f'[{hstname.upper()}] server needs a hardware reboot after package updates')
        log.log('MAINT', f'Daily maintenance has ended for [{hstname.upper()}]')
    else:
        log.trace(f'no maintenance needed, not in maintenance time window')


@log.catch
async def asyncinstancerestart(inst, reason, startonly=False):
    checkdirs(inst)
    log.debug(f'instance restart verification starting for {inst}')
    if not await instancestate.check(inst, 'restarting') or not await instancestate.check(inst, 'restartwaiting'):
        await db.update(f"UPDATE instances SET restartreason = '{reason}' WHERE name = '{inst}'")
        asyncio.create_task(asyncrestartloop(inst, startonly))
    else:
        log.debug(f'skipping start/restart for {inst} because restart already running')


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


@log.catch
async def asyncperformbackup(inst):
    await asyncio.sleep(random.randint(1, 5) * 6)
    log.log('MAINT', f'Performing a world data backup on [{inst.title()}]')
    await asyncserverexec(['arkmanager', 'backup', f'@{inst}'])


@log.catch
async def asynccheckbackup(instances):
    for inst in instances:
        checkdirs(inst)
        lastrestart = await asyncgetlastrestart(inst)
        lt = Now() - float(lastrestart)
        if (lt > 21600 and lt < 21900) or (lt > 43200 and lt < 43500) or (lt > 64800 and lt < 65100):
            asyncio.create_task(asyncperformbackup(inst))
        else:
            log.trace(f'no backups needed for {inst}')


@log.catch
async def asynccheckifenabled(inst):
    pass
    instdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if serverneedsrestart():
        await db.update(f"UPDATE instances SET restartserver = True WHERE name = '{inst.lower()}'")
    if instdata['enabled'] and instdata['isrunning'] == 0 and not await instancestate.check(inst, 'restartwaiting') and not await instancestate.check(inst, 'restarting'):
        log.log('MAINT', f'Instance [{inst.title()}] is not running and set to [enabled]. Starting server')
        asyncio.create_task(asyncrestartinstnow(inst, startonly=True))
    elif not instdata['enabled'] and instdata['isrunning'] == 1 and not await instancestate.check(inst, 'restartwaiting'):
        log.warning(f'Instance [{inst.title()}] is running and set to [disabled]. Stopping server')
        await asyncinstancerestart(inst, 'admin restart')


@log.catch
async def asynccheckifalreadyrestarting(inst):
    instdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if instdata['needsrestart'] == "True":
        if not await instancestate.check(inst, 'restartwaiting') and not await instancestate.check(inst, 'restarting'):
            log.debug(f'restart flag set for instance {inst}, starting restart loop')
            asyncio.create_task(asyncrestartloop(inst))
        else:
            log.trace(f'instance {inst} trying to restart but already restarting')
    else:
        log.trace(f'instace {inst} does not need a restart')


@log.catch
async def asynccheckupdates(instances):
    global updgennotify
    if is_arkupdater == "True" and Now() - updgennotify > Secs['hour']:
        log.trace('running updatecheck for {hstname}')
        try:
            ustate, curver, avlver = await asyncisnewarkver('all')
            if not ustate:
                log.trace('ark update check found no ark updates available')
            else:
                for inst in instances:
                    await instancestate.set(inst, 'updating')
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
                await instancestate.set(inst, "updatewaiting")
                await instancestate.unset(inst, "updating")
                await pushoversend('Ark Update', msg)
        except:
            log.exception(f'error in determining ark version')

    for inst in instances:
        checkdirs(inst)
        ismodupdd = await asyncserverexec(['arkmanager', 'checkmodupdate', f'@{inst}'], wait=True)  # #############
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
            await instancestate.set(inst, "updating")
            log.log('UPDATE', f'ARK mod update [{modname}] id [{modid}] detected for instance [{inst.title()}]')
            log.debug(f'downloading mod updates for instance {inst}')
            await asyncserverexec(['arkmanager', 'update', '--downloadonly', '--update-mods', f'@{inst}'])
            log.debug(f'mod updates for instance {inst} download complete')
            aname = f'{modname} Mod Update'
            await asyncwritediscord(f'{modname} Mod Update', Now(), name=f'https://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}', server='UPDATE')
            msg = f'{modname} Mod Update\nhttps://steamcommunity.com/sharedfiles/filedetails/changelog/{modid}'
            await pushoversend('Mod Update', msg)
            await instancestate.unset(inst, 'updating')
            await instancestate.set(inst, "updatewaiting")
            await asyncinstancerestart(inst, aname)
        else:
            log.trace(f'no updated mods were found for instance {inst}')


@log.catch
async def asynccheckrestart(instances):
    for inst in instances:
        log.trace(f'running restartcheck for {inst}')
        await asynccheckifenabled(inst)
        await asynccheckifalreadyrestarting(inst)
