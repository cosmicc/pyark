#!/usr/bin/python3

import discord
import asyncio
from cmdlistener import *

client = discord.Client()

def discordbot():
    @client.event
    async def on_ready():
        log.info(f'discord logged in as {client.user.name} id {client.user.id}')

    @client.event
    async def on_message(message):
        if message.content.startswith('!who') or message.content.startswith('!whoson') or message.content.startswith('!whosonline'):
            log.info('responding to whos online request from discord')
            potime = 70
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM instances')
            srvrs = c.fetchall()
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
                        print(row[1],chktme)
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1])
                        else:
                            plist=plist + ', %s' % (row[1])
                if pcnt != 0:
                    msg = f'{each[0].upper()} has {pcnt} players online: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].upper()} has no players online.'
                    await client.send_message(message.channel, msg)

        elif message.content.startswith('!recent') or message.content.startswith('!whorecent') or message.content.startswith('!lasthour'):
            #await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            potime = 3600
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM instances')
            srvrs = c.fetchall()
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
                        print(row[1],chktme)
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1])
                        else:
                            plist=plist + ', %s' % (row[1])
                if pcnt != 0:
                    msg = f'{each[0].upper()} has had {pcnt} players in last hour: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].upper()} has had no players in last hour.'
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
                        msg = f'{seenname} was last seen {plasttime} ago on {flast[3]}'
                        await client.send_message(message.channel, msg)
                    else:
                        msg = f'Player {seenname} is online now on {flast[3]}'
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
            msg = f'Commands: !who, !recent, !today, !timeleft, !lastwipe, !lastrestart, !lastseen <playername>'
            await client.send_message(message.channel, msg)

        elif message.content.startswith('!whotoday') or message.content.startswith('!today') or message.content.startswith('!lastday'):
            #await asyncio.sleep(5)
            log.info('responding to recent players request from discord')
            potime = 86400
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM instances')
            srvrs = c.fetchall()
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
                        print(row[1],chktme)
                        pcnt += 1
                        if plist == '':
                            plist = '%s' % (row[1])
                        else:
                            plist=plist + ', %s' % (row[1])
                if pcnt != 0:
                    msg = f'{each[0].upper()} has had {pcnt} players today: {plist}'
                    await client.send_message(message.channel, msg)
                else:
                    msg = f'{each[0].upper()} has had no players today.'
                    await client.send_message(message.channel, msg)


    client.run('NDkwNjQ2MTI2MDI3MDc5Njgw.DoNcWg.5LU6rycTgXNnApPL_6L2e9Tr5j0')
