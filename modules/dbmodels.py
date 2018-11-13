from active_alchemy import ActiveAlchemy
from datetime import datetime

db = ActiveAlchemy("postgresql+pg8000://pyark:nGXaQ2x6UzSx396EYvgSfv54BX7w8x2X@172.31.250.112:51432/pyark_test")


class general(db.Model):
    cfgver = db.Column(db.Integer())
    announce = db.Column(db.String())


class instances(db.Model):
    name = db.Column(db.String(12), unique=True, nullable=False)
    lastrestart = db.Column(db.DateTime, default=datetime.now())
    lastdinowipe = db.Column(db.DateTime, default=datetime.now())
    needsrestart = db.Column(db.Boolean, default=False)
    lastvote = db.Column(db.DateTime, default=datetime.now())
    restartreason = db.Column(db.String(), default="")
    cfgver = db.Column(db.SmallInteger, default=0)
    restartcountdown = db.Column(db.SmallInteger, default=30)
    arkserverkey = db.Column(db.String(), default="")
    isup = db.Column(db.Boolean, default=False)
    islistening = db.Column(db.Boolean, default=False)
    isrunning = db.Column(db.Boolean, default=False)
    uptimestamp = db.Column(db.DateTime, default=datetime.now())
    actmem = db.Column(db.String(7), default="0.00")
    totmem = db.Column(db.String(7), default="0.00")
    steamlink = db.Column(db.String(), default="")
    arkserverslink = db.Column(db.String(), default="")
    battlemetricslink = db.Column(db.String(), default="")
    arkversion = db.Column(db.String(7), default="")
    uptime = db.Column(db.SmallInteger, default=0)
    rank = db.Column(db.SmallInteger, default=0)
    score = db.Column(db.SmallInteger, default=0)
    votes = db.Column(db.SmallInteger, default=0)
    hostname = db.Column(db.String(), default="")
    inevent = db.Column(db.SmallInteger, default=0)


class players(db.Model):
    steamid = db.Column(db.String(17), unique=True, nullable=False)
    playername = db.Column(db.String(), default="Newplayer")
    lastseen = db.Column(db.DateTime, default=datetime.now())
    server = db.Column(db.String(12), default="")
    playedtime = db.Column(db.Integer, default=0)
    rewardpoints = db.Column(db.Integer, default=50)
    firstseen = db.Column(db.DateTime, default=datetime.now())
    connects = db.Column(db.SmallInteger, default=1)
    discordid = db.Column(db.String(), default="")
    banned = db.Column(db.Boolean, default=False)
    totalauctions = db.Column(db.SmallInteger, default=0)
    itemauctions = db.Column(db.SmallInteger, default=0)
    dinoauctions = db.Column(db.SmallInteger, default=0)
    restartbit = db.Column(db.Boolean, default=False)
    primordialbit = db.Column(db.Boolean, default=False)
    homeserver = db.Column(db.String(12), default="")
    transferpoints = db.Column(db.Integer, default=0)
    lastpointtimestamp = db.Column(db.DateTime, default=datetime.now())
    lottowins = db.Column(db.SmallInteger, default=0)
    lotterywinnings = db.Column(db.Integer, default=0)
    email = db.Column(db.EmailType, default="")
    password = db.Column(db.String(), default="")
    apikey = db.Column(db.String(), default="")


class kicklist(db.Model):
    instance = db.Column(db.String(12), default="")
    steamid = db.Column(db.String(17), unique=True, nullable=False)


class chatbuffer(db.Model):
    server = db.Column(db.String(12))
    name = db.Column(db.String())
    message = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.now())


class globalbuffer(db.Model):
    server = db.Column(db.String(12))
    name = db.Column(db.String())
    message = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.now())
    private = db.Column(db.Boolean)


class linkrequests(db.Model):
    steamid = db.Column(db.String(17), unique=True, nullable=False)
    name = db.Column(db.String())
    reqcode = db.Column(db.SmallInteger)


class events(db.Model):
    completed = db.Column(db.Boolean, default=False)
    starttime = db.Column(db.DateTime, default=datetime.now())
    endtime = db.Column(db.DateTime)
    title = db.Column(db.String())
    description = db.Column(db.String())
    cfgfilesuffix = db.Column(db.String(8))


class lotteryinfo(db.Model):
    payout = db.Column(db.SmallInteger)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    buyinpoints = db.Column(db.SmallInteger)
    length = db.Column(db.SmallInteger)
    players = db.Column(db.SmallInteger)
    winner = db.Column(db.String())
    announced = db.Column(db.Boolean)


class lotteryplayers(db.Model):
    steamid = db.Column(db.String(17), unique=True)
    playername = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.now())
    paid = db.Column(db.Boolean, default=False)


class lotterydeposits(db.Model):
    steamid = db.Column(db.String(17))
    playername = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.now())
    points = db.Column(db.SmallInteger)
    withdraw = db.Column(db.Boolean)


db.create_all()


def main():
    #row = db.query(instances.id, instaces.name, User.email)\
    #    .filter(and_(User.id == id, User.username == username)).first()
    #print("id=%s username=%s email=%s" % row) # positional
    #print(row.id, row.username) # by label
    #print(dict(zip(row.keys(), row))) # as a dict


    instance = instances.query()

    print(instance.filter(instances.isrunning == False).name)
    #customer_dict = dict((col, getattr(customer, col)) for col in customer.__table__.columns.keys())
    #print(customer_dict)
    #print(zip(*instance)[0])
    #for instance in inst:

    #instances.create(name='volcano')
    #for user in testtable.query():
    #    print(user.name)


if __name__ == '__main__':
    main()

