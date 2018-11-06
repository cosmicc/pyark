from modules.dbhelper import dbupdate
from modules.players import getplayer
from modules.timehelper import Now
from time import sleep
import logging
import socket
import subprocess

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def gchatrelay(inst):
    while True:
        try:
            cbuff = db_getall('globalbuffer', fmt='dict')
            if cbuff:
                for each in cbuff:
                    if each['server'] == 'ALERT' and each['name'] == 'ALERT' and each['private'] is False and float(each['timestamp']) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (each['message'], inst), shell=True)
                    elif each['server'] == inst and each['name'] == 'ALERT' and each['private'] is False and float(each['timestamp']) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s" @%s' % (each['message'], inst), shell=True)
                    elif each['server'] != inst and each['name'] != 'ALERT' and each['private'] is False and float(each['timestamp']) > Now() - 3:
                        subprocess.run('arkmanager rconcmd "ServerChat %s@%s: %s" @%s'
                                       % (each['name'].title(), each['server'].capitalize(), each['message'], inst), shell=True)
                    elif each['private'] is True and float(each['timestamp']) > Now() - 3:
                        cplayer = getplayer(playername=each['name'], fmt='dict'):
                        if cplayer:
                            if cplayer['server'] == inst:
                                subprocess.run("""arkmanager rconcmd 'ServerChatTo "%s" %s' @%s""" % (cplayer['steamid'], each['message'], inst), shell=True)
                    if float(each['timestamp']) < Now() - 10:
                        dbupdate("DELETE FROM globalbuffer WHERE id = '%s'" % (each['id'],))
            sleep(3)
        except:
            log.critical('Critical Error in Global Chat Relayer!', exc_info=True)
