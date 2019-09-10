import asyncio
from functools import partial

from loguru import logger as log

import globvars
from modules.asyncdb import DB as db
from modules.clusterevents import asynciseventtime
from modules.dbhelper import cleanstring
from modules.players import asyncnewplayer
from modules.servertools import asyncserverchatto, asyncserverrconcmd, asyncserverscriptcmd
from modules.timehelper import Now, elapsedTime, playedTime
from modules.subprotocol import SubProtocol


async def asyncstopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Online monitor thread has ended')
            exit(0)
        asyncio.sleep(1)


@log.catch
async def asyncresetplayerbit(steamid):
    await db.update(f"UPDATE players SET restartbit = 0 WHERE steamid = '{steamid}'")


@log.catch
async def asyncserverisinrestart(steamid, inst, player):
    rbt = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if rbt[3] == "True":
        log.log('UPDATE', f'Notifying player [{player[1].title()}] that [{inst.title()}] will be restarting in {rbt[7]} min')
        mtxt = f'WARNING: server is restarting in {rbt[7]} minutes for a {rbt[5]}'
        await asyncserverchatto(inst, steamid, mtxt)


@log.catch
async def asyncisinlottery(steamid):
    isinlotto = await db.fetchone("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'")
    if isinlotto:
        isinlotto2 = await db.fetchone(f"SELECT * FROM lotteryplayers WHERE steamid = '{steamid}'")
        if isinlotto2:
            return True
        else:
            return False
    else:
        return True


@log.catch
async def asynclottodeposits(player, inst):
    steamid = player["steamid"]
    lottocheck = await db.fetchall(f"""SELECT * FROM lotterydeposits WHERE steamid = '{steamid}'""")
    if lottocheck and inst == player[5]:
        for weach in lottocheck:
            if weach[4] == 1:
                log.log('POINTS', f'{weach[3]} lottery win points added to [{player[1].title()}]')
                msg = f'{weach[3]} Reward points have been deposited into your account for a lottery win!'
                await asyncserverchatto(inst, steamid, msg)
                scmd = f'tcsar addarctotal {steamid} {int(weach[3])}'
                await asyncserverscriptcmd(inst, scmd)
            elif weach[4] == 0:
                log.log('POINTS', f'{weach[3]} lottery entry points removed from [{player[1].title()}]')
                msg = f'{weach[3]} Reward points have been withdrawn from your account for a lottery entry'
                await asyncserverchatto(inst, steamid, msg)
                scmd = f'tcsar setarctotal {steamid} {int(player[5]) - int(weach[3])}'
                await asyncserverscriptcmd(inst, scmd)
        await db.update(f"DELETE FROM lotterydeposits WHERE steamid = '{steamid}'")


@log.catch
async def asynccheckifbanned(steamid):
    oplayer = await db.fetchone(f"SELECT steamid FROM players WHERE steamid = '{steamid}' AND banned != ''")
    bplayer = await db.fetchone(f"SELECT steamid FROM banlist WHERE steamid = '{steamid}'")
    if oplayer or bplayer:
        return True
    else:
        return False


