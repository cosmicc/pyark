import configparser as ConfigParser

basefile = '/home/ark/shared/config/GameUserSettings-base.ini'
custfile = '/home/ark/shared/config/GameUserSettings-extinction.ini'
newfile = '/home/ark/shared/config/GameUserSettings-extinction.rdy'


config = ConfigParser.RawConfigParser()
config.optionxform = str
config.read(basefile)

with open(custfile, 'r') as f:
    lines = f.readlines()
    for each in lines:
        each = each.strip().split(',')
        config.set(each[0], each[1], each[2])


with open(newfile, 'w') as configfile:
    config.write(configfile)
