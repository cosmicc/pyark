from loguru import logger as log

from modules.asyncdb import DB as db
from modules.servertools import asyncserverbcast, asyncserverchat, asyncserverchatto
from modules.timehelper import Now

# globalbuffer (chat TO servers)


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
    pass
    # steamid = await asyncgetsteamid(whos)
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
                    log.log('CHAT', f'{chatline["server"].upper():>8}| ADMIN: {chatline["message"]}')
                    await asyncwritechatlog(chatline['server'], 'ADMIN', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                    await asyncwritechat(chatline['server'], 'Admin', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                    await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                elif chatline['broadcast'] and not chatline['private']:
                    await asyncserverbcast(chatline['server'], chatline["message"])
                    log.log('CHAT', f'{chatline["server"].upper():>8}| BROADCAST: {chatline["message"]}')
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
    return True
