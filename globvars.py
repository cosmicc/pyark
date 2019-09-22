from pathlib import Path
from time import time
from typing import Dict, List, Set

from modules.configreader import arkrootpath, instances, sharedpath

instpids = Dict[str, int]  # Instance pids
instpidfiles = Dict[str, int]  # Instance pid files from arkmanager

gamelogger = False  # if the gamelogger is running or not

votertable = List[str]  # populated voter table for wild wipe votes
votestarttime: float = time()
isvoting: bool = False  # is a vote taking place
lastvoter: int = 0
welcomes = Set[str]  # list of steamid of running new player welcomes
greetings = Set[str]  # list of steamid or running returning player greets

delay = Dict[str, int]  # Delay times for each task
timer = Dict[str, float]  # timers for each task

atinstances: tuple = ('@island', '@ragnarok', '@valguero', '@crystal', '@coliseum')

arkmanager_paths = List[Path]
gameini_customconfig_files = Dict[str, Path]
gusini_customconfig_files = Dict[str, Path]
server_needsrestart_file: Path = Path('/run/reboot-required')
server_uptime_file: Path = Path('/proc/uptime')
gameini_final_file: Path = arkrootpath / 'ShooterGame/Saved/Config/LinuxServer/Game.ini'
gusini_final_file: Path = arkrootpath / 'ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini'
gameini_baseconfig_file: Path = sharedpath / 'config/Game-base.ini'
gusini_baseconfig_file: Path = sharedpath / 'config/GameUserSettings-base.ini'
gusini_tempconfig_file: Path = sharedpath / 'config/GameUserSettings.tmp'
for inst in instances:
    arkmanager_paths.append(sharedpath / f'logs/arkmanager/{inst}')
    gusini_customconfig_files.update({inst: sharedpath / f'config/GameUserSettings-{inst.lower()}.ini'})
    gameini_customconfig_files.update({inst: sharedpath / f'config/Game-{inst.lower()}.ini'})
    instpidfiles.update({inst: Path(f'/home/ark/ARK/ShooterGame/Saved/.arkserver-{inst}.pid')})
    instpids.update({inst: None})
