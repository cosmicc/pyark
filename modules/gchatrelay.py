from time import sleep

from loguru import logger as log

import globvars
from modules.asyncdb import DB as db
from modules.servertools import asyncserverbcast, asyncserverchat, asyncserverchatto, serverexec, asynctimeit
from modules.timehelper import Now

# globalbuffer (chat TO servers)


def stopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Gchatrelay thread has ended')
            exit(0)
        sleep(1)


async def asyncgetsteamid(whoasked):
    player = await db.fetchone(f"SELECT * FROM players WHERE (playername = '{whoasked.lower()}') or (alias = '{whoasked.lower()}')")
    if player is None:
        log.critical(f'Player lookup failed! possible renamed player: {whoasked}')
        return None
    else:
        return player['steamid']


async def asyncwritechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = await db.fetchone(f"SELECT * from players WHERE playername = '{whos}'", result='count')
        if isindb:
            await db.update("""INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')""" % (inst, whos, msg.replace("'", ""), tstamp))

    elif whos == "ALERT":
        await db.update("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (inst, whos, msg, tstamp))


@log.catch
async def asyncwritechatlog(inst, whos, msg, tstamp):
    steamid = await asyncgetsteamid(whos)
    # if steamid:
        # clog = f"""{tstamp} [{whos.upper()}]{msg}\n"""
        # if not os.path.exists(f'/home/ark/shared/logs/{inst}'):
            # log.error(f'Log directory /home/ark/shared/logs/{inst} does not exist! creating')
            # os.mkdir(f'/home/ark/shared/logs/{inst}', 0o777)
            # os.chown(f'/home/ark/shared/logs/{inst}', 1001, 1005)
        # with aiofiles.open(f"/home/ark/shared/logs/{inst}/chat.log", "at") as f:
        #   await f.write(clog)
        # await f.close()


@log.catch
async def asyncgchatrelay(instances):
        if 'gchatrelay' not in globvars.taskworkers:
            globvars.taskworkers.append('gchatrelay')
            chatbuffer = await db.fetchall(f"SELECT * from globalbuffer")
            if chatbuffer:
                for chatline in chatbuffer:
                    if chatline['server'].lower() in instances:
                        if chatline['name'] == 'LOTTERY':
                            await asyncserverbcast(chatline['server'], chatline["message"])
                            await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                        elif chatline['name'] == 'ALERT':
                            await asyncserverchat(chatline['server'], chatline["message"])
                            await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                        elif not chatline['private'] and not chatline['broadcast']:
                            await asyncserverchat(chatline['server'], f'Admin: {chatline["message"]}')
                            log.log('CHAT', f'{chatline["server"]} | ADMIN | {chatline["message"]}')
                            await asyncwritechatlog(chatline['server'], 'ADMIN', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                            await asyncwritechat(chatline['server'], 'Admin', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                            await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                        elif chatline['broadcast'] and not chatline['private']:
                            await asyncserverbcast(chatline['server'], chatline["message"])
                            log.log('CHAT', f'{chatline["server"]} | BROADCAST | {chatline["message"]}')
                            await asyncwritechatlog(chatline['server'], 'BROADCAST', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                            await asyncwritechat(chatline['server'], 'Broadcast', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                            await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                        elif chatline['private'] and not chatline['broadcast']:
                            player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{chatline['name']}'")
                            if player:
                                if player['server'].lower() in instances:
                                    log.log('CHAT', f'{chatline["server"]} | Admin_to_{player["playername"].title()} | {chatline["message"]}')
                                    await asyncwritechatlog(chatline["server"], f'Admin to {player["playername"].title()}', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                                    await asyncserverchatto(chatline['server'], player['steamid'], f'AdminPrivate: {chatline["message"]}')
                                    log.log('CHAT', f'{chatline["server"]} | Admin_to_{player["playername"].title()} | {chatline["message"]}')
                            await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                        else:
                            log.error(f'gchatrelay error: {chatline}')
            globvars.taskworkers.remove('gchatrelay')
            return True
