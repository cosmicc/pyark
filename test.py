from time import sleep

from fsmonitor import FSMonitorThread


def cb(event):
        print(event.name)


m = FSMonitorThread(callback=cb)
watch = m.add_dir_watch("/home/ark/shared/config")

while True:
    sleep(1)
    print('.')
