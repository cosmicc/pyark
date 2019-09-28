from datetime import datetime, timedelta

from modules.dbhelper import dbquery, dbupdate


def sendmessage(from_player, to_player, message):
    if to_player == "76561198388849736":
        to_player = "76561198408657294"
    dbupdate(
        "INSERT INTO messages (timestamp, from_player, to_player, message, read) VALUES (NOW(), '%s', '%s', '%s', False)"
        % (from_player, to_player, message)
    )


def getmessages(steamid, sent=False, fmt="dict"):
    if sent:
        return dbquery(
            "SELECT * FROM messages WHERE from_player = '%s'" % (steamid,), fmt=fmt
        )
    else:
        return dbquery(
            "SELECT * FROM messages WHERE to_player = '%s'" % (steamid,), fmt=fmt
        )


def lastsentdt(steamid):
    data = dbquery(
        "SELECT timestamp FROM messages WHERE from_player = '%s' ORDER BY timestamp DESC"
        % (steamid,),
        fetch="one",
    )
    if data is None:
        return False
    else:
        return data[0]


def validatelastsent(steamid):
    data = lastsentdt(steamid)
    if data:
        if lastsentdt(steamid) < datetime.now() - timedelta(seconds=120):
            return True
        else:
            return False
    else:
        return True


def validatenumsent(steamid):
    if getmessages(steamid, sent=True, fmt="count") < 5:
        return True
    else:
        return False
