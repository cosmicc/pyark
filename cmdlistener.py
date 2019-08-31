from datetime import datetime, timedelta
from modules.configreader import instance, numinstances
from modules.dbhelper import dbquery, dbupdate, cleanstring, asyncglupdate, asyncdbquery, asyncdbupdate
from modules.players import newplayer
from modules.instances import homeablelist, getlastwipe, getlastrestart, writeglobal, asyncgetinstancelist
from modules.timehelper import elapsedTime, playedTime, wcstamp, tzfix, Secs, Now, datetimeto
from modules.servertools import serverexec, asyncserverchat, asyncserverchatto, asyncserverbcast, asyncserverscriptcmd
from lottery import asyncgetlastlotteryinfo
from time import sleep, time
from loguru import logger as log
import random
import subprocess
import threading
import os
import asyncio
import aiofiles
from gtranslate import trans_to_eng
import uvloop

lastvoter = 0.1
votertable = []
votestarttime = Now()
arewevoting = False


@log.catch
async def asynctask(function, wait, *args, **kwargs):
        task = asyncio.create_task(function(*args, **kwargs))
        if wait:
            return await task
        else:
            return True


async def asyncwritechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = await asyncdbquery(f"SELECT * from players WHERE playername = '{whos}'", 'count', fetch='one')
        if isindb:
            await asyncdbupdate("""INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')""" % (inst, whos, msg.replace("'", ""), tstamp))

    elif whos == "ALERT":
        await asyncdbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery("SELECT * from players WHERE playername = '%s'" % (whos,), fetch='one')
        if isindb:
            dbupdate("""INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')""" % (inst, whos, msg.replace("'", ""), tstamp))

    elif whos == "ALERT":
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


async def asyncgetsteamid(whoasked):
    player = await asyncdbquery(f"SELECT * FROM players WHERE (playername = '{whoasked}') or (alias = '{whoasked}')", 'dict', 'one')
    if player is None:
        log.critical(f'Player lookup failed! possible renamed player: {whoasked}')
        return None
    else:
        return player['steamid']


def getsteamid(whoasked):
    sid = dbquery("SELECT steamid FROM players WHERE (playername = '%s') or (alias = '%s')" % (whoasked, whoasked), fetch='one')
    if sid is None:
        log.critical(f'Player lookup failed! possible renamed player: {whoasked}')
        return 0
    else:
        return sid[0]


@log.catch
async def asyncresptimeleft(inst, whoasked):
    insts = await asyncdbquery(f"SELECT * FROM instances WHERE name = '{inst}'", 'dict', 'one')
    if insts['needsrestart'] == 'True':
        message = f'{inst.title()} is restarting in {insts["restartcountdown"]} minutes'
        await asyncserverchat(inst, message)
    else:
        message = f'{inst.title()} is not pending a restart'
        await asyncserverchat(inst, message)


@log.catch
async def asyncgetlastseen(seenname):
    player = await asyncdbquery(f"SELECT * FROM players WHERE playername = '{seenname}' ORDER BY lastseen DESC", 'dict', 'one')
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
        player = await asyncdbquery(f"SELECT * FROM players WHERE playername = '{whoasked}' ORDER BY lastseen DESC", 'dict', 'one')
        ptime = playedTime(player['playedtime'])
        steamid = player['steamid']
        message = f"Your current reward points: {player['rewardpoints'] + player['transferpoints']}\nYour total play time is {ptime}\nYour home server is {player['homeserver'].capitalize()}"
        await asyncserverchatto(inst, steamid, message)


@log.catch
async def asyncgettimeplayed(seenname):
    player = await asyncdbquery(f"SELECT * FROM players WHERE playername = '{seenname}' ORDER BY lastseen DESC", 'dict', 'one')
    if not player:
        return 'No player found with that name'
    else:
        plasttime = playedTime(float(player['playedtime']))
        return f"""{player["playername"].title()} total playtime is {plasttime} on home server {player["homeserver"].title()}"""


@log.catch
async def asyncgettip():
    tip = await asyncdbquery("SELECT * FROM tips WHERE active = True ORDER BY count ASC, random()", 'dict', 'one')
    await asyncdbupdate("UPDATE tips set count = {int(tip['count'] + 1} WHERE id = {tip['id'])}")
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
            players = await asyncdbquery(f"SELECT * FROM players WHERE server = '{inst}'", 'tuple', 'all')
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
        log.exception()
        message = f'Server {inst.capitalize()} does not exist.'
        await asyncserverchat(oinst, message)


