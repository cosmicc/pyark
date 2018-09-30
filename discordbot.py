#!/usr/bin/python3

import time, logging, threading, sqlite3, subprocess, socket
import discord
import asyncio
from timehelper import *
from auctionhelper import *
from configreader import *

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)

client = discord.Client()

channel = discord.Object(id=config.get('general','discordchatchan'))
channel2 = discord.Object(id=config.get('general','discordgenchan'))

def getlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastdinowipe FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def getlastrestart(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastrestart FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def writechat(inst,whos,msg,tstamp):
    isindb = False
    if whos != 'ALERT':
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * from players WHERE playername = ?', (whos,))
        isindb = c.fetchone()
        c.close()
        conn.close()
    elif whos == "ALERT" or isindb:
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('INSERT INTO chatbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,tstamp))
        conn.commit()
        c.close()
        conn.close()

def writeglobal(inst,whos,msg):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)', (inst,whos,msg,time.time()))
    conn.commit()
    c.close()
    conn.close()

def islinkeduser(duser):
    conn3 = sqlite3.connect(sqldb)
    c3 = conn3.cursor()
    c3.execute('SELECT * FROM players WHERE discordid = ?', (duser.lower(),))
    islinked = c3.fetchall()
    c3.close()
    conn3.close()
    if islinked:
        return True
    else:
        return False

def setprimordialbit(steamid,pbit):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('UPDATE players SET primordialbit = ? WHERE steamid = ?', (pbit,steamid))
    conn.commit()
    c.close()
    conn.close()

def discordbot():
    async def chatbuffer():
        await client.wait_until_ready()
        while not client.is_closed:
            try:
                conn3 = sqlite3.connect(sqldb)
                c3 = conn3.cursor()
                c3.execute('SELECT * FROM chatbuffer')
                cbuff = c3.fetchall()
                c3.close()
                conn3.close()
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
                    conn3 = sqlite3.connect(sqldb)
                    c3 = conn3.cursor()
                    c3.execute('DELETE FROM chatbuffer')
                    conn3.commit()
                    c3.close()
                    conn3.close()
                conn3 = sqlite3.connect(sqldb)
                c3 = conn3.cursor()
                now = float(time.time())
                c3.execute('SELECT * FROM players WHERE lastseen < ? AND lastseen > ?',(now-40,now-42))
                cbuffr = c3.fetchall()
                c3.close()
                conn3.close()
                for reach in cbuffr:
                    log.info(f'{reach[1]} has left the server {reach[0]}')
                    writechat(reach[3],'ALERT',f'>>> {reach[1].capitalize()} has left the server',wcstamp())
            except:
                log.critical('Critical Error in Chat Buffer discord writer!', exc_info=True)
                try:
                    if c in vars():
                        c.close()
                except:
                    pass
                try:
                    if conn in vars():
                        conn.close()
                except:
                    pass
                try:
                    if c3 in vars():
                        c3.close()
                except:
                    pass
                try:
                    if conn3 in vars():
                        conn3.close()
                except:
                    pass
            await asyncio.sleep(5)

    def savediscordtodb(author):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT * FROM discordnames WHERE discordname = ?', (str(author),))
        didexists = c.fetchone()
        c.close()
        conn.close()
        if not didexists:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('INSERT INTO discordnames (discordname) VALUES (?)', (str(author),))
            conn.commit()
            c.close()
            conn.close()

    @client.event
    async def on_ready():
        log.info(f'discord logged in as {client.user.name} id {client.user.id}')

    @client.event
    async def on_message(message):
        savediscordtodb(message.author)
        if message.content.startswith('!who') or message.content.startswith('!whoson') or message.content.startswith('!whosonline'):
            log.info('responding to whos online request from discord')
            potime = 40
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM instances')
            srvrs = c.fetchall()
            c.close()
            conn.close()
            for each in srvrs:
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM players WHERE server = ?', [each[0]])
                flast = c.fetchall()
                c.close()
                conn.close()
                pcnt = 0
                plist = ''
                for row in flast:
                    chktme = time.time()-float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].capitalize())
                        else:
                            plist=plist + ', %s' % (row[1].capitalize())
                if pcnt != 0:
                    msg = f'{each[0].capitalize()} has {pcnt} players online: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].capitalize()} has no players online.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!recent') or message.content.startswith('!whorecent') or message.content.startswith('!lasthour'):
            #await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            potime = 3600
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM instances')
            srvrs = c.fetchall()
            c.close()
            conn.close()
            for each in srvrs:
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM players WHERE server = ?', [each[0]])
                flast = c.fetchall()
                c.close()
                conn.close()
                pcnt = 0
                plist = ''
                for row in flast:
                    chktme = time.time()-float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].capitalize())
                        else:
                            plist=plist + ', %s' % (row[1].capitalize())
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
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM players WHERE playername = ?', [seenname])
                flast = c.fetchone()
                c.close()
                conn.close()
                if not flast:
                    msg = f'No player was found with name {seenname}'
                    await client.send_message(message.channel, msg)
                else:
                    plasttime = elapsedTime(time.time(),float(flast[2]))
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
                lastwipet = elapsedTime(time.time(),float(getlastwipe(instr)))
                msg = f'Last wild dino wipe for {instr.capitalize()} was {lastwipet} ago'
                await client.send_message(message.channel, msg)
            else:
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM instances')
                srvrs = c.fetchall()
                c.close()
                conn.close()
                for each in srvrs:
                    lastwipet = elapsedTime(time.time(),float(getlastwipe(each[0])))
                    msg = f'Last wild dino wipe for {each[0].capitalize()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)
        elif message.content.startswith('!lastrestart'):
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1]
                lastrestartt = elapsedTime(time.time(),float(getlastrestart(instr)))
                msg = f'Last server restart for {instr.capitalize()} was {lastrestartt} ago'
                await client.send_message(message.channel, msg)
            else:
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM instances')
                srvrs = c.fetchall()
                c.close()
                conn.close()
                for each in srvrs:
                    lastwipet = elapsedTime(time.time(),float(getlastrestart(each[0])))
                    msg = f'Last server restart for {each[0].upper()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!help'):
            msg = f'Commands: !mods, !who, !lasthour, !lastday, !lastnew, !linkme, !kickme, !myinfo, !timeleft, !lastwipe, !lastrestart, !lastseen <playername>, !primordial'
            await client.send_message(message.channel, msg)
        elif message.content.startswith('!vote') or message.content.startswith('!startvote'):
            msg = f'Voting is only allowed in-game'
            await client.send_message(message.channel, msg)


        elif message.content.startswith('!whotoday') or message.content.startswith('!today') or message.content.startswith('!lastday'):
            #await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            potime = 86400
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM instances')
            srvrs = c.fetchall()
            c.close()
            conn.close()
            for each in srvrs:
                conn = sqlite3.connect(sqldb)
                c = conn.cursor()
                c.execute('SELECT * FROM players WHERE server = ?', [each[0]])
                flast = c.fetchall()
                c.close()
                conn.close()
                pcnt = 0
                plist = ''
                for row in flast:
                    chktme = time.time()-float(row[2])
                    if chktme < potime:
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1].capitalize())
                        else:
                            plist=plist + ', %s' % (row[1].capitalize())
                if pcnt != 0:
                    msg = f'{each[0].capitalize()} has had {pcnt} players today: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].capitalize()} has had no players today.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!kickme'):
            whofor = str(message.author).lower()
            log.info(f'kickme request from {whofor} on discord')
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE discordid = ?', (whofor,))
            kuser = c.fetchone()
            c.close()
            conn.close()
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'kickme request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not connected to a player yet.'
                    await client.send_message(message.channel, msg)
                else:
                    if time.time()-float(kuser[2]) > 300:
                        log.info(f'kickme request from {whofor} denied, not connected to a server')
                        msg = f'You are not connected to any servers'
                        await client.send_message(message.channel, msg)
                    else:
                        log.info(f'kickme request from {whofor} passed, kicking player on {kuser[3]}')
                        msg = f'Kicking {kuser[1].capitalize()} from the {kuser[3].capitalize()} server'
                        await client.send_message(message.channel, msg)
                        conn = sqlite3.connect(sqldb)
                        c = conn.cursor()
                        c.execute('INSERT INTO kicklist (instance,steamid) VALUES (?,?)', (kuser[3],kuser[0]))
                        conn.commit()
                        c.close()
                        conn.close()
        elif message.content.startswith('!home') or message.content.startswith('!myhome'):
            whofor = str(message.author).lower()
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE discordid = ?', (whofor,))
            kuser = c.fetchone()
            c.close()
            conn.close()
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'home server request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not connected to a player yet.'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'meh'
                    await client.send_message(message.channel, msg)    

        elif message.content.startswith('!myinfo') or message.content.startswith('!points'):
            whofor = str(message.author).lower()
            log.info(f'myinfo request from {whofor} on discord')
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE discordid = ?', (whofor,))
            kuser = c.fetchone()
            c.close()
            conn.close()
            if kuser:
                if kuser[8] != whofor:
                    log.info(f'myinfo request from {whofor} denied, no account linked')
                    msg = f'Your discord account is not connected to a player yet.'
                    await client.send_message(message.channel, msg)
                else:
                    log.info(f'myinfo request from {whofor} passed, showing info for player {kuser[1]}')
                    pauctions = fetchauctiondata(kuser[0])
                    au1, au2, au3 = getauctionstats(pauctions)
                    writeauctionstats(kuser[0],au1,au2,au3)
                    ptime = playedTime(float(kuser[4].replace(',','')))
                    ptr = elapsedTime(float(time.time()),float(kuser[2]))
                    msg = f'Your current ARc reward points: {kuser[5]}.'
                    await client.send_message(message.channel, msg)
                    msg = f'Last played on {kuser[3].capitalize()} {ptr} ago.'
                    await client.send_message(message.channel, msg)
                    msg = f'Your home server is: {kuser[15].capitalize()}.'
                    await client.send_message(message.channel, msg)
                    msg = f'Your total play time is {ptime}.'
                    await client.send_message(message.channel, msg)
                    msg = f'You have {au1} current auctions: {au2} Items - {au3} Dinos'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!newest') or message.content.startswith('!lastnew'):
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT firstseen FROM players')
            lastseens = c.fetchall()
            c.execute('SELECT * from players WHERE firstseen = ?', (max(lastseens,)))
            lsplayer = c.fetchone()
            c.close()
            conn.close()
            log.info(f'responding to lastnew request on discord')
            lspago = elapsedTime(time.time(),float(lsplayer[6]))
            msg = f'Newest cluster player is {lsplayer[1].capitalize()} online {lspago} ago on {lsplayer[3]}'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!mods'):
            whofor = str(message.author).lower()
            msg = f'https://steamcommunity.com/sharedfiles/filedetails/?id=1475281369'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!lotto'):
            whofor = str(message.author).lower()
            newname = message.content.split(' ')
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM lotteryinfo WHERE winner = "Incomplete"')
            linfo = c.fetchall()
            c.close()
            conn.close()
            if len(newname) > 1:
                if newname[1] == 'enter' or newname[1] == 'join':
                    msg = 'You must be in game to enter into a lottery'
            if linfo:
                if linfo[1] == 'points':
                    msg = f'Current lottery is up to {linfo[2]} ARc reward points.'
                else:
                    msg = f'Current lottery is for a {linfo[2]}.'
                await client.send_message(message.channel, msg)
                msg = f'{linfo[6]} players have entered into this lottery so far.'
                await client.send_message(message.channel, msg)
                ltime = estshift(datetime.fromtimestamp(float(linfo[3])+(3600*int(linfo[5])))).strftime('%a, %b %d %I:%M%p')
                msg = f'Lottery ends {ltime} EST in {elapsedTime(float(linfo[3])+(3600*int(linfo[5])),time.time())}'
                await client.send_message(message.channel, msg)
     
            else:
                msg = 'There are no lotterys currently underway.'
                await client.send_message(message.channel, msg)

        elif message.content.startswith('!primordial'):
            whofor = str(message.author).lower()
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * from players WHERE discordid = ?', (whofor,))
            pplayer = c.fetchone()
            c.close()
            conn.close()
            if not pplayer:
                msg = f'Your discord account needs to be linked to you game account first. !link in game'
                await client.send_message(message.channel, msg)
            else:
                if int(pplayer[14]) == 1:
                    setprimordialbit(pplayer[0],0)
                    msg = f'Your primordial server restart warning is now OFF'
                    await client.send_message(message.channel, msg)
                else:
                    setprimordialbit(pplayer[0],1)
                    msg = f'Your primordial server restart warning is now ON'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!link') or message.content.startswith('!linkme'):
            whofor = str(message.author).lower()
            user = message.author
            log.info(f'responding to link account request on discord from {whofor}')
            sw = message.content.split(' ')
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE discordid == ?', (whofor,))
            dplayer = c.fetchone()
            c.close()
            conn.close()
            if dplayer:
                log.info(f'link account request on discord from {whofor} denied, already linked')
                msg = f'Your discord account is already linked to your game account'
                await client.send_message(message.channel, msg)
            else:
                if len(sw) > 1:
                    rcode = sw[1]
                    conn = sqlite3.connect(sqldb)
                    c = conn.cursor()
                    c.execute('SELECT * FROM linkrequests WHERE reqcode == ?', (rcode,))
                    reqs = c.fetchone()
                    c.close()
                    conn.close()
                    if reqs:
                        log.info(f'link account request on discord from {whofor} accepted. {reqs[1]} {whofor} {reqs[0]}')
                        conn = sqlite3.connect(sqldb)
                        c = conn.cursor()
                        c.execute('UPDATE players SET discordid = ? WHERE steamid = ?', (whofor,reqs[0]))
                        c.execute('DELETE FROM linkrequests WHERE reqcode = ?', (rcode,))
                        conn.commit()
                        c.close()
                        conn.close()
                        msg = f'Your discord account [{whofor}] is now linked to your player {reqs[1]}'
                        await client.send_message(message.channel, msg)
                        role = discord.utils.get(user.server.roles, name="Linked Player")
                        await client.add_roles(user, role)    
                    else:
                        log.info(f'link account request on discord from {whofor} denied, code not found')
                        msg = f'That link request code was not found. You must start a link request in-game to get your code'
                        await client.send_message(message.channel, msg)
                else:
                    log.info(f'link account request on discord from {whofor} denied, no code specified')
                    msg = f'You must start a link request in-game first to get a code, then specify that code here, to link your account'
                    await client.send_message(message.channel, msg)
        elif str(message.channel) == 'server-chat':
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT playername FROM players WHERE discordid = ?', (str(message.author).lower(),))
            whos = c.fetchone()
            c.close()
            conn.close()
            if whos:
                writeglobal('discord',whos[0],str(message.content))


    client.loop.create_task(chatbuffer())
    try:
        while True:
            client.run(config.get('general','discordtoken'))
    except:
        log.critical('Critical Error in Discord Bot Routine!', exc_info=True)
        try:
            if c in vars():
                c.close()
        except:
            pass
        try:
            if conn in vars():
                conn.close()
        except:
            pass
        try:
            if c3 in vars():
                c3.close()
        except:
            pass
        try:
            if conn3 in vars():
                conn3.close()
        except:
            pass


