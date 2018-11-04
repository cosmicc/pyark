from modules.dbhelper import dbquery, dbupdate
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


def sendservermessage(inst, whos, msg):  # old writeglobal()
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             (inst.lower(), whos, msg, Now()))


if __name__ == '__main__':
    exit()
