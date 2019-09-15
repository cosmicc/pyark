from configparser import ConfigParser
from socket import gethostname
from pathlib import Path

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
sharedpath = Path(config.get('general', 'sharedpath'))
arkrootpath = Path(config.get('general', 'arkrootpath'))
jsonpath = Path(config.get('general', 'jsonlogpath'))
pylogpath = Path(config.get('general', 'pyarklogpath'))
pyarkfile = Path(config.get('general', 'pyarklogfile'))

adminfile = Path(config.get('general', 'adminlogfile'))
pointsfile = Path(config.get('general', 'pointslogfile'))
crashfile = Path(config.get('general', 'crashlogfile'))
errorfile = Path(config.get('general', 'errorlogfile'))
chatfile = Path(config.get('general', 'chatlogfile'))

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
    instances = instances + (config.get(f'instance{each}', 'name'),)

jsonlogfile = jsonpath / f'{hstname.lower()}_log.json'
jsondebugfile = jsonpath / f'{hstname.lower()}_debug.json'
jsonchatfile = jsonpath / f'{hstname.lower()}_chat.json'
jsongamefile = jsonpath / f'{hstname.lower()}_game.json'
pyarklogfile = pylogpath / pyarkfile
pointslogfile = pylogpath / pointsfile
crashlogfile = pylogpath / crashfile
errorlogfile = pylogpath / errorfile
pointslogfile = pylogpath / pointsfile
adminlogfile = pylogpath / adminfile
chatlogfile = pylogpath / chatfile


