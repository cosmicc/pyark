from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.timehelper import Now
from sys import exit
import logging
import socket

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def instancelist():
    dbdata = dbquery('SELECT name FROM instances', fmt='list', single=True)
    return dbdata


def getlastwipe(inst):
    dbdata = dbquery("SELECT lastdinowipe FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    if dbdata:
        return int(dbdata)
    else:
        return None


def getlastrestart(inst):
    dbdata = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (inst.lower(),), fetch='one', single=True)
    if dbdata:
        return int(dbdata[0])
    else:
        return None


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT':
        isindb = getplayer(whos)
    elif whos == "ALERT" or isindb:
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                 (inst, whos, msg, tstamp))


def writeglobal(inst, whos, msg):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             (inst, whos, msg, Now()))


def serverchat(msg, inst='ALERT', whosent='ALERT'):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             (inst, whosent, msg, Now()))


if __name__ == '__main__':
    exit()
