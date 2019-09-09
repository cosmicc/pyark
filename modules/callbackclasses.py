import asyncio
from loguru import logger as log


class DFProtocol(asyncio.SubprocessProtocol):

    FD_NAMES = ['stdin', 'stdout', 'stderr']

    def __init__(self, done_future):
        self.done = done_future
        super().__init__()

    def connection_made(self, transport):
        log.info('process started {}'.format(transport.get_pid()))
        self.transport = transport

    def pipe_data_received(self, fd, data):
        log.success(f'read {len(data)} bytes from {self.FD_NAMES[fd]}')
        if fd == 1:
            self._parse_results(data)

    def process_exited(self):
        log.info('process exited')
        return_code = self.transport.get_returncode()
        log.info('return code {}'.format(return_code))
        self.done.set_result((return_code))

    def _parse_results(self, line):
        log.info('parsing results')
        if not line:
            return []
        log.info(f'LINE: {line}')
        # return results
