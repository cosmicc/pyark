from pathlib import Path
from time import sleep

from fsmonitor import FSMonitorThread

a = Path("home/ark/shared/config/GameUserSettings-coliseum.ini")


def cb(event):
    if event.action_name == "modify":
        if event.name == a.name:
            print("YES!")
    # print(event.action_name)
    # print(event.name)


m = FSMonitorThread(callback=cb)
watch = m.add_dir_watch("/home/ark/shared/config")

while True:
    sleep(1)
    print(".")
