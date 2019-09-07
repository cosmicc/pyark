from pathlib import Path
from time import time

from modules.configreader import arkroot, instances, sharedpath

taskworkers = []  # list of working tasks
votertable = []  # populated voter table for wild wipe votes
votestarttime = time()
isvoting = False  # is a vote taking place
welcomes = []  # list of steamid new player welcomes
greetings = []  # list of steamid returning player greets

delay = {}  # Delay times for each task
timer = {}  # timers for each task

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
