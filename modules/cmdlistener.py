import asyncio
import os
import random
import subprocess
import threading
from datetime import datetime, timedelta
from time import time

import aiofiles
import uvloop
from loguru import logger as log
from modules.asyncdb import asyncDB
from modules.dbhelper import cleanstring, dbquery, dbupdate
from modules.gtranslate import trans_to_eng
from modules.instances import asyncgetinstancelist, getlastrestart, getlastwipe, homeablelist
from modules.lottery import asyncgetlastlotteryinfo
from modules.players import newplayer
from modules.servertools import asyncserverbcast, asyncserverchat, asyncserverchatto, asyncserverscriptcmd, serverexec
from modules.timehelper import Now, Secs, datetimeto, elapsedTime, playedTime, tzfix, wcstamp

lastvoter = 0.1
votertable = []
votestarttime = Now()
arewevoting = False


async def asyncstopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Command listener thread has ended')
            exit(0)
        asyncio.sleep(1)


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


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,), fetch='one')
        if isindb:
            dbupdate("""INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')""" % (inst, whos, msg.replace("'", ""), tstamp))

    elif whos == "ALERT":
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


async def asyncgetsteamid(whoasked):
    player = await db.fetchone(f"SELECT * FROM players WHERE (playername = '{whoasked}') or (alias = '{whoasked}')")
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
    log.debug(f'{type(tip)}')
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
    log.debug(f'populating vote table for {inst}')
    global votertable
    votertable = []
    playercount = 0
    players = await db.fetchall(f"SELECT * FROM players WHERE server = '{inst}' and online = True")
    for player in players:
        checktime = time() - float(player['lastseen'])
        if checktime < 90:
            playercount += 1
            newvoter = [player['steamid'], player['playername'], 3]
            votertable.append(newvoter)
    log.debug(votertable)
    return playercount


async def asyncsetvote(whoasked, myvote):
    global votertable
    for each in votertable:
        if each[0] == await asyncgetsteamid(whoasked):
            each[2] = myvote


async def asyncgetvote(whoasked):
    for each in votertable:
        if each[0] == await asyncgetsteamid(whoasked):
            return each[2]
    return 99


