import asyncio
import signal
from concurrent.futures._base import CancelledError
from datetime import datetime
from datetime import time as dt
from datetime import timedelta
from os import _exit, getpid

import discord
from discord.ext import commands
from loguru import logger as log

from modules.asyncdb import DB as db
from modules.clusterevents import getcurrenteventinfo, getlasteventinfo, getnexteventinfo, iseventtime
from modules.configreader import (changelog_id, discordtoken, generalchat_id,
                                  hstname, infochat_id, maint_hour, serverchat_id)
from modules.dbhelper import dbquery, dbupdate
from modules.instances import getlastrestart, getlastrestartreason, getlastwipe, instancelist, writeglobal
from modules.lottery import getlottowinnings, isinlottery, totallotterydeposits
from modules.players import (getnewestplayers, getplayer, getplayerlastseen, getplayerlastserver, getplayersonlinenames,
                             getplayerstoday, gettopplayedplayers, isplayeradmin, setprimordialbit)
from modules.timehelper import Now, Secs, datetimeto, elapsedTime, epochto, playedTime

__name__ = 'discordbot'

log.configure(extra={'hostname': hstname, 'instance': 'MAIN'})


async def shutdown(signal, client):
    """Cleanup tasks tied to the service's shutdown."""
    log.warning(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    [task.cancel() for task in tasks]

    log.warning(f"Cancelling {len(tasks)} outstanding tasks")
    try:
        await asyncio.gather(*tasks)
    except:
        log.warning('task ending error skipped')
    client.stop()


async def asyncwritediscord(msg, tstamp, server='generalchat', name='ALERT'):
    await db.update(f"INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('{server}', '{name}', '{msg}', '{tstamp}')")


def writediscord(msg, tstamp, server='generalchat', name='ALERT'):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (server, name, msg, tstamp))


def d2dt_maint(dtme):
    tme = dt(int(maint_hour) - 1, 55)
    return datetime.combine(dtme, tme)


async def addmessage(mtype, messageid):
    log.trace(f'Adding discord message id [{messageid}] to {mtype} table')
    await db.update("INSERT INTO messagetracker (messagetype, messageid) VALUES ('%s', '%s')" % (mtype, messageid))


async def getrates():
    return await db.fetchone("SELECT * FROM rates WHERE type = 'current'")


async def getlastannounce(atype):
    lastl = await db.fetchone(f"SELECT {atype} FROM general")
    return lastl[0]


async def gettip():
    tip = await db.fetchone("SELECT * FROM tips WHERE active = True ORDER BY count ASC, random()")
    await db.update("UPDATE tips set count = %s WHERE id = %s" % (int(tip['count']) + 1, tip['id']))
    return tip['tip']


async def setlastannounce(atype, tstamp):
    await db.update(f"UPDATE general SET {atype} = '{tstamp}'")


async def savediscordtodb(author):
    didexists = await db.fetchone("SELECT * FROM discordnames WHERE discordname = '%s'" % (str(author).replace("'", ""),))
    if not didexists:
        await db.update("INSERT INTO discordnames (discordname) VALUES ('%s')" % (str(author).replace("'", ""),))


