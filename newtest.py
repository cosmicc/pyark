from modules.servertools import serverexec


def getopenfiles():
    result = serverexec(['sysctl', 'fs.file-nr'], nice=19, null=False)
    newresult = result.stdout.decode('utf-8').strip().split(' ')[2].split('\t')
    print(newresult)


getopenfiles()