async def asyncgetlastvote(inst):
    insts = dbquery(f"SELECT * FROM instances WHERE name = '{inst}'", 'dict', 'one')
    return insts['lastdinowipe']


def getlastvote(inst):
    flast = dbquery("SELECT lastdinowipe FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return ''.join(flast[0])


def isvoting(inst):
    for each in range(numinstances):
        if instance[each]['name'] == inst and 'votethread' in instance[each]:
            if instance[each]['votethread'].is_alive():
                return True
            else:
                return False


def populatevoters(inst):
    log.debug(f'populating vote table for {inst}')
    global votertable
    votertable = []
    pcnt = 0
    pdata = dbquery("SELECT * FROM players WHERE server = '%s'" % (inst,))
    for row in pdata:
        chktme = Now() - float(row[2])
        if chktme < 90:
            pcnt += 1
            newvoter = [row[0], row[1], 3]
            votertable.append(newvoter)
    log.debug(votertable)
    return pcnt


def setvote(whoasked, myvote):
    global votertable
    for each in votertable:
        if each[0] == getsteamid(whoasked):
            each[2] = myvote


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
    if not isvoting(inst):
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
                asyncio.create_task(asyncwritechat(inst, 'ALERT', f'### A wild dino wipe vote has failed with a NO vote from \
{whoasked.capitalize()}', wcstamp()))


def votingpassed():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    if vcnt == tvoters:
        return True
    else:
        return False


def enoughvotes():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    if vcnt >= tvoters / 2:
        return True
    else:
        return False


def resetlastvote(inst):
    newtime = Now()
    dbupdate("UPDATE instances SET lastvote = '%s' WHERE name = '%s'" % (newtime, inst))


def resetlastwipe(inst):
    newtime = Now()
    dbupdate("UPDATE instances SET lastdinowipe = '%s' WHERE name = '%s'" % (newtime, inst))


def howmanyvotes():
    vcnt = 0
    tvoters = 0
    for each in votertable:
        tvoters += 1
        if each[2] == 1 or each[2] == 2:
            vcnt += 1
    return vcnt, tvoters


@log.catch
def wipeit(inst):
    yesvoters, totvoters = howmanyvotes()
    log.log('VOTE', f'YES has won ({yesvoters}/{totvoters}), wild dinos are wiping on [{inst.title()}] in 15 seconds')
    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                     A Wild dino wipe vote has finished</>\n<RichColor Color="0,1,0,1">                     YES votes have won! ('%s' of '%s' Players)</>\n\n  <RichColor Color="1,1,0,1">               !! WIPING ALL WILD DINOS IN 10 SECONDS !!</>""" % (yesvoters, totvoters)
    subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
    writechat(inst, 'ALERT', f'### A wild dino wipe vote has won by YES vote ({yesvoters}/{totvoters}). \
Wiping wild dinos now.', wcstamp())
    sleep(7)
    subprocess.run('arkmanager rconcmd "Destroyall BeeHive_C" @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    sleep(3)
    subprocess.run('arkmanager rconcmd DestroyWildDinos @%s' % (inst), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    resetlastwipe(inst)
    log.log('WIPE', f'All wild dinos have been wiped from [{inst.title()}]')


def votingthread(inst, whoasked):
    log.log('VOTE', f'A wild dino wipe vote has started for [{inst.title()}] by [{whoasked.title()}]')
    global lastvoter
    global votestarttime
    global arewevoting
    global votertable
    arewevoting = True
    pon = populatevoters(inst)
    setvote(whoasked, 2)
    bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r<RichColor Color="1,0.65,0,1">             A Wild dino wipe vote has started with {pon} online players</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe\n                           Voting lasts 3 minutes"""
    subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)
    votestarttime = Now()
    sltimer = 0
    writechat(inst, 'ALERT', f'### A wild dino wipe vote has been started by {whoasked.capitalize()}', wcstamp())
    while arewevoting:
        sleep(5)
        if votingpassed() and Now() - votestarttime > 10:
            wipeit(inst)
            arewevoting = False
        elif Now() - votestarttime > Secs['3min']:
            if enoughvotes():
                wipeit(inst)
                arewevoting = False
            else:
                yesvoters, totvoters = howmanyvotes()
                subprocess.run('arkmanager rconcmd "ServerChat Not enough votes (%s of %s). voting has ended." @%s' %
                               (yesvoters, totvoters, inst), shell=True)
                log.log('VOTE', f'Voting has ended on [{inst.title()}] Not enough votes ({yesvoters}/{totvoters})')
                writechat(inst, 'ALERT', f'### Wild dino wipe vote failed with not enough votes ({yesvoters} of \
{totvoters})', wcstamp())
                arewevoting = False
        else:
            if sltimer == 120:
                log.log('VOTE', f'Sending voting waiting message to vote on [{inst.title()}]')
                bcast = f"""Broadcast <RichColor Color="0.0.0.0.0.0"> </>\r\r<RichColor Color="1,0.65,0,1">                  A Wild dino wipe vote is waiting for votes!</>\n\n<RichColor Color="1,1,0,1">                 Vote now by typing</><RichColor Color="0,1,0,1"> !yes or !no</><RichColor Color="1,1,0,1"> in global chat</>\n\n         A wild dino wipe does not affect tame dinos already knocked out\n                    A single NO vote will cancel the wipe"""
                subprocess.run(f"""arkmanager rconcmd '''{bcast}''' @'%s'""" % (inst,), shell=True)

        sltimer += 5
    log.debug(votertable)
    votertable = []
    lastvoter = Now()
    resetlastvote(inst)
    log.debug(f'voting thread has ended on {inst}')


