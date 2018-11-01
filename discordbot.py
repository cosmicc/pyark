#!/usr/bin/python3

from auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats
from clusterevents import getcurrenteventinfo, getlasteventinfo, getnexteventinfo
from configreader import config
from datetime import datetime
from dbhelper import dbquery, dbupdate
from timehelper import elapsedTime, playedTime, estshift, wcstamp, epochto
import asyncio
import discord
import logging
import socket
import time

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

client = discord.Client()

channel = discord.Object(id=config.get('general', 'discordchatchan'))
channel2 = discord.Object(id=config.get('general', 'discordgenchan'))


def getlastwipe(inst):
    lastwipe = dbquery('SELECT lastdinowipe FROM instances WHERE name = "%s"' % (inst,))
    return ''.join(lastwipe[0])


def getlastrestart(inst):
    lastwipe = dbquery('SELECT lastrestart FROM instances WHERE name = "%s"' % (inst,))
    return ''.join(lastwipe[0])


def getlottowinnings(pname):
    pwins = dbquery('SELECT type, payoutitem FROM lotteryinfo WHERE winner = "%s"' % (pname,))
    totpoints = 0
    twins = 0
    for weach in pwins:
        if weach[0] == 'points':
            totpoints = totpoints + int(weach[1])
        twins += 1
    return twins, totpoints


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = dbquery('SELECT * from players WHERE playername = "%s"' % (whos,), fetch='one')
    elif whos == "ALERT" or isindb:
        dbupdate('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ("%s", "%s", "%s", "%s")' %
                 (inst, whos, msg, tstamp))


def writeglobal(inst, whos, msg):
    dbupdate('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ("%s", "%s", "%s", "%s")' %
             (inst, whos, msg, time.time()))


def islinkeduser(duser):
    islinked = dbquery('SELECT * FROM players WHERE discordid = "%s"' % (duser.lower(),))
    if islinked:
        return True
    else:
        return False


def setprimordialbit(steamid, pbit):
    dbupdate('UPDATE players SET primordialbit = "%s" WHERE steamid = "%s"' % (pbit, steamid))


