import asyncio
import random
from datetime import datetime, timedelta
from functools import partial
from time import time

from loguru import logger as log

import globvars
from modules.asyncdb import DB as db
from modules.dbhelper import cleanstring
from modules.gtranslate import trans_to_eng
from modules.instances import asyncgetinstancelist, asyncgetlastrestart, asyncgetlastwipe, asyncwipeit, homeablelist
from modules.lottery import asyncgetlastlotteryinfo
from modules.players import asyncnewplayer
from modules.redis import redis, instancestate, instancevar, globalvar
from modules.servertools import asyncserverbcast, asyncserverchat, asyncserverchatto, asyncserverscriptcmd
from modules.subprotocol import SubProtocol
from modules.timehelper import Now, Secs, datetimeto, elapsedTime, playedTime, wcstamp, truncate


async def asyncwriteglobal(inst, whos, msg):
    await db.update("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                    (inst, whos, msg, Now()))


async def asyncwritechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = await db.fetchone(f"SELECT * from players WHERE playername = '{whos}'", result='count')
        if isindb:
            await db.update("""INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')""" % (inst, whos, msg.replace("'", ""), tstamp))

    elif whos == "ALERT":
        await db.update("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


@log.catch
async def asyncwritechatlog(inst, whos, msg, tstamp):
    pass
    # steamid = await asyncgetsteamid(whos)
    # if steamid:
    # clog = f"""{tstamp} [{whos.upper()}]{msg}\n"""
    # if not os.path.exists(f'/home/ark/shared/logs/{inst}'):
    #    log.error(f'Log directory /home/ark/shared/logs/{inst} does not exist! creating')
    #    os.mkdir(f'/home/ark/shared/logs/{inst}', 0o777)
    #    os.chown(f'/home/ark/shared/logs/{inst}', 1001, 1005)
    # with aiofiles.open(f"/home/ark/shared/logs/{inst}/chat.log", "at") as f:
    #   await f.write(clog)
    # await f.close()


async def asyncgetsteamid(whoasked):
    player = await db.fetchone(f"SELECT * FROM players WHERE (playername = '{whoasked.lower()}') or (alias = '{whoasked.lower()}')")
    if player is None:
        log.critical(f'Player lookup failed! possible renamed player: {whoasked}')
        return None
    else:
        return player['steamid']


@log.catch
async def asyncresptimeleft(inst, whoasked):
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if insts['needsrestart'] == 'True':
        message = f'{inst.title()} is restarting in {insts["restartcountdown"]} minutes'
        await asyncserverchat(inst, message)
    else:
        message = f'{inst.title()} is not pending a restart'
        await asyncserverchat(inst, message)


@log.catch
async def asyncgetlastseen(seenname):
    player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{seenname}' ORDER BY lastseen DESC")
    if not player:
        return 'No player found with that name'
    else:
        plasttime = elapsedTime(Now(), float(player['lastseen']))
        if plasttime != 'now':
            return f'{player["playername"].title()} was last seen {plasttime} ago on {player["server"].title()}'
        else:
            return f'{player["playername"].title()} is online now on {player["server"].title()}'


@log.catch
async def asyncrespmyinfo(inst, whoasked):
    steamid = await asyncgetsteamid(whoasked)
    if steamid:
        player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{whoasked}' ORDER BY lastseen DESC")
        ptime = playedTime(player['playedtime'])
        steamid = player['steamid']
        message = f"Your current reward points: {player['rewardpoints'] + player['transferpoints']}\nYour total play time is {ptime}\nYour home server is {player['homeserver'].capitalize()}"
        await asyncserverchatto(inst, steamid, message)


@log.catch
async def asyncgettimeplayed(seenname):
    player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{seenname}' ORDER BY lastseen DESC")
    if not player:
        return 'No player found with that name'
    else:
        plasttime = playedTime(float(player['playedtime']))
        return f"""{player["playername"].title()} total playtime is {plasttime} on home server {player["homeserver"].title()}"""


@log.catch
async def asyncgettip(db):
    tip = await db.fetchone("SELECT * FROM tips WHERE active = True ORDER BY count ASC, random()")
    db.update("UPDATE tips set count = {int(tip['count'] + 1} WHERE id = {tip['id'])}")
    return tip['tip']


@log.catch
async def whoisonlinewrapper(inst, oinst, whoasked, crnt):
    if oinst == inst:
        slist = await asyncgetinstancelist()
        for each in slist:
            await asyncwhoisonline(each, oinst, whoasked, True, crnt)
    else:
        await asyncwhoisonline(inst, oinst, whoasked, False, crnt)


@log.catch
async def asyncwhoisonline(inst, oinst, whoasked, filt, crnt):
    try:
        if crnt == 1:
            potime = 40
        elif crnt == 2:
            potime = Secs['hour']
        elif crnt == 3:
            potime = Secs['day']
        if inst not in await asyncgetinstancelist():
            message = f'{inst.capitalize()} is not a valid server'
            await asyncserverchat(oinst, message)
        else:
            players = await db.fetchall(f"SELECT * FROM players WHERE server = '{inst}'")
            pcnt = 0
            plist = ''
            for player in players:
                chktme = Now() - float(player['lastseen'])
                if chktme < potime:
                    pcnt += 1
                    if plist == '':
                        plist = '%s' % (player['playername'].title())
                    else:
                        plist = plist + ', %s' % (player['playername'].title())
            if pcnt != 0:
                if crnt == 1:
                    message = f'{inst.capitalize()} has {pcnt} players online: {plist}'
                    await asyncserverchat(oinst, message)
                elif crnt == 2:
                    message = f'{inst.capitalize()} has had {pcnt} players in the last hour: {plist}'
                    await asyncserverchat(oinst, message)
                elif crnt == 3:
                    message = f'{inst.capitalize()} has had {pcnt} players in the last day: {plist}'
                    await asyncserverchat(oinst, message)
            if pcnt == 0 and not filt:
                message = f'{inst.capitalize()} has no players online.'
                await asyncserverchat(oinst, message)
    except:
        log.exception('exception in whosisonline')
        message = f'Server {inst.capitalize()} does not exist.'
        await asyncserverchat(oinst, message)


async def asyncgetlastvote(inst):
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return insts['lastvote']


async def asyncpopulatevoters(inst):
    log.trace(f'populating vote table for {inst}')
    globvars.votertable = []
    playercount = 0
    players = await db.fetchall(f"SELECT * FROM players WHERE server = '{inst}' and online = True")
    for player in players:
        if not await globalvar.checklist(f'{inst}-leaving', player['steamid']):
            playercount += 1
            newvoter = [player['steamid'], player['playername'], 3]
            globvars.votertable.append(newvoter)
    return playercount


async def asyncsetvote(whoasked, myvote):
    for each in globvars.votertable:
        if each[0] == await asyncgetsteamid(whoasked):
            each[2] = myvote


async def asyncgetvote(whoasked):
    for each in globvars.votertable:
        if each[0] == await asyncgetsteamid(whoasked):
            return each[2]
    return 99


async def asynccastedvote(inst, whoasked, myvote):
    if not globvars.isvoting:
        message = f'No vote is taking place now'
        await asyncserverchat(inst, message)
    else:
        steamid = await asyncgetsteamid(whoasked)
        if await asyncgetvote(whoasked) == 99:
            message = 'Sorry, you are not eligible to vote in this round'
            await asyncserverchatto(inst, steamid, message)
        elif not steamid:
            message = 'Sorry, you are not eligible to vote. Tell an admin they need to update your name!'
            await asyncserverchatto(inst, steamid, message)
        elif await asyncgetvote(whoasked) == 2:
            message = "You started the vote. you're assumed a YES vote."
            await asyncserverchatto(inst, steamid, message)
        elif await asyncgetvote(whoasked) == 1:
            message = 'You have already voted YES. you can only vote once.'
            await asyncserverchatto(inst, steamid, message)
        else:
            if myvote:
                await asyncsetvote(whoasked, 1)
                message = 'Your YES vote has been cast'
                await asyncserverchatto(inst, steamid, message)
            else:
                await asyncsetvote(whoasked, 0)
                message = 'Your NO vote has been cast'
                await asyncserverchatto(inst, steamid, message)
                log.log('VOTE', f'Voting NO has won, NO wild dino wipe will be performed for {inst}')
                globvars.isvoting = False
                bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n\n<RichColor Color="1,1,0,1">                            NO votes have won!</>\n  <RichColor Color="1,0,0,1">                      Wild dinos will NOT be wiped</>\n\n           You must wait 10 minutes before you can start another vote"""
                await asyncserverbcast(inst, bcast)
                await asyncwritechat(inst, 'ALERT', f'### A wild dino wipe vote has failed with a NO vote from \
{whoasked.capitalize()}', wcstamp())


def votingpassed():
    votecount = 0
    for each in globvars.votertable:
        if each[2] == 1 or each[2] == 2:
            votecount += 1
    if votecount == len(globvars.votertable):
        return True
    else:
        return False


def howmanyvotes():
    votecount = 0
    for each in globvars.votertable:
        if each[2] == 1 or each[2] == 2:
            votecount += 1
    return votecount


async def asyncresetlastvote(inst):
    await db.update(f"UPDATE instances SET lastvote = '{int(time())}' WHERE name = '{inst}'")


async def asyncresetlastwipe(inst):
    await db.update(f"UPDATE instances SET lastdinowipe = '{int(time())}' WHERE name = '{inst}'")


@log.catch
async def asyncwipeprep(inst):
    yesvoters = howmanyvotes()
    totvoters = len(globvars.votertable)
    log.log('VOTE', f'YES has won ({yesvoters}/{totvoters}), wild dinos are wiping on [{inst.title()}] in 10 seconds')
    bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n<RichColor Color="0,1,0,1">                     YES votes have won! ('{yesvoters}' of '{totvoters}' Players)</>\n\n  <RichColor Color="1,1,0,1">               !! WIPING ALL WILD DINOS IN 10 SECONDS !!</>"""
    await asyncserverbcast(inst, bcast)
    await asyncwritechat(inst, 'ALERT', f'A wild dino wipe vote has won by YES vote ({yesvoters}/{totvoters}). Wiping wild dinos now.', wcstamp())
    await asyncio.sleep(5)
    asyncio.create_task(asyncwipeit(inst))
    await asyncresetlastwipe(inst)
    return True


async def asyncvoter(inst, whoasked):
    log.log('VOTE', f'A wild dino wipe vote has started for [{inst.title()}] by [{whoasked.title()}]')
    votercount = await asyncpopulatevoters(inst)
    await asyncsetvote(whoasked, 2)
    bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">             A Wild dino wipe vote has started with {votercount} online players</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe\n                           Voting lasts 3 minutes"""
    await asyncserverbcast(inst, bcast)
    asyncloop = asyncio.get_running_loop()
    globvars.votestarttime = asyncloop.time()
    await asyncwritechat(inst, 'ALERT', f'### A wild dino wipe vote has been started by {whoasked.capitalize()}', wcstamp())
    warned = False
    while globvars.isvoting:
        await asyncio.sleep(5)
        if votingpassed() and globvars.isvoting:
            globvars.isvoting = False
            asyncio.create_task(asyncwipeprep(inst))
        elif asyncloop.time() - globvars.votestarttime > Secs['2min']:
            if globvars.isvoting:
                globvars.isvoting = False
                asyncio.create_task(asyncwipeprep(inst))
        elif asyncloop.time() - globvars.votestarttime > 60 and not warned:
            warned = True
            log.log('VOTE', f'Sending voting waiting message to vote on [{inst.title()}]')
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">         A Wild dino wipe vote is waiting for votes! ({howmanyvotes()} of {len(globvars.votertable)})</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe"""
            await asyncserverbcast(inst, bcast)
    globvars.lastvoter = time()
    await asyncresetlastvote(inst)
    log.debug(f'voting task has ended on {inst}')
    return True


async def asyncstartvoter(inst, whoasked):
    if globvars.isvoting:
        message = 'Voting has already started. cast your vote now'
        await asyncserverchat(inst, message)
    elif await instancestate.check(inst, 'maintenance'):
        message = 'You cannot start a vote during server maintenance'
        await asyncserverchat(inst, message)
    elif await instancestate.check(inst, 'restartwaiting'):
        message = 'You cannot start a vote while the server is in restart countdown'
        await asyncserverchat(inst, message)
    elif time() - float(await asyncgetlastwipe(inst)) < Secs['4hour']:   # 4 hours between wipes
        rawtimeleft = Secs['4hour'] - (Now() - float(await asyncgetlastwipe(inst)))
        timeleft = playedTime(rawtimeleft)
        message = f'You must wait {timeleft} until the next wild wipe vote can start'
        await asyncserverchat(inst, message)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 4 hour timer')
    elif Now() - float(await asyncgetlastvote(inst)) < Secs['10min']:                      # 10 min between failed attempts
        rawtimeleft = Now() - await asyncgetlastvote(inst)
        timeleft = playedTime(rawtimeleft)
        message = f'You must wait {timeleft} until the next wild wipe vote can start'
        await asyncserverchat(inst, message)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 10 min timer')
    else:
        globvars.isvoting = True
        asyncio.create_task(asyncvoter(inst, whoasked))


def isserver(line):
    rawissrv = line.split(':')
    if len(rawissrv) > 1:
        if rawissrv[1].strip() == 'SERVER':
            return True
        else:
            return False
    else:
        return False


async def asynclinker(inst, whoasked):
    steamid = await asyncgetsteamid(whoasked)
    player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
    if player:
        if player['discordid'] is None or player['discordid'] == '':
            rcode = ''.join(str(x) for x in random.sample(range(10), 4))
            log.log('PLAYER', f'Generated code [{rcode}] for link request from [{player["playername"].title()}] on [{inst.title()}]')
            await db.update(f"""DELETE from linkrequests WHERE steamid = '{player["steamid"]}'""")
            await db.update(f"""INSERT INTO linkrequests (steamid, name, reqcode) VALUES ('{player["steamid"]}', '{player["playername"]}', '{str(rcode)}')""")
            message = f'Your discord link code is {rcode}, goto discord now and type !linkme {rcode}'
            await asyncserverchatto(inst, player["steamid"], message)
        else:
            log.warning(f'link request for {player["playername"]} denied, already linked')
            message = f'You already have a discord account linked to this account'
            await asyncserverchatto(inst, player["steamid"], message)
    else:
        log.error(f'User not found in DB {whoasked}!')
    return True


@log.catch
async def processtcdata(inst, tcdata):
    steamid = tcdata['SteamID']
    playername = tcdata['PlayerName'].lower()
    player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
    if not player:
        if player['steamid'] not in globvars.welcomes:
            asyncio.create_task(asyncnewplayer(steamid, playername, inst))
    else:
        playtime = int(float(tcdata['TotalPlayed'].replace(',', '')))
        rewardpoints = int(tcdata['Points'].replace(',', ''))
        if playername.lower() != player['playername'].lower():
            log.log('UPDATE', f'Player name update for [{player["playername"]}] to [{playername}]')
            await db.update(f"UPDATE players SET playername = '{playername}' WHERE steamid = '{steamid}'")
        if inst == player['homeserver']:
            log.trace(f'player {playername} with steamid {steamid} was found on HOME server {inst}. updating info.')
            await db.update(f"UPDATE players SET playedtime = '{playtime}', rewardpoints = '{rewardpoints}' WHERE steamid = '{steamid}'")
        else:
            if Now() - int(player['lastseen']) < 200 and Now() - player['lastlogin'] > 30 and player['server'] == inst:
                log.trace(f'player {playername} with steamid {steamid} was found on NON-HOME server {inst}. updating info')
                transferdata = await db.fetchone(f"SELECT * from transferpoints WHERE steamid = '{steamid}' and server = '{inst}'")
                if transferdata:
                    await db.update(f"UPDATE transferpoints SET points = '{rewardpoints}' WHERE steamid = '{steamid}' and server = '{inst}'")
                elif rewardpoints != 0:
                    await db.update(f"INSERT INTO transferpoints (steamid, server, points) VALUES ('{steamid}', '{inst}', {rewardpoints})")


async def asynchomeserver(inst, whoasked, ext):
    steamid = await asyncgetsteamid(whoasked)
    if steamid:
        player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
        if ext != '':
            tservers = []
            tservers = homeablelist()
            ext = ext.lower()
            if ext in tservers:
                if ext != player['homeserver']:
                    if inst == player['homeserver']:
                        log.log('PLAYER', f'[{player["playername"].title()}] has transferred home servers from [{player["homeserver"].title()}] to [{ext.title()}] with {player["rewardpoints"]} points')
                        command = 'tcsar setarctotal {steamid} 0'
                        await asyncserverscriptcmd(inst, command)
                        await db.update(f"""UPDATE players SET homemovepoints = {player["rewardpoints"]}, homeserver = '{ext}' WHERE steamid = '{steamid}'""")
                        message = f'Your {player["rewardpoints"]} points have been transferred to your new home server: {ext.capitalize()}'
                        await asyncserverchatto(inst, steamid, message)
                    else:
                        message = f'You must be on your home server {player["homeserver"].capitalize()} to change your home'
                        await asyncserverchatto(inst, steamid, message)
                else:
                    message = f'{ext.capitalize()} is already your home server'
                    await asyncserverchatto(inst, steamid, message)
            else:
                message = f'{ext.capitalize()} is not a server you can call home in the cluster.'
                await asyncserverchatto(inst, steamid, message)
        else:
            message = f'Your current home server is: {player["homeserver"].capitalize()}'
            await asyncserverchatto(inst, steamid, message)
            message = f'Type !myhome <servername> to change your home.'
            await asyncserverchatto(inst, steamid, message)


@log.catch
async def asynclastlotto(whoasked, inst):
    lastl = await asyncgetlastlotteryinfo()
    message = f'Last lottery was won by {lastl["winner"].upper()} for {lastl["payout"]} points {elapsedTime(datetimeto(lastl["startdate"] + timedelta(hours=int(lastl["days"])), fmt="epoch"),Now())} ago'
    await asyncserverchat(inst, message)


@log.catch
async def asynclotteryinfo(lottery, player, inst):
    message = f'Current lottery is up to {lottery["payout"]} ARc reward points.'
    await asyncserverchatto(inst, player['steamid'], message)
    message = f'{lottery["players"]} players have entered into this lottery so far'
    await asyncserverchatto(inst, player['steamid'], message)
    message = f'Lottery ends in {elapsedTime(datetimeto(lottery["startdate"] + timedelta(hours=lottery["days"]), fmt="epoch"),Now())}'
    await asyncserverchatto(inst, player['steamid'], message)
    inlotto = await db.fetchone(f"""SELECT * FROM lotteryplayers WHERE steamid = '{player["steamid"]}'""")
    if inlotto:
        message = f'You are enterted into this lottery. Good Luck!'
    else:
        message = f'Type !lotto join to spend 10 points and enter into this lottery'
    await asyncserverchatto(inst, player['steamid'], message)


@log.catch
async def asynclottery(whoasked, lchoice, inst):
    lottery = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
    steamid = await asyncgetsteamid(whoasked)
    player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
    if lottery:
        if lchoice == 'join' or lchoice == 'enter':
            log.log('CMD', f'Responding to a [!lotto join] request from [{whoasked.title()}] on [{inst.title()}]')
            lpcheck = await db.fetchone(f"""SELECT * FROM lotteryplayers WHERE steamid = '{player["steamid"]}'""")
            # ltime = estshift(datetime.fromtimestamp(float(linfo[3]) + (Secs['hour'] * int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
            if lpcheck is None:
                await db.update(f"""INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('{player["steamid"]}', '{player["playername"]}', '{Now(fmt='dt')}', 0)""")
                await db.update(f"""UPDATE lotteryinfo SET payout = {lottery['payout'] + lottery['buyin'] * 2}, players = {lottery['players'] + 1} WHERE completed = False""")
                message = f'You have been added to the reward points lottery! A winner will be choosen in {elapsedTime(datetimeto(lottery["startdate"] + timedelta(hours=lottery["days"]), fmt="epoch"), Now())}. Good Luck!'
                await asyncserverchatto(inst, player['steamid'], message)
                log.log('LOTTO', f'Player [{whoasked.title()}] has joined the current active lottery')
            else:
                message = f'You are already participating in this reward point lottery.  Lottery ends in {elapsedTime(datetimeto(lottery["startdate"] + timedelta(hours=lottery["days"]), fmt="epoch"),Now())}'
                await asyncserverchatto(inst, player['steamid'], message)
        else:
            log.log('CMD', f'Responding to a [!lotto] request from [{whoasked.title()}] on [{inst.title()}]')
            await asynclotteryinfo(lottery, player, inst)
    else:
        message = f'There are no current lotterys underway.'
        await asyncserverchat(inst, message)
        log.log('CMD', f'Responding to a [!lotto] request from [{whoasked.title()}] on [{inst.title()}]')
    return True


@log.catch
async def playerjoin(line, inst):
    newline = line[:-17].split(':')
    player = await db.fetchone(f"SELECT * FROM players WHERE steamname = '{cleanstring(newline[1].strip())}'")
    if player:
        if player['homeserver'] != inst:
            xferpointsdata = await db.fetchone(f"""SELECT * FROM transferpoints WHERE steamid = '{player["steamid"]}' and server = '{inst}'""")
            if xferpointsdata:
                log.trace(f'xferpointsdata: {xferpointsdata}')
                command = f'tcsar setarctotal {player["steamid"]} {xferpointsdata["points"]}'
                await asyncserverscriptcmd(inst, command)
        steamid = player['steamid']
        await db.update(f"""UPDATE players SET online = True, refreshsteam = True, lastlogin = '{Now()}', lastseen = '{Now()}', refreshauctions = True, server = '{inst}', connects = {player["connects"] + 1} WHERE steamid = '{steamid}'""")
        if Now() - player['lastseen'] > 250:
            log.log('JOIN', f'Player [{player["playername"].title()}] joined the cluster on [{inst.title()}] Connections: {player["connects"] + 1}')
            message = f'{player["playername"].title()} has joined the server'
            await asyncserverchat(inst, message)
            await asyncwritechat(inst, 'ALERT', f'<<< {player["playername"].title()} has joined the server', wcstamp())
    else:
        log.debug(f'player [{cleanstring(newline[1].strip())}] joined that is not found in database')


@log.catch
async def asyncleavingplayerwatch(player, inst):
    log.debug(f'Player [{player["playername"].title()}] Waiting on transfer from [{inst.title()}]')
    starttime = time()
    stop_watch = False
    transferred = False
    while time() - starttime < 250 and not stop_watch:
        queryplayer = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{player['steamid']}'")
        if queryplayer['server'] != inst:
            fromtxt = f'{player["playername"].title()} has transferred here from {inst.title()}'
            totxt = f'{player["playername"].title()} has transferred to {queryplayer["server"].title()}'
            await asyncserverchat(inst, totxt)
            await asyncwriteglobal(queryplayer["server"].lower(), 'ALERT', fromtxt)
            await asyncwritechat(inst, 'ALERT', f'>><< {player["playername"].title()} has transferred from {inst.title()} to {queryplayer["server"].title()}', wcstamp())
            log.log('XFER', f'Player [{player["playername"].title()}] has transfered from [{inst.title()}] to [{queryplayer["server"].title()}]')
            transferred = True
            stop_watch = True
            await globalvar.remlist(f'{inst}-leaving', player['steamid'])
        await asyncio.sleep(2)

    if not transferred and time() - int(queryplayer['lastseen']) >= 250:
        steamid = player["steamid"]
        await db.update(f"UPDATE players SET online = False, welcomeannounce = True, refreshsteam = True, refreshauctions = True WHERE steamid = '{steamid}'")
        log.log('LEAVE', f'Player [{player["playername"].title()}] left the cluster from [{inst.title()}]')
        mtxt = f'{player["playername"].title()} has logged off the cluster'
        await asyncserverchat(inst, mtxt)
        await globalvar.remlist(f'{inst}-leaving', player['steamid'])
    nplayer = await db.fetchone(f"""SELECT * FROM players where steamid = '{player["steamid"]}'""")
    if player['homeserver'] != inst:
        if not nplayer['online'] or (nplayer['online'] and nplayer['server'] != inst):
            command = f'tcsar setarctotal {player["steamid"]} 0'
            await asyncserverscriptcmd(inst, command)
    return True


@log.catch
async def playerleave(line, inst):
    newline = line[:-15].split(':')
    player = await db.fetchone(f"SELECT * FROM players WHERE steamname = '{cleanstring(newline[1].strip())}'")
    if player:
        await globalvar.addlist(f'{inst}-leaving', player['steamid'])
        await asyncleavingplayerwatch(player, inst)
    else:
        log.error(f'Player with steam name [{newline[1].strip()}] was not found while leaving server')


def deconstructchatline(line):
    try:
        chatnamefull = line.rsplit(':', 1)[0].split(':', 1)[1].strip()
        chatname = chatnamefull.rsplit(')', 1)[0].rsplit('(', 1)[1]
        chatline = line.rsplit(f'({chatname})', 1)[1][2:]
        chattime = datetime.strptime(line.split(':', 1)[0].strip('"'), '%Y.%m.%d_%H.%M.%S')
        log.trace(f'Full name from chat: {chatnamefull}')
        log.trace(f'Got name from chat: {chatname}')
        log.trace(f'Got time from chat: {chattime}')
        log.trace(f'Got chat from chat: {chatline}')
        return {'name': chatname, 'time': chattime, 'line': chatline}
        return chatname
    except:
        log.exception(f'Deconstruct chatline Error: {line}')


@log.catch
async def asyncchatlinedetected(inst, chatdict):
    log.trace(f'chatline detected: {chatdict}')
    transmsg = trans_to_eng(chatdict['line'])
    tstamp = chatdict['time'].strftime('%m-%d %I:%M%p')
    log.log('CHAT', f'{inst} | {chatdict["name"]} | {transmsg}')
    await asyncwritechat(inst, chatdict["name"].lower(), transmsg.replace("'", ""), tstamp)
    await asyncwritechatlog(inst, chatdict["name"].lower(), transmsg, tstamp)


@log.catch
async def addgamelog(inst, ptype, line):
    await redis.zadd('gamelog', time(), f'{inst}||{ptype}||{line}')


@log.catch
async def asyncprocesscmdline(minst, eline):
    dline = eline.decode().replace('"', '').strip()
    lines = dline.split('\n')
    for line in lines:
        inst = minst
        if len(line) < 3 or line.startswith('Running command') or line.startswith('Command processed') or isserver(line) or line.find('Force respawning Wild Dinos!') != -1:
            pass
        elif line.find('[TCsAR]') != -1:
            dfg = line.split('||')
            dfh = dfg[1].split('|')
            tcdata = {}
            for each in dfh:
                ee = each.strip().split(': ')
                if len(ee) > 1:
                    tcdata.update({ee[0]: ee[1]})
            if 'SteamID' in tcdata:
                await processtcdata(minst, tcdata)
        elif line.find('left this ARK!') != -1:
            await playerleave(line, minst)
        elif line.find('joined this ARK!') != -1:
            await playerjoin(line, minst)
        elif line.find('AdminCmd:') != -1 or line.find('Admin Removed Soul Recovery Entry:') != -1:
            await addgamelog(inst, 'ADMIN', line)
        elif line.find(" demolished a '") != -1 or line.find('Your Tribe killed') != -1:
            await addgamelog(inst, 'DEMO', line)
        elif line.find('released:') != -1:
            await addgamelog(inst, 'RELEASE', line)
        elif line.find('trapped:') != -1:
            await addgamelog(inst, 'TRAP', line)
        elif line.find(' was killed!') != -1 or line.find(' was killed by ') != -1:
            await addgamelog(inst, 'DEATH', line)
        elif line.find('Tamed a') != -1:
            await addgamelog(inst, 'TAME', line)
        elif line.find(" claimed '") != -1 or line.find(" unclaimed '") != -1:
            await addgamelog(inst, 'CLAIM', line)
        elif line.find(' was added to the Tribe by ') != -1 or line.find(' was promoted to ') != -1 or line.find(' was demoted from ') != -1 or line.find(' uploaded a') != -1 or line.find(' downloaded a dino:') != -1 or line.find(' requested an Alliance ') != -1 or line.find(' Tribe to ') != -1 or line.find(' was removed from the Tribe!') != -1 or line.find(' set to Rank Group ') != -1 or line.find(' requested an Alliance with ') != -1 or line.find(' was added to the Tribe!') != -1:
            await addgamelog(inst, 'TRIBE', line)
        elif line.find('starved to death!') != -1:
            await addgamelog(inst, 'DECAY', line)
        elif line.find('was auto-decay destroyed!') != -1 or line.find('was destroyed!') != -1:
            await addgamelog(inst, 'DECAY', line)
        elif line.startswith('Error:'):
            await addgamelog(inst, 'UNKNOWN', line)
        else:
            chatdict = deconstructchatline(line)
            whoasked = chatdict['name']
            log.trace(f'chatline who: {whoasked}')
            incmd = chatdict['line']
            if incmd.startswith('!test'):
                log.log('CMD', f'Responding to a [!test] request from [{whoasked.title()}] on [{minst.title()}]')
                message = 'hi'
                bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n\n<RichColor Color="1,1,0,1">                            NO votes have won!</>\n  <RichColor Color="1,0,0,1">                      Wild dinos will NOT be wiped</>\n\n           You must wait 10 minutes before you can start another vote"""
                await asyncserverbcast(minst, bcast)

            elif incmd.startswith('!help'):
                message = f'Commands: @all, !who, !lasthour, !lastday,  !timeleft, !myinfo, !myhome, !lastwipe,'
                await asyncserverchat(inst, message)
                message = f'!lastrestart, !vote, !tip, !lottery, !lastseen <playername>, !playtime <playername>'
                await asyncserverchat(inst, message)
                log.log('CMD', f'Responded to a [!help] request from [{whoasked.title()}] on [{minst.title()}]')
            elif incmd.startswith(('/kit', '!kit')):
                log.log('CMD', f'Responding to a kit request from [{whoasked.title()}] on [{minst.title()}]')
                message = f'To view kits you must make a level 1 rewards vault and hang it on a wall or foundation. Free starter items and over 80 kits available. !help for more commands'
                await asyncserverchat(inst, message)

            elif incmd.startswith('/'):
                message = f'Commands in this cluster start with a ! (Exclimation Mark)  Type !help for a list of commands'
                await asyncserverchat(inst, message)

            elif incmd.startswith(('!lastdinowipe', '!lastwipe')):
                lastwipe = elapsedTime(Now(), await asyncgetlastwipe(minst))
                message = f'Last wild dino wipe was {lastwipe} ago'
                await asyncserverchat(inst, message)
                log.log('CMD', f'Responding to a [!lastwipe] request from [{whoasked.title()}] on [{minst.title()}]')

            elif incmd.startswith('!lastrestart'):
                lastrestart = elapsedTime(Now(), await asyncgetlastrestart(minst))
                message = f'Last server restart was {lastrestart} ago'
                await asyncserverchat(inst, message)
                log.log('CMD', f'Responding to a [!lastrestart] request from [{whoasked.title()}] on [{minst.title()}]')

            elif incmd.startswith('!lastseen'):
                rawseenname = line.split(':')
                orgname = rawseenname[1].strip()
                lsnname = rawseenname[2].split('!lastseen')
                if len(lsnname) > 1:
                    seenname = lsnname[1].strip().lower()
                    message = await asyncgetlastseen(seenname)
                    log.log('CMD', f'Responding to a [!lastseen] request for [{seenname.title()}] from [{orgname.title()}] on [{minst.title()}]')
                else:
                    message = f'You must specify a player name to search'
                    log.log('CMD', f'Responding to a invalid [!lastseen] request from [{orgname.title()}] on [{minst.title()}]')
                await asyncserverchat(minst, message)

            elif incmd.startswith('!playedtime'):
                rawseenname = line.split(':')
                orgname = rawseenname[1].strip()
                lsnname = rawseenname[2].split('!playedtime')
                seenname = lsnname[1].strip().lower()
                if lsnname:
                    message = await asyncgettimeplayed(seenname)
                else:
                    message = await asyncgettimeplayed(whoasked)
                await asyncserverchat(inst, message)
                log.log('CMD', f'Responding to a [!playedtime] request for [{whoasked.title()}] on [{minst.title()}]')

            elif incmd.startswith(('!recent', '!whorecent', '!lasthour')):
                rawline = line.split(':')
                lastlline = rawline[2].strip().split(' ')
                if len(lastlline) == 2:
                    ninst = lastlline[1]
                else:
                    ninst = minst
                log.log('CMD', f'Responding to a [!recent] request for [{whoasked.title()}] on [{minst.title()}]')
                await whoisonlinewrapper(ninst, minst, whoasked, 2)

            elif incmd.startswith(('!today', '!lastday')):
                rawline = line.split(':')
                lastlline = rawline[2].strip().split(' ')
                if len(lastlline) == 2:
                    ninst = lastlline[1]
                else:
                    ninst = minst
                log.log('CMD', f'Responding to a [!today] request for [{whoasked.title()}] on [{minst.title()}]')
                await whoisonlinewrapper(ninst, minst, whoasked, 3)

            elif incmd.startswith(('!tip', '!justthetip')):
                log.log('CMD', f'Responding to a [!tip] request from [{whoasked.title()}] on [{minst.title()}]')
                tip = await asyncgettip(db)
                message = tip
                await asyncserverchat(inst, message)

            elif incmd.startswith(('!mypoints', '!myinfo')):
                log.log('CMD', f'Responding to a [!myinfo] request from [{whoasked.title()}] on [{minst.title()}]')
                await asyncrespmyinfo(minst, whoasked)

            elif incmd.startswith(('!players', '!whoson', '!who')):
                rawline = line.split(':')
                lastlline = rawline[2].strip().split(' ')
                if len(lastlline) == 2:
                    ninst = lastlline[1]
                else:
                    ninst = minst
                log.log('CMD', f'Responding to a [!who] request for [{whoasked.title()}] on [{minst.title()}]')
                await whoisonlinewrapper(ninst, minst, whoasked, 1)

            elif incmd.startswith(('!myhome', '!transfer', '!home', '!sethome')):
                rawline = line.split(':')
                lastlline = rawline[2].strip().split(' ')
                if len(lastlline) == 2:
                    ninst = lastlline[1]
                else:
                    ninst = ''
                log.log('CMD', f'Responding to a [!myhome] request for [{whoasked.title()}] on [{minst.title()}]')
                message = "The Home command is disabled for repairs"
                await asyncserverchat(inst, message)
                # await asynchomeserver(minst, whoasked, ninst)

            elif incmd.startswith(('!vote', '!startvote', '!wipe')):
                log.debug(f'Responding to a [!vote] request from [{whoasked.title()}] on [{minst.title()}]')
                await asyncstartvoter(minst, whoasked)

            elif incmd.startswith(('!agree', '!yes')):
                log.debug(f'responding to YES vote on {minst} from {whoasked}')
                await asynccastedvote(minst, whoasked, True)

            elif incmd.startswith(('!disagree', '!no')):
                log.log('VOTE', f'Responding to NO vote on [{minst.title()}] from [{whoasked.title()}]')
                await asynccastedvote(minst, whoasked, False)

            elif incmd.startswith(('!timeleft', '!restart')):
                log.log('CMD', f'Responding to a [!timeleft] request from [{whoasked.title()}] on [{minst.title()}]')
                await asyncresptimeleft(minst, whoasked)

            elif incmd.startswith(('!linkme', '!link')):
                log.log('CMD', f'Responding to a [!linkme] request from [{whoasked.title()}] on [{minst.title()}]')
                await asynclinker(minst, whoasked)

            elif incmd.startswith(('!lottery', '!lotto')):
                rawline = line.split(':')
                if len(rawline) > 2:
                    lastlline = rawline[2].strip().split(' ')
                    if len(lastlline) == 2:
                        lchoice = lastlline[1]
                    else:
                        lchoice = False
                    await asynclottery(whoasked, lchoice, minst)

            elif incmd.startswith(('!lastlotto', '!winner')):
                log.log('CMD', f'Responding to a [!lastlotto] request from [{whoasked.title()}] on [{minst.title()}]')
                await asynclastlotto(minst, whoasked)

            elif incmd.startswith('!'):
                steamid = await asyncgetsteamid(whoasked)
                log.warning(f'Invalid command request from [{whoasked.title()}] on [{minst.title()}]')
                message = "Invalid command. Try !help"
                await asyncserverchatto(inst, steamid, message)

            elif incmd.startswith(globvars.atinstances):
                newchatline = chatdict['line'].split(" ", 1)[1]
                tstamp = chatdict['time'].strftime('%m-%d %I:%M%p')
                await asyncwriteglobal(minst, chatdict['name'], newchatline)
                await asyncwritechat('generalchat', chatdict['name'], newchatline, tstamp)

            else:
                await asyncchatlinedetected(inst, chatdict)


async def cmdsexecute(inst):
    asyncloop = asyncio.get_running_loop()
    cmd_done = asyncio.Future(loop=asyncloop)
    factory = partial(SubProtocol, cmd_done, inst, parsetask=asyncprocesscmdline)
    proc = asyncloop.subprocess_exec(factory, 'arkmanager', 'rconcmd', 'getgamelog', f'@{inst}', stdin=None, stderr=None)
    try:
        transport, protocol = await proc
        await cmd_done
    finally:
        transport.close()


async def cmdscheck(instances):
    for inst in instances:
        if await instancevar.getbool(inst, 'islistening'):
            asyncio.create_task(cmdsexecute(inst))