async def asyncstartvoter(inst, whoasked):
    global instance
    if isvoting(inst):
        message = 'Voting has already started. cast your vote now'
        await asyncserverchat(inst, message)
    elif Now() - float(getlastvote(inst)) < Secs['4hour']:          # 4 hours between wipes
        rawtimeleft = Secs['4hour'] - (Now() - float(getlastvote(inst)))
        timeleft = playedTime(rawtimeleft)
        message = f'You must wait {timeleft} until the next wild wipe vote can start'
        await asyncserverchat(inst, message)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 4 hour timer')
    elif Now() - float(lastvoter) < Secs['10min']:                  # 10 min between attempts
        rawtimeleft = Secs['10min'] - (Now() - lastvoter)
        timeleft = playedTime(rawtimeleft)
        message = f'You must wait {timeleft} until the next wild wipe vote can start'
        await asyncserverchat(inst, message)
        log.log('VOTE', f'Vote start denied for [{whoasked.title()}] on [{inst.title()}] because 10 min timer')
    else:
        for each in range(numinstances):
            if instance[each]['name'] == inst:
                instance[each]['votethread'] = threading.Thread(name='%s-voter' % inst, target=votingthread, args=(inst, whoasked))
                instance[each]['votethread'].start()


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
    player = await asyncdbquery(f"SELECT * FROM players WHERE steamid = '{steamid}'", 'dict', 'one')
    if player:
        if player['discordid'] is None or player['discordid'] == '':
            rcode = ''.join(str(x) for x in random.sample(range(10), 4))
            log.log('PLAYER', f'Generated code [{rcode}] for link request from [{player["playername"].title()}] on [{inst.title()}]')
            await asyncdbupdate(f"""DELETE from linkrequests WHERE steamid = '{player["steamid"]}'""")
            await asyncdbupdate(f"""INSERT INTO linkrequests (steamid, name, reqcode) VALUES ('{player["steamid"]}', '{player["playername"]}', '{str(rcode)}')""")
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
        with aiofiles.open(f"/home/ark/shared/logs/{inst}/chat.log", "at") as f:
            await f.write(clog)
        await f.close()


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
    player = await asyncdbquery(f"SELECT * FROM players WHERE steamid = '{steamid}'", 'dict', 'one')
    if not player:
        welcom = threading.Thread(name='welcoming-%s' % steamid, target=newplayer, args=(steamid, playername, inst))
        welcom.start()
    else:
        playtime = int(float(tcdata['TotalPlayed'].replace(',', '')))
        rewardpoints = int(tcdata['Points'].replace(',', ''))
        if playername.lower() != player['playername'].lower():
            log.log('UPDATE', f'Player name update for [{player["playername"]}] to [{playername}]')
            await asyncdbupdate("UPDATE players SET playername = '%s' WHERE steamid = '%s'" % (playername, steamid))
        if inst == player['homeserver']:
            log.trace(f'player {playername} with steamid {steamid} was found on HOME server {inst}. updating info.')
            await asyncdbupdate("UPDATE players SET playedtime = '%s', rewardpoints = '%s' WHERE steamid = '%s'" %
                                (playtime, rewardpoints, steamid))
        else:
            log.trace(f'player {playername} with steamid {steamid} was found on NON-HOME server {inst}. updating info.')
            if int(player['transferpoints']) != int(rewardpoints):
                if int(rewardpoints) != 0:
                    if Now() - float(player['lastpointtimestamp']) > 60:
                        log.debug(f'adding {rewardpoints} non home points to {player["homeserver"]} transfer points for {playername} on {inst}')
                        await asyncdbupdate(f"UPDATE players SET transferpoints = '{int(rewardpoints)}', lastpointtimestamp = '{str(Now())}' WHERE steamid = '{str(steamid)}'")
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
        player = await asyncdbquery(f"SELECT * FROM players WHERE steamid = '{steamid}'", 'dict', 'one')
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
                        await asyncdbupdate(f"""UPDATE players SET transferpoints = {player["rewardpoints"]}, homeserver = '{ext}' WHERE steamid = '{steamid}'""")
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
    inlotto = await asyncdbquery(f"""SELECT * FROM lotteryplayers WHERE steamid = '{player["steamid"]}'""", 'dict', 'one')
    if inlotto:
        message = f'You are enterted into this lottery. Good Luck!'
    else:
        message = f'Type !lotto join to spend {lottery["buyin"]} points and enter into this lottery'
    await asyncserverchatto(inst, player['steamid'], message)


