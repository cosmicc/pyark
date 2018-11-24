from clusterevents import getcurrenteventinfo, iseventtime
from datetime import datetime
from flask import request, Blueprint
from flask_restplus import Api, Resource, fields
from functools import wraps
from modules.dbhelper import dbquery, dbupdate
from modules.timehelper import estshift, elapsedTime, playedTime, Now
from modules.configreader import apilogfile
from numpy import mean
from secrets import token_urlsafe
import time
import logging

apilog = logging.getLogger('werkzeug')
log_format = logging.Formatter('%(asctime)s:[%(levelname)s]:%(message)s')
log_file = logging.FileHandler(apilogfile)
log_file.setLevel(logging.DEBUG)
log_file.setFormatter(log_format)
apilog.addHandler(log_file)
# app.logger.addHandler(log_file)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

webapi = Blueprint('api', __name__)
api = Api(webapi, title='Galaxy Cluster RestAPI', version='1.0', doc='/', authorizations=authorizations)  # doc=False


playerquery = api.model('PlayerQuery', {'playername': fields.String('Player Name'), 'steamid': fields.Integer('Steam ID')})
lotteryquery = api.model('LottoQuery', {'buyinpoints': fields.Integer('Buy-in Points'), 'length': fields.Integer('Length in Hours')})
serverquery = api.model('ServerQuery', {'servername': fields.String('Server Name')})


def generatetoken():
    return token_urlsafe(24)


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
        nlist = dbquery("SELECT value FROM %s WHERE date > '%s'" % (each, ntime - ilength), db='statsdb')
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
    allplayers = dbquery("SELECT * from players")
    oplayers = []
    for row in allplayers:
        diff_time = float(time.time()) - float(row[2])
        total_min = diff_time / 60
        minutes = int(total_min % 60)
        hours = int(total_min / 60)
        days = int(hours / 24)
        if minutes <= 1 and hours < 1 and days < 1:
            pcnt += 1
            oplayers.append(row[1].title())
    return pcnt, oplayers


def howmanyonlinesvr(inst):
    pcnt = 0
    allplayers = dbquery("SELECT * from players WHERE server = '%s'" % (inst,))
    oplayers = []
    for row in allplayers:
        diff_time = float(time.time()) - float(row[2])
        total_min = diff_time / 60
        minutes = int(total_min % 60)
        hours = int(total_min / 60)
        days = int(hours / 24)
        if minutes <= 1 and hours < 1 and days < 1:
            pcnt += 1
            oplayers.append(row[1].title())
    return pcnt, oplayers


def newplayers(when):
    if when == 'daily':
        utime = 86400
    elif when == 'weekly':
        utime = 604800
    elif when == 'monthly':
        utime = 2592000
    nplayers = dbquery("SELECT playername from players WHERE firstseen > '%s' ORDER BY firstseen DESC" % (time.time() - utime,))
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
            allplayers = dbquery("SELECT * from players")
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


