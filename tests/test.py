import subprocess

def getliveonline(inst):
    rawrun = subprocess.run('arkmanager status @%s' % (inst), stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, shell=True)
    rawrun2 = rawrun.stdout.decode('utf-8').split('\n')
    print(rawrun2)
    for ea in rawrun2:
        sttitle = stripansi(ea.split(':')[0]).strip()
        if (sttitle == 'Players:'):
            print(stripansi(ea.split(':')[1]).strip().split('/')[0].strip())

getliveonline('ragnarok')

