import sys
import pyinotify
from time import sleep
from loguru import logger as log
from pathlib import Path

testfile = Path('/home/ark/shared/config/Game-coliseum.ini')


class EventProcessor(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        print(event.pathname)
        if event.pathname == str(testfile):
            print('yes!')


file_watch_manager = pyinotify.WatchManager()
file_event_notifier = pyinotify.ThreadedNotifier(file_watch_manager, EventProcessor())
file_watch_manager.add_watch('/home/ark/shared/config', pyinotify.IN_CLOSE_WRITE)
file_event_notifier.start()

while True:
    print('.')
    sleep(1)
