import psutil


def checkpyark():
    for line in open('/tmp/pyark.lock', 'r'):
        pyarkpid = int(line)
    if psutil.pid_exists(pyarkpid):
        pyarkproc = psutil.Process(pid=pyarkpid)
        print(pyarkproc.name())
        print(pyarkproc.exe())
        print(pyarkproc.status())
    else:
        print('no such process')


checkpyark()