@log.catch
async def asynclottery(whoasked, lchoice, inst):
    lottery = await asyncdbquery("SELECT * FROM lotteryinfo WHERE completed = False", 'dict', 'one')
    steamid = await asyncgetsteamid(whoasked)
    player = await asyncdbquery(f"SELECT * FROM players WHERE steamid = '{steamid}'", 'dict', 'one')
    if lottery:
        if lchoice == 'join' or lchoice == 'enter':
            log.log('CMD', f'Responding to a [!lotto join] request from [{whoasked.title()}] on [{inst.title()}]')
            lpcheck = await asyncdbquery(f"""SELECT * FROM lotteryplayers WHERE steamid = '{player["steamid"]}'""", 'dict', 'one')
            # ltime = estshift(datetime.fromtimestamp(float(linfo[3]) + (Secs['hour'] * int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
            if lpcheck is None:
                await asyncdbupdate(f"""INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('{player["steamid"]}', '{player["playername"]}', '{Now(fmt='dt')}', 0)""")
                await asyncdbupdate(f"""UPDATE lotteryinfo SET payout = {lottery['payout'] + lottery['buyin'] * 2}, players = {lottery['players'] + 1} WHERE completed = False""")
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
    player = await asyncdbquery(f"SELECT * FROM players WHERE steamname = '{cleanstring(newline[1].strip())}'", 'dict', 'one')
    if player:
        steamid = player['steamid']
        await asyncdbupdate(f"""UPDATE players SET online = True, refreshsteam = True, refreshauctions = True, lastseen = '{Now()}', server = '{inst}', connects = {player["connects"] + 1} WHERE steamid = '{steamid}'""")
        if Now() - player['lastseen'] > 250:
            log.log('JOIN', f'Player [{player["playername"].title()}] joined the cluster on [{inst.title()}] Connections: {player["connects"] + 1}')
            message = f'{player["playername"].title()} has joined the server'
            await asyncserverchat(inst, message)
            asyncio.create_task(asyncwritechat(inst, 'ALERT', f'<<< {player["playername"].title()} has joined the server', wcstamp()))


@log.catch
def leavingplayerthread(player, inst):
    log.debug(f'Thread started for leaving player [{player["playername"].title()}] on [{inst.title()}]')
    timerstart = Now()
    killthread = False
    transferred = False
    while Now() - timerstart < 250 and not killthread:
        lplayer = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (player['steamid']), single=True, fmt='dict', fetch='one')
        if lplayer['server'] != inst:
            fromtxt = f'{player["playername"].title()} has transferred here from {inst.title()}'
            totxt = f'{player["playername"].title()} has transferred to {lplayer["server"].title()}'
            serverexec(['arkmanager', 'rconcmd', f'ServerChat {totxt}', f'@{inst}'], nice=19, null=True)
            writeglobal(lplayer["server"].lower(), 'ALERT', fromtxt)
            writechat(inst, 'ALERT', f'>><< {player["playername"].title()} has transferred from {inst.title()} to {lplayer["server"].title()}', wcstamp())
            log.log('XFER', f'Player [{player["playername"].title()}] has transfered from [{inst.title()}] to [{lplayer["server"].title()}]')
            transferred = True
            killthread = True
        sleep(1)
    if not transferred and Now() - lplayer['lastseen'] >= 240:
        steamid = player["steamid"]
        dbupdate(f"UPDATE players SET online = False, refreshsteam = True, refreshauctions = True WHERE steamid = '{steamid}'")
        log.log('LEAVE', f'Player [{player["playername"].title()}] left the cluster from [{inst.title()}]')
        mtxt = f'{player["playername"].title()} has logged off the cluster'
        serverexec(['arkmanager', 'rconcmd', f'ServerChat {mtxt}', f'@{inst}'], nice=19, null=True)
        log.debug(f'Thread ending for leaving player [{player["playername"].title()}]')


