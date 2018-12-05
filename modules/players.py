from modules.dbhelper import dbquery, dbupdate, formatdbdata
from modules.timehelper import Now, Secs


def getplayer(steamid='', discordid='', playername='', fmt='tuple'):
    if steamid != '':
        dbdata = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,), fetch='one')
    elif playername != '':
        dbdata = dbquery("SELECT * FROM players WHERE playername = '%s' or alias = '%s'" % (playername, playername), fetch='one')
    elif discordid != '':
        dbdata = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (discordid,), fetch='one')
    return formatdbdata(dbdata, 'players', qtype=fmt, single=True)


def getplayerlastseen(steamid='', playername=''):
    if playername != '':
        dbdata = dbquery("SELECT lastseen FROM players WHERE playername = '%s'" % (playername.lower(),), fetch='one', fmt='string')
    elif steamid != '':
        dbdata = dbquery("SELECT lastseen FROM players WHERE steamid = '%s'" % (steamid,), fetch='one', fmt='string')
    else:
        raise ValueError
        return None
    if dbdata:
        return int(dbdata)
    else:
        return None


def getplayerlastserver(steamid='', playername=''):
    if playername != '':
        dbdata = dbquery("SELECT server FROM players WHERE playername = '%s'" % (playername.lower(),), fetch='one', fmt='string')
    elif steamid != '':
        dbdata = dbquery("SELECT lastseen FROM players WHERE steamid = '%s'" % (steamid,), fetch='one', fmt='string')
    else:
        raise ValueError
        return None
    return dbdata


def getplayersonline(inst, fmt='list', case='normal'):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > '%s' ORDER BY playername" % (Now() - 40))
    else:
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > '%s' AND server = '%s' ORDER BY playername" % (Now() - 40, inst.lower()))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


def isplayeronline(playername='', steamid=''):
    if steamid != '':
        dbdata = dbquery("SELECT playername FROM players WHERE steamid = '%s' AND lastseen > '%s'" % (steamid, Now() - 40), fetch='one')
    elif playername != '':
        dbdata = dbquery("SELECT playername FROM players WHERE playername = '%s' AND lastseen > '%s'" % (playername, Now() - 40), fetch='one')
    if dbdata:
        return True
    else:
        return False


def kickplayer(instance, steamid):
        dbupdate("INSERT INTO kicklist (instance,steamid) VALUES ('%s','%s')" % (instance, steamid))


def isplayerold(playername='', steamid=''):
    if steamid != '':
        dbdata = dbquery("SELECT playername FROM players WHERE steamid = '%s' AND lastseen > '%s'" % (steamid, Now() - Secs['month']), fetch='one')
    elif playername != '':
        dbdata = dbquery("SELECT playername FROM players WHERE playername = '%s' AND lastseen > '%s'" % (playername, Now() - Secs['month']), fetch='one')
    if dbdata:
        return False
    else:
        return True


def getlastplayersonline(inst, fmt='list', last=5, case='normal'):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen < %s ORDER BY lastseen DESC LIMIT %s" % (Now() - Secs['1min'], last))
    else:
        dbdata = dbquery("SELECT playername FROM players WHERE server = '%s' AND lastseen < %s ORDER BY lastseen DESC LIMIT %s" % (inst.lower(), Now() - 60, last))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


def getplayerstoday(inst, fmt='list', case='normal'):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > %s ORDER BY lastseen DESC" % (Now() - Secs['1day']))
    else:
        dbdata = dbquery("SELECT playername FROM players WHERE server = '%s' AND lastseen > %s ORDER BY lastseen DESC" % (inst.lower(), Now() - Secs['1day']))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


def isplayerlinked(discordid='', steamid=''):
    islinked = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (discordid.lower(),))
    if islinked:
        return True


def isplayerbanned(steamid='', playername=''):
    if steamid == '':
        isbanned = dbquery("SELECT * FROM players WHERE banned != '' AND playername = '%s'" % (playername.lower(),), fetch='one')
    else:
        isbanned = dbquery("SELECT * FROM players WHERE banned != '' AND steamid = '%s'" % (steamid,), fetch='one')
    if isbanned:
        return True
    else:
        return False


def banunbanplayer(steamid, ban=False):
    if ban:
        try:
            dbupdate("UPDATE players SET banned = True WHERE steamid = '%s'" % (steamid,))
            dbupdate("DELETE FROM messages WHERE from_player = '%s' or to_player = '%s'" % (steamid, steamid))
            dbupdate("UPDATE web_users SET active = False WHERE steamid = '%s'" % (steamid,))
        except:
            return False
        return True
    else:
        try:
            dbupdate("UPDATE players SET banned = NULL WHERE steamid = '%s'" % (steamid,))
            dbupdate("UPDATE web_users SET active = True WHERE steamid = '%s'" % (steamid,))
        except:
            return False
        return True


def getnewestplayers(inst, fmt='list', case='normal', last=5):
    if inst == 'all':
        dbdata = dbquery("SELECT playername from players ORDER BY firstseen DESC LIMIT %s" % (last,))
    else:
        dbdata = dbquery("SELECT playername from players WHERE homeserver = '%s' ORDER BY firstseen DESC LIMIT %s" % (inst, last))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


def gettopplayedplayers(inst, fmt='list', case='normal', last=5):
    if inst == 'all':
        dbdata = dbquery("SELECT playername from players ORDER BY playedtime DESC LIMIT %s" % (last,))
    else:
        dbdata = dbquery("SELECT playername from players WHERE homeserver = '%s' ORDER BY playedtime DESC LIMIT %s" % (inst, last))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


