from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.timehelper import Now
from sys import exit
from loguru import logger as log
import subprocess
from re import compile as rcompile


def stripansi(stripstr):
    ansi_escape = rcompile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return(ansi_escape.sub('', stripstr))


def processinststatus(inst):
    rawrun = subprocess.run('arkmanager status @%s' % (inst), stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, shell=True)
    rawrun2 = rawrun.stdout.decode('utf-8').split('\n')
    log.log('TEST', rawrun2)
    serverrunning = None
    serveronline = None
    players = None
    serverbuild = None
    activeplayers = None
    steamlink = None
    arkserverslink = None
    serverversion = None
    serverpid = 0
    for ea in rawrun2:
        sttitle = stripansi(ea.split(':')[0]).strip()
        if (sttitle == 'Server running'):
            if (stripansi(ea.split(':')[1]).strip() == 'Yes'):
                serverrunning = True
            elif (stripansi(ea.split(':')[1]).strip() == 'No'):
                serverrunning = False
                serveronline = False
                serverlistening = False
        if (sttitle == 'Server PID'):
            serverpid = stripansi(ea.split(':')[1]).strip()
        if (sttitle == 'Server listening'):
            if (stripansi(ea.split(':')[1]).strip() == 'Yes'):
                serverlistening = True
            elif (stripansi(ea.split(':')[1]).strip() == 'No'):
                serveronline = False
        if (sttitle == 'Server online'):
            if (stripansi(ea.split(':')[1]).strip() == 'Yes'):
                serveronline = True
            elif (stripansi(ea.split(':')[1]).strip() == 'No'):
                serveronline = False
        if (sttitle == 'Players'):
            players = int(stripansi(ea.split(':')[1]).strip().split('/')[0].strip())
        if (sttitle == 'Active Players'):
            activeplayers = int(stripansi(ea.split(':')[1]).strip())
        if (sttitle == 'Server build ID'):
            serverbuild = stripansi(ea.split(':')[1]).strip()
        if (sttitle == 'Server version'):
            serverversion = stripansi(ea.split(':')[1]).strip()
        if (sttitle == 'ARKServers link'):
            arkserverslink = stripansi(ea.split('  ')[1]).strip()
        if (sttitle == 'Steam connect link'):
            steamlink = stripansi(ea.split('  ')[1]).strip()
        try:
            dbupdate("UPDATE instances SET serverpid = %s, sup = '%s', islistening = '%s', isrunning = '%s' WHERE name = '%s'" % (int(serverpid), serverrunning, serverlistening, serveronline, inst))
        except:
            log.exception('Error writing up stats to database')
        if players is not None and activeplayers is not None and serverbuild is not None and serverversion is not None and steamlink is not None and arkserverslink is not None:
            try:
                dbupdate("UPDATE instances SET arkbuild = '%s', arkversion = '%s', steamlink = '%s', arkserverslink = '%s', connectingplayers = '%s', activeplayers = '%s' WHERE name = '%s'" % (int(serverbuild), serverversion, steamlink, arkserverslink, int(players), int(activeplayers), inst))
            except:
                log.exception('Error writing extra stats to database')
    return serverrunning, serveronline

def enableinstance(inst):
    dbupdate("UPDATE instances SET enabled = True WHERE name = '%s'" % (inst,))


def disableinstance(inst):
    dbupdate("UPDATE instances SET enabled = False WHERE name = '%s'" % (inst,))


def iscurrentconfig(inst):
    gcfg = dbquery("SELECT pendingcfg FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    dbdata = dbquery("SELECT cfgver FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == gcfg[0]:
        return True
    else:
        return False


def isinrestart(inst):
    dbdata = dbquery("SELECT needsrestart FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == 'True':
        return True
    else:
        return False


def isinstancerunning(inst):
    dbdata = dbquery("SELECT isrunning FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == 1:
        return True
    else:
        return False


def isinstanceup(inst):
    dbdata = dbquery("SELECT isup FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == 1:
        return True
    else:
        return False


def getlastcrash(inst):
    dbdata = dbquery("SELECT lastcrash FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] is not None:
        return dbdata[0]
    else:
        return 'Never'


def instancelist():
    dbdata = dbquery('SELECT name FROM instances ORDER BY name', fmt='list', single=True)
    return dbdata


def homeablelist():
    dbdata = dbquery('SELECT name FROM instances WHERE homeable = true', fmt='list', single=True)
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


def getlastrestartreason(inst):
    dbdata = dbquery("SELECT restartreason FROM instances WHERE name = '%s'" % (inst.lower(),), fetch='one', single=True)
    if dbdata:
        return dbdata[0]
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


def serverchat(msg, inst='ALERT', whosent='ALERT', private=False, broadcast=False):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp,private,broadcast) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" %
             (inst, whosent, msg, Now(), private, broadcast))


def restartinstance(server, cancel=False):
    if not cancel:
        dbupdate("UPDATE instances SET needsrestart = 'True', restartreason = 'admin restart' WHERE name = '%s'" % (server, ))
    else:
        dbupdate("UPDATE instances SET needsrestart = 'False' WHERE name = '%s'" % (server, ))


def getlog(inst, whichlog, lines=20):
    if whichlog == 'chat':
        clogfile = f'/home/ark/shared/logs/{inst}/chatlog/chat.log'
    elif whichlog == 'game':
        clogfile = f'/home/ark/shared/logs/{inst}/gamelog/game.log'
    num_lines = sum(1 for line in open(clogfile))
    cloglist = []
    with open(clogfile, 'r') as filehandle:
        cline = 1
        for line in filehandle:
            if cline > num_lines - lines:
                alist = {}
                alist['dtime'] = line.split(' [')[0]
                alist['pname'] = line[line.find("[") + 1:line.find("]")]
                alist['msg'] = line.split(']: ')[1].strip('\n')
                cloglist.append(alist)
            cline += 1
    return cloglist


if __name__ == '__main__':
    exit()