def serverstatus(inst):
    nlist = dbquery("SELECT isup FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if nlist[0] == 1:
        return 'Online'
    elif nlist[0] == 0:
        return 'Offline'


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
        nlist = dbquery("SELECT value, date FROM %s WHERE date > '%s'" % (each, ntime - ilength), db='statsdb')
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
        instr = dbquery("SELECT name from instances")
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
        linfo = dbquery("SELECT timestamp, lengthdays from lotteryinfo WHERE id = '%s'" % (value,))
        endtime = float(linfo[0]) + (3600 * linfo[1])
        if endtime > time.time():
            return f'in {elapsedTime(endtime, time.time())}'
        else:
            return f'{elapsedTime(time.time(), endtime)} ago'


def isinlottery():
    linfo = dbquery("SELECT * from lotteryinfo WHERE winner = 'Incomplete'")
    if linfo:
        return True
    else:
        return False


class lotteryendtime(fields.Raw):
    def format(self, value):
        linfo = dbquery("SELECT timestamp, lengthdays from lotteryinfo WHERE id = '%s'" % (value,))
        endtime = float(linfo[0]) + (3600 * linfo[1])
        endtime = datetime.fromtimestamp(endtime)
        return estshift(endtime).strftime('%a %b %-d %-I:%M %p')


class lotteryplayers(fields.Raw):
    def format(self, value):
        linfo = dbquery("SELECT playername from lotteryplayers")
        nlinfo = []
        for each in linfo:
            nlinfo.append(each[0].title())
        return nlinfo


class whenlastplayer(fields.Raw):
    def format(self, value):
        linfo = dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1" % (value,), db='statsdb')
        return elapsedTime(time.time(), int(linfo[0]))


class svrinevent(fields.Raw):
    def format(self, value):
        if value == 0:
            return 'False'
        else:
            return 'True'


def whenlastplayersvr(inst):
    linfo = dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1" % (inst,), db='statsdb', fetch='one')
    return elapsedTime(time.time(), int(linfo[0]))


def whenlastplayerall():
    instances = dbquery("SELECT name from instances")
    a = 0
    for each in instances:
        lastone = dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC" % (each[0],), db='statsdb', fetch='one')
        if a == 0:
            lastdate = lastone[0]
        else:
            if lastone[0] > lastdate:
                lastdate = lastone[0]
        a += 1
    if lastdate < time.time() - 300:
        return elapsedTime(time.time(), int(lastdate))
    else:
        return 'Now'


m_serverinfo = api.model('serverinfo', {
    'hostname': fields.String,
    'instance': fields.String(attribute='name'),
    'playersonline': playerson(attribute='name'),
    'lastplayeronline': whenlastplayer(attribute='name'),
    'lastrestart': elapsedtime(attribute='lastrestart'),
    'restartreason': fields.String,
    'lastdinowipe': elapsedtime(attribute='lastdinowipe'),
    'isrestarting': fields.String(attribute='needsrestart'),
    'inevent': svrinevent(attribute='inevent'),
    'eventid': fields.Integer(attribute='inevent'),
    'lastvote': elapsedtime(attribute='lastvote'),
    'arkversion': fields.String,
    'config_ver': fields.Integer(attribute='cfgver'),
    'restartcountdown': fields.Integer,
    'isonline': int2bool(attribute='isup'),
    'islistening': int2bool(attribute='islistening'),
    'isrunning': int2bool(attribute='isrunning'),
    'lastcheck': elapsedtime(attribute='uptimestamp'),
    'uptime': fields.Integer,
    'rank': fields.Integer,
    'score': fields.Integer,
    'votes': fields.Integer,
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
    alldata = dbquery("PRAGMA table_info('%s')" % (mtable,))
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
            return {'message': 'Not Authorized'}, 401
        pkeys = dbquery("SELECT * FROM players WHERE apikey = '%s'" % (token,), fmt='dict', fetch='one')
        if pkeys is None:
            apilog.warning(f'API request invalid token: {token}')
            return {'message': 'Invalid Token'}, 401
        if pkeys['banned'] == 'True':
            apilog.warning(f'API request from banned player: {pkeys[0]} token: {token}')
            return {'message': 'You are Banned'}, 401
        apilog.info(f'API request granted for player: {pkeys["playername"]} steamid: {pkeys["steamid"]}')
        return f(*args, **kwargs)
    return decorated


@webapi.route('/admin/broadcast')
class Broadcast(Resource):
    @api.doc(security='apikey')
    @token_required
    def post(self):
        pass


@webapi.route('/admin/servermessage')
class Message(Resource):
    @api.doc(security='apikey')
    @token_required
    def post(self):
        pass


@webapi.route('/admin/playermessage')
class DirectMessage(Resource):
    @api.doc(security='apikey')
    @token_required
    def post(self):
        pass


@api.route('/players/online')
class PlayersOnline(Resource):
    # @api.doc(security='apikey')
    # @token_required
    def get(self):
        nap = []
        pcnt = 0
        pps = dbquery("SELECT playername FROM players WHERE lastseen > %s ORDER BY lastseen" % (Now(fmt='epoch') - 40,))
        for each in pps:
            pcnt += 1
            nap.append(each[0])
        return {'players': pcnt, 'names': nap}


@api.route('/servers/status')
class ServerStatus(Resource):
    # @api.doc(security='apikey')
    # @token_required
    def get(self):
        nap = []
        insts = dbquery("SELECT * FROM instances", fmt='dict')
        for inst in insts:
            if inst['isup'] == 1:
                if inst['needsrestart'] == 1:
                    status = 'restarting'
                else:
                    status = "online"
            else:
                status = "offline"
            nap.append(status)
        return nap


@api.route('/players')
class Players(Resource):
    @api.doc(security='apikey')
    @token_required
    def get(self):
        nap = []
        pcnt = 0
        pps = dbquery("SELECT playername FROM players ORDER BY playername")
        for each in pps:
            pcnt += 1
            nap.append(each[0])
        return {'players': pcnt, 'names': nap}


@api.route('/servers')
class Servers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    def get(self):
        nap = []
        qinst = dbquery("SELECT name FROM instances")
        scnt = 0
        for each in qinst:
            scnt += 1
            nap.append(each[0])
        return {'servers': scnt, 'names': nap}


@api.route('/servers/info')
class ServerInfo(Resource):
    # @api.doc(security='apikey')
    # @token_required
    @api.expect(serverquery)
    @api.marshal_with(m_serverinfo)
    def post(self):
        sname = api.payload['servername']
        if sname is not None or sname != 'string':
            q_server = dbquery("SELECT * FROM instances WHERE name = '%s'" % (sname,))
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
        instr = dbquery("SELECT name from instances")
        cluster = {}
        statsinst = []
        np, oplayers = howmanyonline()
        cluster['numberonline'] = np
        cluster['lastplayeronline'] = whenlastplayerall()
        cluster['playersonline'] = oplayers
        cluster['newplayers'] = {'lastday': newplayers('daily'), 'lastweek': newplayers('weekly'), 'lastmonth': newplayers('monthly')}
        cluster['inlottery'] = isinlottery()
        for each in instr:
            nap = {}
            nt, ny = howmanyonlinesvr(each[0])
            nap = {'name': each[0], 'status': serverstatus(each[0]), 'numberonline': nt, 'lastplayeronline': whenlastplayersvr(each[0]), 'playersonline': ny}
            statsinst.append(nap)
        if not iseventtime():
            cluster['inevent'] = 'false'
        else:
            eventinfo = getcurrenteventinfo()
            cluster['inevent'] = 'true'
            cluster['eventtitle'] = eventinfo[4]
        cluster['instances'] = statsinst

        return (cluster), 201


@api.route('/cluster/stats')
class ClusterStats(Resource):
    # @api.doc(security='apikey')
    # @token_required
    # @api.marshal_with(m_clusterinfo)
    def get(self):
        instr = dbquery("SELECT name from instances")
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
    @api.doc(security='apikey')
    @token_required
    def get(self):
        newnap = []
        supernap = {}
        try:
            q_player = dbquery("SELECT * FROM players WHERE banned != NULL")
            banlist = dbquery("SELECT * FROM banlist")
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


@api.route('/players/info')
class PlayerInfo(Resource):
    @api.doc(security='apikey')
    @token_required
    @api.expect(playerquery)
    @api.marshal_with(m_fullplayerinfo)
    def post(self):
        pname = api.payload['playername']
        steamid = api.payload['steamid']
        if pname is not None or pname != 'string':
            q_player = dbquery("SELECT * FROM players WHERE playername = '%s'" % (pname,))
        elif steamid is not None or steamid != 0:
            q_player = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,))
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
    # @api.marshal_with(m_fullplayerinfo)
    def get(self):
        nap = []
        try:
            q_player = dbquery("SELECT playername FROM players ORDER BY firstseen DESC LIMIT 10")
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        for each in q_player:
            nap.append(each[0])
        return {'names': nap}


@api.route('/players/topplaytime')
class TopPlayers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    # @api.marshal_with(m_minplayerinfo)
    def get(self):
        nap = []
        try:
            q_player = dbquery("SELECT playername FROM players ORDER BY playedtime DESC LIMIT 10")
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        try:
            for each in q_player:
                nap.append(each[0])
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return {'names': nap}


@api.route('/players/hitandruns')
class HNRPlayers(Resource):
    # @api.doc(security='apikey')
    # @token_required
    # @api.marshal_with(m_fullplayerinfo)
    def get(self):
        nap = []
        cnt = 0
        try:
            q_player = dbquery("SELECT * FROM players WHERE playedtime < 3600 ORDER BY playedtime DESC", fmt='dict')
        except:
            apilog.critical(f'error in retreiving info from db for api request', exc_info=True)
        try:
            for each in q_player:
                if time.time() - int(each['lastseen']) > 259200:
                    cnt += 1
                    nap.append(each['playername'])
        except:
            apilog.critical(f'error in calculating api request', exc_info=True)
        return {'players': cnt, 'names': nap}


@api.route('/cluster/lottery/current')
class ClusterLottery(Resource):
    @api.doc(security='apikey')
    @token_required
    @api.marshal_with(m_clottery)
    def get(self):
        try:
            current_lotto = dbquery("SELECT * FROM lotteryinfo WHERE winner == 'Incomplete'")
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
    @api.doc(security='apikey')
    @token_required
    @api.marshal_with(m_lotteryplayers)
    def get(self):
        try:
            lottowinners = dbquery("SELECT * FROM players ORDER BY lottowins DESC, lotterywinnings DESC LIMIT 10")
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
    @api.doc(security='apikey')
    @token_required
    @api.marshal_with(m_lottery)
    def get(self):
        try:
            lhist = dbquery("SELECT * FROM lotteryinfo WHERE winner != 'Incomplete' ORDER BY id DESC")
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


@webapi.route('/cluster/lottery/start')
class StartLottery(Resource):
    @api.doc(security='apikey')
    @api.expect(lotteryquery)
    @token_required
    def post(self):
        afetch = dbquery("SELECT * FROM lotteryinfo WHERE winner == 'Incomplete'")
        if not afetch:
            try:
                bip = api.payload['buyinpoints'] * 10
                lottoends = datetime.fromtimestamp(time.time() + (3600 * int(api.payload['length']))).strftime('%a, %b %d %I:%M%p')
                dbupdate("INSERT INTO lotteryinfo (type,payoutitem,timestamp,buyinpoints,lengthdays,players,winner) VALUES ('%s','%s','%s','%s','%s',0,'Incomplete')" % ('points', bip, time.time(), api.payload['buyinpoints'], api.payload['length']))
                return {'message': 'Lottery Started', 'payout': bip, 'buyinpoints': api.payload['buyinpoints'], 'lotterylength': api.payload['length'], 'lotteryends': lottoends}
            except:
                return {'message': 'Error starting lottery'}
        else:
            return {'message': 'Error starting lottery. A lottery is already running'}


@api.route('/players/expired')
class ExpiredPlayers(Resource):
    @api.doc(security='apikey')
    @token_required
    @api.marshal_with(m_fullplayerinfo)
    def get(self):
        newnap = []
        try:
            q_player = dbquery("SELECT * FROM players WHERE lastseen < '%s' ORDER BY lastseen ASC" % (time.time() - 2592000,))
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
