from pathlib import Path
from time import time

from modules.configreader import arkroot, instances, sharedpath

taskworkers = set([])  # list of working tasks
votertable = []  # populated voter table for wild wipe votes
votestarttime = time()
isvoting = False  # is a vote taking place
lastvoter = 0
welcomes = set([])  # list of steamid of running new player welcomes
greetings = set([])  # list of steamid or running returning player greets

delay = {}  # Delay times for each task
timer = {}  # timers for each task

isrunning = set([])  # Instances that ar running on this server
islistening = set([])
isonline = set([])  # Instances that are online on this server

arkmanager_paths = []
gameini_customconfig_files = {}
gusini_customconfig_files = {}
gameini_final_file = Path(f'{arkroot}/ShooterGame/Saved/Config/LinuxServer/Game.ini')
gusini_final_file = Path(f'{arkroot}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini')
gameini_baseconfig_file = Path(f'{sharedpath}/config/Game-base.ini')
gusini_baseconfig_file = Path(f'{sharedpath}/config/GameUserSettings-base.ini')
gusini_tempconfig_file = Path(f'{sharedpath}/config/GameUserSettings.tmp')
for inst in instances:
    arkmanager_paths.append(Path(f'/home/ark/shared/logs/arkmanager/{inst}'))
    gusini_customconfig_files.update({inst: Path(f'{sharedpath}/config/GameUserSettings-{inst.lower()}.ini')})
    gameini_customconfig_files.update({inst: Path(f'{sharedpath}/config/Game-{inst.lower()}.ini')})
