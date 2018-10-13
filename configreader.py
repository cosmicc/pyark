from configparser import ConfigParser

configfile = '/home/ark/pyark.cfg'


class ExtConfigParser(ConfigParser):
    def getlist(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.split(','))))

    def getlistint(self, section, option):
        return [int(x) for x in self.getlist(section, option)]


config = ExtConfigParser()
config.read(configfile)

sharedpath = config.get('general', 'shared')
arkroot = config.get('general', 'arkroot')
logfile = config.get('general', 'log')

sqldb = f'{sharedpath}/db/pyark.db'

numinstances = int(config.get('general', 'instances'))
instance = [dict() for x in range(numinstances)]

instr = ''

for each in range(numinstances):
    a = config.get('instance%s' % (each), 'name')
    instance[each] = {'name': a, }
    if instr == '':
        instr = '%s' % (a)
    else:
        instr = instr + ', %s' % (a)
        instr = instr + ', %s' % (a)


isupdater = config.get('general', 'isupdater')
imthedbot = config.get('general', 'isdiscordbot')
