from configparser import ConfigParser
from socket import gethostname

configfile = '/home/ark/pyark.cfg'


class ExtConfigParser(ConfigParser):
    def getlist(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.split(','))))

    def getlistint(self, section, option):
        return [int(x) for x in self.getlist(section, option)]


config = ExtConfigParser()
config.read(configfile)

hstname = gethostname().upper()

# General
loglevel = config.get('general', 'loglevel')
sharedpath = config.get('general', 'shared')
arkrootpath = config.get('general', 'arkroot')
#jsonlogpath = config.get('general', 'jsonlogpath')
#pyarklogpath = config.get('general', 'pyarklogpath')
#pyarklogfile = config.get('general', 'pyarklogfile')

adminfile = config.get('general', 'adminlogfile')
pointsfile = config.get('general', 'pointslogfile')
jsondebugfile = config.get('general', 'jsondebugfile')
crashlogfile = config.get('general', 'crashlogfile')
errorlogfile = config.get('general', 'errorlogfile')
chatlogfile = config.get('general', 'chatlogfile')

maint_hour = config.get('general', 'maint_hour')

is_arkupdater = config.get('general', 'is_arkupdater')

# SteamAPI
steamapikey = config.get('steam', 'steamapikey')

# RestAPI
apilogfile = config.get('restapi', 'logfile')

# Postgresql
psql_host = config.get('postgresql', 'host')
psql_port = config.get('postgresql', 'port')
psql_user = config.get('postgresql', 'user')
psql_pw = config.get('postgresql', 'password')
psql_db = config.get('postgresql', 'db')

# Redis
redis_host = config.get('redis', 'host')
redis_port = config.get('redis', 'port')
redis_pw = config.get('redis', 'password')
redis_db = config.get('redis', 'db')

# Discord
generalchat_id = config.get('discord', 'general_channel')
serverchat_id = config.get('discord', 'serverchat_channel')
infochat_id = config.get('discord', 'info_channel')
changelog_id = config.get('discord', 'changelog_channel')
discordtoken = config.get('discord', 'token')

# Pushover
po_userkey = config.get('pushover', 'userkey')
po_appkey = config.get('pushover', 'appkey')

# Webserver
webserver_enabled = config.get('webserver', 'enabled')
webserver_ip = config.get('webserver', 'ip')
webserver_port = config.get('webserver', 'port')
secsalt = config.get('webserver', 'security_salt')
testing_seckey = config.get('webserver', 'debug_testkey')

numinstances = int(config.get('general', 'instances'))

instances = ()

for each in range(numinstances):
    instances = instances + config.get(f'instance{each}', 'name')
