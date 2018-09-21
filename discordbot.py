#!/usr/bin/python3

import time
import discord
import asyncio
from timehelper import elapsedTime, playedTime

client = discord.Client()

def bufferreader():
    conn3 = sqlite3.connect(sqldb)
    c3 = conn.cursor()
    c3.execute('SELECT * FROM chatbuffer')
    cbuff = c3.fetchall()
    c3.close()
    conn3.close()
    if cbuff:
        for each in cbuff:
            log.warning(each)
        conn3 = sqlite3.connect(sqldb)
        c3 = conn.cursor()
        c3.execute('DELETE FROM chatbuffer')
        conn3.commit()
        c3.close()
        conn3.close()
    time.sleep(120)


def discordbot():
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
            potime = 70
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
                msg = f'Last wild dino wipe for {instr.upper()} was {lastwipet} ago'
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
                    msg = f'Last wild dino wipe for {each[0].upper()} was {lastwipet} ago'
                    await client.send_message(message.channel, msg)
        elif message.content.startswith('!lastrestart'):
            lwt = message.content.split(' ')
            if len(lwt) > 1:
                instr = lwt[1]
                lastrestartt = elapsedTime(time.time(),float(getlastrestart(instr)))
                msg = f'Last server restart for {instr.upper()} was {lastrestartt} ago'
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
            msg = f'Commands: !who, !lasthour, !lastday, !lastnew, !linkme, !kickme, !timeleft, !lastwipe, !lastrestart, !lastseen <playername>'
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
                        msg = f'Kicking {kuser[1]} from the {kuser[3].capitalize()} server'
                        await client.send_message(message.channel, msg)
                        conn = sqlite3.connect(sqldb)
                        c = conn.cursor()
                        c.execute('INSERT INTO kicklist (instance,steamid) VALUES (?,?)', (kuser[3],kuser[0]))
                        conn.commit()
                        c.close()
                        conn.close()
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
                log.info(f'link account request on discord from {whofor}i denied, already linked')
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
                        role = discord.utils.get(user.server.roles, name="Verified Player")
                        await client.add_roles(user, role)    
                    else:
                        log.info(f'link account request on discord from {whofor} denied, code not found')
                        msg = f'That link request code was not found. You must start a link request in-game to get your code'
                        await client.send_message(message.channel, msg)
                else:
                    log.info(f'link account request on discord from {whofor} denied, no code specified')
                    msg = f'You must start a link request in-game first to get a code, then specify that code here, to link your account'
                    await client.send_message(message.channel, msg)

    chatlistener = threading.Thread(name='chat-listener', target = bufferreader)
    chatlistener.start()

    try:
        client.run('NDkwNjQ2MTI2MDI3MDc5Njgw.DoNcWg.5LU6rycTgXNnApPL_6L2e9Tr5j0')
    except:
        if c in vars():
            c.close()
        if conn in vars()
            conn.close()
        if c3 in vars():
            c3.close()
        if conn3 in vars()
            conn3.close()
        e = sys.exc_info()
        log.critical(e)
