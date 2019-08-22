from modules.configreader import hstname
from loguru import logger as log

log.remove()

log.configure(extra={'hostname': hstname, 'instance': 'MAIN', })

log.level("START", no=38, color="<fg 39>", icon="¤")
log.level("JOIN", no=21, color="<fg 201>", icon="¤")
log.level("LEAVE", no=21, color="<fg 129>", icon="¤")
log.level("XFER", no=21, color="<fg 204>", icon="¤")
log.level("POINTS", no=22, color="<fg 118>", icon="¤")
log.level("LOTTO", no=23, color="<fg 70>", icon="¤")
log.level("VOTE", no=20, color="<fg 208>", icon="¤")
log.level("CMD", no=20, color="<fg 147>", icon="¤")
log.level("CRASH", no=29, color="<fg 15><bg 166>", icon="¤")
log.level("WIPE", no=20, color="<fg 86>", icon="¤")
log.level("UPDATE", no=20, color="<light-cyan>", icon="¤")
log.level("MAINT", no=20, color="<fg 121>", icon="¤")
log.level("GIT", no=30, color="<fg 229>", icon="¤")
log.level("EXIT", no=35, color="<fg 228><bg 18>", icon="¤")
log.level("KICK", no=20, color="<fg 216>", icon="¤")
log.level("EVENTS", no=20, color="<fg 138>", icon="¤")
log.level('CHAT', no=3, color="<fg 58>", icon="¤")
log.level('TRAP', no=3, color="<fg 48>", icon="¤")
log.level('DEATH', no=3, color="<fg 68>", icon="¤")
log.level('TAME', no=3, color="<fg 78>", icon="¤")
log.level('RELEASE', no=3, color="<fg 88>", icon="¤")
log.level('DECAY', no=3, color="<fg 98>", icon="¤")
log.level("ADMIN", no=3, color="<fg 15><bg 94>", icon="¤")
log.level("TEST", no=5, color="<black><bg 148>", icon="¤")

shortlogformat = '<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level><fg 248>|</fg 248><level>{extra[hostname]: >5}</level><fg 248>|</fg 248><level>{level: <7}</level><fg 248>|</fg 248> <level>{message}</level>'

simplelogformat = '{time:YYYY-MM-DD HH:mm:ss.SSS} | {extra[hostname]: <5} | {message}'

gamelogformat = '{time:YYYY-MM-DD HH:mm:ss} | {extra[instance]: <5} | {message}'

chatlogformat = '{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}'

longlogformat = '<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level><fg 248>|</fg 248><level>{extra[hostname]: >5}</level> <fg 248>|</fg 248> <level>{level: <7}</level> <fg 248>|</fg 248> <level>{message: <72}</level> <fg 243>|</fg 243> <fg 109>{name}:{function}:{line}</fg 109>'
