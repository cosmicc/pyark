import asyncio

class DFProtocol(asyncio.SubprocessProtocol):

    FD_NAMES = ['stdin', 'stdout', 'stderr']

    def __init__(self, done_future):
        self.done = done_future
        self.buffer = bytearray()
        super().__init__()

    def connection_made(self, transport):
        print('process started {}'.format(transport.get_pid()))
        self.transport = transport

    def pipe_data_received(self, fd, data):
        print('read {} bytes from {}'.format(len(data),
                                             self.FD_NAMES[fd]))
        if fd == 1:
            self.buffer.extend(data)

    def process_exited(self):
        print('process exited')
        return_code = self.transport.get_returncode()
        print('return code {}'.format(return_code))
        if not return_code:
            cmd_output = bytes(self.buffer).decode()
            results = self._parse_results(cmd_output)
        else:
            results = []
        self.done.set_result((return_code, results))

    def _parse_results(self, output):
        print('parsing results')
        # Output has one row of headers, all single words.  The
        # remaining rows are one per filesystem, with columns
        # matching the headers (assuming that none of the
        # mount points have whitespace in the names).
        if not output:
            return []
        lines = output.splitlines()
        headers = lines[0].split()
        devices = lines[1:]
        results = [
            dict(zip(headers, line.split()))
            for line in devices
        ]
        return results
