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

# General
sharedpath = config.get('general', 'shared')
arkroot = config.get('general', 'arkroot')
logfile = config.get('general', 'logfile')
is_arkupdater = config.get('general', 'is_arkupdater')
is_asdatapuller = config.get('general', 'is_asdatapuller')
is_discordbot = config.get('general', 'is_discordbot')
is_statscollector = config.get('general', 'is_statscollector')
is_lotterymanager = config.get('general', 'is_lotterymanager')

# RestAPI
apilogfile = config.get('restapi', 'logfile')

# Postgresql
psql_host = config.get('postgresql', 'host')
psql_port = config.get('postgresql', 'port')
psql_user = config.get('postgresql', 'user')
psql_pw = config.get('postgresql', 'password')
psql_db = config.get('postgresql', 'db')
psql_statsdb = config.get('postgresql', 'statsdb')
# psql_stats = "dbname='pyarkstats', user='pyark', host='{pshost}', port='{psport}', password='{pspw}'"

# Discord
discord_channel = config.get('discord', 'general_channel')
discord_serverchat = config.get('discord', 'serverchat_channel')
discordtoken = config.get('discord', 'token')

# Pushover
po_userkey = config.get('pushover', 'userkey')
po_appkey = config.get('pushover', 'appkey')

# Webserver
webserver_enabled = config.get('webserver', 'enabled')
webserver_ip = config.get('webserver', 'ip')
webserver_port = config.get('webserver', 'port')
secsalt = config.get('webserver', 'security_salt')

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
