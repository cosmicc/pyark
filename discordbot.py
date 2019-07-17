from datetime import timedelta
from clusterevents import getcurrenteventinfo, getlasteventinfo, getnexteventinfo
from modules.auctionhelper import fetchauctiondata, getauctionstats, writeauctionstats
from modules.configreader import discord_channel, discord_serverchat, discordtoken
from modules.dbhelper import dbquery, dbupdate
from modules.instances import instancelist, getlastwipe, getlastrestart, writechat, writeglobal, getlastrestartreason
from modules.players import getplayer, getplayerlastserver, getplayersonline, getlastplayersonline, getplayerlastseen, getplayerstoday, getnewestplayers, gettopplayedplayers, isplayeradmin, setprimordialbit
from modules.timehelper import elapsedTime, playedTime, wcstamp, epochto, Now, Secs, datetimeto, d2dt_maint
from time import sleep
from lottery import totallotterydeposits, isinlottery, getlottowinnings
from os import system
import asyncio
import discord
from discord.ext import commands
from loguru import logger as log

client = commands.Bot(command_prefix='!', case_insensitive=True)
client.remove_command('help')

lastupdateannounce = Now(fmt='dt') + timedelta(minutes=21)

channel = discord.Object(id=discord_serverchat)
channel2 = discord.Object(id=discord_channel)

SUCCESS_COLOR = 0x00ff00
FAIL_COLOR = 0xff0000
INFO_COLOR = 0x0088ff
HELP_COLOR = 0xff8800

rejectmsg = 'Bot commands are limited to the **`#bot-channel`** and **Private message** (here)\nType **`!help`** for a description of all the commands'


def clog(msg, inst):
    with open(f"/home/ark/shared/logs/{inst}/gamelog/crash.log", "at") as f:
            f.write(f"""{Now(fmt='string')} - {msg.strip()}\n""")
    f.close()


def getlastlottoannounce():
    lastl = dbquery("SELECT lastlottoannounce FROM general", fetch='one', single=True)
    return lastl[0]


def getrates():
    return dbquery("SELECT * FROM rates", fetch='one', fmt='dict')


def setlastlottoannounce(tstamp):
    dbupdate("UPDATE general SET lastlottoannounce = '%s'" % (tstamp,))


def writediscord(msg, tstamp, server='generalchat', name='ALERT'):
    dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (server, name, msg, tstamp))


def savediscordtodb(author):
    didexists = dbquery("SELECT * FROM discordnames WHERE discordname = '%s'" % (str(author),), fetch='one')
    if not didexists:
        dbupdate("INSERT INTO discordnames (discordname) VALUES ('%s')" % (str(author),))


