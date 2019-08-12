import sys
import select
import tty
import termios
from time import sleep

class NonBlockingConsole(object):

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_data(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return False


with NonBlockingConsole() as nbc:
    i = 0
    while True:
        print(i)
        sleep(.01)
        i += 1
        if nbc.get_data() == '\x1b':  # x1b is ESC
            break
