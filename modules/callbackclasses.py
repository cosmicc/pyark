import asyncio
from loguru import logger as log
from modules.instances import asyncprocessstatusline, asyncfinishstatus


class DFProtocol(asyncio.SubprocessProtocol):

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