def pyarkbot():
    global generalchat
    global serverchat
    with open('/tmp/pyark.pid', 'a') as pidfile:
        pidfile.write(f'\n{str(getpid())}')

    SUCCESS_COLOR = 0x00ff00
    FAIL_COLOR = 0xff0000
    INFO_COLOR = 0x0088ff
    HELP_COLOR = 0xff8800

    rejectmsg = 'Bot commands are limited to the **`#bot-channel`** and **Private message** (here)\nType **`!help`** for a description of all the commands'

    client = commands.Bot(command_prefix='!', case_insensitive=True)
    client.remove_command('help')

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        client.loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, client.loop)))

    @client.event
    async def on_ready():
        await db.connect(process=__name__)
        log.log('SUCCESS', f'Discord logged in as {client.user.name} id {client.user.id}')
        activity = discord.Game(name="!help")
        try:
            await client.change_presence(status=discord.Status.online, activity=activity)
        except:
            log.error('Exiting')

    @client.event
    async def on_member_join(member):
        log.info(f'New user [{member}] has joined the Galaxy Discord Server')
        fmt = 'If you are already a player on the servers, type **`!linkme`** in-game to link your discord account to your ark player.\n'
        fmt = fmt + 'Type **`!servers`** for links and status of the servers\nType **`!mods`** for a link to the mod collection\n**`!help`** for all the other commands\n\n'
        fmt = fmt + 'More help can be found with pinned messages in **#help**\nDont be afraid to ask for help in discord!'
        embed = discord.Embed(title="Welcome to the Galaxy Cluster Ultimate Extinction Core Server Discord!", description=fmt, color=HELP_COLOR)
        await member.send(embed=embed)

    @client.event
    async def on_command_error(ctx, error):
        try:
            if isinstance(error, commands.CommandNotFound):
                log.warning(f'Invalid discord command [{ctx.message.content}] sent from [{ctx.message.author}]')
                msg = f'Command **`{ctx.message.content}`** does not exist.  **`!help`** for a list and description of all the commands.'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
            elif isinstance(error, NotLinked):
                log.info(f'Player is not linked {ctx.message.author}')
                msg = f'Your discord account needs to be linked to your in-game player first. Type **`!linkme`** in-game to do this'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
            elif isinstance(error, commands.CheckFailure):
                log.warning(f'discord check failed: {error}')
            else:
                log.warning(f'discord bot error for {ctx.message.author}: {ctx.message.content} - {error}')
        except:
            log.exception('command error: ')

    async def clearmessages(ntype):
        await client.wait_until_ready()
        generalchat = client.get_channel(int(generalchat_id))
        log.trace(f'starting discord {ntype} message clearing')
        msgs = await db.fetchall(f"SELECT messageid FROM messagetracker WHERE messagetype = '{ntype}'")
        if msgs:
            for msgid in msgs:
                try:
                    msg = await generalchat.fetch_message(int(msgid['messageid']))
                    await msg.delete()
                except:
                    log.exception(f'error while deleting {ntype} from db')
                else:
                    log.debug(f'Deleted {ntype} message id: {msg.id}')
                finally:
                    await db.update(f"""DELETE from messagetracker WHERE messageid = '{msgid["messageid"]}'""")

    async def taskchecker():
        await client.wait_until_ready()
        await asyncio.sleep(3)
        generalchat = client.get_channel(int(generalchat_id))
        while not client.is_closed():
            try:
                log.trace('executing discord bot task checker')
                if Now(fmt='dt') - await getlastannounce('lastlottoannounce') > timedelta(hours=7) and isinlottery():
                    linfo = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
                    log.log('LOTTO', 'Announcing running lottery in discord')
                    embed = discord.Embed(title=f"A lottery is currently running!", color=INFO_COLOR)
                    embed.set_author(name='Galaxy Cluster Reward Point Lottery', icon_url='https://blacklabelagency.com/wp-content/uploads/2017/08/money-icon.png')
                    embed.add_field(name=f"Current lottery is up to **{linfo['payout']} Points**", value=f"**{linfo['players'] + 1}** Players have entered into this lottery so far\nLottery ends in **{elapsedTime(datetimeto(linfo['startdate'] + timedelta(hours=linfo['days']), fmt='epoch'),Now())}**\n\n**`!lotto enter`** to join the lottery\n**`!points`** for more information\n**`!winners`** for recent results", inline=True)
                    msg = await generalchat.send(embed=embed)
                    await setlastannounce('lastlottoannounce', Now(fmt='dt'))
                    bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="0,1,0,1">                      A points lottery is currently running!</>\n                        {linfo['buyin']} points to enter in this lottery\n<RichColor Color="1,1,0,1">           Current lottery is up to {linfo['payout']} points and grows as players enter </>\n                      Lottery Ends in {elapsedTime(datetimeto(linfo['startdate'] + timedelta(hours=linfo['days']), fmt='epoch'),Now())}\n\n                  Type !lotto for more info or !lotto enter to join"""
                    writeglobal('ALERT', 'LOTTERY', bcast)
                    await clearmessages('lotterymessage')
                    await addmessage('lotterymessage', msg.id)
                if Now(fmt='dt') - await getlastannounce('lasteventannounce') > timedelta(hours=12) and iseventtime():
                    log.info('Announcing running event in discord')
                    event = getcurrenteventinfo()
                    embed = discord.Embed(title=f"An event is running!", color=INFO_COLOR)
                    embed.set_author(name='Galaxy Cluster Server Events', icon_url='https://library.kissclipart.com/20180903/ueq/kissclipart-party-emoji-clipart-party-popper-emoji-aa28695001083d98.png')
                    embed.add_field(name=f"The {event[4]} Event is live on all servers", value=f"{event[5]}\nEvent ends in {elapsedTime(Now(), datetimeto(d2dt_maint(event[2]), fmt='epoch'))} ", inline=False)
                    msg = await generalchat.send(embed=embed)
                    await setlastannounce('lasteventannounce', Now(fmt='dt'))
                    await clearmessages('eventmessage')
                    await addmessage('eventmessage', msg.id)

                try:
                    await serversinfo(None, refresher=True)
                except discord.errors.NotFound:
                    log.error('Cant find server info messages to refresh')
                try:
                    await serverrates(None, refresher=True)
                except discord.errors.NotFound:
                    log.error('Cant find rates info messages to refresh')
                except:
                    log.exception('some other error')
                if Now(fmt='dt') - await getlastannounce('lasttipannounce') > timedelta(hours=4):
                    await protip('', refresher=True)
                    await setlastannounce('lasttipannounce', Now(fmt='dt'))
                await asyncio.sleep(10)
            except CancelledError:
                _exit(0)
            except:
                log.exception('error in task checker!')
                await asyncio.sleep(10)

    async def chatbuffer():
        await client.wait_until_ready()
        await asyncio.sleep(5)
        serverchat = client.get_channel(int(serverchat_id))
        generalchat = client.get_channel(int(generalchat_id))
        changelogchat = client.get_channel(int(changelog_id))
        while not client.is_closed():
            try:
                cbuff = await db.fetchall("SELECT * FROM chatbuffer")
                if cbuff:
                    for each in cbuff:
                        if each[0] == "ALERT":
                            msg = each[2]
                            await serverchat.send(msg)
                            # await asyncio.sleep(2)

                        elif each[0] == 'LOTTOSTART':
                            await setlastannounce('lastlottoannounce', Now(fmt='dt'))
                            embed = discord.Embed(title=f"A new Lottery has started!", color=INFO_COLOR)
                            embed.set_author(name='Galaxy Cluster Reward Points Lottery', icon_url='https://blacklabelagency.com/wp-content/uploads/2017/08/money-icon.png')
                            buyin = int(each[2]) / 25
                            embed.add_field(name=f"Starting Pot: {each[2]} Points", value=f"It costs **{int(buyin)} Points** to join this lottery, lottery winnings grow as more join\nLottery will end in **{each[1]}**\n**`!lotto enter`** to join this lottery\n**`!points`** for more information\n**`!winners`** for recent results", inline=False)
                            msg = await generalchat.send(embed=embed)
                            await clearmessages('lotterymessage')
                            await addmessage('lotterymessage', msg.id)

                        elif each[0] == 'LOTTOEND':
                            embed = discord.Embed(title=f"The current Lottery has ended", color=INFO_COLOR)
                            embed.set_author(name='Galaxy Cluster Reward Points Lottery', icon_url='https://blacklabelagency.com/wp-content/uploads/2017/08/money-icon.png')
                            embed.add_field(name=f"Congratulations to {each[2].upper()} winning **{each[1]}** Points", value=f"Next lottery will start in **1** hour\n**`!points`** for more information\n**`!winners`** for recent results", inline=False)
                            msg = await generalchat.send(embed=embed)
                            await clearmessages('lotterymessage')
                            await addmessage('lotterymessage', msg.id)

                        elif each[0] == 'EVENTSTART':
                            await setlastannounce('lasteventannounce', Now(fmt='dt'))
                            event = getcurrenteventinfo()
                            embed = discord.Embed(title=f"A new event is starting!", color=INFO_COLOR)
                            embed.set_author(name='Galaxy Cluster Server Events', icon_url='https://library.kissclipart.com/20180903/ueq/kissclipart-party-emoji-clipart-party-popper-emoji-aa28695001083d98.png')
                            embed.add_field(name=f"The {event[4]} Event is live on all servers", value=f"{event[5]}", inline=False)
                            msg = await generalchat.send(embed=embed)
                            await clearmessages('eventmessage')
                            await addmessage('eventmessage', msg.id)

                        elif each[0] == 'EVENTEND':
                            event = getlasteventinfo()
                            nevent = getnexteventinfo()
                            embed = discord.Embed(title=f"The current event is ending!", color=INFO_COLOR)
                            embed.set_author(name='Galaxy Cluster Server Events', icon_url='https://library.kissclipart.com/20180903/ueq/kissclipart-party-emoji-clipart-party-popper-emoji-aa28695001083d98.png')
                            embed.add_field(name=f"The {event[4]} Event is ending on all servers", value=f"Next event **{nevent[4]}** starts in **{elapsedTime(Now(), datetimeto(d2dt_maint(nevent[2]), fmt='epoch'))}**", inline=False)
                            msg = await generalchat.send(embed=embed)
                            await clearmessages('eventmessage')
                            await addmessage('eventmessage', msg.id)
                            await setlastannounce('lasteventannounce', Now(fmt='dt'))

                        elif each[0] == 'UPDATE':
                            if Now(fmt='dt') - await getlastannounce('lastupdateannounce') > timedelta(minutes=15):
                                await setlastannounce('lastupdateannounce', Now(fmt='dt'))
                                embed = discord.Embed(title=f"A New Update has been released!", color=INFO_COLOR)
                                embed.set_author(name='ARK Updater for Galaxy Cluster Servers', icon_url='https://patchbot.io/images/games/ark_sm.png')
                                embed.add_field(name=f"Update Reason: {each[2]}", value=f"{each[1]}\n\nAny applicable servers will begin a **30 min** restart countdown now", inline=False)
                                umsg = f'* {each[2]} has been released <{each[1]}>'
                                await generalchat.send(embed=embed)
                                await changelogchat.send(umsg)
                        else:
                            if each[1] == "serverchat":
                                msg = f'{each[3]} [{each[0].capitalize()}] {each[2]}'
                            else:
                                msg = f'{each[3]} [{each[0].capitalize()}] {each[1].capitalize()} {each[2]}'
                            await serverchat.send(msg)
                            await asyncio.sleep(1)
                    await db.update("DELETE FROM chatbuffer")
                # now = Now()
                #  change this to online = true and lastseen > 180
                # cbuffr = dbquery("SELECT * FROM players WHERE lastseen < '%s' AND lastseen > '%s'" % (now - 40, now - 44))
                # if cbuffr:
                #    for reach in cbuffr:
                    # log.log('LEAVE', f'Player [{reach[1].title()}] has left [{reach[3].title()}]')
                    # mt = f'{reach[1].capitalize()} has left the server'
                    # writeglobal(reach[3], 'ALERT', mt)
                    # writechat(reach[3], 'ALERT', f'>>> {reach[1].title()} has left the server', wcstamp())
            except discord.errors.HTTPException:
                log.warning('HTTP Exception error while contacting discord!')
                await asyncio.sleep(10)
            except:
                log.exception('Critical Error in Chat Buffer discord writer!')
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(5)

    class NotLinked(commands.CheckFailure):
        pass

    def is_linked(ctx):
        player = dbquery("SELECT * from players WHERE discordid = '%s'" % (str(ctx.message.author).lower(),), fetch='one')
        if player is not None:
            return True
        else:
            raise NotLinked()

    def is_admin(ctx):
        player = dbquery("SELECT steamid from players WHERE discordid = '%s'" % (str(ctx.message.author).lower(),), fetch='one')
        if player is not None:
            if isplayeradmin(player[0]):
                return True
            else:
                return False
        else:
            log.warning(f'admin command {ctx.message.content} was rejected for {ctx.message.author}')
            return False

    def logcommand(ctx):
        if type(ctx.message.channel) == discord.channel.DMChannel:
            dchan = 'Direct Message'
        else:
            dchan = ctx.message.channel
        log.log('CMD', f'Responding to [{ctx.message.content}] request from [{ctx.message.author}] in [#{dchan}]')
        return True

    async def messagesend(ctx, embed, allowgeneral=False, reject=True, adminonly=False):
        try:
            if type(ctx.message.channel) == discord.channel.DMChannel:
                return await ctx.message.author.send(embed=embed)
            elif str(ctx.message.channel) != 'bot-channel' or (not allowgeneral and str(ctx.message.channel) == 'general-chat'):
                role = str(discord.utils.get(ctx.message.author.roles, name="Cluster Admin"))
                if role != 'Cluster Admin':
                    await ctx.message.delete()
                if reject and role != 'Cluster Admin':
                    rejectembed = discord.Embed(description=rejectmsg, color=HELP_COLOR)
                    return await ctx.message.author.send(embed=rejectembed)
                elif role != 'Cluster Admin':
                    return await ctx.message.author.send(embed=embed)
                else:
                    return await ctx.message.channel.send(embed=embed)
            else:
                return await ctx.message.channel.send(embed=embed)
        except:
            log.exception('Critical error in discord send')

    async def serversinfo(ctx, refresher=False):
        dbsvr = await db.fetchall("SELECT * FROM instances ORDER BY name ASC")
        msg = 'Galaxy Cluster Ultimate Extinction Core Servers:'
        embed = discord.Embed(title=msg, color=INFO_COLOR)
        for instt in dbsvr:
            if int(instt[9]) == 0:
                onl = 'OFFLINE'
                pcnt = 0
            elif int(instt[9]) == 1:
                onl = 'ONLINE'
                flast = await db.fetchall(f"SELECT * FROM players WHERE server = '{instt[0]}' AND online = True")
                pcnt = len(flast)
            embed.add_field(name=f'Server {instt[0].capitalize()} is  **{onl}**  Players ({pcnt}/50)', value=f'Hostname: {instt[23]}\nSteam: {instt[15]}\nArkServers: {instt[16]}\nBattleMetrics: {instt[17]}', inline=False)
        if refresher:
            infochat = client.get_channel(int(infochat_id))
            msg = await infochat.fetch_message(603680854325329931)
            await msg.edit(embed=embed)
            log.trace('Discord server-and-mod server information updated')
        else:
            await messagesend(ctx, embed, allowgeneral=True, reject=False)

    async def protip(ctx, refresher=False):
        tip = await gettip()
        if refresher:
            generalchat = client.get_channel(int(generalchat_id))
            content = f'Protip: {tip}'
            msg = await generalchat.send(content=content)
            await clearmessages('tipmessage')
            await addmessage('tipmessage', msg.id)
        else:
            msg = f'{tip}'
            if type(ctx.message.channel) == discord.channel.DMChannel:
                return await ctx.message.author.send(content=msg)
            else:
                return await ctx.message.channel.send(content=msg)

    async def serverrules(ctx):
        embed = discord.Embed(title='Current Galaxy Cluster Server Rules:', color=INFO_COLOR)
        msg = f"#1 No Griefing of any kind.  This includes all forms.\n#2 DO NOT DROP EGGS YOU DONT WANT, EAT THEM!\n#3  DO NOT SELL/GIVE AWAY BOSSES & PRIMORDIALS. People have to progress on their own.\n#4 Don't build to block.  Don't block dence resource areas or caves.  Don't block player spawn in areas.\n#5 Don't pillar reserve areas.  There is no reason to here.\n#6 Do not leave dinos auto mating/breeding while offline.\n#7 This cluster only has one small PvP server, and its for fun between friends.  It is not Deathmatch there.  It's for events, light RP, and fun only.  See Rule #1"
        embed.add_field(name=f"If unsure about anything, ever, ask in Discord.  Ignorance is not an excuse.", value=msg, inline=True)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    async def serverrates(ctx, refresher=False):
        rates = await getrates()
        cevent = getcurrenteventinfo()
        if cevent is None:
            eventtext = 'No events are currently active (Normal Rates)'
        else:
            eventtext = f'{cevent[4]} event is active (Boosted Rates)'
        embed = discord.Embed(title='Current Galaxy Cluster Server Rates:', color=INFO_COLOR)
        embed.add_field(name=f"{eventtext}", value=f"Breeding Speed: **{rates['breed']}x**\nTaming Speed: **{rates['tame']}x**\nHarvest Speed: **{rates['harvest']}x**\nMating Speed: **{rates['mating']}x**\nMating Interval: **{rates['matingint']}x**\nHatching Speed: **{rates['hatch']}x**\nPlayer XP Speed: **{rates['playerxp']}x**\nTamed Health Recovery: **{rates['tamehealth']}%**\nPlayer Health Recovery: **{rates['playerhealth']}%**\nPlayer Stamina Drain: **{rates['playersta']}%**\nFood/Water Drain Speed: **{rates['foodwater']}%**\nReward Points per Hour: **{rates['pph']}** ({rates['pphx']}x)", inline=True)
        if refresher:
            infochat = client.get_channel(int(infochat_id))
            msg = await infochat.fetch_message(603680843356962857)
            await msg.edit(embed=embed)
            log.trace('Discord server-and-mod rates information updated')
        else:
            await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(name='help', aliases=['helpme', 'commands'])
    @commands.check(logcommand)
    async def _help(ctx):
        msg = ''
        # msg3 = '!lasthour, !timeleft'
        msg = msg + "**`!mods`**  - Link to all the mods for this cluster\n"
        msg = msg + "**`!servers`**  - Status and links to all the servers in the cluster\n"
        msg = msg + "**`!rates`**  - Current ARK game rates for all the cluster servers\n"
        msg = msg + "**`!rules`**  - List of all the cluster rules\n"
        msg = msg + "**`!events`**  - Current and upcomming cluster events\n"
        msg = msg + "**`!decay`**  - Cluster dino & structure decay rates and expire timers\n"
        msg = msg + "**`!who`**  - List all players currently online on all the servers\n"
        msg = msg + "**`!timeleft <server>`**  - How much time left in server restart countdown\n"
        msg = msg + "**`!myinfo`**  - Your in-game player information\n"
        msg = msg + "**`!expire`**  - Your in-game experation timers and time left before dino/structure decay\n"
        msg = msg + "**`!ec`**  - Links to more Extinction Core Mod information\n"
        msg = msg + "**`!points`**  - More information about the Galaxy Cluster points system\n"
        msg = msg + "**`!linkme <code>`**  - Link your discord account to your in-game player with <code> from typing !linkme in-game\n"
        msg = msg + "**`!kickme`**  - Kick your player from the server it was on so you don't have to wait\n"
        msg = msg + "**`!lotto`**  - Show information about the current lottery\n"
        msg = msg + "**`!lotto enter`**  - Join the current lottery if one exists\n"
        msg = msg + "**`!today`**  - List all players online in the last 24 hours\n"
        msg = msg + "**`!lastseen <playername>`**  - Show the last time a player was online in-game\n"
        msg = msg + "**`!lastwipe <server>`**  - Show the last time a wild dino wipe was performed\n"
        msg = msg + "**`!lastrestart <server>`**  - Show the last time the server was restarted and why\n"
        msg = msg + "**`!myhome`**  - Show what your current Home server is set to (where all your points go)\n"
        msg = msg + "**`!newest`**  - List the last 5 newest players to the cluster\n"
        msg = msg + "**`!topplayed`**  - List the top 10 players with the most playtime\n"
        msg = msg + "**`!lastlotto`**  - List the last 5 lottery winners\n"
        msg = msg + "**`!winners`**  - List the 5 all-time lottery winners\n"
        msg = msg + "**`!tip`**  - Get a pro tip from the bot\n\n"
        msg = msg + "The servers available are:"
        for eachinst in instancelist():
            msg = msg + f"  **`{eachinst}`**,"
        msg = msg + "\n\n"
        msg = msg + 'Commands can be privately messaged directly to the bot or in the **#bot-channel**'

        embed = discord.Embed(title="Galaxy Custom Bot Commands:", description=msg, color=HELP_COLOR)
        await ctx.message.author.send(embed=embed)
        if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
            await ctx.message.delete()

    @client.command(name='mods', aliases=['mod', 'arkmods'])
    @commands.check(logcommand)
    async def _mods(ctx):
        msg = f'Galaxy Cluster Ultimate Extinction Core Mod Collection:\nhttps://steamcommunity.com/sharedfiles/filedetails/?id=1475281369'
        embed = discord.Embed(description=msg, color=HELP_COLOR)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(name='points', aliases=['rewards'])
    @commands.check(logcommand)
    async def _rewards(ctx):
        msg = f'Galaxy Cluster Ultimate Extinction Core Rewards Vault, ARc Points, Home Server, Lotterys, & Currency:\nhttps://docs.google.com/document/d/154QjLnw4hjxe_DtiTqfSwINsKdUp9Iz3M_umcI5zkRk/edit?usp=sharing'
        embed = discord.Embed(description=msg, color=HELP_COLOR)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(name='ec', aliases=['extinction'])
    @commands.check(logcommand)
    async def _ec(ctx):
        msg = f'Extinction Core Info:\nhttps://steamcommunity.com/workshop/filedetails/discussion/817096835/1479857071254169967\nExtinction Core Wiki:\nhttp://extinctioncoreark.wikia.com/wiki/Extinction_Core_Wiki\nExtinction Core Dino Spreadsheet\nhttps://docs.google.com/spreadsheets/d/1GtqBvFK0R0VI7dj7CdkXEuQydqw3xjITZmc0qD95Kug/edit?usp=sharing'
        embed = discord.Embed(description=msg, color=HELP_COLOR)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(name='servers', aliases=['server', 'status'])
    @commands.check(logcommand)
    async def _servers(ctx):
        await serversinfo(ctx)

    @client.command(name='primordial')
    @commands.check(logcommand)
    @commands.check(is_linked)
    async def _primordial(ctx):
        pplayer = await db.fetchone(f"SELECT * from players WHERE discordid = '{str(ctx.message.author).lower()}'")
        if int(pplayer[14]) == 1:
            setprimordialbit(pplayer[0], 0)
            msg = f'Your primordial server restart warning is now OFF'
            embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)
        else:
            setprimordialbit(pplayer[0], 1)
            msg = f'Your primordial server restart warning is now ON'
            embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='topplayed', aliases=['topplayers', 'topplaytime'])
    @commands.check(logcommand)
    async def _topplayed(ctx):
        lsplayer = gettopplayedplayers('all', last=10)
        nom = 0
        msg = ''
        for each in lsplayer:
            nom += 1
            lsplay = getplayer(playername=each)
            lspago = playedTime(lsplay[4])
            msg = msg + f'#{nom} **{lsplay[1].title()}** from **{lsplay[15].capitalize()}** total play time **{lspago}**\n'
        embed = discord.Embed(title='Top 10 highest play time in the cluster:', description=msg, color=INFO_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='newest', aliases=['newplayers', 'lastnew'])
    @commands.check(logcommand)
    async def _newest(ctx):
        newlist = getnewestplayers('all', last=5)
        msg2 = 'Last 5 Newest Players to the cluster:'
        msg = ''
        for each in newlist:
            lsplayer = getplayer(playername=each)
            lspago = elapsedTime(Now(), lsplayer[6], nowifmin=False)
            msg = msg + f'**{lsplayer[1].title()}** joined ***{lsplayer[3].capitalize()}***  -  {lspago} ago\n'
        embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='myinfo', aliases=['mypoints', 'info'])
    @commands.check(logcommand)
    @commands.check(is_linked)
    async def _myinfo(ctx):
        whofor = str(ctx.message.author).lower()
        kuser = getplayer(discordid=whofor)
        log.debug(f'myinfo request from {whofor} passed, showing info for player {kuser[1]}')
        ptime = playedTime(int(kuser[4]))
        ptr = elapsedTime(Now(), int(kuser[2]))
        lpts = totallotterydeposits(kuser[0])
        msg = f'Last played **{ptr} ago** on server ***{kuser[3].capitalize()}***\n'
        msg = msg + f'Your current reward points: **{kuser[5] + kuser[16] + lpts}**\n'
        msg = msg + f'Your home server is: **{kuser[15].capitalize()}**\nYour total play time is: **{ptime}**\n'
        msg = msg + f'You have **{kuser[10]}** current auctions: **{kuser[11]}** Items & **{kuser[12]}** Dinos\n'
        tpwins, twpoints = getlottowinnings(kuser[1])
        msg = msg + f'Total Lotterys Won: **{tpwins}**  Total Lottery Points Won: **{twpoints}** Points\n'
        woodtime = 1296000
        stonetime = 1987200
        metaldinotime = 2624400
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
        embed = discord.Embed(title=f'Player information for **{kuser[1].capitalize()}**:', description=msg, color=SUCCESS_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=False)

    @client.command(name='winners', aliases=['lottowinners', 'lastlotto'])
    @commands.check(logcommand)
    async def _winners(ctx):
        last5 = await db.fetchall("SELECT * FROM lotteryinfo WHERE completed = True AND winner != 'None' ORDER BY id DESC LIMIT 5")
        top5 = await db.fetchall("SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 5")
        msg2 = 'Last 5 Lottery Winners:'
        msg = ''
        try:
            for peach in last5:
                msg = msg + f'**{peach[6].capitalize()}** won **{peach[1]}** Points  -  {elapsedTime(datetimeto(peach[2] + timedelta(hours=int(peach[5])), fmt="epoch"),Now())} ago\n'
            embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)
            msg2 = 'Top 5 All Time Lottery Winners:'
            ccount = 0
            newtop = top5.copy()
            msg = ''
            for heach in newtop:
                ccount += 1
                msg = msg + f'#{ccount} **{heach[1].capitalize()}** with **{heach[18]}** Lottery Wins.  **{heach[19]}** Total points won.\n'
        except:
            log.exception('Critical Error determining lottery winners!')
        embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='decay', aliases=['expire', 'mydecay'])
    @commands.check(logcommand)
    async def _decay(ctx):
        whofor = str(ctx.message.author).lower()
        kuser = getplayer(discordid=whofor)
        msg2 = 'Galaxy Cluster Structure & Dino expire times:'
        msg = 'Dinos: **30 Days**, Tek: **38 Days**, Metal: **30 Days**, Stone: **23 Days**, Wood: **15 Days**\n'
        msg = msg + f'Thatch: **7.5 Days**, Greenhouse: **9.5 Days** (Use MetalGlass for **30 Day** Greenhouse).\n\n'
        if kuser:
            if kuser[8] != whofor:
                log.info(f'decay request from {whofor} public only, no account linked')
                msg = msg + f'Your discord account is not linked, I cannot determine your decay time left.'
            else:
                log.debug(f'decay request from {whofor} accepted, showing detailed info')
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
                    log.exception('Critical Error in decay calculation!')
        embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='event', aliases=['events'])
    @commands.check(logcommand)
    async def _event(ctx):
        lastevent = getlasteventinfo()
        currentevent = getcurrenteventinfo()
        nextevent = getnexteventinfo()
        try:
            if currentevent:
                title = f'Event {currentevent[4]} is currently active'
                desc = f'{currentevent[5]}\nEvent ends in {elapsedTime(datetimeto(d2dt_maint(currentevent[3]), fmt="epoch"), Now())}'
            else:
                title = f'There are no events currently active'
                desc = f'Last event was {lastevent[4]} {elapsedTime(datetimeto(d2dt_maint(lastevent[3]), fmt="epoch"), Now())} ago'
            embed = discord.Embed(title=title, description=desc, color=INFO_COLOR)
            if nextevent:
                embed.add_field(name=f'Next event is {nextevent[4]}', value=f'{nextevent[5]}\nNext event starts in {elapsedTime(datetimeto(d2dt_maint(nextevent[2]), fmt="epoch"), Now())}', inline=False)
            else:
                embed.add_field(name=f'Next Event is not scheduled yet', value=f'Check back again soon for the next event', inline=False)
            await messagesend(ctx, embed=embed, allowgeneral=True, reject=False)
        except:
            log.exception(f'Error calculating events')

    @client.command(name='vote', aliases=['startvote'])
    @commands.check(logcommand)
    async def _vote(ctx):
        msg = f'Wild dino wipe voting is only allowed in-game.\n\nGoto the #poll-channel to vote on a poll.'
        embed = discord.Embed(description=msg, color=FAIL_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='lastrestart', aliases=['restart'])
    @commands.check(logcommand)
    async def _lastrestart(ctx, *args):
        if args:
            instr = args.lower()
            if instr in instancelist():
                lastrestartt = elapsedTime(Now(), getlastrestart(instr))
                msg = f'**{instr.title()}** last restarted **{lastrestartt} ago** for a {getlastrestartreason(instr)}'
                embed = discord.Embed(description=msg, color=INFO_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)
            else:
                msg = f'The server **{instr.title()}** does not exist in the cluster, !help for more information'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)
        else:
            msg = ''
            for each in instancelist():
                lastwipet = elapsedTime(Now(), getlastrestart(each))
                msg = msg + f'**{each.capitalize()}** last restarted **{lastwipet} ago** for a {getlastrestartreason(each)}\n'
            embed = discord.Embed(description=msg, color=INFO_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='lastwipe', aliases=['lastwildwipe'])
    @commands.check(logcommand)
    async def _lastwipe(ctx, *args):
        if args:
            instr = args[0].lower()
            if instr in instancelist():
                lastwipet = elapsedTime(Now(), getlastwipe(instr))
                msg = f'Last wild dino wipe for **{instr.capitalize()}** was **{lastwipet} ago**'
                embed = discord.Embed(description=msg, color=INFO_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)
            else:
                msg = f'The server **{instr.capitalize()}** was not found in the cluster, !help for more information'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)
        else:
            msg = ''
            for each in instancelist():
                lastwipet = elapsedTime(Now(), getlastwipe(each))
                msg = msg + f'Last wild dino wipe for **{each.capitalize()}** was **{lastwipet} ago**\n'
            embed = discord.Embed(description=msg, color=INFO_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='timeleft', aliases=['time'])
    @commands.check(logcommand)
    async def _timeleft(ctx, *args):
        if args:
            instr = args[0].lower()
            if instr in instancelist():
                srest = await db.fetchone(f"SELECT needsrestart, restartcountdown FROM instances where name = '{instr}'")
                if srest[0][0] == 'False':
                    msg = f'Server **{instr.title()}** is not currently in a restart countdown'
                else:
                    msg = f'Server **{instr.title()}** has **{srest[0][1]}** minutes left until restart'
                embed = discord.Embed(description=msg, color=INFO_COLOR)
                await messagesend(ctx, embed, allowgeneral=True, reject=True)
            else:
                msg = f'The server **{instr.capitalize()}** was not found in the cluster, !help for more information'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)
        else:
            msg = ''
            for each in instancelist():
                srest = await db.fetchone(f"SELECT needsrestart, restartcountdown FROM instances where name = '{each}'")
                if srest[0][0] == 'False':
                    msg = msg + f'Server **{each.title()}** is not currently in a restart countdown\n'
                else:
                    msg = msg + f'Server **{each.title()}** has **{srest[1]}** minutes left until restart\n'
            embed = discord.Embed(description=msg, color=INFO_COLOR)
            await messagesend(ctx, embed, allowgeneral=True, reject=True)

    @client.command(name='who', aliases=['players', 'whosonline', 'online'])
    @commands.check(logcommand)
    async def _who(ctx):
        tcnt = 0
        for each in instancelist():
            pcnt = getplayersonlinenames(each, fmt='count')
            tcnt = tcnt + pcnt
        embed = discord.Embed(title=f" **{tcnt}**  total players currently online in the cluster", color=INFO_COLOR)
        for each in instancelist():
            pcnt = getplayersonlinenames(each, fmt='count')
            plist = getplayersonlinenames(each, fmt='string', case='title')
            if pcnt != 0:
                embed.add_field(name=f"{each.capitalize().strip()} has  **{pcnt}**  players online:", value=f"{plist}", inline=False)
            else:
                embed.add_field(name=f"{each.capitalize().strip()} has no players online", value="\u200b", inline=False)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(name='rates', aliases=['serverrates', 'rate'])
    @commands.check(logcommand)
    async def _rates(ctx):
        await serverrates(ctx)

    @client.command(name='rules', aliases=['serverrules', 'clusterrules'])
    @commands.check(logcommand)
    async def _rules(ctx):
        await serverrules(ctx)

    @client.command(name='tip', aliases=['tips', 'protip', 'justthetip'])
    @commands.check(logcommand)
    async def _tip(ctx):
        await protip(ctx)

    @client.command(name='testing123')
    @commands.check(logcommand)
    @commands.check(is_admin)
    async def _test(ctx):
        try:
            linfo = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
            bcast = f"""<RichColor Color="0.0.0.0.0.0"> </>\n<RichColor Color="0,1,0,1">                      A points lottery is currently running!</>\n                        {linfo['buyin']} points to enter in this lottery\n<RichColor Color="1,1,0,1">           Current lottery is up to {linfo['payout']} points and grows as players enter </>\n                      Lottery Ends in {elapsedTime(datetimeto(linfo['startdate'] + timedelta(hours=linfo['days']), fmt='epoch'),Now())}\n\n                  Type !lotto for more info or !lotto enter to join"""

            writeglobal('coliseum', 'LOTTERY', bcast)

        except:
            log.exception('error in test')

    @client.command(name='whotoday', aliases=['today', 'lastday'])
    @commands.check(logcommand)
    async def _today(ctx):
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
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(name='kickme', aliases=['kick'])
    @commands.check(logcommand)
    @commands.check(is_linked)
    async def _kickme(ctx):
        whofor = str(ctx.message.author).lower()
        kuser = getplayer(discordid=whofor)
        if Now() - float(kuser[2]) > 300:
            log.info(f'kickme request from {whofor} denied, not connected to a server')
            msg = f'**{kuser[1].capitalize()}** is not connected to any servers in the cluster'
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
        else:
            log.debug(f'kickme request from {whofor} passed, kicking player on {kuser[3]}')
            msg = f'Kicking **{kuser[1].capitalize()}** from the ***{kuser[3].capitalize()}*** server'
            await db.update(f"INSERT INTO kicklist (instance,steamid) VALUES ('{kuser[3]}','{kuser[0]}')")
            embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
        if str(ctx.message.channel) == 'bot-channel':
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.author.send(embed=embed)
        if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
            await ctx.message.delete()

    @client.command(name='linkme', aliases=['link'])
    @commands.check(logcommand)
    async def _linkme(ctx, *args):
        whofor = str(ctx.message.author).lower()
        dplayer = await db.fetchone(f"SELECT playername FROM players WHERE discordid = '{whofor}'")
        if dplayer:
            log.info(f'link account request on discord from {whofor} denied, already linked')
            msg = f'Your discord account is already linked to your in-game player **{dplayer[0].title()}**'
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
        else:
            if args:
                reqs = await db.fetchone(f"SELECT * FROM linkrequests WHERE reqcode = '{args[0]}'")
                if reqs:
                    log.success(f'Link on discord from [{whofor.title()}] successful for player [{reqs[1].title()}]')
                    await db.update(f"UPDATE players SET discordid = '{whofor}' WHERE steamid = '{reqs[0]}'")
                    await db.update(f"DELETE FROM linkrequests WHERE reqcode = '{args[0]}'")
                    msg = f'Your discord account *[{whofor}]* is now linked to your player **{reqs[1].title()}**\n\nYou can now use discord commands like:\n**`!kickme`** to kick your player off the server so you dont have to wait\n**`!myinfo`** to see all your cluster player information\n**`!help`** for a list of all the commands'
                    embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                    try:
                        await client.http.add_role(329659318972448771, ctx.message.author.id, 329691280412114945)
                    except:
                        log.error('Error applying Linked Player role to user [{user}]')
                else:
                    log.warning(f'link account request on discord from {whofor} denied, code not found')
                    msg = f'That link request code was not found. You must get a link code from typing !linkme in-game'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
            else:
                log.warning(f'link account request on discord from {whofor} denied, no code specified')
                msg = f'You must first type !linkme in-game to get a code, then specify that code here to link your accounts'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
        if str(ctx.message.channel) == 'bot-channel':
            await ctx.message.channel.send(embed=embed)
        else:
            await ctx.message.author.send(embed=embed)
        if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
            await ctx.message.delete()

    @client.command(name='lastseen', aliases=['laston', 'lastonline'])
    @commands.check(logcommand)
    async def _lastseen(ctx, *, arg):
        seenname = arg.lower()
        flast = getplayerlastseen(playername=seenname)
        if not flast:
            msg = f'No player was found with name **{seenname}**'
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)
        else:
            plasttime = elapsedTime(Now(), flast)
            srv = getplayerlastserver(playername=seenname)
            if plasttime != 'now':
                msg = f'**{seenname.title()}** was last seen **{plasttime} ago** on ***{srv.capitalize()}***'
                embed = discord.Embed(description=msg, color=INFO_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)
            else:
                msg = f'**{seenname.title()}** is online now on ***{srv.capitalize()}***'
                embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @_lastseen.error
    async def lastseen_error(error, ctx):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = f'You must specify a player name to search for: **`!lastseen <playername>`**'
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(name='myhome', aliases=['home', 'homeserver', 'sethome'])
    @commands.check(logcommand)
    @commands.check(is_linked)
    async def _myhome(ctx, *args):
        whofor = str(ctx.message.author).lower()
        kuser = getplayer(discordid=whofor)
        if kuser:
            if args:
                log.log('PLAYER', f'home server change request for {kuser[1]}')
                msg = f'You must type **!myhome <newserver>** in-game chat on your current home server **{kuser[15].capitalize()}** to change home servers'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
            else:
                log.log('PLAYER', f'Home server request granted for [{kuser[1].title()}]')
                msg = f'Your current home server is: **{kuser[15].capitalize()}**\nThis is the server all your points go to'
                embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
        else:
            log.warning(f'Home server request from [{whofor.title()}] denied, no account linked')
            msg = f"Your discord account is not linked to your in-game player, Type **`!linkme`** in-game to do this"
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=False)

    @client.command(name='lotto', aliases=['lottery'])
    @commands.check(logcommand)
    @commands.check(is_linked)
    async def _lotto(ctx, *args):
                generalchat = client.get_channel(int(generalchat_id))
                whofor = str(ctx.message.author).lower()
                linfo = await db.fetchone("SELECT * FROM lotteryinfo WHERE completed = False")
                if args:
                    if args[0].lower() == 'enter' or args[0].lower() == 'join':
                        lpinfo = await db.fetchone(f"SELECT * FROM players WHERE discordid = '{whofor}'")
                        if not lpinfo:
                            log.warning(f'Lottery join request from [{whofor.title()}] denied, account not linked')
                            msg = f'Your discord account must be linked to your in-game player account to join a lottery from discord.\nType !linkme in-game to do this'
                            embed = discord.Embed(description=msg, color=FAIL_COLOR)
                            if str(ctx.message.channel) == 'bot-channel':
                                await ctx.message.channel.send(embed=embed)
                            else:
                                await ctx.message.author.send(embed=embed)
                        else:
                            whofor = lpinfo[1]
                            lpcheck = await db.fetchone(f"SELECT * FROM lotteryplayers WHERE steamid = '{lpinfo[0]}'")
                            lfo = 'Reward Points'
                            # ltime = epochto(float(linfo[3]) + (Secs['hour'] * int(linfo[5])), 'string', est=True)
                            if lpcheck is None:
                                await db.update("INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('%s', '%s', '%s', '%s')" % (lpinfo[0], lpinfo[1], Now(fmt='dt'), 0))
                                await db.update("UPDATE lotteryinfo SET payout = '%s', players = '%s' WHERE id = %s" % (linfo["payout"] + linfo["buyin"] * 2, linfo["players"] + 1, linfo["id"]))
                                msg = f'You have been added to the {lfo} lottery!\nThis lottery has now risen to **{linfo["payout"] + linfo["buyin"] * 2}** points.\nA winner will be choosen in **{elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}**. Good Luck!'
                                embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                                if str(ctx.message.channel) == 'bot-channel':
                                    await ctx.message.channel.send(embed=embed)
                                else:
                                    await ctx.message.author.send(embed=embed)
                                if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
                                    await ctx.message.delete()
                                log.log('LOTTO', f'Player [{whofor.title()}] has joined the current active lottery')
                                if Now(fmt='dt') - await getlastannounce('lastlottoannounce') > timedelta(hours=1):
                                    embed2 = discord.Embed(title=f"A player has entered the lottery!", color=INFO_COLOR)
                                    embed2.set_author(name='Galaxy Cluster Reward Point Lottery', icon_url='https://blacklabelagency.com/wp-content/uploads/2017/08/money-icon.png')
                                    embed2.add_field(name=f"Current lottery has risen to **{linfo['payout'] + linfo['buyin'] * 2} Points**", value=f"**{linfo['players'] + 1}** Players have entered into this lottery so far\nLottery ends in **{elapsedTime(datetimeto(linfo['startdate'] + timedelta(hours=linfo['days']), fmt='epoch'),Now())}**\n**`!lotto enter`** to join the lottery\n**`!points`** for more information\n**`!winners`** for recent results", inline=True)
                                    msg = await generalchat.send(embed=embed2)
                                    await setlastannounce('lastlottoannounce', Now(fmt='dt'))
                                    await clearmessages('lotterymessage')
                                    await addmessage('lotterymessage', msg.id)
                                else:
                                    pass
                            elif not linfo:
                                msg = 'There are no lotterys currently underway.'
                                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                                if str(ctx.message.channel) == 'bot-channel':
                                    await ctx.message.channel.send(embed=embed)
                                else:
                                    await ctx.message.author.send(embed=embed)
                                if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
                                    await ctx.message.delete()
                            else:
                                msg = f'You are already participating in the current lottery for {lfo}.\nThis lottery is currently at **{linfo["payout"]}** points.\nLottery ends in **{elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}**'
                                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                                if str(ctx.message.channel) == 'bot-channel':
                                    await ctx.message.channel.send(embed=embed)
                                else:
                                    await ctx.message.author.send(embed=embed)
                                if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
                                    await ctx.message.delete()
                else:
                    if linfo:
                        msg = f'It costs **{linfo["buyin"]} points** to join this lottery\n**`!lotto enter`** to join the lottery\n**`!winners`** for recent results\n**`!points`** for more information'
                        embed = discord.Embed(title=f"Current lottery is up to {linfo['payout']} reward points", description=f"{linfo['players']} players have entered into this lottery so far", color=SUCCESS_COLOR)
                        embed.add_field(name=f'Lottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}', value=msg, inline=False)
                        if str(ctx.message.channel) == 'bot-channel':
                            await ctx.message.channel.send(embed=embed)
                        else:
                            await ctx.message.author.send(embed=embed)
                    else:
                        msg = 'There are no lotteries currently underway.'
                        embed = discord.Embed(description=msg, color=FAIL_COLOR)
                        await ctx.message.author.send(embed=embed)
                        if type(ctx.message.channel) != discord.channel.DMChannel and str(ctx.message.channel) != 'bot-channel':
                            await ctx.message.delete()

    @client.event
    async def on_message(message):
        await savediscordtodb(message.author)
        if str(message.author) == "Galaxy Cluster#7499":
            log.trace('skipping processing of bots own on_message trigger')

        elif message.content.lower().find('join the server') != -1 or message.content.lower().find('how do i join') != -1 or message.content.lower().find('server link') != -1 or message.content.lower().find('mod collection') != -1 or message.content.lower().find('mod list') != -1 or message.content.lower().find('link to server') != -1:
            log.log('CMD', f'Responding to [join server] chat for [{message.author}] on [{message.channel}]')
            msg = f'The **`#mods-rates-servers`** channel has information and links to the servers, mods and rates, **`!help`** for commands'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await message.channel.send(embed=embed)

        elif message.content.lower().find('what are the rates') != -1 or message.content.lower().find('server rates') != -1 or message.content.lower().find('tame rate') != -1 or message.content.lower().find('harvest rate') != -1 or message.content.lower().find('current rates') != -1 or message.content.lower().find('breeding rate') != -1 or message.content.lower().find('rates here') != -1:
            log.log('CMD', f'Responding to [server rates] chat for [{message.author}] on [{message.channel}]')
            msg = 'Try using the **`!rates`** command to get current server rates, **`!help`** for more information'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await message.channel.send(embed=embed)

        elif message.content.lower().find('servers up') != -1 or message.content.lower().find('servers down') != -1 or message.content.lower().find('server up') != -1 or message.content.lower().find('server down') != -1 or message.content.lower().find('server status') != -1:
            log.log('CMD', f'Responding to [server up/down] chat for [{message.author}] on [{message.channel}]')
            msg = 'Try using the **`!servers`** command to get all the current servers statuses, **`!help`** for more information'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await message.channel.send(embed=embed)

        elif message.content.lower().find("isn't that right bot") != -1 or message.content.lower().find('isnt that right bot') != -1 or message.content.lower().find('right bot?') != -1:
            log.log('CMD', f'Responding to [right bot?] chat from [{message.author}] on [{message.channel}]')
            msg = 'I dont know shit.'
            await message.channel.send(msg)

        elif message.content.lower().find("hi bot") != -1 or message.content.lower().find('hello bot') != -1:
            log.log('CMD', f'Responding to [hello bot] chat from [{message.author}] on [{message.channel}]')
            msg = 'Hello'
            await message.channel.send(msg)

        elif message.content.lower().find("wb bot") != -1 or message.content.lower().find('welcome back bot') != -1:
            log.log('CMD', f'Responding to [wb bot] chat from [{message.author}] on [{message.channel}]')
            msg = "It's great to be back"
            await message.channel.send(msg)

        elif str(message.channel) == 'server-chat':
            whos = await db.fetchone("fSELECT playername FROM players WHERE discordid = '{str(message.author).lower()}'")
            if whos:
                writeglobal('discord', whos[0], str(message.content).strip("'"))

        elif str(message.channel) == 'server-notifications':
            if message.content.lower().find('server has crashed! - restarting server') != -1:
                generalchat = client.get_channel(int(generalchat_id))
                inst = message.content.split(':')[0].split()[3].lower()
                log.log('CRASH', f'{inst.upper()} Server has crashed at {Now(fmt="string", est=True)} EST')
                await db.update("UPDATE instances SET isup = 0, lastcrash = '%s', lastrestart = '%s' where name = '%s'" % (Now(fmt='dt'), str(Now(fmt='epoch')), inst))
                msg = f'The **{inst.title()}** server has crashed!\n\nServer is now restarting, there may be a slight rollback'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await generalchat.send(embed=embed)
        else:
            await client.process_commands(message)

    while True:
        try:
            client.loop.create_task(chatbuffer())
            client.loop.create_task(taskchecker())
            client.run(discordtoken)
        except RuntimeError:
            _exit(1)
        except:
            log.exception('Critical Error in Discord Bot Routine.')
        finally:
            client.close()
