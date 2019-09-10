import asyncio
import globvars
from loguru import logger as log
from modules.instances import asyncfinishstatus
from re import compile as rcompile


class StatusProtocol(asyncio.SubprocessProtocol):

    FD_NAMES = ['stdin', 'stdout', 'stderr']

    def __init__(self, done_future, inst):
        self.done = done_future
        self.inst = inst
        super().__init__()

    def connection_made(self, transport):
        log.trace('process started {}'.format(transport.get_pid()))
        self.transport = transport

    def pipe_data_received(self, fd, data):
        log.trace(f'read {len(data)} bytes from {self.FD_NAMES[fd]}')
        if fd == 1:
            self._parse_results(data)

    def process_exited(self):
        log.trace('process exited')
        return_code = self.transport.get_returncode()
        log.trace('return code {}'.format(return_code))
        asyncio.create_task(asyncfinishstatus(self.inst))
        self.done.set_result((return_code))

    def _parse_results(self, line):
        log.trace('parsing results')
        if not line:
            return []
        asyncio.create_task(asyncprocessstatusline(self.inst, line))


def stripansi(stripstr):
    ansi_escape = rcompile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return(ansi_escape.sub('', stripstr))


async def asyncprocessstatusline(inst, eline):
        line = eline.decode()
        status_title = stripansi(line.split(':')[0]).strip()
        if not status_title.startswith('Running command'):
            status_value = stripansi(line.split(':')[1]).strip()
            log.debug(f'processing status line: {line}')
            if status_title == 'Server running':
                if status_value == 'Yes':
                    globvars.status_counts[inst]['running'] = 0
                elif status_value == 'No':
                    globvars.status_counts[inst]['running'] = globvars.status_counts[inst]['running'] + 1

            elif status_title == 'Server listening':
                if status_value == 'Yes':
                    globvars.status_counts[inst]['listening'] = 0
                elif status_value == 'No':
                    globvars.status_counts[inst]['listening'] = globvars.status_counts[inst]['listening'] + 1

            elif status_title == 'Server online':
                if status_value == 'Yes':
                    globvars.status_counts[inst]['online'] = 0
                elif status_value == 'No':
                    globvars.status_counts[inst]['online'] = globvars.status_counts[inst]['online'] + 1

            elif status_title == 'Server PID':
                globvars.instpids[inst] = int(status_value)

            elif (status_title == 'Players'):
                players = int(status_value.split('/')[0].strip())
                globvars.instplayers[inst]['connecting'] = int(players)

            elif (status_title == 'Active Players'):
                globvars.instplayers[inst]['active'] = int(status_value)

            elif (status_title == 'Server build ID'):
                globvars.instarkbuild[inst] = int(status_value)

            elif (status_title == 'Server version'):
                globvars.instarkversion[inst] = status_value

            elif (status_title == 'ARKServers link'):
                arkserverslink = stripansi(line.split('  ')[1]).strip()
                globvars.instlinks[inst]['arkservers'] = arkserverslink

            elif (status_title == 'Steam connect link'):
                steamlink = stripansi(line.split('  ')[1]).strip()
                globvars.instlinks[inst]['steam'] = steamlink
