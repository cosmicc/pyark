import psutil

inst = 'ragnarok'
pidfile = f'/home/ark/ARK/ShooterGame/Saved/.arkserver-{inst}.pid'

file = open(pidfile, 'r')
arkpid = file.read()

print(arkpid)
arkprocess = psutil.Process(int(arkpid))
arkmem = arkprocess.memory_percent()
print(arkmem)