@log.catch
async def asyncplayergreet(steamid, steamname, inst):
    xferpoints = 0
    log.debug(f'processing greeting for [{steamname}]')
    if await asynccheckifbanned(steamid):
        log.warning(f'BANNED player [{steamname}] [{steamid}] has tried to connect or is online on [{inst.title()}]. kicking and banning.')
        await asyncserverchatto(inst, steamid, 'You are not welcome here. Goodbye')
        await asyncio.sleep(3)
        await asyncserverrconcmd(inst, f'kickplayer {steamid}')
        # subprocess.run("""arkmanager rconcmd 'banplayer %s' @%s""" % (steamid, inst), shell=True)
    else:
        player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
        if not player:
            asyncio.create_task(asyncnewplayer(steamid, steamname, inst))
        else:
            if player['homeserver'] == inst:
                xfertable = await db.fetchall(f"""SELECT * FROM transferpoints WHERE steamid = '{player["steamid"]}'""")
                xferpoints = 0
                for each in xfertable:
                    xferpoints = xferpoints + int(each['points'])
                xferpoints = xferpoints + int(player['transferpoints'])
                await db.update(f"""UPDATE players SET transferpoints = 0 WHERE steamid = '{player["steamid"]}'""")
                if xferpoints != 0:
                    await db.update(f"""DELETE FROM transferpoints WHERE steamid = '{player["steamid"]}'""")
                    log.log('POINTS', f'Transferred {xferpoints} non-home server points for [{player[1].title()}] on [{inst.title()}]')
                    await asyncserverscriptcmd(inst, f'tcsar addarctotal {steamid} {xferpoints}')
            if player['homemovepoints'] != 0 and player['homeserver'] == inst:
                homemovepoints = int(player['homemovepoints'])
                log.log('POINTS', f'Transferred {homemovepoints} points for [{player[1].title()}] on [{inst.title()}] from a home server move')
                await db.update(f"UPDATE players SET homemovepoints = 0 WHERE steamid = '{steamid}'")
                await asyncserverscriptcmd(inst, f'tcsar addarctotal {steamid} {homemovepoints}')
            if not player['welcomeannounce']:  # existing online player
                log.trace(f'Existing online player [{player[1].title()}] was found on [{inst.title()}]. updating info.')
                await db.update(f"UPDATE players SET online = True, lastseen = '{Now()}', server = '{inst}' WHERE steamid = '{steamid}'")
            else:  # new player connection
                log.debug(f'New online player [{player[1].title()}] was found on [{inst.title()}]. updating info.')
                await db.update(f"UPDATE players SET online = True, welcomeannounce = False, lastseen = '{Now()}', server = '{inst}', connects = {int(player[7]) + 1}, refreshauctions = True, refreshsteam = True WHERE steamid = '{steamid}'")
                laston = elapsedTime(Now(), int(player['lastseen']))
                totplay = playedTime(int(player[4]))
                newpoints = int(player[5]) + xferpoints
                mtxt = f'Welcome back {player[1].title()}, you have {newpoints} reward points on {player[15].capitalize()}, last online {laston} ago, total time played {totplay}'
                await asyncserverchatto(inst, steamid, mtxt)
                await asyncio.sleep(1)
                serverplayers = await db.fetchall(f"SELECT * FROM players WHERE server = '{inst}' AND steamid != '{steamid}' AND online = True")
                playerlist = ''
                for splayer in serverplayers:
                    if playerlist == '':
                        playerlist = f'{splayer["playername"].title()}'
                    else:
                        playerlist = playerlist + f', {splayer["playername"].title()}'
                if len(serverplayers) != 0:
                    msg = f'There are {len(serverplayers)} other players online: {playerlist}'
                else:
                    msg = f'There are no other players are online on this server.'
                await asyncserverchatto(inst, steamid, msg)
                await asyncio.sleep(2)
                if int(player[14]) == 1 and int(player[13]) == 1 and player[3] == inst:
                    mtxt = f'WARNING: Server has restarted since you logged in, reset your primordials if they are not stored in a soul terminal'
                    await asyncserverchatto(inst, steamid, mtxt)
                    await asyncresetplayerbit(steamid)
                if player[8] == '':
                    await asyncio.sleep(3)
                    mtxt = f'Your player is not linked with a discord account yet. type !linkme in global chat'
                    await asyncserverchatto(inst, steamid, mtxt)
                if not await asyncisinlottery(steamid):
                    await asyncio.sleep(3)
                    mtxt = f'A lottery you have not entered yet is underway. Type !lotto for more information'
                    await asyncserverchatto(inst, steamid, mtxt)
                currentevent = await asynciseventtime()
                if currentevent:
                    await asyncio.sleep(3)
                    mtxt = f'{currentevent[4]} event is currently active!'
                    await asyncserverchatto(inst, steamid, mtxt)
                annc = await db.fetchone("SELECT announce FROM general")
                if annc and annc[0] is not None:
                    await asyncio.sleep(2)
                    mtxt = annc[0]
                    await asyncserverchatto(inst, steamid, mtxt)
            if xferpoints != 0:
                    await asyncio.sleep(5)
                    mtxt = f'{xferpoints} rewards points were transferred to you from other cluster servers'
                    await asyncserverchatto(inst, steamid, mtxt)
            if int(player['homemovepoints']) != 0:
                    await asyncio.sleep(5)
                    mtxt = f'{xferpoints} rewards points were transferred here from a home server move'
                    await asyncserverchatto(inst, steamid, mtxt)
            await asynclottodeposits(player, inst)
            await asyncserverisinrestart(steamid, inst, player)
    globvars.greetings.remove(steamid)


