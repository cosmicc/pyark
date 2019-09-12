import subprocess

import redis

from modules.configreader import hstname, redis_host, redis_port

r = redis.Redis(host=redis_host, port=redis_port, db=0)
pubsub = r.pubsub()
pubsub.subscribe([f'{hstname.lower()}-commands'])
for response in pubsub.listen():
    if response['type'] == 'message' and response['channel'].decode() == f'{hstname.lower()}-commands':
        if response['data'].decode() == 'restart':
            subprocess.run(['systemctl', 'restart', 'pyark'], shell=False, capture_output=False)
        elif response['data'].decode() == 'stop':
            subprocess.run(['systemctl', 'stop', 'pyark'], shell=False, capture_output=False)
        elif response['data'].decode() == 'start':
            subprocess.run(['systemctl', 'start', 'pyark'], shell=False, capture_output=False)
        elif response['data'].decode() == 'gitpull':
            subprocess.run(['git', 'pull'], shell=True, cwd='/home/ark/pyark', capture_output=False)
