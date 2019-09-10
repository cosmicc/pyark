import asyncio
from re import compile as rcompile
from functools import partial
from loguru import logger as log

import globvars
from modules.asyncdb import DB as db


class SubProtocol(asyncio.SubprocessProtocol):

    FD_NAMES = ['stdin', 'stdout', 'stderr']

    def __init__(self, done_future, inst, parsetask=False, finishtask=False):
        self.done = done_future
        self.inst = inst
        self.finishtask = finishtask
        super().__init__()

    def connection_made(self, transport):
        log.trace('process started {}'.format(transport.get_pid()))
        self.transport = transport

    def pipe_data_received(self, fd, data):
        log.trace(f'read {len(data)} bytes from {self.FD_NAMES[fd]}')
        if fd == 1:
            self._parse_results(data)

    def process_exited(self):
        return_code = self.transport.get_returncode()
        log.trace('return code {}'.format(return_code))

        if self.finishtask:
            asyncio.create_task(self.finishtask(self.inst))
        self.done.set_result((return_code))

    def _parse_results(self, line):
        if not line:
            return []
        asyncio.create_task(self.pasrsetask(self.inst, line))


def stripansi(stripstr):
    ansi_escape = rcompile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return(ansi_escape.sub('', stripstr))