async def asynccastedvote(inst, whoasked, myvote):
    global arewevoting
    if not isvoting:
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
                arewevoting = False
                bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n\n<RichColor Color="1,1,0,1">                            NO votes have won!</>\n  <RichColor Color="1,0,0,1">                      Wild dinos will NOT be wiped</>\n\n           You must wait 10 minutes before you can start another vote"""
                await asyncserverbcast(inst, bcast)
                await asyncwritechat(inst, 'ALERT', f'### A wild dino wipe vote has failed with a NO vote from \
{whoasked.capitalize()}', wcstamp())


def votingpassed():
    votecount = 0
    totalvoters = 0
    for each in votertable:
        totalvoters += 1
        if each[2] == 1 or each[2] == 2:
            votecount += 1
    if votecount == totalvoters:
        return True
    else:
        return False


def enoughvotes():
    votecount = 0
    totalvoters = 0
    for each in votertable:
        totalvoters += 1
        if each[2] == 1 or each[2] == 2:
            votecount += 1
    if votecount >= totalvoters / 2:
        return True
    else:
        return False


def howmanyvotes():
    votecount = 0
    totalvoters = 0
    for each in votertable:
        totalvoters += 1
        if each[2] == 1 or each[2] == 2:
            votecount += 1
    return votecount, totalvoters


async def asyncresetlastvote(inst):
    await db.update(f"UPDATE instances SET lastvote = '{time()}' WHERE name = '{inst}'")


async def asyncresetlastwipe(inst):
    await db.update("UPDATE instances SET lastdinowipe = '{time()}' WHERE name = '{inst}'")


@log.catch
async def asyncwipeit(inst):
    yesvoters, totvoters = howmanyvotes()
    log.log('VOTE', f'YES has won ({yesvoters}/{totvoters}), wild dinos are wiping on [{inst.title()}] in 15 seconds')
    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n<RichColor Color="0,1,0,1">                     YES votes have won! ('%s' of '%s' Players)</>\n\n  <RichColor Color="1,1,0,1">               !! WIPING ALL WILD DINOS IN 10 SECONDS !!</>""" % (yesvoters, totvoters)
    await asyncserverbcast(inst, bcast)
    await asyncwritechat(inst, 'ALERT', f'### A wild dino wipe vote has won by YES vote ({yesvoters}/{totvoters}). \
Wiping wild dinos now.', wcstamp())
    await asyncio.sleep(7)
    ##########################################
    subprocess.run('arkmanager rconcmd "Destroyall BeeHive_C" @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    await asyncio.sleep(3)
    subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    await asyncresetlastwipe(inst)
    log.log('WIPE', f'All wild dinos have been wiped from [{inst.title()}]')


async def asyncvoter(inst, whoasked):
    log.log('VOTE', f'A wild dino wipe vote has started for [{inst.title()}] by [{whoasked.title()}]')
    global lastvoter
    global isvoting
    global votertable
    votercount = await asyncpopulatevoters(inst)
    await asyncsetvote(whoasked, 2)
    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">             A Wild dino wipe vote has started with {votercount} online players</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe\n                           Voting lasts 3 minutes"""
    await asyncserverbcast(inst, bcast)
    votestarttime = time()
    await asyncwritechat(inst, 'ALERT', f'### A wild dino wipe vote has been started by {whoasked.capitalize()}', wcstamp())
    warned = False
    while isvoting:
        await asyncio.sleep(5)
        if votingpassed() and time() - votestarttime >= Secs['2min']:
            isvoting = False
            asyncio.create_task(asyncwipeit(inst))
        elif time() - votestarttime > Secs['2min']:
            if enoughvotes():
                isvoting = False
                asyncio.create_task(asyncwipeit(inst))
            else:
                isvoting = False
                yesvoters, totvoters = await howmanyvotes()
                message = f'Not enough votes ({yesvoters} of {totvoters}). voting has ended.'
                await asyncserverchat(inst, message)
                log.log('VOTE', f'Voting has ended on [{inst.title()}] Not enough votes ({yesvoters}/{totvoters})')
                await asyncwritechat(inst, 'ALERT', f'### Wild dino wipe vote failed with not enough votes ({yesvoters} of \
{totvoters})', wcstamp())
        elif time() - votestarttime > 60 and not warned:
            warned = True
            log.log('VOTE', f'Sending voting waiting message to vote on [{inst.title()}]')
            bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                  A Wild dino wipe vote is waiting for votes!</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe"""
            await asyncserverbcast(inst, bcast)
    log.debug(votertable)
    votertable = []
    lastvoter = time()
    await asyncresetlastvote(inst)
    log.debug(f'voting thread has ended on {inst}')


async def asyncstartvoter(inst, whoasked):
    global isvoting
    if isvoting:
        message = 'Voting has already started. cast your vote now'
        await asyncserverchat(inst, message)
    elif time() - float(await asyncgetlastvote(inst)) < Secs['4hour']:   # 4 hours between wipes
        rawtimeleft = Secs['4hour'] - (Now() - float(await asyncgetlastvote(inst)))
        timeleft = playedTime(rawtimeleft)
        message = f'You must wait {timeleft} until the next wild wipe vote can start'
        await asyncserverchat(inst, message)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 4 hour timer')
    elif time() - float(lastvoter) < Secs['10min']:                      # 10 min between failed attempts
        rawtimeleft = Secs['10min'] - (Now() - lastvoter)
        timeleft = playedTime(rawtimeleft)
        message = f'You must wait {timeleft} until the next wild wipe vote can start'
        await asyncserverchat(inst, message)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 10 min timer')
    else:
        isvoting = True
        asyncio.create_task(asyncvoter(inst, whoasked))


def getnamefromchat(chat):
    try:
        log.debug(f'getnamefromchat: {chat}')
        rawlineorg = chat.split(':')
        if len(rawlineorg) > 1:
            rawline = rawlineorg[1].split(' (')
            rawline = rawline[1][:-1].strip()
            return rawline.lower()
    except:
        log.error(f'GetNameFromChat Error: {chat}')


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


@log.catch
async def asyncwritechatlog(inst, whos, msg, tstamp):
    steamid = await asyncgetsteamid(whos)
    if steamid:
        clog = f"""{tstamp} [{whos.upper()}]{msg}\n"""
        if not os.path.exists(f'/home/ark/shared/logs/{inst}'):
            log.error(f'Log directory /home/ark/shared/logs/{inst} does not exist! creating')
            os.mkdir(f'/home/ark/shared/logs/{inst}', 0o777)
            os.chown(f'/home/ark/shared/logs/{inst}', 1001, 1005)
        #with aiofiles.open(f"/home/ark/shared/logs/{inst}/chat.log", "at") as f:
        #    await f.write(clog)
        #await f.close()


@log.catch
def writechatlog(inst, whos, msg, tstamp):
    isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos, ), fetch='one')
    if isindb:
        clog = f"""{tstamp} [{whos.upper()}]{msg}\n"""
        if not os.path.exists(f'/home/ark/shared/logs/{inst}'):
            log.error(f'Log directory /home/ark/shared/logs/{inst} does not exist! creating')
            os.mkdir(f'/home/ark/shared/logs/{inst}', 0o777)
            os.chown(f'/home/ark/shared/logs/{inst}', 1001, 1005)
        with open(f"/home/ark/shared/logs/{inst}/chat.log", "at") as f:
            f.write(clog)
        f.close()


@log.catch
async def processtcdata(inst, tcdata):
    steamid = tcdata['SteamID']
    playername = tcdata['PlayerName'].lower()
    player = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{steamid}'")
    if not player:
        welcom = threading.Thread(name='welcoming-%s' % steamid, target=newplayer, args=(steamid, playername, inst))
        welcom.start()
    else:
        playtime = int(float(tcdata['TotalPlayed'].replace(',', '')))
        rewardpoints = int(tcdata['Points'].replace(',', ''))
        if playername.lower() != player['playername'].lower():
            log.log('UPDATE', f'Player name update for [{player["playername"]}] to [{playername}]')
            await db.update("UPDATE players SET playername = '%s' WHERE steamid = '%s'" % (playername, steamid))
        if inst == player['homeserver']:
            log.trace(f'player {playername} with steamid {steamid} was found on HOME server {inst}. updating info.')
            await db.update("UPDATE players SET playedtime = '%s', rewardpoints = '%s' WHERE steamid = '%s'" %
                            (playtime, rewardpoints, steamid))
        else:
            log.trace(f'player {playername} with steamid {steamid} was found on NON-HOME server {inst}. updating info.')
            if int(player['transferpoints']) != int(rewardpoints):
                if int(rewardpoints) != 0:
                    if Now() - float(player['lastpointtimestamp']) > 60:
                        log.debug(f'adding {rewardpoints} non home points to {player["homeserver"]} transfer points for {playername} on {inst}')
                        await db.update(f"UPDATE players SET transferpoints = '{int(rewardpoints)}', lastpointtimestamp = '{str(Now())}' WHERE steamid = '{str(steamid)}'")
                        command = f'tcsar setarctotal {steamid} 0'
                        await asyncserverscriptcmd(inst, command)
                    else:
                        log.trace(f'reward points not past threshold for wait (to avoid duplicates) for \
{playername} on {inst}, skipping')
                else:
                    log.trace(f'zero reward points to account for {playername} on {inst}, skipping')
            else:
                log.trace(f'duplicate reward points to account for {playername} on {inst}, skipping')


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
                        await db.update(f"""UPDATE players SET transferpoints = {player["rewardpoints"]}, homeserver = '{ext}' WHERE steamid = '{steamid}'""")
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
        message = f'Type !lotto join to spend {lottery["buyin"]} points and enter into this lottery'
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


@log.catch
async def playerjoin(line, inst):
    newline = line[:-17].split(':')
    player = await db.fetchone(f"SELECT * FROM players WHERE steamname = '{cleanstring(newline[1].strip())}'")
    if player:
        steamid = player['steamid']
        await db.update(f"""UPDATE players SET online = True, refreshsteam = True, refreshauctions = True, lastseen = '{Now()}', server = '{inst}', connects = {player["connects"] + 1} WHERE steamid = '{steamid}'""")
        if Now() - player['lastseen'] > 250:
            log.log('JOIN', f'Player [{player["playername"].title()}] joined the cluster on [{inst.title()}] Connections: {player["connects"] + 1}')
            message = f'{player["playername"].title()} has joined the server'
            await asyncserverchat(inst, message)
            await asyncwritechat(inst, 'ALERT', f'<<< {player["playername"].title()} has joined the server', wcstamp())


@log.catch
async def asyncleavingplayerwatch(player, inst):
    log.debug(f'Started leaving player watch for [{player["playername"].title()}] on [{inst.title()}]')
    starttime = time()
    stop_watch = False
    transferred = False
    while time() - starttime < 250 and not stop_watch:
        queryplayer = await db.fetchone(f"SELECT * FROM players WHERE steamid = '{player['steamid']}'")
        if queryplayer['server'] != inst:
            fromtxt = f'{player["playername"].title()} has transferred here from {inst.title()}'
            totxt = f'{player["playername"].title()} has transferred to {queryplayer["server"].title()}'
            serverexec(['arkmanager', 'rconcmd', f'ServerChat {totxt}', f'@{inst}'], nice=19, null=True)
            await asyncwriteglobal(queryplayer["server"].lower(), 'ALERT', fromtxt)
            await asyncwritechat(inst, 'ALERT', f'>><< {player["playername"].title()} has transferred from {inst.title()} to {queryplayer["server"].title()}', wcstamp())
            log.log('XFER', f'Player [{player["playername"].title()}] has transfered from [{inst.title()}] to [{queryplayer["server"].title()}]')
            transferred = True
            stop_watch = True
        await asyncio.sleep(1)
    if not transferred and time() - int(queryplayer['lastseen']) >= 240:
        steamid = player["steamid"]
        await db.update(f"UPDATE players SET online = False, refreshsteam = True, refreshauctions = True WHERE steamid = '{steamid}'")
        log.log('LEAVE', f'Player [{player["playername"].title()}] left the cluster from [{inst.title()}]')
        mtxt = f'{player["playername"].title()} has logged off the cluster'
        serverexec(['arkmanager', 'rconcmd', f'ServerChat {mtxt}', f'@{inst}'], nice=19, null=True)
        log.debug(f'Thread ending for leaving player [{player["playername"].title()}]')


@log.catch
async def playerleave(line, inst):
    newline = line[:-15].split(':')
    player = await db.fetchone(f"SELECT * FROM players WHERE steamname = '{cleanstring(newline[1].strip())}'")
    if player:
        log.debug(f'Player [{player["playername"].title()}] Waiting on transfer from [{inst.title()}]')
        asyncio.create_task(asyncleavingplayerwatch(player, inst))
    else:
        log.error(f'Player with steam name [{newline[1].strip()}] was not found while leaving server')


@log.catch
async def asyncchatlineelsed(line, inst):
    log.debug(f'chatline elsed: {line}')
    rawline = line.split('(')
    if len(rawline) > 1:
        rawname = rawline[1].split(')')
        whoname = rawname[0].lower()
        if len(rawname) > 1:
            cmsg = rawname[1]
            nmsg = line.split(': ')
            if len(nmsg) > 2:
                if nmsg[0].startswith('"'):
                    dto = datetime.strptime(nmsg[0][3:], '%y.%m.%d_%H.%M.%S')
                else:
                    dto = datetime.strptime(nmsg[0][2:], '%y.%m.%d_%H.%M.%S')
                tstamp = dto.strftime('%m-%d %I:%M%p')
                cmsg = trans_to_eng(cmsg)
                log.log('CHAT', f'{inst} | {whoname} | {cmsg[2:]}')
                await asyncwritechat(inst, whoname, cmsg.replace("'", ""), tstamp)
                await asyncwritechatlog(inst, whoname, cmsg, tstamp)


@log.catch
async def asyncprocessline(minst, line):
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
        # log.log('GLRAW', f"""|{inst.upper()}|ADMIN|{line.replace('"', '')}""".strip())
        await db.update([inst, 'ADMIN', line.replace('"', '').strip()], db='gl')
    elif line.find(" demolished a '") != -1 or line.find('Your Tribe killed') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|DEMO|{line.replace('"', '')}""".strip())
        await db.update([inst, 'DEMO', line.replace('"', '').strip()], db='gl')
    elif line.find('released:') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|RELEASE|{line.replace('"', '')}""".strip())
        await db.update([inst, 'RELEASE', line.replace('"', '').strip()], db='gl')
    elif line.find('trapped:') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|TRAP|{line.replace('"', '')}""".strip())
        await db.update([inst, 'TRAP', line.replace('"', '').strip()], db='gl')
    elif line.find(' was killed!') != -1 or line.find(' was killed by ') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|DEATH|{line.replace('"', '')}""".strip())
        await db.update([inst, 'DEATH', line.replace('"', '').strip()], db='gl')
    elif line.find('Tamed a') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|TAME|{line.replace('"', '')}""".strip())
        await db.update([inst, 'TAME', line.replace('"', '').strip()], db='gl')
    elif line.find(" claimed '") != -1 or line.find(" unclaimed '") != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|CLAIM|{line.replace('"', '')}""".strip())
        await db.update([inst, 'CLAIM', line.replace('"', '').strip()], db='gl')
    elif line.find(' was added to the Tribe by ') != -1 or line.find(' was promoted to ') != -1 or line.find(' was demoted from ') != -1 or line.find(' uploaded a') != -1 or line.find(' downloaded a dino:') != -1 or line.find(' requested an Alliance ') != -1 or line.find(' Tribe to ') != -1 or line.find(' was removed from the Tribe!') != -1 or line.find(' set to Rank Group ') != -1 or line.find(' requested an Alliance with ') != -1 or line.find(' was added to the Tribe!') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|TRIBE|{line.replace('"', '')}""".strip())
        await db.update([inst, 'TRIBE', line.replace('"', '').strip()], db='gl')
    elif line.find('starved to death!') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|DECAY|{line.replace('"', '')}""".strip())
        await db.update([inst, 'DECAY', line.replace('"', '').strip()], db='gl')
    elif line.find('was auto-decay destroyed!') != -1 or line.find('was destroyed!') != -1:
        # log.log('GLRAW', f"""|{inst.upper()}|DECAY|{line.replace('"', '')}""".strip())
        await db.update([inst, 'DECAY', line.replace('"', '').strip()], db='gl')
    elif line.startswith('Error:'):
        # log.log('GLRAW', f"""|{inst.upper()}|UNKNOWN|{line.replace('"', '')}""".strip())
        await db.update([inst, 'UNKNOWN', line.replace('"', '').strip()], db='gl')
    else:
        whoasked = getnamefromchat(line)
        log.trace(f'chatline who: {whoasked}')
        if whoasked is not None:
            lsw = line.lower().split(':')
            if len(lsw) == 3:
                incmd = lsw[2].strip()
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
                elif incmd.startswith('@all'):
                    try:
                        rawline = line.split('(')
                        if len(rawline) > 1:
                            rawname = rawline[1].split(')')
                            whoname = rawname[0].lower()
                            if len(rawname) > 1:
                                cmsg = rawname[1].split('@all')[1].strip()
                                if cmsg != '':
                                    nmsg = line.split(': ')
                                    if len(nmsg) > 2:
                                        try:
                                            if nmsg[0].startswith('"'):
                                                dto = datetime.strptime(nmsg[0][3:], '%y.%m.%d_%H.%M.%S')
                                                dto = dto - tzfix
                                            else:
                                                dto = datetime.strptime(nmsg[0][2:], '%y.%m.%d_%H.%M.%S')
                                                dto = dto - tzfix
                                            tstamp = dto.strftime('%m-%d %I:%M%p')
                                            await asyncwriteglobal(minst, whoname, cmsg)
                                            await asyncwritechat('generalchat', whoname, cmsg, tstamp)
                                        except:
                                            log.exception('could not parse date from chat')
                    except:
                        log.exception('Critical Error in global chat writer!')

                elif incmd.startswith(('/kit', '!kit')):
                    log.log('CMD', f'Responding to a kit request from [{whoasked.title()}] on [{minst.title()}]')
                    message = f'To view kits you must make a level 1 rewards vault and hang it on a wall or foundation. Free starter items and over 80 kits available. !help for more commands'
                    await asyncserverchat(inst, message)

                elif incmd.startswith('/'):
                    message = f'Commands in this cluster start with a ! (Exclimation Mark)  Type !help for a list of commands'
                    await asyncserverchat(inst, message)

                elif incmd.startswith(('!lastdinowipe', '!lastwipe')):
                    lastwipe = elapsedTime(Now(), getlastwipe(minst))
                    message = f'Last wild dino wipe was {lastwipe} ago'
                    await asyncserverchat(inst, message)
                    log.log('CMD', f'Responding to a [!lastwipe] request from [{whoasked.title()}] on [{minst.title()}]')

                elif incmd.startswith('!lastrestart'):
                    lastrestart = elapsedTime(Now(), getlastrestart(minst))
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
                    await asynchomeserver(minst, whoasked, ninst)

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
                    asyncio.create_task(asynclinker(minst, whoasked))

                elif incmd.startswith(('!lottery', '!lotto')):
                    rawline = line.split(':')
                    if len(rawline) > 2:
                        lastlline = rawline[2].strip().split(' ')
                        if len(lastlline) == 2:
                            lchoice = lastlline[1]
                        else:
                            lchoice = False
                        asyncio.create_task(asynclottery(whoasked, lchoice, minst))

                elif incmd.startswith(('!lastlotto', '!winner')):
                    log.log('CMD', f'Responding to a [!lastlotto] request from [{whoasked.title()}] on [{minst.title()}]')
                    await asynclastlotto(minst, whoasked)

                elif incmd.startswith('!'):
                    steamid = await asyncgetsteamid(whoasked)
                    log.warning(f'Invalid command request from [{whoasked.title()}] on [{minst.title()}]')
                    message = "Invalid command. Try !help"
                    await asyncserverchatto(inst, steamid, message)
                else:
                    await asyncchatlineelsed(line, inst)
            else:
                await asyncchatlineelsed(line, inst)


@log.catch
async def processchunk(inst, chunk):
    for line in iter(chunk.splitlines()):
        await asyncprocessline(inst, line)


@log.catch
async def checkcommands(inst, dtime, stop_event):
    global isvoting
    isvoting = False
    asyncloop = asyncio.get_running_loop()
    await db.connect()
    while not stop_event.is_set():
        cmdpipe = serverexec(['arkmanager', 'rconcmd', 'getgamelog', f'@{inst}'], nice=5, null=False)
        chunk = cmdpipe.stdout.decode("utf-8")
        starttime = time()
        asyncio.create_task(processchunk(inst, chunk))
        while time() - starttime < dtime:
            await asyncio.sleep(1)
    pendingtasks = asyncio.Task.all_tasks()
    await asyncio.gather(*pendingtasks)
    await db.close()
    asyncloop.stop()
    log.debug('Command listener thread has ended')
    exit(0)


@log.catch
def cmdlistener_thread(inst, dtime, stop_event):
    global db
    log.debug(f'Command listener thread for {inst} is starting')
    db = asyncDB()
    log.patch(lambda record: record["extra"].update(instance=inst))
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(checkcommands(inst, dtime, stop_event))
