from pathlib import Path
from time import time

from modules.configreader import arkrootpath, instances, sharedpath

instpids = {}  # Instance pids
instpidfiles = {}  # Instance pid files from arkmanager

gamelog = False  # if the gamelogger is running or not

taskworkers = set([])  # list of working tasks
votertable = []  # populated voter table for wild wipe votes
votestarttime = time()
isvoting = False  # is a vote taking place
lastvoter = 0
welcomes = set([])  # list of steamid of running new player welcomes
greetings = set([])  # list of steamid or running returning player greets

delay = {}  # Delay times for each task
timer = {}  # timers for each task

atinstances = ('@island', '@ragnarok', '@valguero', '@crystal', '@coliseum')

arkmanager_paths = []
gameini_customconfig_files = {}
gusini_customconfig_files = {}
gameini_final_file = arkrootpath / '/ShooterGame/Saved/Config/LinuxServer/Game.ini'
gusini_final_file = arkrootpath / '/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini'
gameini_baseconfig_file = sharedpath / '/config/Game-base.ini'
gusini_baseconfig_file = sharedpath / '/config/GameUserSettings-base.ini'
gusini_tempconfig_file = sharedpath / '/config/GameUserSettings.tmp'
for inst in instances:
    arkmanager_paths.append(sharedpath / f'/logs/arkmanager/{inst}')
    gusini_customconfig_files.update({inst: sharedpath / '/config/GameUserSettings-{inst.lower()}.ini'})
    gameini_customconfig_files.update({inst: sharedpath / '/config/Game-{inst.lower()}.ini'})
    instpidfiles.update({inst: Path(f'/home/ark/ARK/ShooterGame/Saved/.arkserver-{inst}.pid')})
    instpids.update({inst: None})