@log.catch
async def playerleave(line, inst):
    newline = line[:-15].split(':')
    player = await asyncdbquery(f"SELECT * FROM players WHERE steamname = '{cleanstring(newline[1].strip())}'", 'dict', 'one')
    if player:
        log.debug(f'Player [{player["playername"].title()}] Waiting on transfer from [{inst.title()}]')
        leaving = threading.Thread(name='leaving-%s' % player["steamid"], target=leavingplayerthread, args=(player, inst))
        leaving.start()
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
                asyncio.create_task(asyncwritechat(inst, whoname, cmsg.replace("'", ""), tstamp))
                asyncio.create_task(asyncwritechatlog(inst, whoname, cmsg, tstamp))


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
        await asyncglupdate(inst, 'ADMIN', line.replace('"', '').strip())
    elif line.find(" demolished a '") != -1 or line.find('Your Tribe killed') != -1:
        await asyncglupdate(inst, 'DEMO', line.replace('"', '').strip())
    elif line.find('released:') != -1:
        await asyncglupdate(inst, 'RELEASE', line.replace('"', '').strip())
    elif line.find('trapped:') != -1:
        await asyncglupdate(inst, 'TRAP', line.replace('"', '').strip())
    elif line.find(' was killed!') != -1 or line.find(' was killed by ') != -1:
        await asyncglupdate(inst, 'DEATH', line.replace('"', '').strip())
    elif line.find('Tamed a') != -1:
        await asyncglupdate(inst, 'TAME', line.replace('"', '').strip())
    elif line.find(" claimed '") != -1 or line.find(" unclaimed '") != -1:
        await asyncglupdate(inst, 'CLAIM', line.replace('"', '').strip())
    elif line.find(' was added to the Tribe by ') != -1 or line.find(' was promoted to ') != -1 or line.find(' was demoted from ') != -1 \
    or line.find(' uploaded a') != -1 or line.find(' downloaded a dino:') != -1 or line.find(' requested an Alliance ') != -1 \
    or line.find(' Tribe to ') != -1 or line.find(' was removed from the Tribe!') != -1 or line.find(' set to Rank Group ') != -1 \
    or line.find(' requested an Alliance with ') != -1 or line.find(' was added to the Tribe!') != -1:
        await asyncglupdate(inst, 'TRIBE', line.replace('"', '').strip())
    elif line.find('starved to death!') != -1:
        await asyncglupdate(inst, 'DECAY', line.replace('"', '').strip())
    elif line.find('was auto-decay destroyed!') != -1 or line.find('was destroyed!') != -1:
        await asyncglupdate(inst, 'DECAY', line.replace('"', '').strip())
    elif line.startswith('Error:'):
        await asyncglupdate(inst, 'UNKNOWN', line.replace('"', '').strip())
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
                                            writeglobal(minst, whoname, cmsg)
                                            asyncio.create_task(asyncwritechat('generalchat', whoname, cmsg, tstamp))
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
                    tip = await asyncgettip()
                    message = tip['tip']
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
async def checkcommands(inst, dtime):
    while True:
        try:
            cmdpipe = serverexec(['arkmanager', 'rconcmd', 'getgamelog', f'@{inst}'], nice=5, null=False)
            b = cmdpipe.stdout.decode("utf-8")
            for line in iter(b.splitlines()):
                asyncio.create_task(asyncprocessline(inst, line))
            await asyncio.sleep(dtime)
        except:
            log.exception(f'Exception in checkcommands loop')


@log.catch
def clisten(inst, dtime):
    log.debug(f'starting the command listener thread for {inst}')
    log.patch(lambda record: record["extra"].update(instance=inst))
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    #asyncloop = asyncio.new_event_loop()
    #asyncloop.call_at(2, checkcommands, inst, dtime)
    #try:
    #    asyncloop.run_forever()
    #finally:
    #    asyncloop.run_until_complete(asyncloop.shutdown_asyncgens())
    #    asyncloop.close()
    asyncio.run(checkcommands(inst, dtime))