def discordbot():
    async def chatbuffer():
        await client.wait_until_ready()
        while not client.is_closed:
            try:
                cbuff = dbquery('SELECT * FROM chatbuffer')
                if cbuff:
                    for each in cbuff:
                        if each[0] == "generalchat":
                            msg = each[2]
                            await client.send_message(channel2, msg)
                            await asyncio.sleep(2)
                        else:
                            if each[1] == "ALERT":
                                msg = f'{each[3]} [{each[0].capitalize()}] {each[2]}'
                            else:
                                msg = f'{each[3]} [{each[0].capitalize()}] {each[1].capitalize()} {each[2]}'
                            await client.send_message(channel, msg)
                            await asyncio.sleep(2)
                    dbupdate('DELETE FROM chatbuffer')
                now = float(time.time())
                cbuffr = dbquery('SELECT * FROM players WHERE lastseen < "%s" AND lastseen > "%s"' % (now - 40, now - 45))
                if cbuffr:
                    for reach in cbuffr:
                        log.info(f'{reach[1]} has left the server {reach[3]}')
                        mt = f'{reach[1].capitalize()} has left the server'
                        writeglobal(reach[3], 'ALERT', mt)
                        writechat(reach[3], 'ALERT', f'>>> {reach[1].capitalize()} has left the server', wcstamp())
            except:
                log.critical('Critical Error in Chat Buffer discord writer!', exc_info=True)
            await asyncio.sleep(5)

    def savediscordtodb(author):
        didexists = dbquery('SELECT * FROM discordnames WHERE discordname = "%s"' % (str(author),), fetch='one')
        if not didexists:
            dbupdate('INSERT INTO discordnames (discordname) VALUES ("%s")' % (str(author),))

    @client.event
    async def on_member_join(member):
        server = member.server
        fmt = 'Welcome to the Galaxy Cluster Ultimate Extinction Core Server Discord.\nIf you are already a player \
on the servers, you can !linkme in game to link your discord account to your ark player.\n!servers for links to the \
servers, !mods for a link to the mod collection, !help for everything else\nIf you need any help ask in #general-chat'
        await client.send_message(server, fmt.format(member, server))

    @client.event
    async def on_ready():
        log.info(f'discord logged in as {client.user.name} id {client.user.id}')

    @client.event
    async def on_message(message):
        savediscordtodb(message.author)
        if message.content.startswith('!who') or message.content.startswith('!whoson') \
                or message.content.startswith('!whosonline'):
            log.info('responding to whos online request from discord')
            potime = 40
            srvrs = dbquery('SELECT * FROM instances')
            for each in srvrs:
                flast = dbquery('SELECT * FROM players WHERE server = "%s"' % (each[0],))
                pcnt = 0
                plist = ''
                for row in flast:
                    chktme = time.time() - float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].title())
                        else:
                            plist = plist + ', %s' % (row[1].title())
                if pcnt != 0:
                    msg = f'{each[0].capitalize()} has {pcnt} players online: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].capitalize()} has no players online.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!recent') or message.content.startswith('!whorecent') \
                or message.content.startswith('!lasthour'):
            # await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            potime = 3600
            srvrs = dbquery('SELECT * FROM instances')
            for each in srvrs:
                flast = dbquery('SELECT * FROM players WHERE server = "%s"' % (each[0],))
                pcnt = 0
                plist = ''
                for row in flast:
                    chktme = time.time() - float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].title())
                        else:
                            plist = plist + ', %s' % (row[1].title())
                if pcnt != 0:
                    msg = f'{each[0].capitalize()} has had {pcnt} players in last hour: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].capitalize()} has had no players in last hour.'
                    await client.send_message(message.channel, msg)
        elif message.content.startswith('!lastseen'):
            newname = message.content.split(' ')
            if len(newname) > 1:
                log.info(f'responding to lastseen request for {newname[1]} from discord')
                seenname = newname[1]
                flast = dbquery('SELECT * FROM players WHERE playername = "%s"' % (seenname,), fetch='one')
                if not flast:
                    msg = f'No player was found with name {seenname}'
                    await client.send_message(message.channel, msg)
                else:
                    plasttime = elapsedTime(time.time(), float(flast[2]))
                    if plasttime != 'now':
                        msg = f'{seenname.capitalize()} was last seen {plasttime} ago on {flast[3]}'
                        await client.send_message(message.channel, msg)
                    else:
                        msg = f'{seenname.capitalize()} is online now on {flast[3]}'
                        await client.send_message(message.channel, msg)
            else:
                msg = f'You must specify a player name to search for'
                await client.send_message(message.channel, msg)

        elif message.content.startswith('!lastwipe'):
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1]
                lastwipet = elapsedTime(time.time(), float(getlastwipe(instr)))
                msg = f'Last wild dino wipe for {instr.capitalize()} was {lastwipet} ago'
                await client.send_message(message.channel, msg)
            else:
                srvrs = dbquery('SELECT * FROM instances')
                for each in srvrs:
                    lastwipet = elapsedTime(time.time(), float(getlastwipe(each[0])))
                    msg = f'Last wild dino wipe for {each[0].capitalize()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)
        elif message.content.startswith('!lastrestart'):
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1]
                lastrestartt = elapsedTime(time.time(), float(getlastrestart(instr)))
                msg = f'Last server restart for {instr.capitalize()} was {lastrestartt} ago'
                await client.send_message(message.channel, msg)
            else:
                srvrs = dbquery('SELECT * FROM instances')
                for each in srvrs:
                    lastwipet = elapsedTime(time.time(), float(getlastrestart(each[0])))
                    msg = f'Last server restart for {each[0].capitalize()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!help'):
            msg = f'Commands: !mods, !ec, !rewards, !servers, !event, !decay, !myinfo, !who, !lasthour, !lastday, !lastnew, !linkme, !kickme, !lotto, !lastlotto, !winners, !timeleft, !lastwipe, !lastrestart, !lastseen, !primordial\n\nCommand descriptions pinned in #game-help channel\nCommands can be privately messaged directly to the bot or publicly in any channel'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!vote') or message.content.startswith('!startvote'):
            msg = f'Voting is only allowed in-game'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!whotoday') or message.content.startswith('!today') \
                or message.content.startswith('!lastday'):
            # await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            potime = 86400
            srvrs = dbquery('SELECT * FROM instances')
            for each in srvrs:
                flast = dbquery('SELECT * FROM players WHERE server = "%s"' % (each[0],))
                pcnt = 0
                plist = ''
                for row in flast:
                    chktme = time.time() - float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].capitalize())
                        else:
                            plist = plist + ', %s' % (row[1].capitalize())
                if pcnt != 0:
                    msg = f'{each[0].capitalize()} has had {pcnt} players today: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].capitalize()} has had no players today.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!event') or message.content.startswith('!events'):
            whofor = str(message.author).lower()
            log.info(f'event request from {whofor} on discord')
            lastevent = getlasteventinfo()
            currentevent = getcurrenteventinfo()
            nextevent = getnexteventinfo()
            msg = ''
            if lastevent and lastevent is not None:
                msg = msg + f'Last Event was: {lastevent[4]} ended {elapsedTime(lastevent[3], time.time())} ago\n'
            if currentevent and currentevent is not None:
                msg = msg + f'Current Event is: {currentevent[4]} - {currentevent[5]}\nCurrent Event ends {epochto(currentevent[3], 'string')} EST in {elapsedTime(currentevent[3], time.time())}\n'
            else:
                msg = msg + f'There is no Event currently running\n'
            if nextevent and nextevent is not None:
                msg = msg + f'Next Event is: {nextevent[4]} and starts {epochto(nextevent[2], 'string')} EST in {elapsedTime(nextevent[2], time.time())}\n'
            else:
                msg = msg + f'Next Event is not scheduled yet.\n'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!decay') or message.content.startswith('!expire'):
            whofor = str(message.author).lower()
            log.info(f'decay request from {whofor} on discord')
            kuser = dbquery('SELECT * FROM players WHERE discordid = "%s"' % (whofor,), fetch='one')
            msg = f'Galaxy Cluster structure & dino decay times:\nDinos: 30 Days, Tek: 38 Days, Metal: 30 Days, Stone: 23 Days, Wood: 15 Days, Thatch: 7.5 Days, Greenhouse: 9.5 Days (Use MetalGlass for 30 Day Greenhouse).\n'
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'decay request from {whofor} public only, no account linked')
                    msg = msg + f'Your discord account is not linked, I cannot determine your decay time left.'
                else:
                    log.info(f'decay request from {whofor} accepted, showing detailed info')
                    msg = msg + f'Assuming you were in render range and no other tribe members on, decay time left since last online for {kuser[1].capitalize()}:\n'
                    woodtime = 1310400
                    stonetime = 1969200
                    metaldinotime = 2592000
                    now = time.time()
                    try:
                        etime = now - float(kuser[2])
                        wdate = estshift(datetime.fromtimestamp(float(kuser[2]) + woodtime)).strftime('%a, %b %d %I:%M %p')
                        sdate = estshift(datetime.fromtimestamp(float(kuser[2]) + stonetime)).strftime('%a, %b %d %I:%M %p')
                        mdate = estshift(datetime.fromtimestamp(float(kuser[2]) + metaldinotime)).strftime('%a, %b %d %I:%M %p')
                        if woodtime > etime:
                            woodt = f'Your Wood Expires: {wdate} EST - {elapsedTime(woodtime, etime)} Left'
                        elif etime < 3600:
                            woodt = f'Your Wood Expires: 15 Days'
                        else:
                            woodt = 'Your Wood Structures have passed Experation Time!'
                        if stonetime > etime:
                            stonet = f'Your Stone Expires: {sdate} EST - {elapsedTime(stonetime, etime)} Left'
                        elif etime < 3600:
                            stonet = f'Your Stone Expires: {sdate} EST - {elapsedTime(stonetime)} Left'
                        else:
                            stonet = 'Your Stone Structures have passwd Experation Time!'
                        if metaldinotime > etime:
                            metalt = f'Your Metal & Dinos Expire: {mdate} EST - {elapsedTime(metaldinotime, etime)} Left'
                        elif etime < 3600:
                            metalt = f'Your Metal & Dinos Expire: 30 Days'
                        else:
                            metalt = 'Your Metal Structures & Dinos have passed Experation Time!'
                        msg = msg + f'{woodt}\n{stonet}\n{metalt}'
                    except:
                        log.critical('Critical Error in decay calculation!', exc_info=True)
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!kickme') or message.content.startswith('!kick'):
            whofor = str(message.author).lower()
            log.info(f'kickme request from {whofor} on discord')
            kuser = dbquery('SELECT * FROM players WHERE discordid = "%s"' % (whofor,), fetch='one')
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'kickme request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not connected to a player yet.'
                    await client.send_message(message.channel, msg)
                else:
                    if time.time() - float(kuser[2]) > 300:
                        log.info(f'kickme request from {whofor} denied, not connected to a server')
                        msg = f'You are not connected to any servers'
                        await client.send_message(message.channel, msg)
                    else:
                        log.info(f'kickme request from {whofor} passed, kicking player on {kuser[3]}')
                        msg = f'Kicking {kuser[1].capitalize()} from the {kuser[3].capitalize()} server'
                        await client.send_message(message.channel, msg)
                        dbupdate('INSERT INTO kicklist (instance,steamid) VALUES (%s,%s)' % (kuser[3], kuser[0]))
        elif message.content.startswith('!home') or message.content.startswith('!myhome'):
            newsrv = message.content.split(' ')
            whofor = str(message.author).lower()
            kuser = dbquery('SELECT * FROM players WHERE discordid = "%s"' % (whofor,), fetch='one')
            if kuser:
                if len(newsrv) > 1:
                    log.info(f'home server change request for {kuser[1]}')
                    msg = f'You have to type !myhome on your current home server {kuser[15].capitalize()} \
to change home servers'
                    await client.send_message(message.channel, msg)
                else:
                    log.info(f'home server request granted for {kuser[1]}')
                    msg = f'Your home server is: {kuser[15].capitalize()}'
                    await client.send_message(message.channel, msg)
            else:
                log.info(f'home server request from {whofor} denied, no account linked')
                msg = f"Your discord account is not connected to a player yet, so I don't know your home server."
                await client.send_message(message.channel, msg)

        elif message.content.startswith('!winners') or message.content.startswith('!lottowinners'):
            whofor = str(message.author).lower()
            log.info(f'lotto winners request from {whofor} on discord')
            last5 = dbquery('SELECT * FROM lotteryinfo WHERE winner != "Incomplete" AND winner != "None" ORDER BY id DESC LIMIT 5')
            top5 = dbquery('SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 5')
            msg = 'Last 5 Lottery Winners:\n'
            now = time.time()
            try:
                for peach in last5:
                    msg = msg + f'{peach[7].capitalize()} won {peach[2]} Points  {elapsedTime(now, int(peach[5])*3600 + float(peach[3]))} ago\n'
                msg = msg + '\nTop 5 All Time Lottery Winners:\n'
                ccount = 0
                newtop = top5.copy()
                for heach in newtop:
                    ccount += 1
                    msg = msg + f'#{ccount} {heach[1].capitalize()} with {heach[18]} Lottery Wins.  {heach[19]} Points Total Won.\n'
            except:
                log.critical('Critical Error determining lottery winners!', exc_info=True)
            await client.send_message(message.channel, msg)


        elif message.content.startswith('!myinfo') or message.content.startswith('!mypoints'):
            whofor = str(message.author).lower()
            log.info(f'myinfo request from {whofor} on discord')
            kuser = dbquery('SELECT * FROM players WHERE discordid = "%s"' % (whofor,), fetch='one')
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'myinfo request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not connected to a player yet.'
                    await client.send_message(message.channel, msg)
                else:
                    log.info(f'myinfo request from {whofor} passed, showing info for player {kuser[1]}')
                    pauctions = fetchauctiondata(kuser[0])
                    au1, au2, au3 = getauctionstats(pauctions)
                    writeauctionstats(kuser[0], au1, au2, au3)
                    ptime = playedTime(float(kuser[4]))
                    ptr = elapsedTime(float(time.time()), float(kuser[2]))
                    msg = f'Your current ARc reward points: {kuser[5]}\nLast played on {kuser[3].capitalize()} {ptr} ago.\n'
                    msg = msg + f'Your home server is: {kuser[15].capitalize()}\nYour total play time is {ptime}\n'
                    msg = msg + f'You have {au1} current auctions: {au2} Items, {au3} Dinos\n'
                    tpwins, twpoints = getlottowinnings(kuser[1])
                    msg = msg + f'Total Lotterys Won: {tpwins}  Total Lottery Points Won: {twpoints} Points\n'
                    woodtime = 1296000
                    stonetime = 1987200
                    metaldinotime = 2624400
                    now = time.time()
                    try:
                        etime = now - float(kuser[2])
                        wdate = estshift(datetime.fromtimestamp(float(kuser[2]) + woodtime)).strftime('%a, %b %d %I:%M %p')
                        sdate = estshift(datetime.fromtimestamp(float(kuser[2]) + stonetime)).strftime('%a, %b %d %I:%M %p')
                        mdate = estshift(datetime.fromtimestamp(float(kuser[2]) + metaldinotime)).strftime('%a, %b %d %I:%M %p')
                        if woodtime > etime:
                            woodt = f'Your Wood Structures Expire: {wdate} EST - {elapsedTime(woodtime, etime)} Left'
                        elif etime < 3600:
                            woodt = f'Your Wood Structures Expire: 15 Days Left'
                        else:
                            woodt = 'Your Wood Structures have passed Experation Time!'
                        if stonetime > etime:
                            stonet = f'Your Stone Structures Expire: {sdate} EST - {elapsedTime(stonetime, etime)} Left'
                        elif etime < 3600:
                            stonet = f'Your Stone Structures Expire: 23 Days Left'
                        else:
                            stonet = 'Your Stone Structures have passwd Experation Time!'
                        if metaldinotime > etime:
                            metalt = f'Your Metal & Dinos Expire: {mdate} EST - {elapsedTime(metaldinotime, etime)} Left'
                        elif etime < 3600:
                            metalt = f'Your Metal & Dinos Expire: 30 Days Left'
                        else:
                            metalt = 'Your Metal Structures & Dinos have passed Experation Time!'
                        msg = msg + f'{woodt}\n{stonet}\n{metalt}'
                    except:
                        log.critical('Critical Error in decay calculation!', exc_info=True)
                    await client.send_message(message.channel, msg)
        elif message.content.startswith('!newest') or message.content.startswith('!lastnew'):
            lastseens = dbquery('SELECT firstseen FROM players')
            lsplayer = dbquery('SELECT * from players WHERE firstseen = "%s"' % (max(lastseens,)))
            log.info(f'responding to lastnew request on discord')
            lspago = elapsedTime(time.time(), float(lsplayer[6]))
            msg = f'Newest cluster player is {lsplayer[1].capitalize()} online {lspago} ago on {lsplayer[3]}'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!topplayed') or message.content.startswith('!topplayed'):
            lsplayer = dbquery('SELECT * from players ORDER BY playedtime DESC LIMIT 10')
            log.info(f'responding to topplayed request on discord')
            msg = ''
            nom = 0
            for each in lsplayer:
                nom += 1
                lspago = playedTime(float(each[4]))
                msg = msg + f'#{nom} {each[1].capitalize()} at {lspago}\n'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!mods'):
            whofor = str(message.author).lower()
            msg = f'Galaxy Cluster Ultimate Extinction Core Mod Collection:\nhttps://steamcommunity.com/sharedfiles/filedetails/?id=1475281369'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!rewards') or message.content.startswith('!currency'):
            whofor = str(message.author).lower()
            msg = f'Galaxy Cluster Ultimate Extinction Core Rewards Vault, ARc Points, Home Server, Lotterys, & Currency:\nhttps://docs.google.com/document/d/154QjLnw4hjxe_DtiTqfSwINsKdUp9Iz3M_umcI5zkRk/edit?usp=sharing'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!ec'):
            whofor = str(message.author).lower()
            msg = f'Extinction Core Info:\nhttps://steamcommunity.com/workshop/filedetails/discussion/817096835/1479857071254169967\nhttp://extinctioncoreark.wikia.com/wiki/Extinction_Core_Wiki\nhttps://docs.google.com/spreadsheets/d/1GtqBvFK0R0VI7dj7CdkXEuQydqw3xjITZmc0qD95Kug/edit?usp=sharing'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!servers'):
            whofor = str(message.author).lower()
            dbsvr = dbquery('SELECT * FROM instances')
            # msg = 'Galaxy Cluster Ultimate Extinction Core Servers:\n'
            for instt in dbsvr:
                if int(instt[9]) == 0:
                    onl = 'OFFLINE'
                    pcnt = 0
                elif int(instt[9]) == 1:
                    onl = 'ONLINE'
                    flast = dbquery('SELECT * FROM players WHERE server = "%s"' % (instt[0],))
                    pcnt = 0
                    for row in flast:
                        chktme = time.time() - float(row[2])
                        if chktme < 40:
                            pcnt += 1
                msg = f'Server {instt[0].capitalize()} is {onl} Players ({pcnt}/50) - {instt[15]} \
- {instt[16]} - {instt[17]}\n'
                await client.send_message(message.channel, msg)
                time.sleep(.5)

        elif message.content.startswith('!lastlotto') or message.content.startswith('!lastlottery'):
            whofor = str(message.author).lower()
            linfo = dbquery('SELECT * FROM lotteryinfo WHERE winner != "Incomplete" ORDER BY id DESC', fetch='one')
            if linfo[1] == 'item':
                msg = f'Last lottery was {linfo[2]} won by {linfo[7].capitalize()}. \
{elapsedTime(time.time(),linfo[3])} ago'
                await client.send_message(message.channel, msg)
            elif linfo[1] == 'points':
                if linfo[7] == 'None':
                    msg = f'Last lottery was {linfo[2]} Arc reward points not won because lack of players. \
{elapsedTime(time.time(),linfo[3])} ago'
                else:
                    msg = f'Last lottery was {linfo[2]} Arc reward points won by {linfo[7].capitalize()}. \
{elapsedTime(time.time(),linfo[3])} ago'
                await client.send_message(message.channel, msg)
        elif message.content.startswith('!lotto') or message.content.startswith('!lottery'):
            whofor = str(message.author).lower()
            newname = message.content.split(' ')
            linfo = dbquery('SELECT * FROM lotteryinfo WHERE winner = "Incomplete"', fetch='one')
            if len(newname) > 1:
                if newname[1] == 'enter' or newname[1] == 'join':
                    lpinfo = dbquery('SELECT * FROM players WHERE discordid = "%s"' % (whofor,), fetch='one')
                    if not lpinfo:
                        log.info(f'lottery join request from {whofor} denied, account not linked')
                        msg = f'Your discord account must be linked to your player account to join a lottery from \
discord.\nType !linkme in game'
                        await client.send_message(message.channel, msg)
                    else:
                        whofor = lpinfo[1]
                        lpcheck = dbquery('SELECT * FROM lotteryplayers WHERE steamid = "%s"' % (lpinfo[0],), fetch='one')
                        if linfo[1] == 'points':
                            lfo = 'ARc Rewards Points'
                        else:
                            lfo = linfo[2]
                        ltime = estshift(datetime.fromtimestamp(float(linfo[3]) +
                                                                (3600 * int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
                        if lpcheck is None:
                            dbupdate('INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES \
                                     (%s, %s, %s, %s)' % (lpinfo[0], lpinfo[1], time.time(), 0))
                            if linfo[1] == 'points':
                                dbupdate('UPDATE lotteryinfo SET payoutitem = "%s" WHERE winner = "Incomplete"' %
                                         (str(int(linfo[2]) + int(linfo[4])), ))
                            dbupdate('UPDATE lotteryinfo SET players = "%s" WHERE id = "%s"' % (int(linfo[6]) + 1, linfo[0]))
                            msg = f'You have been added to the {lfo} lottery!\nA winner will be choosen on {ltime} \
in {elapsedTime(float(linfo[3])+(3600*int(linfo[5])),time.time())}. Good Luck!'
                            await client.send_message(message.channel, msg)
                            log.info(f'player {whofor} has joined the current active lottery.')
                        else:
                            msg = f'You are already participating in this lottery for {lfo}.\nLottery ends {ltime} \
in {elapsedTime(float(linfo[3])+(3600*int(linfo[5])),time.time())}'
                            await client.send_message(message.channel, msg)
            else:
                if linfo:
                    if linfo[1] == 'points':
                        msg = f'Current lottery is up to {linfo[2]} ARc reward points.'
                    else:
                        msg = f'Current lottery is for a {linfo[2]}.'
                    await client.send_message(message.channel, msg)
                    msg = f'{linfo[6]} players have entered into this lottery so far.'
                    await client.send_message(message.channel, msg)
                    ltime = estshift(datetime.fromtimestamp(float(linfo[3]) +
                                                            (3600 * int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
                    msg = f'Lottery ends {ltime} EST in {elapsedTime(float(linfo[3])+(3600*int(linfo[5])),time.time())}'
                    await client.send_message(message.channel, msg)
                    msg = f'Type !lotto enter to join the lottery'
                    await client.send_message(message.channel, msg)
                else:
                    msg = 'There are no lotterys currently underway.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!primordial'):
            whofor = str(message.author).lower()
            pplayer = dbquery('SELECT * from players WHERE discordid = "%s"' % (whofor,), fetch='one')
            if not pplayer:
                msg = f'Your discord account needs to be linked to you game account first. !link in game'
                await client.send_message(message.channel, msg)
            else:
                if int(pplayer[14]) == 1:
                    setprimordialbit(pplayer[0], 0)
                    msg = f'Your primordial server restart warning is now OFF'
                    await client.send_message(message.channel, msg)
                else:
                    setprimordialbit(pplayer[0], 1)
                    msg = f'Your primordial server restart warning is now ON'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!link') or message.content.startswith('!linkme'):
            whofor = str(message.author).lower()
            user = message.author
            log.info(f'responding to link account request on discord from {whofor}')
            sw = message.content.split(' ')
            dplayer = dbquery('SELECT * FROM players WHERE discordid == "%s"' % (whofor,), fetch='one')
            if dplayer:
                log.info(f'link account request on discord from {whofor} denied, already linked')
                msg = f'Your discord account is already linked to your game account'
                await client.send_message(message.channel, msg)
            else:
                if len(sw) > 1:
                    rcode = sw[1]
                    reqs = dbquery('SELECT * FROM linkrequests WHERE reqcode == "%s"' % (rcode,), fetch='one')
                    if reqs:
                        log.info(f'link account request on discord from {whofor} accepted. \
{reqs[1]} {whofor} {reqs[0]}')
                        dbupdate('UPDATE players SET discordid = "%s" WHERE steamid = %s' % (whofor, reqs[0]))
                        dbupdate('DELETE FROM linkrequests WHERE reqcode = "%s"' % (rcode,))
                        msg = f'Your discord account [{whofor}] is now linked to your player {reqs[1]}'
                        await client.send_message(message.channel, msg)
                        role = discord.utils.get(user.server.roles, name="Linked Player")
                        await client.add_roles(user, role)
                    else:
                        log.info(f'link account request on discord from {whofor} denied, code not found')
                        msg = f'That link request code was not found. You must start a link request \
in-game to get your code'
                        await client.send_message(message.channel, msg)
                else:
                    log.info(f'link account request on discord from {whofor} denied, no code specified')
                    msg = f'You must start a link request in-game first to get a code, then specify that code here, \
to link your account'
                    await client.send_message(message.channel, msg)
        elif str(message.channel) == 'server-chat':
            whos = dbquery('SELECT playername FROM players WHERE discordid = "%s"' % (str(message.author).lower(),), fetch='one')
            if whos:
                writeglobal('discord', whos[0], str(message.content))
    client.loop.create_task(chatbuffer())
    while True:
        try:
            client.run(config.get('general', 'discordtoken'))
        except:
            log.critical('Critical Error in Discord Bot Routine!', exc_info=True)
