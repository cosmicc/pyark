from loguru import logger as log
from modules.configreader import hstname, loglevel, jsonlogfile, jsondebugfile, pointslogfile, pyarklogfile, adminlogfile, crashlogfile, errorlogfile, chatlogfile, gamelogfile

log.remove()

log.configure(extra={'hostname': hstname, 'instance': 'None'})

log.level("START", no=38, color="<fg 39>", icon="¤")
log.level("EXIT", no=35, color="<fg 228><bg 18>", icon="¤")
log.level("GIT", no=30, color="<fg 229>", icon="¤")
log.level("CRASH", no=29, color="<fg 15><bg 166>", icon="¤")

log.level("LOTTO", no=23, color="<fg 70>", icon="¤")
log.level("POINTS", no=22, color="<fg 118>", icon="¤")
log.level("JOIN", no=21, color="<fg 201>", icon="¤")
log.level("LEAVE", no=21, color="<fg 129>", icon="¤")
log.level("XFER", no=21, color="<fg 219>", icon="¤")
log.level("VOTE", no=20, color="<fg 221>", icon="¤")
log.level("CMD", no=20, color="<fg 147>", icon="¤")
log.level("WIPE", no=20, color="<fg 86>", icon="¤")
log.level("UPDATE", no=20, color="<light-cyan>", icon="¤")
log.level("MAINT", no=20, color="<fg 121>", icon="¤")
log.level("KICK", no=20, color="<fg 216>", icon="¤")
log.level("EVENTS", no=20, color="<fg 138>", icon="¤")
log.level("NEW", no=20, color="<fg 230>", icon="¤")
log.level("PLAYER", no=20, color="<fg 180>", icon="¤")
log.level("WATCH", no=20, color="<fg 180>", icon="¤")

log.level('CHAT', no=3, color="<fg 58>", icon="¤")
log.level('TRAP', no=3, color="<fg 105>", icon="¤")
log.level('DEATH', no=3, color="<fg 197>", icon="¤")
log.level('TAME', no=3, color="<fg 113>", icon="¤")
log.level('RELEASE', no=3, color="<fg 111>", icon="¤")
log.level('DECAY', no=3, color="<fg 208>", icon="¤")
log.level('DEMO', no=3, color="<fg 209>", icon="¤")
log.level('CLAIM', no=3, color="<fg 122>", icon="¤")
log.level('TRIBE', no=3, color="<fg 178>", icon="¤")
log.level("ADMIN", no=3, color="<fg 11><bg 17>", icon="¤")

shortlogformat = '<level>{time:MM-DD hh:mm:ss.SSS A}</level><fg 248>|</fg 248><level>{extra[hostname]: >5}</level><fg 248>|</fg 248><level>{level: <7}</level><fg 248>|</fg 248> <level>{message}</level>'

simplelogformat = '{time:MM-DD hh:mm:ss.SSS A} | {extra[hostname]: <5} | {message}'

gamelogformat = '<level>{message}</level>'

chatlogformat = '{time:ddd hh:mm A} | {message}'

longlogformat = '<level>{time:MM-DD hh:mm:ss.SSS A}</level><fg 248>|</fg 248><level>{extra[hostname]: >5}</level> <fg 248>|</fg 248> <level>{level: <7}</level> <fg 248>|</fg 248> <level>{message: <72}</level> <fg 243>|</fg 243> <fg 109>{name}:{function}:{line}</fg 109>'


def checkdebuglog(record):
    if record['level'] == 'DEBUG' or record['level'] == 'TRACE':
        return True
    else:
        return False


def checkgamelog(record):
    if record['level'] == 'TRAP' or record['level'] == 'ADMIN' or record['level'] == 'DEATH' or record['level'] == 'TAME' or record['level'] == 'DECAY' or record['level'] == 'DEMO' or record['level'] == 'TRIBE' or record['level'] == 'CLAIM' or record['level'] == 'RELEASE':
        return True
    else:
        return False


def checklogadmin(record):
    if record['level'] == 'ADMIN':
        return True
    else:
        return False


def checkchatlog(record):
    if record['level'] == 'CHAT':
        return True
    else:
        return False


def checklogpoints(record):
    if record['level'] == 'POINTS':
        return True
    else:
        return False


def checklogcrash(record):
    if record['level'] == 'CRASH':
        return True
    else:
        return False


def checkerrorlog(record):
    if record['level'] == 'ERROR' or record['level'] == 'CRITICAL':
        return True
    else:
        return False


# Instance Json log
log.add(sink=str(jsonlogfile), level=19, buffering=1, enqueue=True, backtrace=False, diagnose=False, serialize=True, colorize=True, format=shortlogformat)

# Instance Json debug log
if loglevel == 'DEBUG' or loglevel == 'TRACE':
    if loglevel == 'DEBUG':
        lev = 10
    else:
        lev = 5
    log.add(sink=str(jsondebugfile), level=lev, buffering=1, enqueue=True, backtrace=True, diagnose=True, serialize=True, colorize=True, format=shortlogformat, delay=False, filter=checkdebuglog)

# General combined log pyark.log
log.add(sink=str(pyarklogfile), level=20, buffering=1, enqueue=True, backtrace=False, diagnose=False, colorize=True, format=longlogformat)

# Points Logging points.log
log.add(sink=str(pointslogfile), level=22, buffering=1, enqueue=True, backtrace=False, diagnose=False, colorize=False, format=simplelogformat, delay=False, filter=checklogpoints)

# Admin Logging admin.log
log.add(sink=str(adminlogfile), level=3, buffering=1, enqueue=True, backtrace=False, diagnose=False, colorize=False, format=simplelogformat, delay=False, filter=checklogadmin)

# Crash Logging crash.log
log.add(sink=str(crashlogfile), level=29, buffering=1, enqueue=True, backtrace=False, diagnose=False, colorize=False, format=simplelogformat, delay=False, filter=checklogcrash)

# Error Logging error.log
log.add(sink=str(errorlogfile), level=40, buffering=1, enqueue=True, backtrace=True, diagnose=True, colorize=True, format=longlogformat, delay=False, filter=checkerrorlog)

# chat Logging error.log
log.add(sink=str(chatlogfile), level=3, buffering=1, enqueue=True, backtrace=False, diagnose=False, colorize=False, format=chatlogformat, delay=False, filter=checkchatlog)

# game Logging game.log
log.add(sink=str(gamelogfile), level=3, buffering=1, enqueue=True, backtrace=False, diagnose=False, serialize=False, colorize=True, format=gamelogformat, delay=False, filter=checkgamelog)
