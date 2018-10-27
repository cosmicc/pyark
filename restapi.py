import time, logging, sqlite3, socket
from sys import exit
from datetime import datetime
from numpy import mean
from flask import Flask, request, Blueprint, Response
from flask_restplus import Api, Resource, fields, marshal
from functools import wraps
from timehelper import estshift, elapsedTime, playedTime
from configreader import sqldb, statsdb, restapi_token, restapi_ip, restapi_port, apilogfile

hstname = socket.gethostname()

app = Flask(__name__)

apilog = logging.getLogger('werkzeug')
#apilog = logging.getLogger(__name__)
log_format = logging.Formatter('%(asctime)s:[%(levelname)s]:%(message)s')
log_file = logging.FileHandler(apilogfile)
log_file.setLevel(logging.DEBUG)
log_file.setFormatter(log_format)
apilog.addHandler(log_file)
app.logger.addHandler(log_file)
#apilog = app.logger


blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(blueprint, title='Galaxy Cluster RestAPI', version='1.0', doc='/docs')  # doc=False

app.register_blueprint(blueprint)

app.config['SWAGGER_UI_JSONEDITOR'] = True

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

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
    oplayers = []
    for row in allplayers:
        diff_time = float(time.time()) - float(row[2])
        total_min = diff_time / 60
        minutes = int(total_min % 60)
        hours = int(total_min / 60)
        days = int(hours / 24)
        if minutes <= 1 and hours < 1 and days < 1:
            pcnt += 1
            oplayers.append(row[1])
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


class lotteryends(fields.Raw):
    def format(self, value):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT timestamp, lengthdays from lotteryinfo WHERE id = ?', (value,))
        linfo = c.fetchone()
        c.close()
        conn.close()
        endtime = float(linfo[0]) + (3600 * linfo[1])
        if endtime > time.time():
            return f'in {elapsedTime(endtime, time.time())}'
        else:
            return f'{elapsedTime(time.time(), endtime)} ago'


def isinlottery():
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('SELECT * from lotteryinfo WHERE winner = "Incomplete"')
    linfo = c.fetchone()
    c.close()
    conn.close()
    if linfo:
        return True
    else:
        return False


class lotteryendtime(fields.Raw):
    def format(self, value):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT timestamp, lengthdays from lotteryinfo WHERE id = ?', (value,))
        linfo = c.fetchone()
        c.close()
        conn.close()
        endtime = float(linfo[0]) + (3600 * linfo[1])
        endtime = datetime.fromtimestamp(endtime)
        return estshift(endtime).strftime('%a %b %-d %-I:%M %p')


class lotteryplayers(fields.Raw):
    def format(self, value):
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT playername from lotteryplayers')
        linfo = c.fetchall()
        c.close()
        conn.close()
        nlinfo = []
        for each in linfo:
            nlinfo.append(each[0])
        return nlinfo


class whenlastplayer(fields.Raw):
    def format(self, value):
        conn = sqlite3.connect(statsdb)
        c = conn.cursor()
        c.execute('SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1' % (value,))
        linfo = c.fetchone()
        c.close()
        conn.close()
        return elapsedTime(time.time(), int(linfo[0]))


# estshift(datetime.fromtimestamp(float(value))).strftime('%a, %b %d %I:%M %p')

#def getallplaytime(when, statsinst):
#    for each in statsinst:
#        int(percentage(getplaytime(each, when),28800))
#        playedTime(str(getplaytime(when))

