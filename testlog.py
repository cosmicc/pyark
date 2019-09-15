from modules.logwatch import LogWatcher


def callback(filename, lines):
    for line in lines:
        print(line)


watcher = LogWatcher("/home/ark/shared/logs/pyark/json", callback, tail_lines=5)
watcher.loop()
