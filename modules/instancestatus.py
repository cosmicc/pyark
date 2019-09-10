import asyncio
import globvars
from loguru import logger as log
from re import compile as rcompile
from modules.asyncdb import DB as db


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


async def asyncfinishstatus(inst):
    log.debug('running statusline completion task')
    if globvars.status_counts[inst]['running'] >= 3:
        isrunning = 0
        globvars.isrunning.discard(inst)
    else:
        isrunning = 1
        globvars.isrunning.add(inst)
    if globvars.status_counts[inst]['listening'] >= 3:
        globvars.islistening.discard(inst)
        islistening = 0
    else:
        islistening = 1
        globvars.islistening.add(inst)
    if globvars.status_counts[inst]['online'] >= 3:
        globvars.isonline.discard(inst)
        isonline = 0
    else:
        globvars.isonline.add(inst)
        isonline = 1
    if globvars.instplayers[inst]['active'] is not None:
        if int(globvars.instplayers[inst]['active']) > 0:
            globvars.isrunning.add(inst)
            globvars.islistening.add(inst)
            globvars.isonline.add(inst)
            isrunning = 1
            islistening = 1
            isonline = 1
        log.trace(f'pid: {globvars.instpids[inst]}, online: {isonline}, listening: {islistening}, running: {isrunning}, {inst}')
        await db.update(f"UPDATE instances SET serverpid = '{globvars.instpids[inst]}', isup = '{isonline}', islistening = '{islistening}', isrunning = '{isrunning}', arkbuild = '{globvars.instarkbuild[inst]}', arkversion = '{globvars.instarkversion[inst]}' WHERE name = '{inst}'")
        if globvars.instplayers[inst]['connecting'] is not None and globvars.instplayers[inst]['active'] is not None and globvars.instlinks[inst]['steam'] is not None and globvars.instlinks[inst]['arkservers'] is not None:
            await db.update(f"""UPDATE instances SET steamlink = '{globvars.instlinks[inst]["steam"]}', arkserverslink = '{globvars.instlinks[inst]["arkservers"]}', connectingplayers = '{globvars.instplayers[inst]['connecting']}', activeplayers = '{globvars.instplayers[inst]['active']}' WHERE name = '{inst}'""")
        return True


