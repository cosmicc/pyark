from modules.dbhelper import dbupdate, db_getall
from modules.players import getplayer
from modules.timehelper import Now
from time import sleep
from loguru import logger as log
import subprocess


@log.catch
def gchatrelay(inst):
    while True:
        try:
            cbuff = db_getall('globalbuffer', fmt='dict')
            if cbuff:
                for msg in cbuff:
                    if msg['server'] == 'ALERT':
                        msg['server'] == 'ALL'

                    if msg['server'] == 'ALL' or msg['server'].lower() == inst and float(msg['timestamp']) > Now() - 3:
                        if msg['name'] == 'ALERT' and not msg['private'] and not msg['broadcast']:
                            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (msg['message'], inst), shell=True)
                        elif msg['broadcast']:
                            subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (msg['message'], inst), shell=True)
                        elif msg['private']:
                            cplayer = getplayer(playername=msg['name'], fmt='dict')
                            if cplayer:
                                if cplayer['server'] == inst:
                                    subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" Private: %s' @%s""" % (cplayer['steamid'], msg['message'], inst), shell=True)

        





                    elif msg['server'] != inst and msg['name'] != 'ALERT' and float(msg['timestamp']) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s@%s: %s" @%s' % (msg['name'].title(), msg['server'].capitalize(), msg['message'], inst), shell=True)

                    if float(msg['timestamp']) < Now() - 10:
                        dbupdate("DELETE FROM globalbuffer WHERE id = '%s'" % (msg['id'],))
            sleep(3)
        except:
            log.exception('Critical Error in Global Chat Relayer!')
