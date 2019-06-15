from datetime import timedelta
from clusterevents import getcurrenteventinfo, getlasteventinfo, getnexteventinfo
from modules.auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats
from modules.configreader import discord_channel, discord_serverchat, discordtoken
from modules.dbhelper import dbquery, dbupdate
from modules.instances import instancelist, getlastwipe, getlastrestart, writechat, writeglobal
from modules.players import getplayer, getplayerlastserver, getplayersonline, getlastplayersonline, getplayerlastseen, getplayerstoday, getnewestplayers, gettopplayedplayers
from modules.timehelper import elapsedTime, playedTime, wcstamp, epochto, Now, Secs, datetimeto, d2dt_maint
from time import sleep
from lottery import totallotterydeposits
from os import system
import asyncio
import discord
import logging
import socket

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

client = discord.Client()

channel = discord.Object(id=discord_serverchat)
channel2 = discord.Object(id=discord_channel)


def writediscord(msg, tstamp):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % ('generalchat', 'ALERT', msg, tstamp))


def getlottowinnings(pname):
    pwins = dbquery("SELECT payout FROM lotteryinfo WHERE winner = '%s'" % (pname,))
    totpoints = 0
    twins = 0
    for weach in pwins:
        totpoints = totpoints + int(weach[0])
        twins += 1
    return twins, totpoints


def setprimordialbit(steamid, pbit):
    dbupdate("UPDATE players SET primordialbit = '%s' WHERE steamid = '%s'" % (pbit, steamid))


