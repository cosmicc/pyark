from modules.dbhelper import dbupdate, db_getall
from modules.players import getplayer
from modules.timehelper import Now
from cmdlistener import writechatlog
from modules.instances import writechat
from time import sleep
from loguru import logger as log
import subprocess

# globalbuffer (chat TO servers)


@log.catch
def gchatrelay(inst):
    while True:
        try:
            cbuff = db_getall('globalbuffer', fmt='dict')
            if cbuff:
                for msg in cbuff:
                    if msg['server'] == 'ALERT':
                        msg['server'] == 'ALL'

                    if (msg['server'] == 'ALL' or msg['server'].lower() == inst) and not Now() - float(msg['timestamp']) > 3:
                        if msg['name'] == 'ALERT':
                            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (f"{msg['message']}", inst), shell=True)
                        elif not msg['private'] and not msg['broadcast'] and not Now() - float(msg['timestamp']) > 3:
                            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (f"Admin: {msg['message']}", inst), shell=True)
                            log.log('CHAT', f'{inst} | ADMIN | {msg["message"]}')
                            writechatlog(inst, 'ADMIN', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                            writechat(inst, '*Admin', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))

                        elif msg['broadcast'] and not msg['private'] and not Now() - float(msg['timestamp']) > 3:
                            subprocess.run('arkmanager rconcmd "Broadcast %s" @%s' % (msg['message'], inst), shell=True)
                            log.log('CHAT', f'{inst} | BROADCAST | {msg["message"]}')
                            writechatlog(inst, 'BROADCAST', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                            writechat(inst, 'Broadcast', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))

                        elif msg['private'] and not msg['broadcast'] and not Now() - float(msg['timestamp']) > 3:
                            cplayer = getplayer(playername=msg['name'], fmt='dict')
                            if cplayer:
                                if cplayer['server'] == inst:
                                    log.log('CHAT', f'{inst} | Admin_to_{cplayer["playername"].title()} | {msg["message"]}')
                                    writechatlog(inst, f'Admin to {cplayer["playername"].title()}', msg['message'], Now(fmt='dt').strftime('%m-%d %I:%M%p'))
                                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" AdminPrivate: %s' @%s""" % (cplayer['steamid'], msg['message'], inst), shell=True)
                                    log.log('CHAT', f'{inst} | Admin_to_{cplayer["playername"].title()} | {msg["message"]}')

                    # elif msg['server'] != inst and msg['name'] != 'ALERT' and float(msg['timestamp']) > Now() - 3:
                    #    log.trace(f'Server chat: msg["server"].capitalize() - msg["name"].title() -  msg["message"]')
                    #    subprocess.run('arkmanager rconcmd "ServerChat %s@%s: %s" @%s' % (msg['name'].title(), msg['server'].capitalize(), msg['message'], inst), shell=True)

                    if float(msg['timestamp']) < Now() - 10:
                        log.trace('clearing globalbuffer table')
                        dbupdate("DELETE FROM globalbuffer WHERE id = '%s'" % (msg['id'],))
            sleep(3)
        except:
            log.exception('Critical Error in Global Chat Relayer!')
