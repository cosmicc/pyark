import logging, subprocess, sqlite3, time, threading
from configparser import ConfigParser

log = logging.getLogger(__name__)

class ExtConfigParser(ConfigParser):
    def getlist(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.split(','))))

    def getlistint(self, section, option):
        return [int(x) for x in self.getlist(section, option)]

configfile = '/home/ark/pyark.cfg'

config = ExtConfigParser()
config.read(configfile)

sharedpath = config.get('general', 'shared')
sqldb = f'{sharedpath}/db/pyark.db'
arkroot = config.get('general', 'arkroot')
numinstances = int(config.get('general', 'instances'))
instance = [dict() for x in range(numinstances)]
instr = ''
for each in range(numinstances):
    a = config.get('instance%s' % (each), 'name')
    b = config.get('instance%s' % (each), 'logfile')
    instance[each] = {'name':a,'logfile':b}
    if instr == '':
        instr = '%s' % (a)
    else:
        instr=instr + ', %s' % (a)

def elapsedTime(start_time, stop_time, lshort=False):
    diff_time = start_time - stop_time
    total_min = diff_time / 60
    minutes = int(total_min % 60)
    if minutes == 1:
        if lshort is False:
            minstring = 'Minute'
        else:
            minstring = 'Min'
    else:
        if lshort is False:
            minstring = 'Minutes'
        else:
            minstring = 'Mins'
    hours = int(total_min / 60)
    if hours == 1:
        if lshort is False:
            hourstring = 'Hour'
        else:
            hourstring = 'Hr'
    else:
        if lshort is False:
            hourstring = 'Hours'
        else:
            hourstring = 'Hrs'
    days = int(hours / 24)
    if days == 1:
        if lshort is False:
            daystring = 'Day'
        else:
            daystring = 'Day'
    else:
        if lshort is False:
            daystring = 'Days'
        else:
            daystring = 'Days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes, minstring))
    elif minutes != 0:
        return('{} {}'.format(minutes, minstring))
    elif minutes == 0:
        return('now')
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

def getlastrestart(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastrestart FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def getlastwipe(inst):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT lastdinowipe FROM instances WHERE name = ?', [inst])
    lastwipe = c.fetchall()
    c.close()
    conn.close()
    return ''.join(lastwipe[0])

def checkcommands(inst):
    cmdpipe = subprocess.Popen('arkmanager rconcmd getchat @%s' % (inst), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    b = cmdpipe.stdout.read().decode("utf-8")
    for line in iter(b.splitlines()):
        print(line)
        if line.startswith('Running command') or line.startswith('Error:'):
            pass
        elif line.find('!help') != -1:
            subprocess.run('arkmanager rconcmd "ServerChat Available commands: lastdinowipe, lastrestart" @%s' % (inst), shell=True)
        elif line.find('!lastdinowipe') != -1:
            lastwipe = elapsedTime(time.time(),float(getlastwipe(inst)))
            subprocess.run('arkmanager rconcmd "ServerChat Last wild dino wipe was %s ago" @%s' % (lastwipe, inst), shell=True)
            log.info(f'responded to a lastdinowipe query on instance {inst}')
        elif line.find('!lastrestart') != -1:
            lastrestart = elapsedTime(time.time(),float(getlastrestart(inst)))
            subprocess.run('arkmanager rconcmd "ServerChat Last server restart was %s ago" @%s' % (lastrestart, inst), shell=True)
            log.info(f'responded to a lastrestart query on instance {inst}')

def clisten():
    while True:
        for each in range(numinstances):
            checkcommands(instance[each]['name'])
        time.sleep(10)

