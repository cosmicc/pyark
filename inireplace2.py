import configparser as ConfigParser
import os.path
import subprocess

basecfgfile = '/home/ark/shared/config/GameUserSettings-base.ini'
sharedpath = '/home/ark/shared'


def compareconfigs(config1, config2):
    f1 = open(config1)
    text1Lines = f1.readlines()
    f2 = open(config2)
    text2Lines = f2.readlines()
    set1 = set(text1Lines)
    set2 = set(text2Lines)
    diffList = (set1 | set2) - (set1 & set2)
    if diffList:
        return True
    else:
        return False


def buildconfig(inst, event=None):
    servercfgfile = f'{sharedpath}/config/GameUserSettings-{inst.lower()}.ini'
    newcfgfile = f'{sharedpath}/config/GameUserSettings-{inst.lower()}.rdy'
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    config.read(basecfgfile)

    if os.path.isfile(servercfgfile):
        with open(servercfgfile, 'r') as f:
            lines = f.readlines()
            for each in lines:
                each = each.strip().split(',')
                config.set(each[0], each[1], each[2])

    if event is not None:
        eventcfgfile = f'{sharedpath}/config/GameUserSettings-{event.lower()}.ini'
        with open(eventcfgfile, 'r') as f:
            lines = f.readlines()
            for each in lines:
                each = each.strip().split(',')
                config.set(each[0], each[1], each[2])

    with open(newcfgfile, 'w') as configfile:
        config.write(configfile)

    if compareconfigs(basecfgfile, basecfgfile):
        subprocess.run('mv %s/config/%s %s/stagedconfig' % (sharedpath, newcfgfile, sharedpath), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        return True
    else:
        subprocess.run('rm -f %s/config/%s' % (sharedpath, newcfgfile), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        return False



buildconfig('extinction')