m_serverinfo = api.model('serverinfo', {
    'name': fields.String,
    'playersonline': playerson(attribute='name'),
    'lastplayeronline': whenlastplayer(attribute='name'),
    'lastrestart': elapsedtime(attribute='lastrestart'),
    'restartreason': fields.String,
    'lastdinowipe': elapsedtime(attribute='lastdinowipe'),
    'isrestarting': fields.String(attribute='needsrestart'),
    'lastvote': elapsedtime(attribute='lastvote'),
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



m_minplayerinfo = api.model('minplayerinfo', {
    'steamid': fields.String,
    'name': fields.String(attribute='playername'),
    'discordid': fields.String,
    'lastonline': elapsedtime(attribute='lastseen'),
    'homeserver': fields.String,
    'joined': elapsedtime(attribute='firstseen'),
    'playedtime': plytime(attribute='playedtime'),
})


m_fullplayerinfo = api.clone('playerinfo', m_minplayerinfo, {
    'server': fields.String,
    'connections': fields.Integer(attribute='connects'),
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

m_lotteryplayers = api.clone('lotteryplayerinfo', m_minplayerinfo, {
    'lotteryswon': fields.Integer(attribute='lottowins'),
    'lotterywinnings': fields.Integer,
})

m_lottery = api.model('lottery', {
    'id': fields.Integer,
    'type': fields.String,
    'start': elapsedtime(attribute='timestamp'),
    'end': lotteryends(attribute='id'),
    'endtime': lotteryendtime(attribute='id'),
    'lengthhours': fields.Integer(attribute='lengthdays'),
    'payout': fields.String(attribute='payoutitem'),
    'buyinpoints': fields.Integer,
    'numberplayers': fields.Integer(attribute='players'),
    'winner': fields.String,
    # 'announced': int2bool(attribute='announced')
})

m_clottery = api.clone('currentlottery', m_lottery, {
    'players': lotteryplayers(attribute='id'),
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
            apilog.warning(f'API request without a token')
            return {'message': 'Token is missing'}, 401

        if token != restapi_token:
            apilog.warning(f'API request invalid token: {token}')
            return {'message': 'Invalid Token'}, 401
        apilog.debug(f'API request granted with token: {token}')
        return f(*args, **kwargs)
    return decorated


@api.route('/server/query')
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


@api.route('/cluster/info')
class ClusterInfo(Resource):
    # @api.doc(security='apikey')
    # @token_required
    # @api.marshal_with(m_clusterinfo)
    def get(self):
        global apilog
        conn = sqlite3.connect(sqldb)
        c = conn.cursor()
        c.execute('SELECT name from instances')
        instr = c.fetchall()
        c.close()
        conn.close()
        cluster = {}
        statsinst = []
        for each in instr:
            statsinst.append(each[0])
        cluster['instances'] = statsinst
        np, oplayers = howmanyonline()
        cluster['numberonline'] = np
        cluster['playersonline'] = oplayers
        cluster['newplayers'] = {'lastday': newplayers('daily'), 'lastweek': newplayers('weekly'), 'lastmonth': newplayers('monthly')}
        cluster['inlottery'] = isinlottery()
        return (cluster), 201


@api.route('/cluster/stats')
class ClusterStats(Resource):
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
        cluster = {}
        statsinst = []
        for each in instr:
            statsinst.append(each[0])
        cluster['instances'] = statsinst
        np, oplayers = howmanyonline()
        ahv, ahd = getallhighest('hourly', statsinst)
        aev, aed = getallhighest('eighthour', statsinst)
        adv, add = getallhighest('daily', statsinst)
        awv, awd = getallhighest('weekly', statsinst)
        amv, amd = getallhighest('monthly', statsinst)
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


@api.route('/cluster/banned')
class BannedPlayers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    def get(self):
        newnap = []
        supernap = {}
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE banned != NULL')
            q_player = c.fetchall()
            c.execute('SELECT * FROM banlist')
            banlist = c.fetchall()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        if q_player:
            for each in q_player:
                nap = {}
                nap.update(zip(listcolums('players'), each))
                newnap.append(nap)
            supernap = {'steamids': banlist, 'players': newnap}
        else:
            supernap = {'steamids': banlist, 'players': []}
        return supernap


@api.route('/players/query')
class PlayerInfo(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.expect(playerquery)
    @api.marshal_with(m_fullplayerinfo)
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


@api.route('/players/newest')
class NewPlayers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.marshal_with(m_fullplayerinfo)
    def get(self):
        newnap = []
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players ORDER BY firstseen DESC LIMIT 10')
            q_player = c.fetchall()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        try:
            for each in q_player:
                nap = {}
                nap.update(zip(listcolums('players'), each))
                newnap.append(nap)
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return newnap


@api.route('/players/topplayed')
class TopPlayers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.marshal_with(m_minplayerinfo)
    def get(self):
        newnap = []
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players ORDER BY playedtime DESC LIMIT 10')
            q_player = c.fetchall()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        try:
            for each in q_player:
                nap = {}
                nap.update(zip(listcolums('players'), each))
                newnap.append(nap)
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return newnap



@api.route('/cluster/lottery/current')
class ClusterLottery(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.marshal_with(m_clottery)
    def get(self):
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM lotteryinfo WHERE winner == "Incomplete"')
            current_lotto = c.fetchone()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        try:
            if current_lotto:
                nap = {}
                nap.update(zip(listcolums('lotteryinfo'), current_lotto))
            else:
                nap = {}
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return nap


@api.route('/cluster/lottery/topwinners')
class LotteryWinners(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.marshal_with(m_lotteryplayers)
    def get(self):
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 10')
            lottowinners = c.fetchall()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        newnap = []
        try:
            for each in lottowinners:
                nap = {}
                nap.update(zip(listcolums('players'), each))
                newnap.append(nap)
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return newnap


@api.route('/cluster/lottery/history')
class LotteryHistory(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.marshal_with(m_lottery)
    def get(self):
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM lotteryinfo WHERE winner != "Incomplete" ORDER BY id DESC')
            lhist = c.fetchall()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        newnap = []
        try:
            for each in lhist:
                nap = {}
                nap.update(zip(listcolums('lotteryinfo'), each))
                newnap.append(nap)
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return newnap


@api.route('/players/expired')
class ExpiredPlayers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.marshal_with(m_fullplayerinfo)
    def get(self):
        newnap = []
        try:
            conn = sqlite3.connect(sqldb)
            c = conn.cursor()
            c.execute('SELECT * FROM players WHERE lastseen < ? ORDER BY lastseen ASC', (time.time() - 2592000,))
            q_player = c.fetchall()
            c.close()
            conn.close()
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        try:
            for each in q_player:
                nap = {}
                nap.update(zip(listcolums('players'), each))
                newnap.append(nap)
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return newnap


if __name__ == '__main__':
    app.run(host=restapi_ip, port=restapi_port, debug=True)
