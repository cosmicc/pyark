import subprocess


def serverexec(cmdlist, nice=10, null=False):
    if type(cmdlist) is not list:
        raise TypeError
    else:
        fullcmdlist = ['/usr/bin/nice', '-n', nice] + cmdlist
    if null:
        sproc = subprocess.run(fullcmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        return sproc['returncode']
    else:
        sproc = subprocess.run(fullcmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        return sproc