def discordbot():
    async def chatbuffer():
        await client.wait_until_ready()
        while not client.is_closed:
            try:
                cbuff = dbquery("SELECT * FROM chatbuffer")
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
                    dbupdate("DELETE FROM chatbuffer")
                now = Now()
                cbuffr = dbquery("SELECT * FROM players WHERE lastseen < '%s' AND lastseen > '%s'" % (now - 40, now - 44))
                if cbuffr:
                    for reach in cbuffr:
                        log.info(f'{reach[1]} has left the server {reach[3]}')
                        mt = f'{reach[1].capitalize()} has left the server'
                        writeglobal(reach[3], 'ALERT', mt)
                        writechat(reach[3], 'ALERT', f'>>> {reach[1].title()} has left the server', wcstamp())
            except:
                log.critical('Critical Error in Chat Buffer discord writer!', exc_info=True)
            await asyncio.sleep(5)

    def savediscordtodb(author):
        didexists = dbquery("SELECT * FROM discordnames WHERE discordname = '%s'" % (str(author),), fetch='one')
        if not didexists:
            dbupdate("INSERT INTO discordnames (discordname) VALUES ('%s')" % (str(author),))

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
        if message.content.startswith('!help'):
            msg = f'Commands: !mods, !ec, !rewards, !servers, !event, !decay, !myinfo, !who, !lasthour, !lastday, !lastnew, !linkme, !kickme, !lotto, !lastlotto, !winners, !timeleft, !lastwipe, !lastrestart, !lastseen, !primordial\n\nCommand descriptions pinned in #game-help channel\nCommands can be privately messaged directly to the bot or publicly in any channel'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!whotoday') or message.content.startswith('!today') \
                or message.content.startswith('!lastday'):
            log.info('responding to recent players request from discord')
            for each in instancelist():
                pcnt = getplayerstoday(each, fmt='count')
                plist = getplayerstoday(each, fmt='string')
                if pcnt != 0:
                    msg = f'{each[0].capitalize()} has had {pcnt} players today: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].capitalize()} has had no players today.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!who') or message.content.startswith('!whoson') \
                or message.content.startswith('!whosonline'):
            log.info('responding to whos online request from discord')
            for each in instancelist():
                pcnt = getplayersonline(each, fmt='count')
                plist = getplayersonline(each, fmt='string', case='title')
                if pcnt != 0:
                    msg = f'{each.capitalize()} has {pcnt} players online: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each.capitalize()} has no players online.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!recent') or message.content.startswith('!whorecent') \
                or message.content.startswith('!lasthour'):
            # await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            plist = getlastplayersonline('all', fmt='string', case='title')
            msg = f'Last 5 recent players: {plist}'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!lastseen'):
            newname = message.content.split(' ')
            if len(newname) > 1:
                log.info(f'responding to lastseen request for {newname[1]} from discord')
                seenname = newname[1]
                flast = getplayerlastseen(playername=seenname)
                if not flast:
                    msg = f'No player was found with name {seenname}'
                    await client.send_message(message.channel, msg)
                else:
                    plasttime = elapsedTime(Now(), flast)
                    srv = getplayerlastserver(playername=seenname)
                    if plasttime != 'now':
                        msg = f'{seenname.title()} was last seen {plasttime} ago on {srv.capitalize()}'
                        await client.send_message(message.channel, msg)
                    else:
                        msg = f'{seenname.title()} is online now on {srv.capitalize()}'
                        await client.send_message(message.channel, msg)
            else:
                msg = f'You must specify a player name to search for'
                await client.send_message(message.channel, msg)

        elif message.content.startswith('!lastwipe'):
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1]
                lastwipet = elapsedTime(Now(), getlastwipe(instr))
                msg = f'Last wild dino wipe for {instr.capitalize()} was {lastwipet} ago'
                await client.send_message(message.channel, msg)
            else:
                for each in instancelist():
                    lastwipet = elapsedTime(Now(), getlastwipe(each))
                    msg = f'Last wild dino wipe for {each.capitalize()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!lastrestart'):
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1]
                lastrestartt = elapsedTime(Now(), getlastrestart(instr))
                msg = f'Last server restart for {instr.capitalize()} was {lastrestartt} ago'
                await client.send_message(message.channel, msg)
            else:
                for each in instancelist():
                    lastwipet = elapsedTime(Now(), getlastrestart(each))
                    msg = f'Last server restart for {each.capitalize()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!vote') or message.content.startswith('!startvote'):
            msg = f'Voting is only allowed in-game'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!event') or message.content.startswith('!events'):
            whofor = str(message.author).lower()
            log.info(f'event request from {whofor} on discord')
            lastevent = getlasteventinfo()
            currentevent = getcurrenteventinfo()
            nextevent = getnexteventinfo()
            msg = ''
            try:
                if lastevent and lastevent is not None:
                    msg = msg + f'Last Event was: {lastevent[4]} ended {elapsedTime(datetimeto(d2dt_maint(lastevent[3]), fmt="epoch"), Now())} ago\n'
                if currentevent and currentevent is not None:
                    msg = msg + f'Current Event is: {currentevent[4]} {currentevent[5]}\nCurrent Event ends in {elapsedTime(datetimeto(d2dt_maint(currentevent[3]), fmt="epoch"), Now())}\n'
                else:
                    msg = msg + f'There is no Event currently running\n'
                if nextevent and nextevent is not None:
                    msg = msg + f'Next Event is: {nextevent[4]} and starts in {elapsedTime(datetimeto(d2dt_maint(nextevent[2]), fmt="epoch"), Now())}\n'
                else:
                    msg = msg + f'Next Event is not scheduled yet.\n'
                await client.send_message(message.channel, msg)
            except:
                log.critical(f'Error calculating events', exc_info=True)

        elif message.content.startswith('!decay') or message.content.startswith('!expire'):
            whofor = str(message.author).lower()
            log.info(f'decay request from {whofor} on discord')
            kuser = getplayer(discordid=whofor)
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
                    try:
                        etime = Now() - float(kuser[2])
                        wdate = epochto(float(kuser[2]) + woodtime, 'string', est=True)
                        sdate = epochto(float(kuser[2]) + stonetime, 'string', est=True)
                        mdate = epochto(float(kuser[2]) + metaldinotime, 'string', est=True)
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
            kuser = getplayer(discordid=whofor)
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'kickme request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not connected to a player yet.'
                    await client.send_message(message.channel, msg)
                else:
                    if Now() - float(kuser[2]) > 300:
                        log.info(f'kickme request from {whofor} denied, not connected to a server')
                        msg = f'You are not connected to any servers'
                        await client.send_message(message.channel, msg)
                    else:
                        log.info(f'kickme request from {whofor} passed, kicking player on {kuser[3]}')
                        msg = f'Kicking {kuser[1].capitalize()} from the {kuser[3].capitalize()} server'
                        await client.send_message(message.channel, msg)
                        dbupdate("INSERT INTO kicklist (instance,steamid) VALUES ('%s','%s')" % (kuser[3], kuser[0]))

        elif message.content.startswith('!home') or message.content.startswith('!myhome'):
            newsrv = message.content.split(' ')
            whofor = str(message.author).lower()
            kuser = getplayer(discordid=whofor)
            if kuser:
                if len(newsrv) > 1:
                    log.info(f'home server change request for {kuser[1]}')
                    msg = f'You must type !myhome on your current home server {kuser[15].capitalize()} \
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
            last5 = dbquery("SELECT * FROM lotteryinfo WHERE completed = True AND winner != 'None' ORDER BY id DESC LIMIT 5")
            top5 = dbquery("SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 5")
            msg = 'Last 5 Lottery Winners:\n'
            now = Now()
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
            kuser = getplayer(discordid=whofor)
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
                    ptime = playedTime(int(kuser[4]))
                    ptr = elapsedTime(Now(), int(kuser[2]))
                    lpts = totallotterydeposits(kuser[0])
                    msg = f'Your current ARc reward points: {kuser[5] + kuser[16] + lpts}\nLast played on {kuser[3].capitalize()} {ptr} ago.\n'
                    msg = msg + f'Your home server is: {kuser[15].capitalize()}\nYour total play time is {ptime}\n'
                    msg = msg + f'You have {au1} current auctions: {au2} Items, {au3} Dinos\n'
                    tpwins, twpoints = getlottowinnings(kuser[1])
                    msg = msg + f'Total Lotterys Won: {tpwins}  Total Lottery Points Won: {twpoints} Points\n'
                    woodtime = 1296000
                    stonetime = 1987200
                    metaldinotime = 2624400
                    try:
                        etime = Now() - int(kuser[2])
                        wdate = epochto(int(kuser[2]) + woodtime, 'string', est=True)
                        sdate = epochto(int(kuser[2]) + stonetime, 'string', est=True)
                        mdate = epochto(int(kuser[2]) + metaldinotime, 'string', est=True)
                        if woodtime > etime:
                            woodt = f'Your Wood Structures Expire: {wdate} EST - {elapsedTime(woodtime, etime)} Left'
                        elif etime < Secs['hour']:
                            woodt = f'Your Wood Structures Expire: 15 Days Left'
                        else:
                            woodt = 'Your Wood Structures have passed Experation Time!'
                        if stonetime > etime:
                            stonet = f'Your Stone Structures Expire: {sdate} EST - {elapsedTime(stonetime, etime)} Left'
                        elif etime < Secs['hour']:
                            stonet = f'Your Stone Structures Expire: 23 Days Left'
                        else:
                            stonet = 'Your Stone Structures have passwd Experation Time!'
                        if metaldinotime > etime:
                            metalt = f'Your Metal & Dinos Expire: {mdate} EST - {elapsedTime(metaldinotime, etime)} Left'
                        elif etime < Secs['hour']:
                            metalt = f'Your Metal & Dinos Expire: 30 Days Left'
                        else:
                            metalt = 'Your Metal Structures & Dinos have passed Experation Time!'
                        msg = msg + f'{woodt}\n{stonet}\n{metalt}'
                    except:
                        log.critical('Critical Error in decay calculation!', exc_info=True)
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!newest') or message.content.startswith('!lastnew'):
            log.info(f'responding to lastnew request on discord')
            newlist = getnewestplayers('all', last=3)
            msg = f'Last 3 Newest Players in cluster:\n'
            for each in newlist:
                lsplayer = getplayer(playername=each)
                lspago = elapsedTime(Now(), lsplayer[6])
                msg = msg + f'{lsplayer[1].title()} on {lsplayer[3].capitalize()} {lspago} ago\n'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!topplayed') or message.content.startswith('!topplayers'):
            log.info(f'responding to topplayed request on discord')
            lsplayer = gettopplayedplayers('all', last=10)
            nom = 0
            msg = ''
            for each in lsplayer:
                nom += 1
                lsplay = getplayer(playername=each)
                lspago = playedTime(lsplay[4])
                msg = msg + f'#{nom} {lsplay[1].title()} home {lsplay[15].capitalize()} at {lspago}\n'
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
            dbsvr = dbquery("SELECT * FROM instances")
            # msg = 'Galaxy Cluster Ultimate Extinction Core Servers:\n'
            for instt in dbsvr:
                if int(instt[9]) == 0:
                    onl = 'OFFLINE'
                    pcnt = 0
                elif int(instt[9]) == 1:
                    onl = 'ONLINE'
                    flast = dbquery("SELECT * FROM players WHERE server = '%s'" % (instt[0],))
                    pcnt = 0
                    for row in flast:
                        chktme = Now() - float(row[2])
                        if chktme < 40:
                            pcnt += 1
                msg = f'Server {instt[0].capitalize()} is {onl} Players ({pcnt}/50) - {instt[15]} \
- {instt[16]} - {instt[17]}\n'
                await client.send_message(message.channel, msg)
                sleep(.5)

        elif message.content.startswith('!lastlotto') or message.content.startswith('!lastlottery'):
            whofor = str(message.author).lower()
            linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False ORDER BY id DESC", fetch='one', fmt='dict')
            if linfo["winner"] == 'None':
                msg = f'Last lottery was {linfo["payout"]} Arc reward points not won because lack of players. {elapsedTime(Now(),datetimeto(linfo["startdate"], fmt="epoch"))} ago'
            else:
                msg = f'Last lottery was {linfo["payout"]} Arc reward points won by {linfo["winner"].capitalize()}. \
{elapsedTime(Now(),datetimeto(linfo["startdate"], fmt="epoch"))} ago'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!lotto') or message.content.startswith('!lottery'):
            whofor = str(message.author).lower()
            newname = message.content.split(' ')
            linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
            if len(newname) > 1:
                if newname[1] == 'enter' or newname[1] == 'join':
                    lpinfo = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (whofor,), fetch='one')
                    if not lpinfo:
                        log.info(f'lottery join request from {whofor} denied, account not linked')
                        msg = f'Your discord account must be linked to your player account to join a lottery from \
discord.\nType !linkme in game'
                        await client.send_message(message.channel, msg)
                    else:
                        whofor = lpinfo[1]
                        lpcheck = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
                        lfo = 'ARc Rewards Points'
                        # ltime = epochto(float(linfo[3]) + (Secs['hour'] * int(linfo[5])), 'string', est=True)
                        if lpcheck is None:
                            dbupdate("INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('%s', '%s', '%s', '%s')" % (lpinfo[0], lpinfo[1], Now(fmt='dt'), 0))
                            dbupdate("UPDATE lotteryinfo SET payout = '%s', players = '%s' WHERE id = %s" % (linfo["payout"] + linfo["buyin"] * 2, linfo["players"] + 1, linfo["id"]))
                            msg = f'You have been added to the {lfo} lottery!\nA winner will be choosen in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(days=linfo["days"]), fmt="epoch"),Now())}. Good Luck!'
                            await client.send_message(message.channel, msg)
                            log.info(f'player {whofor} has joined the current active lottery.')
                        else:
                            msg = f'You are already participating in this lottery for {lfo}.\nLottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(days=linfo["days"]), fmt="epoch"),Now())}'
                            await client.send_message(message.channel, msg)
            else:
                if linfo:
                    msg = f'Current lottery is up to {linfo["payout"]} ARc reward points.\n{linfo["players"]} players have entered into this lottery so far.\nLottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(days=linfo["days"]), fmt="epoch"),Now())}\nType !lotto enter to join the lottery'
                    await client.send_message(message.channel, msg)
                else:
                    msg = 'There are no lotterys currently underway.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!primordial'):
            whofor = str(message.author).lower()
            pplayer = dbquery("SELECT * from players WHERE discordid = '%s'" % (whofor,), fetch='one')
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
            dplayer = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (whofor,), fetch='one')
            if dplayer:
                log.info(f'link account request on discord from {whofor} denied, already linked')
                msg = f'Your discord account is already linked to your game account'
                await client.send_message(message.channel, msg)
            else:
                if len(sw) > 1:
                    rcode = sw[1]
                    reqs = dbquery("SELECT * FROM linkrequests WHERE reqcode = '%s'" % (rcode,), fetch='one')
                    if reqs:
                        log.info(f'link account request on discord from {whofor} accepted. \
{reqs[1]} {whofor} {reqs[0]}')
                        dbupdate("UPDATE players SET discordid = '%s' WHERE steamid = '%s'" % (whofor, reqs[0]))
                        dbupdate("DELETE FROM linkrequests WHERE reqcode = '%s'" % (rcode,))
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
            whos = dbquery("SELECT playername FROM players WHERE discordid = '%s'" % (str(message.author).lower(),), fetch='one')
            if whos:
                writeglobal('discord', whos[0], str(message.content))
    client.loop.create_task(chatbuffer())
    while True:
        try:
            client.run(discordtoken)
        except:
            log.critical('Critical Error in Discord Bot Routine.')
            sleep(60)
            system('ark restart')
