from pathlib import Path
from time import time

from modules.configreader import arkroot, instances, sharedpath

instpids = {}  # Instance pids
instpidfiles = {}  # Instance pid files from arkmanager

instplayers = {}  # Dict of online players (active, connecting)
instarkbuild = {}  # instance ark uild numbers
instarkversion = {}  # instance ark version numbers
instlinks = {}  # steam and arkserver links

taskworkers = set([])  # list of working tasks
votertable = []  # populated voter table for wild wipe votes
votestarttime = time()
isvoting = False  # is a vote taking place
lastvoter = 0
welcomes = set([])  # list of steamid of running new player welcomes
greetings = set([])  # list of steamid or running returning player greets

delay = {}  # Delay times for each task
timer = {}  # timers for each task

isrunning = set([])  # Instances that are running on this server
islistening = set([])  # Instances that are listening on this server
isonline = set([])  # Instances that are online on this server

status_counts = {}  # Counts for running checks (to avoid false positives)

sharedpath = Path(sharedpath)
arkrootpath = Path(arkroot)

serverpre = ['@all']
arkmanager_paths = []
gameini_customconfig_files = {}
gusini_customconfig_files = {}
gameini_final_file = Path(f'{arkroot}/ShooterGame/Saved/Config/LinuxServer/Game.ini')
gusini_final_file = Path(f'{arkroot}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini')
gameini_baseconfig_file = Path(f'{str(sharedpath)}/config/Game-base.ini')
gusini_baseconfig_file = Path(f'{str(sharedpath)}/config/GameUserSettings-base.ini')
gusini_tempconfig_file = Path(f'{str(sharedpath)}/config/GameUserSettings.tmp')
for inst in instances:
    arkmanager_paths.append(Path(f'{str(sharedpath)}/logs/arkmanager/{inst}'))
    gusini_customconfig_files.update({inst: Path(f'{str(sharedpath)}/config/GameUserSettings-{inst.lower()}.ini')})
    gameini_customconfig_files.update({inst: Path(f'{str(sharedpath)}/config/Game-{inst.lower()}.ini')})
    status_counts.update({inst: {'running': 0, 'listening': 0, 'online': 0}})
    instpidfiles.update({inst: Path(f'/home/ark/ARK/ShooterGame/Saved/.arkserver-{inst}.pid')})
    instpids.update({inst: None})
    instplayers.update({inst: {'active': None, 'connecting': None}})
    instarkbuild.update({inst: None})
    instarkversion.update({inst: None})
    instlinks.update({inst: {'steam': None, 'arkservers': None}})
    serverpre.append(f'@{inst}')

atinstances = tuple(serverpre)