async def asynckickcheck(instances):
    if 'kickcheck' not in globvars.taskworkers:
        globvars.taskworkers.add('kickcheck')
        for inst in instances:
            if inst in globvars.isonline:
                kicked = await db.fetchone(f"SELECT * FROM kicklist WHERE instance = '{inst}'")
                if kicked:
                    await asyncserverrconcmd(inst, f'kickplayer {kicked[1]}')
                    log.log('KICK', f'Kicking user [{kicked[1]}] from server [{inst.title()}] on kicklist')
                    await db.update(f"DELETE FROM kicklist WHERE steamid = '{kicked[1]}'")
        globvars.taskworkers.remove('kickcheck')
        return True


@log.catch
async def asynconlinedblchecker(instances):
    if 'dblchecker' not in globvars.taskworkers:
        globvars.taskworkers.add('dblchecker')
        for inst in instances:
            if inst in globvars.islistening:
                log.trace(f'Running online doublechecker for {inst}')
                players = await db.fetchall(f"SELECT * FROM players WHERE online = True AND lastseen <= {Now() - 300} AND server = '{inst}'")
                for player in players:
                    log.warning(f'Player [{player["playername"].title()}] wasnt seen logging off [{inst.title()}] Clearing player from online status')
                    await db.update("UPDATE players SET online = False, welcomeannounce = True, refreshsteam = True, server = '%s' WHERE steamid = '%s'" % (player["server"], player["steamid"]))
                    if player['homeserver'] != inst:
                        command = f'tcsar setarctotal {player["steamid"]} 0'
                        await asyncserverscriptcmd(inst, command)
        globvars.taskworkers.remove('dblchecker')


@log.catch
async def asyncprocessonline(inst, eline):
    line = eline.decode().strip('\n "\n')
    print(f'ELINE: {eline}')
    print(f'LINE: {line}')
    if line.startswith(('Running command', '"', ' "', 'Error:')):
        pass
    elif line == 'No Players Connected':
        globvars.instplayers[inst]['online'] = 0
    else:
        lines = line.split('\n')
        players = 0
        for line in lines:
            players = players + 1
            rawline = line.split(',')
            if len(rawline) > 1:
                steamid = rawline[1].strip()
                steamname = cleanstring(rawline[0].split('. ', 1)[1])
                if steamid not in globvars.greetings and steamid not in globvars.welcomes:
                    globvars.greetings.add(steamid)
                    asyncio.create_task(asyncplayergreet(steamid, steamname, inst))
                else:
                    log.debug(f'online player greeting aleady running for {steamname}')
            else:
                log.error(f'problem with parsing online player - {rawline}')
        globvars.instplayers[inst]['online'] = players


async def onlineexecute(inst):
    asyncloop = asyncio.get_running_loop()
    cmd_done = asyncio.Future(loop=asyncloop)
    factory = partial(SubProtocol, cmd_done, inst, parsetask=asyncprocessonline)
    proc = asyncloop.subprocess_exec(factory, 'arkmanager', 'rconcmd', 'listplayers', f'@{inst}', stdin=None, stderr=None)
    try:
        transport, protocol = await proc
        await cmd_done
    finally:
        transport.close()


async def onlinecheck(instances):
    for inst in instances:
        asyncio.create_task(onlineexecute(inst))
