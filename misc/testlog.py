from modules.logwatch import LogWatcher
import os


def callback(filename, lines):
    for line in lines:
        print(line)


watcher = LogWatcher(
    os.path.dirname("/home/ark/shared/logs/pyark/json"),
    callback,
    ["log"],
    persistent_checkpoint=False,
)


watcher.loop()
