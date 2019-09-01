from modules.servertools import serverexec

inst = 'crystal'
cmdpipe = serverexec(['arkmanager', 'rconcmd', 'getgamelog', f'@{inst}'], nice=5, null=False)
b = cmdpipe.stdout.decode("utf-8")
print(len(b.splitlines))
#for line in iter(b.splitlines()):

