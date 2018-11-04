from datetime import datetime
import sys
sys.path.append('/home/ark/pyark')
import dbhelper


def test_checkdb(cursor):
    cursor.execute('select * from general')
    rs = cursor.fetchall()
    assert len(rs) == 1


def test_playerstable(cursor):
    cursor.execute('select * from players')
    rs = cursor.fetchall()
    assert len(rs) > 20


def test_dbquery():
    assert len(dbhelper.dbquery("SELECT * FROM general")) == 1
    assert type(dbhelper.dbquery("SELECT * FROM general")[0]) is tuple
    assert type(dbhelper.dbquery("SELECT value FROM ragnarok LIMIT 1", db='statsdb', fetch='one')[0]) is int
    assert type(dbhelper.dbquery("SELECT * FROM general")) is list
    assert type(dbhelper.dbquery("SELECT cfgver FROM general", fetch='one', fmt='list', single=True)) is list
    assert type(dbhelper.dbquery("SELECT cfgver FROM general", fetch='one', fmt='string', single=True)) is str
    assert type(dbhelper.dbquery("SELECT name FROM instances", fetch='all', fmt='string', single=False)) is str
    assert type(dbhelper.dbquery("SELECT name FROM instances", fetch='all', fmt='list', single=False)) is list
    assert type(dbhelper.dbquery("SELECT name FROM instances", fetch='all', fmt='tuple', single=False)[0]) is tuple
    #assert type(dbhelper.dbquery("SELECT * FROM instances", fetch='all', fmt='dict')) is dict


def test_dbupdate():
    assert dbhelper.dbupdate("INSERT into general (cfgver) VALUES ('9999')") is True
    assert dbhelper.dbupdate("DELETE from general WHERE cfgver = '9999'") is True


def test_db_getcolumns():
    assert dbhelper.db_getcolumns('kicklist') == 'instance[0], steamid[1], '


def test_db_gettables():
    assert type(dbhelper.db_gettables('sqldb')) is list
    assert type(dbhelper.db_gettables('statsdb')) is list
    assert type(dbhelper.db_gettables('sqldb')[0]) is tuple
    assert type(dbhelper.db_gettables('statsdb')[0]) is tuple


def test_db_getall():
    assert type(dbhelper.db_getall('instances')) is list
    assert type(dbhelper.db_getall('instances')[0]) is tuple
    assert type(dbhelper.db_getall('instances', fmt='string', fetch='one')) is str
    assert type(dbhelper.db_getall('instances', fmt='list', fetch='one')) is list
    assert type(dbhelper.db_getall('instances', fmt='dict', fetch='all')[0]) is dict
    assert type(dbhelper.db_getall('instances', fmt='dict', fetch='one')) is dict


def test_db_getvalue():
    assert type(dbhelper.db_getvalue('name', 'instances',)) is tuple
    assert type(dbhelper.db_getvalue('name', 'instances')[0]) is str
    assert type(dbhelper.db_getvalue('name', 'instances', fmt='string', fetch='one')) is str
    assert type(dbhelper.db_getvalue('name', 'instances', fmt='list', fetch='one')) is list
    assert type(dbhelper.db_getvalue('name', 'instances', fmt='dict', fetch='all')[0]) is dict
    assert type(dbhelper.db_getvalue('name', 'instances', fmt='dict', fetch='one')) is dict


def test_getplayer():
    assert dbhelper.getplayer(99999999999999999) is None
    assert dbhelper.getplayer(76561198388849736) is not None
    assert dbhelper.getplayer(76561198388849736)[1] == 'rykker'


def test_playerlastseen():
    assert type(dbhelper.getplayerlastseen(playername='rykker')) is int
    assert type(dbhelper.getplayerlastseen(steamid=76561198388849736)) is int


def test_playerlastserver():
    assert type(dbhelper.getplayerlastserver(playername='rykker')) is str
    assert type(dbhelper.getplayerlastserver(steamid=76561198388849736)) is str


def test_getplayersonline():
    assert type(dbhelper.getplayersonline('ragnarok')) is list
    assert type(dbhelper.getplayersonline('all')) is list
    assert type(dbhelper.getplayersonline('ragnarok', fmt='string')) is str
    assert type(dbhelper.getplayersonline('ragnarok', fmt='count')) is int
    assert type(dbhelper.getplayersonline('all', fmt='count')) is int
    assert type(dbhelper.getplayersonline('all', fmt='string')) is str


def test_instancelist():
    assert type(dbhelper.instancelist()) is list
    assert len(dbhelper.instancelist()) > 0


def test_statsage():
    assert dbhelper.dbquery("SELECT date FROM ragnarok ORDER BY DATE DESC LIMIT 1", db='statsdb', fetch='one')[0] > datetime.now().timestamp() - 3600


def test_getlastplayersonline():
    assert type(dbhelper.getlastplayersonline('all')) is list
    assert len(dbhelper.getlastplayersonline('all')) == 5
    assert len(dbhelper.getlastplayersonline('all', last=8)) == 8
    assert type(dbhelper.getlastplayersonline('all', fmt='string')) is str
    assert type(dbhelper.getlastplayersonline('all', fmt='list')) is list
    assert type(dbhelper.getlastplayersonline('ragnarok')) is list
    assert type(dbhelper.getlastplayersonline('ragnarok', fmt='count')) is int

