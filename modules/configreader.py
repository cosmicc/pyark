from configparser import ConfigParser
from socket import gethostname
from pathlib import Path

configfile: str = "/home/ark/pyark.cfg"


class ExtConfigParser(ConfigParser):
    def getlist(self, section: str, option: str) -> list:
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.split(","))))

    def getlistint(self, section: str, option: str) -> list:
        return [int(x) for x in self.getlist(section, option)]


config = ExtConfigParser()
config.read(configfile)

hstname: str = gethostname().upper()

# General
loglevel: str = config.get("general", "loglevel")
sharedpath: Path = Path(config.get("general", "sharedpath"))
arkrootpath: Path = Path(config.get("general", "arkrootpath"))
jsonpath: Path = Path(config.get("general", "jsonlogpath"))
pylogpath: Path = Path(config.get("general", "pyarklogpath"))
pyarkfile: Path = Path(config.get("general", "pyarklogfile"))

adminfile: Path = Path(config.get("general", "adminlogfile"))
pointsfile: Path = Path(config.get("general", "pointslogfile"))
crashfile: Path = Path(config.get("general", "crashlogfile"))
errorfile: Path = Path(config.get("general", "errorlogfile"))
chatfile: Path = Path(config.get("general", "chatlogfile"))

maint_hour: int = int(config.get("general", "maint_hour"))

is_arkupdater: bool = bool(config.get("general", "is_arkupdater"))

# SteamAPI
steamapikey: str = config.get("steam", "steamapikey")

# RestAPI
apilogfile: str = config.get("restapi", "logfile")

# Postgresql
psql_host: str = config.get("postgresql", "host")
psql_port: int = int(config.get("postgresql", "port"))
psql_user: str = config.get("postgresql", "user")
psql_pw: str = config.get("postgresql", "password")
psql_db: str = config.get("postgresql", "db")

# Redis
redis_host: str = config.get("redis", "host")
redis_port: int = int(config.get("redis", "port"))
redis_pw: str = config.get("redis", "password")
redis_db: str = config.get("redis", "db")

# Discord
generalchat_id: str = config.get("discord", "general_channel")
serverchat_id: str = config.get("discord", "serverchat_channel")
infochat_id: str = config.get("discord", "info_channel")
changelog_id: str = config.get("discord", "changelog_channel")
discordtoken: str = config.get("discord", "token")

# Pushover
po_userkey: str = config.get("pushover", "userkey")
po_appkey: str = config.get("pushover", "appkey")

# Webserver
webserver_enabled: bool = bool(config.get("webserver", "enabled"))
webserver_ip: str = config.get("webserver", "ip")
webserver_port: int = int(config.get("webserver", "port"))
secsalt: str = config.get("webserver", "security_salt")
testing_seckey: str = config.get("webserver", "debug_testkey")

numinstances: int = int(config.get("general", "instances"))

instances: tuple = ()

for each in range(numinstances):
    instances = instances + (config.get(f"instance{each}", "name"),)

jsonlogfile: Path = jsonpath / f"{hstname.lower()}_log.json"
jsondebugfile: Path = jsonpath / f"{hstname.lower()}_debug.json"
pyarklogfile: Path = pylogpath / pyarkfile
pointslogfile: Path = pylogpath / pointsfile
crashlogfile: Path = pylogpath / crashfile
errorlogfile: Path = pylogpath / errorfile
adminlogfile: Path = pylogpath / adminfile
chatlogfile: Path = pylogpath / chatfile
gamelogfile: Path = pylogpath / "game.log"
