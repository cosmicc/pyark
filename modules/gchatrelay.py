from time import sleep

from loguru import logger as log

from modules.cmdlistener import writechatlog
from modules.dbhelper import db_getall, dbupdate
from modules.instances import writechat
from modules.players import getplayer
from modules.servertools import serverexec, asynserverchat, asyncserverchatto, asyncserverbcast
from modules.timehelper import Now

# globalbuffer (chat TO servers)


def stopsleep(sleeptime, stop_event):
    for ntime in range(sleeptime):
        if stop_event.is_set():
            log.debug('Gchatrelay thread has ended')
            exit(0)
        sleep(1)


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
                        log.log('CHAT', f'{inst} | ADMIN | {chatline["message"]}')
                        await asyncwritechatlog(inst, 'ADMIN', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                        await asyncwritechat(inst, 'Admin', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                        await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                    elif chatline['broadcast'] and not chatline['private']:
                        await asyncserverbcast(chatline['server'], chatline["message"])
                        log.log('CHAT', f'{inst} | BROADCAST | {chatline["message"]}')
                        await asyncwritechatlog(inst, 'BROADCAST', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                        await asyncwritechat(inst, 'Broadcast', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                        await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                    elif chatline['private'] and not chatline['broadcast']:
                        player = await db.fetchone(f"SELECT * FROM players WHERE playername = '{chatline['name']}'")
                        if player:
                            if player['server'].lower() is in instances:
                                log.log('CHAT', f'{inst} | Admin_to_{cplayer["playername"].title()} | {chatline["message"]}')
                                await asyncwritechatlog(inst, f'Admin to {cplayer["playername"].title()}', chatline['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                                await asyncserverchatto(chatline['server'], player['steamid'], f'AdminPrivate: {chatline["message"]}')
                                log.log('CHAT', f'{inst} | Admin_to_{cplayer["playername"].title()} | {chatline["message"]}')
                        await db.update(f'DELETE FROM globalbuffer WHERE id = {chatline["id"]}')
                    else:
                        log.error(f'gchatrelay error: {chatline}')
        return True


@log.catch
def gchatrelay_thread(inst, dtime, stop_event):
    while not stop_event.is_set():
        cbuff = db_getall('globalbuffer', fmt='dict')
        if cbuff:
            for msg in cbuff:
                if msg['server'] == 'ALERT':
                    msg['server'] == 'ALL'

                if (msg['server'] == 'ALL' or msg['server'].lower() == inst) and not Now() - float(msg['timestamp']) > 3:
                    if msg['name'] == 'LOTTERY':
                        serverexec(['arkmanager', 'rconcmd', f'Broadcast {msg["message"]}', f'@{inst}'], nice=19, null=True)
                    elif msg['name'] == 'ALERT':
                        serverexec(['arkmanager', 'rconcmd', f'ServerChat {msg["message"]}', f'@{inst}'], nice=19, null=True)
                    elif not msg['private'] and not msg['broadcast'] and not Now() - float(msg['timestamp']) > 3:
                        serverexec(['arkmanager', 'rconcmd', f'ServerChat Admin: {msg["message"]}', f'@{inst}'], nice=19, null=True)
                        log.log('CHAT', f'{inst} | ADMIN | {msg["message"]}')
                        writechatlog(inst, 'ADMIN', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                        writechat(inst, 'Admin', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))

                    elif msg['broadcast'] and not msg['private'] and not Now() - float(msg['timestamp']) > 3:
                        serverexec(['arkmanager', 'rconcmd', f'Broadcast {msg["message"]}', f'@{inst}'], nice=19, null=True)
                        log.log('CHAT', f'{inst} | BROADCAST | {msg["message"]}')
                        writechatlog(inst, 'BROADCAST', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                        writechat(inst, 'Broadcast', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))

                    elif msg['private'] and not msg['broadcast'] and not Now() - float(msg['timestamp']) > 3:
                        cplayer = getplayer(playername=msg['name'], fmt='dict')
                        if cplayer:
                            if cplayer['server'] == inst:
                                log.log('CHAT', f'{inst} | Admin_to_{cplayer["playername"].title()} | {msg["message"]}')
                                writechatlog(inst, f'Admin to {cplayer["playername"].title()}', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                                serverexec(['arkmanager', 'rconcmd', f"""ServerChatTo "{cplayer['steamid']}" AdminPrivate: {msg['message']}""", f'@{inst}'], nice=19, null=True)
                                log.log('CHAT', f'{inst} | Admin_to_{cplayer["playername"].title()} | {msg["message"]}')

                # elif msg['server'] != inst and msg['name'] != 'ALERT' and float(msg['timestamp']) > Now() - 3:
                #    log.trace(f'Server chat: msg["server"].capitalize() - msg["name"].title() -  msg["message"]')
                #    subprocess.run('arkmanager rconcmd "ServerChat %s@%s: %s" @%s' % (msg['name'].title(), msg['server'].capitalize(), msg['message'], inst), shell=True)

                if float(msg['timestamp']) < Now() - 10:
                    log.trace('clearing globalbuffer table')
                    dbupdate("DELETE FROM globalbuffer WHERE id = '%s'" % (msg['id'],))
        stopsleep(dtime, stop_event)
    log.debug('Gchatrelay thread has ended')
    exit(0)
