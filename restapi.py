import sqlite3, time
from datetime import datetime
from numpy import mean
from flask import Flask, request
from flask_restplus import Api, Resource, fields
from functools import wraps
from timehelper import estshift, elapsedTime, playedTime
from configreader import sqldb, statsdb, restapi_token, restapi_ip, restapi_port

app = Flask(__name__)


authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}


api = Api(app, authorizations=authorizations)

playerquery = api.model('PlayerQuery', {'playername': fields.String('Player Name'), 'steamid': fields.Integer('Steam ID')})
serverquery = api.model('ServerQuery', {'servername': fields.String('Server Name')})


def percentage(part, whole):
    return 100 * float(part) / float(whole)


def f2dec(num):
    try:
        tnum = num // 0.01 / 100
    except:
        # log.exception('Error truncating float to 2 decimals: {}'.format(num))
        return False
    else:
        return tnum


def getallavg(length, statsinst):
    if length == 'daily':
        ilength = 86400
    elif length == 'weekly':
        ilength = 604800
    elif length == 'monthly':
        ilength = 2592000
    elif length == 'hourly':
        ilength = 3600
    elif length == 'eighthour':
        ilength = 28800
    avglist = []
    ntime = int(time.time())
    for each in statsinst:
        slist = []
        navglist = []
        conn8 = sqlite3.connect(statsdb)
        c8 = conn8.cursor()
        c8.execute('SELECT value FROM %s WHERE date > %s' % (each, ntime - ilength))
        nlist = c8.fetchall()
        c8.close()
        conn8.close()
        for y in nlist:
            slist.append(y[0])
        if avglist == []:
            avglist = slist
        else:
            navglist = [sum(pair) for pair in zip(slist, avglist)]
            avglist = navglist
    return f2dec(mean(avglist))


def howmanyonline():
    pcnt = 0
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * from players')
    allplayers = c.fetchall()
    c.close()
    conn.close()
    oplayers = ''
    for row in allplayers:
        diff_time = float(time.time()) - float(row[2])
        total_min = diff_time / 60
        minutes = int(total_min % 60)
        hours = int(total_min / 60)
        days = int(hours / 24)
        if minutes <= 1 and hours < 1 and days < 1:
            pcnt += 1
            if oplayers == '':
                oplayers = row[1]
            else:
                oplayers = oplayers + f', {row[1]}'

    return pcnt, oplayers


def newplayers(when):
    if when == 'daily':
        utime = 86400
    elif when == 'weekly':
        utime = 604800
    elif when == 'monthly':
        utime = 2592000
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT playername from players WHERE firstseen > %s ORDER BY firstseen DESC' % (time.time() - utime,))
    nplayers = c.fetchall()
    c.close()
    conn.close()
    return len(nplayers)


class elapsedtime(fields.Raw):
    def format(self, value):
        return elapsedTime(float(time.time()), float(value))


class plytime(fields.Raw):
    def format(self, value):
        return playedTime(value)


class playerson(fields.Raw):
    def format(self, value):
        def howmanyon(inst):
            pcnt = 0
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * from players')
            allplayers = c.fetchall()
            c.close()
            conn.close()
            for row in allplayers:
                diff_time = float(time.time()) - float(row[2])
                total_min = diff_time / 60
                minutes = int(total_min % 60)
                hours = int(total_min / 60)
                days = int(hours / 24)
                if minutes <= 1 and hours < 1 and days < 1 and row[3] == inst:
                    pcnt += 1
            return pcnt
        return howmanyon(value)


def getallhighest(length, statsinst):
    if length == 'daily':
        ilength = 86400
    elif length == 'weekly':
        ilength = 604800
    elif length == 'monthly':
        ilength = 2592000
    elif length == 'hourly':
        ilength = 3600
    elif length == 'eighthour':
        ilength = 28800
    avglist = []
    ntime = int(time.time())
    for each in statsinst:
        slist = []
        navglist = []
        dlist = []
        datelist = []
        conn8 = sqlite3.connect(statsdb)
        c8 = conn8.cursor()
        c8.execute('SELECT value, date FROM %s WHERE date > %s' % (each, ntime - ilength))
        nlist = c8.fetchall()
        c8.close()
        conn8.close()
        for y, x in nlist:
            slist.append(y)
            dlist.append(x)
        if avglist == []:
            avglist = slist
            datelist = dlist
        else:
            navglist = [sum(pair) for pair in zip(slist, avglist)]
            avglist = navglist
            datelist = dlist
    nt = datetime.fromtimestamp(datelist[avglist.index(max(avglist))])
    return max(avglist), estshift(nt).strftime('%a %b %-d %-I:%M %p')


class getinstances(fields.Raw):
    def format(self, value):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT name from instances')
        instr = c.fetchall()
        c.close()
        conn.close()
        print(f'instances: {instr}')
        return instr


class int2bool(fields.Raw):
    def format(self, value):
        if value == 1:
            return 'True'
        elif value == 0:
            return 'False'
        else:
            return 'Error'
# estshift(datetime.fromtimestamp(float(value))).strftime('%a, %b %d %I:%M %p')

#def getallplaytime(when, statsinst):
#    for each in statsinst:
#        int(percentage(getplaytime(each, when),28800))
#        playedTime(str(getplaytime(when))

