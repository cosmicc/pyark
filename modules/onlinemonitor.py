import asyncio
import threading
import time

from loguru import logger as log

from modules.asyncdb import DB as db
from modules.clusterevents import asynciseventtime, getcurrenteventinfo, iseventtime
from modules.dbhelper import cleanstring, dbquery, dbupdate
from modules.players import getplayer, newplayer
from modules.servertools import asyncserverchat, asyncserverchatto, asyncserverexec, asyncserverscriptcmd, serverexec, asynctimeit, asyncserverrconcmd
from modules.timehelper import Now, elapsedTime, playedTime

onlineworkers = []
welcomthreads = []
greetings = []


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
def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,), fetch='one')
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                 (inst, whos, msg, tstamp))


@log.catch
def iswelcoming(steamid):
    for each in welcomthreads:
        if each['steamid'] == steamid:
            if each['sthread'].is_alive():
                return True
            else:
                return False


@log.catch
def isgreeting(steamid):
    for each in greetthreads:
        if each['steamid'] == steamid:
            if each['gthread'].is_alive():
                return True
            else:
                return False


@log.catch
async def asyncserverisinrestart(steamid, inst, player):
    rbt = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if rbt[3] == "True":
        log.log('UPDATE', f'Notifying player [{player[1].title()}] that [{inst.title()}] will be restarting in {rbt[7]} min')
        mtxt = f'WARNING: server is restarting in {rbt[7]} minutes for a {rbt[5]}'
        await asyncserverchatto(inst, steamid, mtxt)


@log.catch
def isinlottery(steamid):
    isinlotto = dbquery("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'", fetch='one')
    if isinlotto:
        isinlotto2 = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (steamid,), fetch='one')
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
    global greetings
    xferpoints = 0
    if await asynccheckifbanned(steamid):
        log.warning(f'BANNED player [{steamname}] [{steamid}] has tried to connect or is online on [{inst.title()}]. kicking and banning.')
        await asyncserverrconcmd(inst, f'kickplayer {steamid}')
        # subprocess.run("""arkmanager rconcmd 'banplayer %s' @%s""" % (steamid, inst), shell=True)
    else:
        player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
        if not player:
            welcom = threading.Thread(name='welcoming-%s' % steamid, target=newplayer, args=(steamid, steamname, inst))
            welcom.start()
        else:
            if player['transferpoints'] != 0 and player['homeserver'] == inst:
                xferpoints = int(player[16])
                log.log('POINTS', f'Transferred {xferpoints} non-home server points for [{player[1].title()}] on [{inst.title()}]')
                await db.update(f"UPDATE players SET transferpoints = 0 WHERE steamid = '{steamid}'")
                await asyncserverscriptcmd(inst, f'tcsar addarctotal {steamid} {xferpoints}')
            if not player['welcomeannounce']:  # existing online player
                log.trace(f'Existing online player [{player[1].title()}] was found on [{inst.title()}]. updating info.')
                await db.update(f"UPDATE players SET online = True, lastseen = '{Now()}', server = '{inst}' WHERE steamid = '{steamid}'")
            else:  # new player connection
                log.debug(f'New online player [{player[1].title()}] was found on [{inst.title()}]. updating info.')
                await db.update(f"UPDATE players SET online = True, welcomeannounce = False, lastseen = '{Now()}', server = '{inst}', connects = {int(player[7]) + 1}, refreshauctions = True, refreshsteam = True WHERE steamid = '{steamid}'")
                laston = elapsedTime(Now(), int(player[2]))
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
                    await asyncio.sleep(5)
                    mtxt = f'Your player is not linked with a discord account yet. type !linkme in global chat'
                    await asyncserverchatto(inst, steamid, mtxt)
                if not isinlottery(steamid):
                    await asyncio.sleep(3)
                    mtxt = f'A lottery you have not entered yet is underway. Type !lotto for more information'
                    await asyncserverchatto(inst, steamid, mtxt)
            if xferpoints != 0:
                    await asyncio.sleep(2)
                    mtxt = f'{xferpoints} rewards points were transferred to you from other cluster servers'
                    await asyncserverchatto(inst, steamid, mtxt)
            await asynclottodeposits(player, inst)
            if int(player[2]) + 60 < Now():
                # mtxt = f'{oplayer[1].capitalize()} has joined the server'
                # serverexec(['arkmanager', 'rconcmd', f'ServerChat {mtxt}', f'@{inst}'], nice=19, null=True)
                # writechat(inst, 'ALERT', f'<<< {oplayer[1].capitalize()} has joined the server', wcstamp())
                await asyncserverisinrestart(steamid, inst, player)
                currentevent = await asynciseventtime()
                if currentevent:
                    await asyncio.sleep(2)
                    mtxt = f'{currentevent[4]} event is currently active!'
                    await asyncserverchatto(inst, steamid, mtxt)
                annc = await db.fetchone("SELECT announce FROM general")
                if annc and annc[0] is not None:
                    await asyncio.sleep(2)
                    mtxt = annc[0]
                    await asyncserverchatto(inst, steamid, mtxt)
    greetings.remove(steamid)


async def asynckickcheck(instances):
    global onlineworkers
    if 'kickcheck' not in onlineworkers:
        onlineworkers.append('kickcheck')
        for inst in instances:
            kicked = await db.fetchone(f"SELECT * FROM kicklist WHERE instance = '{inst}'")
            if kicked:
                serverexec(['arkmanager', 'rconcmd', f'kickplayer {kicked[1]}', f'@{inst}'], nice=10, null=True)
                log.log('KICK', f'Kicking user [{kicked[1].title()}] from server [{inst.title()}] on kicklist')
                await db.update(f"DELETE FROM kicklist WHERE steamid = '{kicked[1]}'")
        onlineworkers.remove('kickcheck')
        return True


async def asyncprocessline(inst, line):
    global greetings
    try:
        if line.startswith(('Running command', '"', ' "', 'Error:', '"No Players')):
            pass
        else:
            rawline = line.split(',')
            if len(rawline) > 1:
                steamid = rawline[1].strip()
                steamname = cleanstring(rawline[0].split('. ', 1)[1])
                if steamid not in greetings:
                    greetings.append(steamid)
                    asyncio.create_task(asyncplayergreet(steamid, steamname, inst))
                else:
                    log.debug(f'online player greeting aleady running for {steamname}')
            else:
                log.error(f'problem with parsing online player - {rawline}')
    except:
        log.exception('Exception in online monitor process line')


async def processplayerchunk(inst, chunk):
    global onlineworkers
    for line in iter(chunk.decode("utf-8").splitlines()):
        await asyncprocessline(inst, line)
    return True


async def asynconlinecheck(instances):
    global onlineworkers
    if 'onlinecheck' not in onlineworkers:
        onlineworkers.append('onlinecheck')
        for inst in instances:
            cmdpipe = await asyncserverexec(['arkmanager', 'rconcmd', 'ListPlayers', f'@{inst}'], wait=True)
            asyncio.create_task(processplayerchunk(inst, cmdpipe['stdout']))
        onlineworkers.remove('onlinecheck')
        return True
