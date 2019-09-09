import time

import psutil

start = time.time()
print(psutil.boot_time())
print(time.time() - start)