m_serverinfo = api.model('serverinfo', {
    'name': fields.String,
    'playersonline': playerson(attribute='name'),
    'lastrestart': elapsedtime(attribute='lastrestart'),
    'lastdinowipe': elapsedtime(attribute='lastdinowipe'),
    'isrestarting': fields.String(attribute='needsrestart'),
    'lastvote': elapsedtime(attribute='lastvote'),
    'restartreason': fields.String,
    'config_ver': fields.Integer(attribute='cfgver'),
    'restartcountdown': fields.Integer,
    'isonline': int2bool(attribute='isup'),
    'islistening': int2bool(attribute='islistening'),
    'isrunning': int2bool(attribute='isrunning'),
    'lastcheck': elapsedtime(attribute='uptimestamp'),
    'activemem': fields.String(attribute='actmem'),
    'totalmem': fields.String(attribute='totmem'),
    'steamlink': fields.String,
    'arkserverslink': fields.String,
    'battlemetricslink': fields.String,
})

m_playerinfo = api.model('playerinfo', {
    'name': fields.String(attribute='playername'),
    'steamid': fields.String,
    'discordid': fields.String,
    'lastonline': elapsedtime(attribute='lastseen'),
    'server': fields.String,
    'homeserver': fields.String,
    'joined': elapsedtime(attribute='firstseen'),
    'connections': fields.Integer(attribute='connects'),
    'playedtime': plytime(attribute='playedtime'),
    'rewardpoints': fields.Integer,
    'transferpoints': fields.Integer,
    'lotteryswon': fields.Integer(attribute='lottowins'),
    'lotterywinnings': fields.Integer,
    'totalauctions': fields.Integer,
    'itemauctions': fields.Integer,
    'dinoauctions': fields.Integer,
    'primordialwarning': int2bool(attribute='primordialbit'),
    'onsincerestart': int2bool(attribute='restartbit'),
})


def listcolums(mtable):
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('PRAGMA table_info({})'.format(mtable))
    alldata = c.fetchall()
    c.close()
    conn.close()
    ap = []
    for row in alldata:
        ap.append(f'{row[1]}')
    return ap


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'X-API-KEY' in request.headers:
            token = request.headers['X-API-KEY']

        if not token:
            return {'message': 'Token is missing'}, 401

        if token != restapi_token:
            return {'message': 'Invalid Token'}, 401

        print('TOKEN: {}'.format(token))
        return f(*args, **kwargs)
    return decorated


@api.route('/serverinfo')
class ServerInfo(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.expect(serverquery)
    @api.marshal_with(m_serverinfo)
    def post(self):
        sname = api.payload['servername']
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        if sname is not None or sname != 'string':
            c.execute('SELECT * FROM instances WHERE name = ?', (sname,))
            q_server = c.fetchone()
            c.close()
            conn.close()
        else:
            return {'message': 'Must specify server name'}, 400
        if not q_server:
            return {'message': 'Server does not exist'}, 400
        else:
            nap = dict(zip(listcolums('instances'), q_server))
            return (nap), 201


@api.route('/clusterinfo')
class ClusterInfo(Resource):
    # @api.doc(security='apikey')
    # @token_required
    # @api.marshal_with(m_clusterinfo)
    def get(self):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT name from instances')
        instr = c.fetchall()

        c.close()
        conn.close()
        ap = ''
        cluster = {}
        statsinst = []
        for each in instr:
            statsinst.append(each[0])
            if ap == '':
                ap = f'{each[0]}'
            else:
                ap = ap + f', {each[0]}'
        ahv, ahd = getallhighest('hourly', statsinst)
        aev, aed = getallhighest('eighthour', statsinst)
        adv, add = getallhighest('daily', statsinst)
        awv, awd = getallhighest('weekly', statsinst)
        amv, amd = getallhighest('monthly', statsinst)
        cluster['instances'] = ap
        np, oplayers = howmanyonline()
        cluster['playersonline'] = np
        cluster['players'] = oplayers
        cluster['newplayers'] = {'lastday': newplayers('daily'), 'lastweek': newplayers('weekly'), 'lastmonth': newplayers('monthly')}
        cluster['stats'] = {
            'lasthour': {
                'average': getallavg('hourly', statsinst),
                'trend': f2dec(getallavg('hourly', statsinst) - np),
                'highest': ahv,
                'hightime': ahd,
            },
            'last8hour': {
                'average': getallavg('eighthour', statsinst),
                'trend': f2dec(getallavg('eighthour', statsinst) - np),
                'highest': aev,
                'hightime': aed,
            },
            'last24hours': {
                'average': getallavg('daily', statsinst),
                'trend': f2dec(getallavg('daily', statsinst) - np),
                'highest': adv,
                'hightime': add,
            },
            'lastweek': {
                'average': getallavg('weekly', statsinst),
                'trend': f2dec(getallavg('weekly', statsinst) - np),
                'highest': awv,
                'hightime': awd,
            },
            'lastmonth': {
                'average': getallavg('monthly', statsinst),
                'trend': f2dec(getallavg('monthly', statsinst) - np),
                'highest': amv,
                'hightime': amd,
            },
        }
        return (cluster), 201


@api.route('/playerinfo')
class PlayerInfo(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.expect(playerquery)
    @api.marshal_with(m_playerinfo)
    def post(self):
        pname = api.payload['playername']
        steamid = api.payload['steamid']
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        if pname is not None or pname != 'string':
            c.execute('SELECT * FROM players WHERE playername = ?', (pname,))
            q_player = c.fetchone()
            c.close()
            conn.close()
        elif steamid is not None or steamid != 0:
            c.execute('SELECT * FROM players WHERE steamid = ?', (steamid,))
            q_player = c.fetchone()
            c.close()
            conn.close()
        else:
            return {'message': 'Must specify player name or steamid'}, 400
        if q_player is None:
            return {'message': 'Player does not exist'}, 400
        else:
            nap = dict(zip(listcolums('players'), q_player))
            return (nap), 201


if __name__ == '__main__':
    app.run(host=restapi_ip, port=restapi_port, debug=True)
