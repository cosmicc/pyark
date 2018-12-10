import configparser as ConfigParser

basefile = '/home/ark/shared/config/GameUserSettings-base.ini'

config = ConfigParser.RawConfigParser()
config.optionxform = str
config.read(basefile)
mojo = ("StructuresPlus", "DisableDinoScanDetails", "true")
mojo = ("ServerSettings", "XPMultiplier", "2.50000")
mojo = ("TCsAR", "BonusAmount", "50")
mojo = ("ServerSettings", "HarvestAmountMultiplier", "5.000000")
HarvestAmountMultiplier
config.set(mojo[0], mojo[1], mojo[2])
with open(basefile, 'w') as configfile:
    config.write(configfile)
