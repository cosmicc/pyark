from datetime import timedelta
from clusterevents import getcurrenteventinfo, getlasteventinfo, getnexteventinfo
from modules.auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats
from modules.configreader import discord_channel, discord_serverchat, discordtoken, discord_botchannel
from modules.dbhelper import dbquery, dbupdate
from modules.instances import instancelist, getlastwipe, getlastrestart, writechat, writeglobal, getlastrestartreason
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
channel3 = discord.Object(id=discord_botchannel)

SUCCESS_COLOR = 0x00ff00
FAIL_COLOR = 0xff0000
INFO_COLOR = 0x0088ff
HELP_COLOR = 0xff8800


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
        log.info(f'new user has joined the Discord server: {member}')
        fmt = 'If you are already a player on the servers, type !linkme in-game to link your discord account to your ark player.\n'
        fmt = fmt + 'Type !servers for links to the servers\nType !mods for a link to the mod collection\n!help for everything else\n\n'
        fmt = fmt + 'If you need any help look for pinned messages in #help'
        embed=discord.Embed(title="Welcome to the Galaxy Cluster Ultimate Extinction core Server Discord", description=fmt, color=HELP_COLOR)
        await client.send_message(member, embed=embed)

    @client.event
    async def on_ready():
        log.info(f'discord logged in as {client.user.name} id {client.user.id}')
        await client.change_presence(game=discord.Game(name="!help"))

    @client.event
    async def on_message(message):
        savediscordtodb(message.author)
        if str(message.author) == "Galaxy Cluster#7499":
            log.debug('skipping processing of bots own on_message trigger')
        #elif message.content.lower().find('join the server') or message.content.lower().find('how do i join') or message.content.lower().find('server link') or message.content.lower().find('link to server'):
        #    log.info(f'responding to join server chat for {message.author} on discrod')
        #    msg = f'The #join-servers channel has information and links to the servers and mods'
        #    await client.send_message(message.channel, msg)
        elif message.content.lower().startswith('!kickme') or message.content.lower().startswith('!kick'):
                whofor = str(message.author).lower()
                log.info(f'kickme request from {whofor} on discord')
                kuser = getplayer(discordid=whofor)
                if kuser:
                    if kuser[8] != whofor:
                        log.info(f'kickme request from {whofor} denied, no account linked')
                        msg = f'Your discord account must be linked to your player for this to work.\nType !linkme in-game to do this.'
                        embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    else:
                        if Now() - float(kuser[2]) > 300:
                            log.info(f'kickme request from {whofor} denied, not connected to a server')
                            msg = f'**{kuser[1].capitalize()}** is not connected to any servers in the cluster'
                            embed = discord.Embed(description=msg, color=FAIL_COLOR)
                        else:
                            log.info(f'kickme request from {whofor} passed, kicking player on {kuser[3]}')
                            msg = f'Kicking **{kuser[1].capitalize()}** from the ***{kuser[3].capitalize()}*** server'
                            dbupdate("INSERT INTO kicklist (instance,steamid) VALUES ('%s','%s')" % (kuser[3], kuser[0]))
                            embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                    if str(message.channel) == 'bot-channel':
                        await client.send_message(message.channel, embed=embed)
                    else:
                        await client.send_message(message.author, embed=embed)
                    if not str(message.channel).startswith('Direct Message') and str(message.channel) != 'bot-channel':
                        await client.delete_message(message)
        elif message.content.lower().startswith('!link') or message.content.lower().startswith('!linkme'):
            whofor = str(message.author).lower()
            user = message.author
            log.info(f'responding to link account request on discord from {whofor}')
            sw = message.content.split(' ')
            dplayer = dbquery("SELECT playername FROM players WHERE discordid = '%s'" % (whofor,), fetch='one')
            if dplayer:
                log.info(f'link account request on discord from {whofor} denied, already linked')
                msg = f'Your discord account is already linked to your in-game player **{dplayer[0].title()}**'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
            else:
                if len(sw) > 1:
                    rcode = sw[1]
                    reqs = dbquery("SELECT * FROM linkrequests WHERE reqcode = '%s'" % (rcode,), fetch='one')
                    if reqs:
                        log.info(f'link account request on discord from {whofor} accepted. \
{reqs[1]} {whofor} {reqs[0]}')
                        dbupdate("UPDATE players SET discordid = '%s' WHERE steamid = '%s'" % (whofor, reqs[0]))
                        dbupdate("DELETE FROM linkrequests WHERE reqcode = '%s'" % (rcode,))
                        msg = f'Your discord account *[{whofor}]* is now linked to your player **{reqs[1].title()}**'
                        embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                        role = discord.utils.get(user.server.roles, name="Linked Player")
                        await client.add_roles(user, role)
                    else:
                        log.info(f'link account request on discord from {whofor} denied, code not found')
                        msg = f'That link request code was not found. You must get a link code from typing !linkme in-game'
                        embed = discord.Embed(description=msg, color=FAIL_COLOR)
                else:
                    log.info(f'link account request on discord from {whofor} denied, no code specified')
                    msg = f'You must first type !linkme in-game to get a code, then specify that code here to link your accounts'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
            if str(message.channel) == 'bot-channel':
                await client.send_message(message.channel, embed=embed)
            else:
                await client.send_message(message.author, embed=embed)
            if not str(message.channel).startswith('Direct Message') and str(message.channel) != 'bot-channel':
                await client.delete_message(message)

        elif message.content.lower().startswith('!help'):
            log.info(f'help request on discord from {message.author}')
            msg = ''
            msg3 = '!event, !lasthour, !lastlotto, !timeleft'
            msg2 = '**Commands can be privately messaged directly to the bot or in the #bot-channel**'
            msg = msg + "**!mods**  - Link to all the mods for this cluster\n"
            msg = msg + "**!servers**  - Status and links to all the servers in the cluster\n"
            msg = msg + "**!who**  - List all players currently online on all the servers\n"
            msg = msg + "**!myinfo**  - Your in-game player information\n"
            msg = msg + "**!expire**  - Your in-game experation timers and time left before dino/structure decay\n"
            msg = msg + "**!ec**  - Links to more Extinction Core Mod information\n"
            msg = msg + "**!points**  - More information about the Galaxy Cluster points system\n"
            msg = msg + "**!linkme <code>**  - Link your discord account to your in-game player with <code> from typing !linkme in-game\n"
            msg = msg + "**!kickme**  - Kick your player from the server it was on so you don't have to wait for it to timeout\n"
            msg = msg + "**!lotto**  - Show information about the current lottery\n"
            msg = msg + "**!lotto enter**  - Join the current lottery if one exists\n"
            msg = msg + "**!today**  - List all players online in the last 24 hours\n"
            msg = msg + "**!lastseen <playername>**  - Show the last time a player was online on a server in the cluster\n"
            msg = msg + "**!lastwipe <server>**  - Show the last time a wild dino wipe was performed on specified server\n"
            msg = msg + "**!lastrestart <server>**  - Show the last time the specified server was restarted and why\n"
            msg = msg + "**!myhome**  - Show what your current Home server is set to (where all your points go)\n"
            msg = msg + "**!newest**  - List the last 5 newest players to the cluster\n"
            msg = msg + "**!topplayed**  - List the top 10 players with the most playtime\n"
            msg = msg + "**!lastlotto**  - List the last 5 lottery winners\n"
            msg = msg + "**!winners**  - List the 5 all-time lottery winners\n"
            msg = msg + "**!primordial**  - Warns you in-game if you haven't logged in since the server has restarted (so you can reset you rprimordials buff bug)\n\n"
            embed=discord.Embed(title="Galaxy Custom Bot Commands:", description=msg, color=HELP_COLOR)
            embed.set_footer(text=msg2)
            await client.send_message(message.author, embed=embed)
            # await client.add_reaction(message, '597645497590874162')
            if not str(message.channel).startswith('Direct Message') and str(message.channel) != 'bot-channel':
                await client.delete_message(message)
        elif str(message.channel) != 'bot-channel' and str(message.channel) != 'general-chat' and not str(message.channel).startswith('Direct Message'):
            msg = 'Bot commands are limited to the **#bot-channel** and **Private message** (here)\nType **!help** for a description of all the commands'
            embed=discord.Embed(description=msg, color=FAIL_COLOR)
            await client.send_message(message.author, embed=embed)
            if not str(message.channel).startswith('Direct Message'):
                await client.delete_message(message)

        elif message.content.lower().startswith('!whotoday') or message.content.lower().startswith('!today') \
                or message.content.lower().startswith('!lastday'):
            log.info(f'responding to recent players request from {message.author} on discord')
            tcnt = 0
            for each in instancelist():
                pcnt = getplayerstoday(each, fmt='count')
                tcnt = tcnt + pcnt
            embed = discord.Embed(title=f" **{tcnt}**  total players online in the last 24 hours", color=INFO_COLOR)
            for each in instancelist():
                pcnt = getplayerstoday(each, fmt='count')
                plist = getplayerstoday(each, fmt='string')
                if pcnt != 0:
                    embed.add_field(name=f'{each.capitalize()} has had  **{pcnt}**  players today:', value=f'{plist}', inline=False)
                else:
                    embed.add_field(name=f'{each.capitalize()} has had no players today', value="\u200b", inline=False)
            await client.send_message(message.channel, embed=embed)
        elif message.content.lower().startswith('!who') or message.content.lower().startswith('!whoson') \
                or message.content.lower().startswith('!whosonline'):
            log.info(f'responding to who online request from {message.author} on discord')
            tcnt = 0
            for each in instancelist():
                pcnt = getplayersonline(each, fmt='count')
                tcnt = tcnt + pcnt
            embed = discord.Embed(title=f" **{tcnt}**  total players currently online in the cluster", color=INFO_COLOR)
            for each in instancelist():
                pcnt = getplayersonline(each, fmt='count')
                plist = getplayersonline(each, fmt='string', case='title')
                if pcnt != 0:
                    embed.add_field(name=f"{each.capitalize().strip()} has  **{pcnt}**  players online:", value=f"{plist}", inline=False)
                else:
                    embed.add_field(name=f"{each.capitalize().strip()} has no players online", value="\u200b", inline=False)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!recent') or message.content.lower().startswith('!whorecent') \
                or message.content.lower().startswith('!lasthour'):
            # await asyncio.sleep(5)
            log.info('responding to recent players request from {message.author} on discord')
            plist = getlastplayersonline('all', fmt='string', case='title')
            msg = f'Last 5 recent players: {plist}'
            await client.send_message(message.channel, msg)

        elif message.content.lower().startswith('!lastseen'):
            newname = message.content.split(' ')
            if len(newname) > 1:
                log.info(f'responding to lastseen request for {newname[1]} from {message.author} on discord')
                seenname = newname[1].lower()
                flast = getplayerlastseen(playername=seenname)
                if not flast:
                    msg = f'No player was found with name **{seenname}**'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    await client.send_message(message.channel, embed=embed)
                else:
                    plasttime = elapsedTime(Now(), flast)
                    srv = getplayerlastserver(playername=seenname)
                    if plasttime != 'now':
                        msg = f'**{seenname.title()}** was last seen **{plasttime} ago** on ***{srv.capitalize()}***'
                        embed = discord.Embed(description=msg, color=INFO_COLOR)
                        await client.send_message(message.channel, embed=embed)
                    else:
                        msg = f'**{seenname.title()}** is online now on ***{srv.capitalize()}***'
                        embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                        await client.send_message(message.channel, embed=embed)
            else:
                msg = f'You must specify a player name to search for: !lastseen <playername>'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!lastwipe'):
            lwt = message.content.split(' ')
            log.info(f'responding to lastwipe request from {message.author} on discord')
            if len(lwt) > 1:
                instr = lwt[1].lower()
                if instr in instancelist():
                    lastwipet = elapsedTime(Now(), getlastwipe(instr))
                    msg = f'Last wild dino wipe for **{instr.capitalize()}** was **{lastwipet} ago**'
                    embed = discord.Embed(description=msg, color=INFO_COLOR)
                    await client.send_message(message.channel, embed=embed)
                else:
                    msg = f'The server **{instr.capitalize()}** was not found in the cluster'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    await client.send_message(message.channel, embed=embed)
            else:
                msg = ''
                for each in instancelist():
                    lastwipet = elapsedTime(Now(), getlastwipe(each))
                    msg = msg + f'Last wild dino wipe for **{each.capitalize()}** was **{lastwipet} ago**\n'
                embed = discord.Embed(description=msg, color=INFO_COLOR)
                await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!lastrestart'):
            log.info(f'responding to lastrestart request from {message.author} on discord')
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1].lower()
                if instr in instancelist():
                    lastrestartt = elapsedTime(Now(), getlastrestart(instr))
                    msg = f'**{instr.title()}** last restarted **{lastrestartt} ago** for a {getlastrestartreason(instr)}'
                    embed = discord.Embed(description=msg, color=INFO_COLOR)
                    await client.send_message(message.channel, embed=embed)
                else:
                    msg = f'The server **{instr.title()}** does not exist in the cluster'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    await client.send_message(message.channel, embed=embed)
            else:
                msg = ''
                for each in instancelist():
                    lastwipet = elapsedTime(Now(), getlastrestart(each))
                    msg = msg + f'**{each.capitalize()}** last restarted **{lastwipet} ago** for a {getlastrestartreason(each)}\n'
                embed = discord.Embed(description=msg, color=INFO_COLOR)
                await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!vote') or message.content.lower().startswith('!startvote'):
            msg = f'Wild dino wipe voting is only allowed in-game.\n\nGoto the #poll-channel to vote on a poll.'
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!event') or message.content.lower().startswith('!events'):
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

        elif message.content.lower().startswith('!decay') or message.content.lower().startswith('!expire'):
            whofor = str(message.author).lower()
            log.info(f'decay request from {whofor} on discord')
            kuser = getplayer(discordid=whofor)
            msg2 = 'Galaxy Cluster Structure & Dino expire times:'
            msg = 'Dinos: **30 Days**, Tek: **38 Days**, Metal: **30 Days**, Stone: **23 Days**, Wood: **15 Days**\n'
            msg = msg + f'Thatch: **7.5 Days**, Greenhouse: **9.5 Days** (Use MetalGlass for **30 Day** Greenhouse).\n\n'
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'decay request from {whofor} public only, no account linked')
                    msg = msg + f'Your discord account is not linked, I cannot determine your decay time left.'
                else:
                    log.info(f'decay request from {whofor} accepted, showing detailed info')
                    msg = msg + f'Assuming you were in render range and no other tribe members on, decay time left since last online for **{kuser[1].capitalize()}**:\n'
                    woodtime = 1310400
                    stonetime = 1969200
                    metaldinotime = 2592000
                    try:
                        etime = Now() - float(kuser[2])
                        wdate = epochto(float(kuser[2]) + woodtime, 'string', est=True)
                        sdate = epochto(float(kuser[2]) + stonetime, 'string', est=True)
                        mdate = epochto(float(kuser[2]) + metaldinotime, 'string', est=True)
                        if woodtime > etime:
                            woodt = f'Your Wood Expires: {wdate} EST - **{elapsedTime(woodtime, etime)}** Left'
                        elif etime < 3600:
                            woodt = f'Your Wood Expires: **15 Days**'
                        else:
                            woodt = '**Your Wood Structures may have expired!**'
                        if stonetime > etime:
                            stonet = f'Your Stone Expires: {sdate} EST - **{elapsedTime(stonetime, etime)}** Left'
                        elif etime < 3600:
                            stonet = f'Your Stone Expires: {sdate} EST - **{elapsedTime(stonetime)}** Left'
                        else:
                            stonet = '**Your Stone Structures may have Expired!**'
                        if metaldinotime > etime:
                            metalt = f'Your Metal & Dinos Expire: {mdate} EST - **{elapsedTime(metaldinotime, etime)}** Left'
                        elif etime < 3600:
                            metalt = f'Your Metal & Dinos Expire: **30 Days**'
                        else:
                            metalt = '**Your Metal Structures & Dinos may have Expired!**'
                        msg = msg + f'{woodt}\n{stonet}\n{metalt}'
                    except:
                        log.critical('Critical Error in decay calculation!', exc_info=True)
            embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!home') or message.content.lower().startswith('!myhome'):
            newsrv = message.content.split(' ')
            whofor = str(message.author).lower()
            kuser = getplayer(discordid=whofor)
            if kuser:
                if len(newsrv) > 1:
                    log.info(f'home server change request for {kuser[1]}')
                    msg = f'You must type **!myhome <newserver>** on your current home server **{kuser[15].capitalize()}** to change home servers'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    await client.send_message(message.channel, embed=embed)
                else:
                    log.info(f'home server request granted for {kuser[1]}')
                    msg = f'Your current home server is: **{kuser[15].capitalize()}**\nThis is the server all your points go to'
                    embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                    await client.send_message(message.channel, embed=embed)
            else:
                log.info(f'home server request from {whofor} denied, no account linked')
                msg = f"Your discord account is not linked to your in-game player, Type !linkme in-game to do this"
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!winners') or message.content.lower().startswith('!lottowinners') or message.content.lower().startswith('!lastlotto'):
            whofor = str(message.author).lower()
            log.info(f'lotto winners request from {whofor} on discord')
            last5 = dbquery("SELECT * FROM lotteryinfo WHERE completed = True AND winner != 'None' ORDER BY id DESC LIMIT 5")
            top5 = dbquery("SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 5")
            msg2 = 'Last 5 Lottery Winners:'
            now = Now()
            msg = ''
            try:
                for peach in last5:
                    msg = msg + f'**{peach[6].capitalize()}** won **{peach[1]}** Points  -  {elapsedTime(datetimeto(peach[2] + timedelta(hours=int(peach[5])), fmt="epoch"),Now())} ago\n'
                embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
                await client.send_message(message.channel, embed=embed)
                msg2 = 'Top 5 All Time Lottery Winners:'
                ccount = 0
                newtop = top5.copy()
                msg = ''
                for heach in newtop:
                    ccount += 1
                    msg = msg + f'#{ccount} **{heach[1].capitalize()}** with **{heach[18]}** Lottery Wins.  **{heach[19]}** Total points won.\n'
            except:
                log.critical('Critical Error determining lottery winners!', exc_info=True)
            embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!myinfo') or message.content.lower().startswith('!mypoints'):
            whofor = str(message.author).lower()
            log.info(f'myinfo request from {whofor} on discord')
            kuser = getplayer(discordid=whofor)
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'myinfo request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not linked to a in-game player. Type !linkme in-game to do this.'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    await client.send_message(message.channel, embed=embed)
                else:
                    log.info(f'myinfo request from {whofor} passed, showing info for player {kuser[1]}')
                    pauctions = fetchauctiondata(kuser[0])
                    au1, au2, au3 = getauctionstats(pauctions)
                    writeauctionstats(kuser[0], au1, au2, au3)
                    ptime = playedTime(int(kuser[4]))
                    ptr = elapsedTime(Now(), int(kuser[2]))
                    lpts = totallotterydeposits(kuser[0])
                    msg = f'Last played **{ptr} ago** on server ***{kuser[3].capitalize()}***\n'
                    msg = msg + f'Your current reward points: **{kuser[5] + kuser[16] + lpts}**\n'
                    msg = msg + f'Your home server is: **{kuser[15].capitalize()}**\nYour total play time is: **{ptime}**\n'
                    msg = msg + f'You have **{au1}** current auctions: **{au2}** Items & **{au3}** Dinos\n'
                    tpwins, twpoints = getlottowinnings(kuser[1])
                    msg = msg + f'Total Lotterys Won: **{tpwins}**  Total Lottery Points Won: **{twpoints}** Points\n'
                    woodtime = 1296000
                    stonetime = 1987200
                    metaldinotime = 2624400
                    try:
                        etime = Now() - int(kuser[2])
                        wdate = epochto(int(kuser[2]) + woodtime, 'string', est=True)
                        sdate = epochto(int(kuser[2]) + stonetime, 'string', est=True)
                        mdate = epochto(int(kuser[2]) + metaldinotime, 'string', est=True)
                        if woodtime > etime:
                            woodt = f'Your Wood Structures Expire: {wdate} EST - **{elapsedTime(woodtime, etime)}** Left'
                        elif etime < Secs['hour']:
                            woodt = f'Your Wood Structures Expire: 15 Days Left'
                        else:
                            woodt = '**Your Wood Structures may have Expired!**'
                        if stonetime > etime:
                            stonet = f'Your Stone Structures Expire: {sdate} EST - **{elapsedTime(stonetime, etime)}** Left'
                        elif etime < Secs['hour']:
                            stonet = f'Your Stone Structures Expire: **23 Days** Left'
                        else:
                            stonet = '**Your Stone Structures may have Expired!**'
                        if metaldinotime > etime:
                            metalt = f'Your Metal & Dinos Expire: {mdate} EST - **{elapsedTime(metaldinotime, etime)}** Left'
                        elif etime < Secs['hour']:
                            metalt = f'Your Metal & Dinos Expire: **30 Days** Left'
                        else:
                            metalt = '**Your Metal Structures & Dinos may have Expired!**'
                        msg = msg + f'{woodt}\n{stonet}\n{metalt}'
                    except:
                        log.critical('Critical Error in decay calculation!', exc_info=True)
                    embed = discord.Embed(title=f'Player information for **{kuser[1].capitalize()}**:', description=msg, color=SUCCESS_COLOR)
                    await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!newest') or message.content.lower().startswith('!lastnew'):
            log.info(f'responding to lastnew request from {message.author} on discord')
            newlist = getnewestplayers('all', last=5)
            msg2 = 'Last 5 Newest Players to the cluster:'
            msg = ''
            for each in newlist:
                lsplayer = getplayer(playername=each)
                lspago = elapsedTime(Now(), lsplayer[6])
                msg = msg + f'**{lsplayer[1].title()}** joined ***{lsplayer[3].capitalize()}***  -  {lspago} ago\n'
            try:
                embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
                await client.send_message(message.channel, embed=embed)
            except:
                log.critical('error in bot', exc_info=True)


        elif message.content.lower().startswith('!topplayed') or message.content.lower().startswith('!topplayers'):
            log.info(f'responding to topplayed request from {message.author} on discord')
            lsplayer = gettopplayedplayers('all', last=10)
            nom = 0
            msg = ''
            for each in lsplayer:
                nom += 1
                lsplay = getplayer(playername=each)
                lspago = playedTime(lsplay[4])
                msg = msg + f'#{nom} **{lsplay[1].title()}** from **{lsplay[15].capitalize()}** total play time **{lspago}**\n'
            embed = discord.Embed(title='Top 10 highest play time in the cluster:', description=msg, color=INFO_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!mods'):
            whofor = str(message.author).lower()
            msg = f'Galaxy Cluster Ultimate Extinction Core Mod Collection:\nhttps://steamcommunity.com/sharedfiles/filedetails/?id=1475281369'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!rewards') or message.content.lower().startswith('!points'):
            whofor = str(message.author).lower()
            msg = f'Galaxy Cluster Ultimate Extinction Core Rewards Vault, ARc Points, Home Server, Lotterys, & Currency:\nhttps://docs.google.com/document/d/154QjLnw4hjxe_DtiTqfSwINsKdUp9Iz3M_umcI5zkRk/edit?usp=sharing'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!ec'):
            whofor = str(message.author).lower()
            msg = f'Extinction Core Info:\nhttps://steamcommunity.com/workshop/filedetails/discussion/817096835/1479857071254169967\nExtinction Core Wiki:\nhttp://extinctioncoreark.wikia.com/wiki/Extinction_Core_Wiki\nExtinction Core Dino Spreadsheet\nhttps://docs.google.com/spreadsheets/d/1GtqBvFK0R0VI7dj7CdkXEuQydqw3xjITZmc0qD95Kug/edit?usp=sharing'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!servers'):
            whofor = str(message.author).lower()
            dbsvr = dbquery("SELECT * FROM instances")
            msg = 'Galaxy Cluster Ultimate Extinction Core Servers:'
            embed = discord.Embed(title=msg, color=INFO_COLOR)
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
                embed.add_field(name=f'Server {instt[0].capitalize()} is  **{onl}**  Players ({pcnt}/50)', value=f'Steam: {instt[15]}\nArkServers: {instt[16]}\nBattleMetrics: {instt[17]}', inline=False)
            await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!lotto') or message.content.lower().startswith('!lottery'):
            whofor = str(message.author).lower()
            newname = message.content.split(' ')
            linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
            if len(newname) > 1:
                if newname[1].lower() == 'enter' or newname[1].lower() == 'join':
                    lpinfo = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (whofor,), fetch='one')
                    if not lpinfo:
                        log.info(f'lottery join request from {whofor} denied, account not linked')
                        msg = f'Your discord account must be linked to your in-game player account to join a lottery from discord.\nType !linkme in-game to do this'
                        embed = discord.Embed(description=msg, color=FAIL_COLOR)
                        await client.send_message(message.channel, embed=embed)
                    else:
                        whofor = lpinfo[1]
                        lpcheck = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
                        lfo = 'ARc Rewards Points'
                        # ltime = epochto(float(linfo[3]) + (Secs['hour'] * int(linfo[5])), 'string', est=True)
                        if lpcheck is None:
                            dbupdate("INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('%s', '%s', '%s', '%s')" % (lpinfo[0], lpinfo[1], Now(fmt='dt'), 0))
                            dbupdate("UPDATE lotteryinfo SET payout = '%s', players = '%s' WHERE id = %s" % (linfo["payout"] + linfo["buyin"] * 2, linfo["players"] + 1, linfo["id"]))
                            msg = f'You have been added to the {lfo} lottery!\nA winner will be choosen in **{elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}**. Good Luck!'
                            embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                            await client.send_message(message.channel, embed=embed)
                            log.info(f'player {whofor} has joined the current active lottery.')
                        elif not linfo:
                            msg = 'There are no lotterys currently underway.'
                            embed = discord.Embed(description=msg, color=FAIL_COLOR)
                            await client.send_message(message.channel, embed=embed)
                        else:
                            msg = f'You are already participating in the current lottery for {lfo}.\nLottery ends in **{elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}**'
                            embed = discord.Embed(description=msg, color=FAIL_COLOR)
                            await client.send_message(message.channel, embed=embed)
            else:
                if linfo:
                    msg = f'Type !lotto enter to join the lottery'
                    embed=discord.Embed(title=f"Current lottery is up to {linfo['payout']} reward points", description=f"{linfo['players']} players have entered into this lottery so far", color=SUCCESS_COLOR)
                    embed.add_field(name=f'Lottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}', value="\u200b", inline=False)
                    embed.set_footer(text=msg)

                    await client.send_message(message.channel, embed=embed)
                else:
                    msg = 'There are no lotterys currently underway.'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
                    await client.send_message(message.channel, embed=embed)

        elif message.content.lower().startswith('!primordial'):
            whofor = str(message.author).lower()
            pplayer = dbquery("SELECT * from players WHERE discordid = '%s'" % (whofor,), fetch='one')
            if not pplayer:
                msg = f'Your discord account needs to be linked to your in-game player first. Type !linkme in-game to do this'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await client.send_message(message.channel, embed=embed)
            else:
                if int(pplayer[14]) == 1:
                    setprimordialbit(pplayer[0], 0)
                    msg = f'Your primordial server restart warning is now OFF'
                    embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                    await client.send_message(message.channel, embed=embed)
                else:
                    setprimordialbit(pplayer[0], 1)
                    msg = f'Your primordial server restart warning is now ON'
                    embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                    await client.send_message(message.channel, embed=embed)

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