@log.catch
def discordbot():
    global client

    async def taskchecker():
        await client.wait_until_ready()
        while not client.is_closed:
            try:
                # log.debug('executing discord bot task checker')
                if Now(fmt='dt') - getlastlottoannounce() > timedelta(hours=6) and isinlottery():
                    linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
                    log.info('announcing running lottery in discord')
                    embed = discord.Embed(title=f"A lottery is currently running!", color=INFO_COLOR)
                    embed.set_author(name='Galaxy Cluster Reward Point Lottery', icon_url='http://icons.iconarchive.com/icons/custom-icon-design/pretty-office-11/512/coin-us-dollar-icon.png')
                    embed.add_field(name=f"Current lottery is up to **{linfo['payout']} Points**", value=f"**{linfo['players'] + 1}** Players have entered into this lottery so far\nLottery ends in **{elapsedTime(datetimeto(linfo['startdate'] + timedelta(hours=linfo['days']), fmt='epoch'),Now())}**\n\nType **`!lotto enter`** to join, or **`!points`** for more information", inline=True)
                    await client.send_message(channel2, embed=embed)
                    setlastlottoannounce(Now(fmt='dt'))
                await asyncio.sleep(60)
            except:
                log.critical('error in task checker!', exc_info=True)

    async def chatbuffer():
        global lastupdateannounce
        await client.wait_until_ready()
        while not client.is_closed:
            try:
                cbuff = dbquery("SELECT * FROM chatbuffer")
                if cbuff:
                    for each in cbuff:
                        if each[0] == "generalchat":
                            msg = each[2]
                            await client.send_message(channel2, msg)
                            # await asyncio.sleep(2)
                        elif each[0] == 'LOTTOSTART':
                            setlastlottoannounce(Now(fmt='dt'))
                            embed = discord.Embed(title=f"A new Lottery has started!", color=SUCCESS_COLOR)
                            embed.set_author(name='Galaxy Cluster Reward Points Lottery', icon_url='http://icons.iconarchive.com/icons/custom-icon-design/pretty-office-11/512/coin-us-dollar-icon.png')
                            buyin = int(each[2]) / 25
                            embed.add_field(name=f"Starting Pot: {each[2]} Points", value=f"It costs **{int(buyin)} Points** to join this lottery, lottery winnings grow as more join\nLottery will end in **{each[1]}**\n\nType **`!lotto enter`** to join this lottery, or **`!points`** for more information", inline=False)
                            await client.send_message(channel2, embed=embed)
                        elif each[0] == 'LOTTOEND':
                            embed = discord.Embed(title=f"The current Lottery has ended", color=SUCCESS_COLOR)
                            embed.set_author(name='Galaxy Cluster Reward Points Lottery', icon_url='http://icons.iconarchive.com/icons/custom-icon-design/pretty-office-11/512/coin-us-dollar-icon.png')
                            embed.add_field(name=f"Congratulations to {each[2].upper()} winning **{each[1]}** Points", value=f"Next lottery will start in **1** hour, Type **`!points`** for more information", inline=False)
                            await client.send_message(channel2, embed=embed)
                        elif each[0] == 'UPDATE':
                            if Now(fmt='dt') - lastupdateannounce > timedelta(minutes=20):
                                lastupdateannounce = Now(fmt='dt')
                                embed = discord.Embed(title=f"A New Update has been released!", color=INFO_COLOR)
                                embed.set_author(name='ARK Updater for Galaxy Cluster Servers', icon_url='https://patchbot.io/images/games/ark_sm.png')
                                embed.add_field(name=f"Update Reason: {each[2]}", value=f"{each[1]}\n\nAny applicable servers will begin a **30 min** restart countdown now", inline=False)
                                await client.send_message(channel2, embed=embed)
                        else:
                            if each[1] == "ALERT":
                                msg = f'{each[3]} [{each[0].capitalize()}] {each[2]}'
                            else:
                                msg = f'{each[3]} [{each[0].capitalize()}] {each[1].capitalize()} {each[2]}'
                            await client.send_message(channel, msg)
                            # await asyncio.sleep(2)
                    dbupdate("DELETE FROM chatbuffer")
                now = Now()
                cbuffr = dbquery("SELECT * FROM players WHERE lastseen < '%s' AND lastseen > '%s'" % (now - 40, now - 44))
                if cbuffr:
                    for reach in cbuffr:
                        log.log('LEAVE', f'{reach[1]} has left the server {reach[3]}')
                        mt = f'{reach[1].capitalize()} has left the server'
                        writeglobal(reach[3], 'ALERT', mt)
                        writechat(reach[3], 'ALERT', f'>>> {reach[1].title()} has left the server', wcstamp())
            except discord.errors.HTTPException:
                log.warning('HTTP Exception error while contacting discord!')
            except:
                log.critical('Critical Error in Chat Buffer discord writer!', exc_info=True)
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

    async def messagesend(ctx, embed, allowgeneral=False, reject=True, adminonly=False):
        try:
            if ctx.message.channel.is_private:
                await client.send_message(ctx.message.author, embed=embed)
            elif str(ctx.message.channel) != 'bot-channel' or (not allowgeneral and str(ctx.message.channel) == 'general-chat'):
                role = str(discord.utils.get(ctx.message.author.roles, name="Cluster Admin"))
                if role != 'Cluster Admin':
                    await client.delete_message(ctx.message)
                if reject and role != 'Cluster Admin':
                    rejectembed = discord.Embed(description=rejectmsg, color=HELP_COLOR)
                    await client.send_message(ctx.message.author, embed=rejectembed)
                elif role != 'Cluster Admin':
                    await client.send_message(ctx.message.author, embed=embed)
                else:
                    await client.send_message(ctx.message.channel, embed=embed)
            else:
                await client.send_message(ctx.message.channel, embed=embed)
        except:
            log.critical('Critical error in discord send', exc_info=True)

    @client.event
    async def on_member_join(member):
        log.info(f'new user has joined the Discord server: {member}')
        fmt = 'If you are already a player on the servers, type **`!linkme`** in-game to link your discord account to your ark player.\n'
        fmt = fmt + 'Type **`!servers`** for links iand status of the servers\nType **`!mods`** for a link to the mod collection\n**`!help`** for all the other commands\n\n'
        fmt = fmt + 'More help can be found with pinned messages in **#help**\nDont be afraid to ask for help in discord!'
        embed = discord.Embed(title="Welcome to the Galaxy Cluster Ultimate Extinction Core Server Discord!", description=fmt, color=HELP_COLOR)
        await client.send_message(member, embed=embed)

    @client.event
    async def on_ready():
        log.info(f'discord logged in as {client.user.name} id {client.user.id}')
        await client.change_presence(game=discord.Game(name="!help"))

    @client.event
    async def on_command_error(error, ctx):
        try:
            if isinstance(error, commands.CommandNotFound):
                log.warning(f'invalid discord command {ctx.message.content} sent from {ctx.message.author}')
                msg = f'**`{ctx.message.content}`** command does not exist'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
            elif isinstance(error, NotLinked):
                log.warning(f'Player is not linked {ctx.message.author}')
                msg = f'Your discord account needs to be linked to your in-game player first. Type **`!linkme`** in-game to do this'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
            elif isinstance(error, commands.CheckFailure):
                log.warning(f'discord check failed: {error}')
            else:
                log.warning(f'discord bot error for {ctx.message.author}: {ctx.message.content} - {error}')
        except:
            log.critical('command error: ', exc_info=True)

    @client.command(pass_context=True, name='help', aliases=['helpme', 'commands'])
    async def _help(ctx):
        log.info(f'help request on discord from {ctx.message.author}')
        msg = ''
        # msg3 = '!lasthour, !timeleft'
        msg = msg + "**`!mods`**  - Link to all the mods for this cluster\n"
        msg = msg + "**`!servers`**  - Status and links to all the servers in the cluster\n"
        msg = msg + "**`!rates`**  - Current ARK game rates for all the cluster servers\n"
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
        msg = msg + "**`!primordial`**  - Warns you in-game if you haven't logged in since the server has restarted (so you can reset your primordial's buff bug)\n\n"
        msg = msg + "The servers available are:"
        for eachinst in instancelist():
            msg = msg + f"  **`{eachinst}`**,"
        msg = msg + "\n\n"
        msg = msg + 'Commands can be privately messaged directly to the bot or in the **#bot-channel**'

        embed = discord.Embed(title="Galaxy Custom Bot Commands:", description=msg, color=HELP_COLOR)
        await client.send_message(ctx.message.author, embed=embed)
        if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
            await client.delete_message(ctx.message)

    @client.command(pass_context=True, name='mods', aliases=['mod', 'arkmods'])
    async def _mods(ctx):
        msg = f'Galaxy Cluster Ultimate Extinction Core Mod Collection:\nhttps://steamcommunity.com/sharedfiles/filedetails/?id=1475281369'
        embed = discord.Embed(description=msg, color=HELP_COLOR)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(pass_context=True, name='points', aliases=['rewards'])
    async def _rewards(ctx):
        msg = f'Galaxy Cluster Ultimate Extinction Core Rewards Vault, ARc Points, Home Server, Lotterys, & Currency:\nhttps://docs.google.com/document/d/154QjLnw4hjxe_DtiTqfSwINsKdUp9Iz3M_umcI5zkRk/edit?usp=sharing'
        embed = discord.Embed(description=msg, color=HELP_COLOR)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(pass_context=True, name='ec', aliases=['extinction'])
    async def _ec(ctx):
        msg = f'Extinction Core Info:\nhttps://steamcommunity.com/workshop/filedetails/discussion/817096835/1479857071254169967\nExtinction Core Wiki:\nhttp://extinctioncoreark.wikia.com/wiki/Extinction_Core_Wiki\nExtinction Core Dino Spreadsheet\nhttps://docs.google.com/spreadsheets/d/1GtqBvFK0R0VI7dj7CdkXEuQydqw3xjITZmc0qD95Kug/edit?usp=sharing'
        embed = discord.Embed(description=msg, color=HELP_COLOR)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(pass_context=True, name='servers', aliases=['server'])
    async def _servers(ctx):
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
            embed.add_field(name=f'Server {instt[0].capitalize()} is  **{onl}**  Players ({pcnt}/50)', value=f'Hostname: {instt[23]}\nSteam: {instt[15]}\nArkServers: {instt[16]}\nBattleMetrics: {instt[17]}', inline=False)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(pass_context=True, name='primordial')
    @commands.check(is_linked)
    async def _primordial(ctx):
        pplayer = dbquery("SELECT * from players WHERE discordid = '%s'" % (str(ctx.message.author).lower(),), fetch='one')
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

    @client.command(pass_context=True, name='topplayed', aliases=['topplayers', 'topplaytime'])
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

    @client.command(pass_context=True, name='newest', aliases=['newplayers', 'lastnew'])
    async def _newest(ctx):
        newlist = getnewestplayers('all', last=5)
        msg2 = 'Last 5 Newest Players to the cluster:'
        msg = ''
        for each in newlist:
            lsplayer = getplayer(playername=each)
            lspago = elapsedTime(Now(), lsplayer[6])
            msg = msg + f'**{lsplayer[1].title()}** joined ***{lsplayer[3].capitalize()}***  -  {lspago} ago\n'
        embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(pass_context=True, name='myinfo', aliases=['mypoints'])
    @commands.check(is_linked)
    async def _myinfo(ctx):
        whofor = str(ctx.message.author).lower()
        kuser = getplayer(discordid=whofor)
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

    @client.command(pass_context=True, name='winners', aliases=['lottowinners', 'lastlotto'])
    async def _winners(ctx):
        last5 = dbquery("SELECT * FROM lotteryinfo WHERE completed = True AND winner != 'None' ORDER BY id DESC LIMIT 5")
        top5 = dbquery("SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 5")
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
            log.critical('Critical Error determining lottery winners!', exc_info=True)
        embed = discord.Embed(title=msg2, description=msg, color=INFO_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(pass_context=True, name='decay', aliases=['expire', 'mydecay'])
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
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(pass_context=True, name='event', aliases=['events'])
    async def _event(ctx):
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
            await messagesend(ctx, msg, allowgeneral=False, reject=True)
        except:
            log.critical(f'Error calculating events', exc_info=True)

    @client.command(pass_context=True, name='vote', aliases=['startvote'])
    async def _vote(ctx):
        msg = f'Wild dino wipe voting is only allowed in-game.\n\nGoto the #poll-channel to vote on a poll.'
        embed = discord.Embed(description=msg, color=FAIL_COLOR)
        await messagesend(ctx, embed, allowgeneral=False, reject=True)

    @client.command(pass_context=True, name='lastrestart', aliases=['restart'])
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

    @client.command(pass_context=True, name='lastwipe', aliases=['lastwildwipe'])
    async def _lastwipe(ctx, *args):
        if args:
            instr = args.lower()
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

    @client.command(pass_context=True, name='timeleft', aliases=['time'])
    async def _timeleft(ctx, *args):
        if args:
            instr = args[0].lower()
            if instr in instancelist():
                srest = dbquery(f"SELECT needsrestart, restartcountdown FROM instances where name = '%s'" % (instr,))
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
                srest = dbquery(f"SELECT needsrestart, restartcountdown FROM instances where name = '%s'" % (each,))
                if srest[0][0] == 'False':
                    msg = msg + f'Server **{each.title()}** is not currently in a restart countdown\n'
                else:
                    msg = msg + f'Server **{each.title()}** has **{srest[1]}** minutes left until restart\n'
            embed = discord.Embed(description=msg, color=INFO_COLOR)
            await messagesend(ctx, embed, allowgeneral=True, reject=True)

    @client.command(pass_context=True, name='who', aliases=['whoson', 'whosonline', 'online'])
    async def _who(ctx):
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
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(pass_context=True, name='rate', aliases=['serverrates', 'rates'])
    async def _rate(ctx):
        rates = getrates()
        cevent = getcurrenteventinfo()
        if cevent is not None:
            eventtext = '*No events are currently active*'
        else:
            eventtext = '*Event is active*'
        embed = discord.Embed(title='Current Galaxy Cluster Server Rates:', color=INFO_COLOR)
        embed.add_field(name=f"{eventtext}", value=f"Breeding Speed: **{rates['breed']}x**\nTaming Speed: **{rates['tame']}x**\nHarvest Speed: **{rates['harvest']}x**\nMating Speed: **{rates['mating']}x**\nMating Interval: **{rates['matingint']}x**\nHatching Speed: **{rates['hatch']}x**\nPlayer XP Speed: **{rates['playerxp']}x**\nTamed Health Recovery: **{rates['tamehealth']}%**\nPlayer Health Recovery: **{rates['playerhealth']}%**\nPlayer Stamina Drain: **{rates['playersta']}% of Vanilla**\nFood/Water Drain Speed: **{rates['foodwater']}% of Vanilla**\nReward Point per Hour: **{rates['pph']} ({rates['pphx']}x)**\n\nType **`!decay`** to see server dino & structure expiration timers", inline=True)
        await messagesend(ctx, embed, allowgeneral=True, reject=False)

    @client.command(pass_context=True, name='test')
    @commands.check(is_admin)
    async def _test(ctx):
        try:
            #rates = getrates()
            #eventr = getlastlottoannounce()
            #user = ctx.message.author
            #a = str(discord.utils.get(user.roles, name="Cluster Admin"))
            #log.warning(a)
            #log.warning(type(a))
            embed = discord.Embed(title=f"test!", color=INFO_COLOR)
            embed.set_author(name='Galaxy Cluster Reward Server Rates', icon_url='http://icons.iconarchive.com/icons/custom-icon-design/pretty-office-11/512/coin-us-dollar-icon.png')
            embed.add_field(name=f"CTX", value=f"{dir(ctx.message.author.server)}", inline=True)
            await messagesend(ctx, embed, allowgeneral=True, reject=True)
        except:
            log.critical('error in test', exc_info=True)

    @client.command(pass_context=True, name='whotoday', aliases=['today', 'lastday'])
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

    @client.command(pass_context=True, name='kickme', aliases=['kick'])
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
            dbupdate("INSERT INTO kicklist (instance,steamid) VALUES ('%s','%s')" % (kuser[3], kuser[0]))
            embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
        if str(ctx.message.channel) == 'bot-channel':
            await client.send_message(ctx.message.channel, embed=embed)
        else:
            await client.send_message(ctx.message.author, embed=embed)
        if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
            await client.delete_message(ctx.message)

    @client.command(pass_context=True, name='linkme', aliases=['link'])
    async def _linkme(ctx, *args):
        whofor = str(ctx.message.author).lower()
        dplayer = dbquery("SELECT playername FROM players WHERE discordid = '%s'" % (whofor,), fetch='one')
        if dplayer:
            log.info(f'link account request on discord from {whofor} denied, already linked')
            msg = f'Your discord account is already linked to your in-game player **{dplayer[0].title()}**'
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
        else:
            if args:
                reqs = dbquery("SELECT * FROM linkrequests WHERE reqcode = '%s'" % (args[0],), fetch='one')
                if reqs:
                    log.info(f'link account request on discord from {whofor} accepted. \
{reqs[1]} {whofor} {reqs[0]}')
                    dbupdate("UPDATE players SET discordid = '%s' WHERE steamid = '%s'" % (whofor, reqs[0]))
                    dbupdate("DELETE FROM linkrequests WHERE reqcode = '%s'" % (args[0],))
                    msg = f'Your discord account *[{whofor}]* is now linked to your player **{reqs[1].title()}**\n\nYou can now use discord commands like:\n**`!kickme`** to kick your player off the server so you dont have to wait\n**`!myinfo`** to see all your cluster player information\n**`!help`** for a list of all the commands'
                    embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                    role = discord.utils.get(ctx.message.author.server.roles, name="Linked Player")
                    await client.add_roles(ctx.message.author, role)
                else:
                    log.info(f'link account request on discord from {whofor} denied, code not found')
                    msg = f'That link request code was not found. You must get a link code from typing !linkme in-game'
                    embed = discord.Embed(description=msg, color=FAIL_COLOR)
            else:
                log.info(f'link account request on discord from {whofor} denied, no code specified')
                msg = f'You must first type !linkme in-game to get a code, then specify that code here to link your accounts'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
        if str(ctx.message.channel) == 'bot-channel':
            await client.send_message(ctx.message.channel, embed=embed)
        else:
            await client.send_message(ctx.message.author, embed=embed)
        if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
            await client.delete_message(ctx.message)

    @client.command(pass_context=True, name='lastseen', aliases=['laston', 'lastonline'])
    async def _lastseen(ctx, *, arg):
        log.info(f'responding to lastseen request for {arg} from {ctx.message.author} on discord')
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

    @client.command(pass_context=True, name='myhome', aliases=['home', 'homeserver', 'sethome'])
    @commands.check(is_linked)
    async def _myhome(ctx, *args):
        whofor = str(ctx.message.author).lower()
        kuser = getplayer(discordid=whofor)
        if kuser:
            if args:
                log.info(f'home server change request for {kuser[1]}')
                msg = f'You must type **!myhome <newserver>** in-game chat on your current home server **{kuser[15].capitalize()}** to change home servers'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
            else:
                log.info(f'home server request granted for {kuser[1]}')
                msg = f'Your current home server is: **{kuser[15].capitalize()}**\nThis is the server all your points go to'
                embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                await messagesend(ctx, embed, allowgeneral=False, reject=False)
        else:
            log.info(f'home server request from {whofor} denied, no account linked')
            msg = f"Your discord account is not linked to your in-game player, Type **`!linkme`** in-game to do this"
            embed = discord.Embed(description=msg, color=FAIL_COLOR)
            await messagesend(ctx, embed, allowgeneral=False, reject=False)

    @client.command(pass_context=True, name='lotto', aliases=['lottery'])
    @commands.check(is_linked)
    async def _lotto(ctx, *args):
                whofor = str(ctx.message.author).lower()
                linfo = dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fetch='one', fmt='dict')
                if args:
                    if args[0].lower() == 'enter' or args[0].lower() == 'join':
                        lpinfo = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (whofor,), fetch='one')
                        if not lpinfo:
                            log.info(f'lottery join request from {whofor} denied, account not linked')
                            msg = f'Your discord account must be linked to your in-game player account to join a lottery from discord.\nType !linkme in-game to do this'
                            embed = discord.Embed(description=msg, color=FAIL_COLOR)
                            if str(ctx.message.channel) == 'bot-channel':
                                await client.send_message(ctx.message.channel, embed=embed)
                            else:
                                await client.send_message(ctx.message.author, embed=embed)
                        else:
                            whofor = lpinfo[1]
                            lpcheck = dbquery("SELECT * FROM lotteryplayers WHERE steamid = '%s'" % (lpinfo[0],), fetch='one')
                            lfo = 'Reward Points'
                            # ltime = epochto(float(linfo[3]) + (Secs['hour'] * int(linfo[5])), 'string', est=True)
                            if lpcheck is None:
                                dbupdate("INSERT INTO lotteryplayers (steamid, playername, timestamp, paid) VALUES ('%s', '%s', '%s', '%s')" % (lpinfo[0], lpinfo[1], Now(fmt='dt'), 0))
                                dbupdate("UPDATE lotteryinfo SET payout = '%s', players = '%s' WHERE id = %s" % (linfo["payout"] + linfo["buyin"] * 2, linfo["players"] + 1, linfo["id"]))
                                msg = f'You have been added to the {lfo} lottery!\nThis lottery has now risen to **{linfo["payout"] + linfo["buyin"] * 2}** points.\nA winner will be choosen in **{elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}**. Good Luck!'
                                embed = discord.Embed(description=msg, color=SUCCESS_COLOR)
                                if str(ctx.message.channel) == 'bot-channel':
                                    await client.send_message(ctx.message.channel, embed=embed)
                                else:
                                    await client.send_message(ctx.message.author, embed=embed)
                                if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
                                    await client.delete_message(ctx.message)
                                log.info(f'player {whofor} has joined the current active lottery.')
                                if Now(fmt='dt') - getlastlottoannounce() > timedelta(hours=2):
                                    embed2 = discord.Embed(title=f"A new lottery player has entered the lottery!", color=INFO_COLOR)
                                    embed2.set_author(name='Galaxy Cluster Reward Point Lottery', icon_url='http://icons.iconarchive.com/icons/custom-icon-design/pretty-office-11/512/coin-us-dollar-icon.png')
                                    embed2.add_field(name=f"Current lottery has risen to **{linfo['payout'] + linfo['buyin'] * 2} Points**", value=f"**{linfo['players'] + 1}** Players have entered into this lottery so far\nLottery ends in **{elapsedTime(datetimeto(linfo['startdate'] + timedelta(hours=linfo['days']), fmt='epoch'),Now())}**\n\nType **`!lotto enter`** to join, or **`!points`** for more information", inline=True)
                                    await client.send_message(channel2, embed=embed2)
                                    setlastlottoannounce(Now(fmt='dt'))
                                else:
                                    pass
                            elif not linfo:
                                msg = 'There are no lotterys currently underway.'
                                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                                if str(ctx.message.channel) == 'bot-channel':
                                    await client.send_message(ctx.message.channel, embed=embed)
                                else:
                                    await client.send_message(ctx.message.author, embed=embed)
                                if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
                                    await client.delete_message(ctx.message)
                            else:
                                msg = f'You are already participating in the current lottery for {lfo}.\nThis lottery is currently at **{linfo["payout"]}** points.\nLottery ends in **{elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}**'
                                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                                if str(ctx.message.channel) == 'bot-channel':
                                    await client.send_message(ctx.message.channel, embed=embed)
                                else:
                                    await client.send_message(ctx.message.author, embed=embed)
                                if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
                                    await client.delete_message(ctx.message)
                else:
                    if linfo:
                        msg = f'It costs **{linfo["buyin"]} points** to join this lottery\n\nType **`!lotto enter`** to join the lottery, **`!points`** for more information'
                        embed = discord.Embed(title=f"Current lottery is up to {linfo['payout']} reward points", description=f"{linfo['players']} players have entered into this lottery so far", color=SUCCESS_COLOR)
                        embed.add_field(name=f'Lottery ends in {elapsedTime(datetimeto(linfo["startdate"] + timedelta(hours=linfo["days"]), fmt="epoch"),Now())}', value=msg, inline=False)
                        if str(ctx.message.channel) == 'bot-channel':
                            await client.send_message(ctx.message.channel, embed=embed)
                        else:
                            await client.send_message(ctx.message.author, embed=embed)
                    else:
                        msg = 'There are no lotteries currently underway.'
                        embed = discord.Embed(description=msg, color=FAIL_COLOR)
                        await client.send_message(ctx.message.author, embed=embed)
                        if not ctx.message.channel.is_private and str(ctx.message.channel) != 'bot-channel':
                            await client.delete_message(ctx.message)

    @client.event
    async def on_message(message):
        savediscordtodb(message.author)
        if str(message.author) == "Galaxy Cluster#7499":
            log.trace('skipping processing of bots own on_message trigger')
        elif message.content.lower().find('join the server') != -1 or message.content.lower().find('how do i join') != -1 or message.content.lower().find('server link') != -1 or message.content.lower().find('mod collection') != -1 or message.content.lower().find('mod list') != -1 or message.content.lower().find('link to server') != -1:
            log.info(f'responding to join server chat for {message.author} on discrod')
            msg = f'The **`#join-servers`** channel has information and links to the servers and mods, **`!help`** for commands'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await client.send_message(message.channel, embed=embed)
        elif message.content.lower().find('what are the rates') != -1 or message.content.lower().find('server rates') != -1 or message.content.lower().find('tame rate') != -1 or message.content.lower().find('harvest rate') != -1 or message.content.lower().find('current rates') != -1 or message.content.lower().find('breeding rate') != -1 or message.content.lower().find('rates here') != -1:
            log.info(f'responding to server rates chat for {message.author} on discrod')
            msg = 'Try using the **`!rates`** command to get current server rates, **`!help`** for more information'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await client.send_message(message.channel, embed=embed)
        elif message.content.lower().find('servers up') != -1 or message.content.lower().find('servers down') != -1 or message.content.lower().find('server up') != -1 or message.content.lower().find('server down') != -1 or message.content.lower().find('server status') != -1:
            log.info(f'responding to server server up/down chat for {message.author} on discrod')
            msg = 'Try using the **`!servers`** command to get all the current servers statuses, **`!help`** for more information'
            embed = discord.Embed(description=msg, color=HELP_COLOR)
            await client.send_message(message.channel, embed=embed)

        elif str(message.channel) == 'server-chat':
            whos = dbquery("SELECT playername FROM players WHERE discordid = '%s'" % (str(message.author).lower(),), fetch='one')
            if whos:
                writeglobal('discord', whos[0], str(message.content))

        elif str(message.channel) == 'server-notifications':
            if message.content.lower().find('server has crashed! - restarting server') != -1:
                inst = message.content.split(':')[0].split()[3].lower()
                dbupdate("UPDATE instances SET lastcrash = '%s' where name = '%s'" % (Now(fmt='dt'), inst))
                dbupdate("UPDATE instances SET lastrestart = '%s' where name = '%s'" % (str(Now(fmt='epoch')), inst))
                clog(f'{Now()} - Server has crashed', inst)
                log.warning(f'server crash notification from {inst}')
                msg = f'The **{inst.title()}** server has crashed!\n\nServer is now restarting, there may be a slight rollback'
                embed = discord.Embed(description=msg, color=FAIL_COLOR)
                await client.send_message(channel2, embed=embed)

        else:
            await client.process_commands(message)

    client.loop.create_task(chatbuffer())
    while True:
        try:
            client.loop.create_task(taskchecker())
            client.run(discordtoken)
        except:
            log.critical('Critical Error in Discord Bot Routine.')
            sleep(60)
            system('ark restart')
