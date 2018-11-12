from flask import Flask, render_template, Response, request
import sys
sys.path.append('/home/ark/pyark')
from modules.configreader import webui_ip, webui_port, webui_debug
from modules.dbhelper import dbquery
from modules.instances import instancelist, isinstanceup, isinrestart, restartinstance, getlog
from modules.players import getplayersonline, getlastplayersonline, isplayerbanned, getplayer, banunbanplayer, isplayeronline, isplayerold, kickplayer
from modules.timehelper import elapsedTime, Now, playedTime, epochto, Secs
from lottery import isinlottery, getlotteryplayers, getlotteryendtime
import json
sys.path.append('/home/ark/pyark/webui')
app = Flask(__name__)


@app.context_processor
def database_processor():
    def ui_getplayersonline(instance, fmt):
        return getplayersonline(instance, fmt=fmt, case='title')
    return dict(ui_getplayersonline=ui_getplayersonline)


@app.context_processor
def database_processor2():
    def ui_getlastplayersonline(instance, fmt):
        return getlastplayersonline(instance, fmt=fmt, case='title')
    return dict(ui_getlastplayersonline=ui_getlastplayersonline)


@app.context_processor
def database_processor3():
    def ui_getplayerserver(player):
        return dbquery("SELECT server FROM players WHERE playername = '%s'" % (player.lower(),), fmt='string', fetch='one')
    return dict(ui_getplayerserver=ui_getplayerserver)


@app.context_processor
def database_processor4():
    def ui_getplayerlasttime(player):
        return elapsedTime(Now(), int(dbquery("SELECT lastseen FROM players WHERE playername = '%s'" % (player.lower(),), fmt='string', fetch='one')))
    return dict(ui_getplayerlasttime=ui_getplayerlasttime)


@app.context_processor
def database_processor5():
    def ui_getinstver(inst):
        return dbquery("SELECT arkversion FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    return dict(ui_getinstver=ui_getinstver)


@app.context_processor
def database_processor6():
    def ui_getrestartleft(inst):
        return dbquery("SELECT restartcountdown FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    return dict(ui_getrestartleft=ui_getrestartleft)


@app.context_processor
def database_processor7():
    def ui_isinlottery():
        return isinlottery()
    return dict(ui_isinlottery=ui_isinlottery)


@app.context_processor
def database_processor8():
    def ui_getlotteryplayers(fmt):
        return getlotteryplayers(fmt=fmt)
    return dict(ui_getlotteryplayers=ui_getlotteryplayers)


@app.context_processor
def database_processor9():
    def ui_getlotteryendtime():
        return getlotteryendtime()
    return dict(ui_getlotteryendtime=ui_getlotteryendtime)


@app.context_processor
def database_processor10():
    def ui_isinstanceup(inst):
        return isinstanceup(inst)
    return dict(ui_isinstanceup=ui_isinstanceup)


@app.context_processor
def database_processor11():
    def ui_isinrestart(inst):
        return isinrestart(inst)
    return dict(ui_isinrestart=ui_isinrestart)


@app.context_processor
def _elapsedTime():
    def ui_elapsedTime(etime):
        return elapsedTime(Now(), int(etime))
    return dict(ui_elapsedTime=ui_elapsedTime)


@app.context_processor
def _playedTime():
    def ui_playedTime(etime):
        return playedTime(int(etime))
    return dict(ui_playedTime=ui_playedTime)


@app.context_processor
def _epochto():
    def ui_epochto(epoch, fmt=''):
        return epochto(int(epoch))
    return dict(ui_epochto=ui_epochto)


@app.context_processor
def _isbanned():
    def ui_isbanned(steamid):
        return isplayerbanned(steamid=steamid)
    return dict(ui_isbanned=ui_isbanned)


@app.context_processor
def _isplayeronline():
    def ui_isplayeronline(steamid):
        return isplayeronline(steamid=steamid)
    return dict(ui_isplayeronline=ui_isplayeronline)


@app.context_processor
def _isplayerold():
    def ui_isplayerold(steamid):
        return isplayerold(steamid=steamid)
    return dict(ui_isplayerold=ui_isplayerold)


@app.context_processor
def _length():
    def ui_len(alist):
        return len(alist)
    return dict(ui_len=ui_len)


@app.context_processor
def _lastactive():
    def ui_lastactive(inst):
        retime = int(dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1" % (inst,), db='statsdb', fetch='one', fmt='string'))
        if Now() - retime > 300:
            return f'{elapsedTime(Now(), retime)} ago'
        else:
            return 'Now'
    return dict(ui_lastactive=ui_lastactive)


@app.context_processor
def _playerlastactive():
    def ui_playerlastactive(lastseen):
        if Now() - lastseen > 40:
            return f'{elapsedTime(Now(), lastseen)} ago'
        else:
            return 'Now'
    return dict(ui_playerlastactive=ui_playerlastactive)


@app.context_processor
def _getannouncement():
    def ui_getannouncement():
        return dbquery("SELECT announce FROM general ", fmt='string', fetch='one')
    return dict(ui_getannouncement=ui_getannouncement)


def instanceinfo(inst):
    return dbquery("SELECT * FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='dict', fetch='one')


def getplayernames():
    return dbquery("SELECT playername FROM players ORDER BY playername ASC", fmt='list', single=True)


def getbannedplayers():
    return dbquery("SELECT playername FROM players WHERE banned != '' ORDER BY playername ASC", fmt='list', single=True)



def getexpiredplayers():
    return dbquery("SELECT playername FROM players WHERE banned = '' AND lastseen < '%s' ORDER BY playername ASC" % (Now() - Secs['month'],), fmt='list', single=True)


def getnewplayers(atime):
    return dbquery("SELECT playername FROM players WHERE banned = '' AND firstseen > '%s' ORDER BY playername ASC" % (Now() - Secs[atime],), fmt='list', single=True)


def getlastevent():
    return dbquery("SELECT * FROM events WHERE completed = 1 ORDER BY endtime DESC", fmt='dict', fetch='one')


def getcurrentevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND startime < '%s' ORDER BY endtime DESC" % (Now(),), fmt='dict', fetch='one')


def getfutureevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND startime > '%s' ORDER BY endtime DESC" % (Now(),), fmt='dict', fetch='one')


@app.context_processor
def _getlog():
    def ui_getlog(instance, wlog):
        chatlog = getlog(instance, wlog)
        return chatlog[::-1]
    return dict(ui_getlog=ui_getlog)


@app.route('/manifest.json')
def manifest():
    data = json.dumps({
        "short_name": "Galaxy",
        "name": "Galaxy Cluster",
        "icons": [
            {
                "src": "/static/images/galaxy192.png",
                "type": "image/png",
                "sizes": "192x192"
            }
        ],
        "start_url": "/",
        "background_color": "#000000",
        "display": "standalone",
        "scope": "/",
        "theme_color": "#000000"
    })
    return Response(data, mimetype='application/x-web-app-manifest+json')


@app.route('/')
def dashboard():
    return render_template('dashboard.html', instances=instancelist())


@app.route('/serverinfo/<instance>')
def serverinfo(instance):
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/playersearch', methods=['POST', 'GET'])
def result():
    if request.method == 'POST':
        return render_template("playerinfo.html", playerinfo=getplayer(playername=request.form['player'].lower(), fmt='dict'))


@app.route('/playerinfo/<player>')
def playerinfo(player):
    return render_template('playerinfo.html', playerinfo=getplayer(playername=player.lower(), fmt='dict'))


@app.route('/playerinfo')
def _players():
    return render_template('playerselect.html', players=getplayernames(), bannedplayers=getbannedplayers(), expiredplayers=getexpiredplayers(), newplayers=getnewplayers('week'))


@app.route('/events')
def _events():
    return render_template('eventinfo.html', lastevent=getlastevent(), currentevent=getcurrentevent(), futureevent=getfutureevent())


@app.route('/bantoggle/<steamid>')
def _bantoggle(steamid):
    if isplayerbanned(steamid=steamid):
        banunbanplayer(steamid=steamid, ban=False)
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))
    else:
        banunbanplayer(steamid=steamid, ban=True)
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'), alertmessage='has been banned from cluster')


@app.route('/kickplayer/<steamid>/<instance>')
def _kickplayer(steamid, instance):
    kickplayer(instance, steamid)
    return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'), alertmessage='has been kicked from server')


@app.route('/server/restart/<instance>')
def _restartinstance(instance):
    restartinstance(instance, cancel=False)
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance), alertmessage='server is set to restart')


@app.route('/server/cancelrestart/<instance>')
def _cancelrestartinstance(instance):
    restartinstance(instance, cancel=True)
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance), alertmessage='server restart canceled')


@app.route('/server/chatlog/<instance>')
def _chatlog(instance):
    chatlog = getlog(instance, 'chat')
    return render_template('serverchatlog.html', serverinfo=instanceinfo(instance), chatlog=chatlog[::-1])


if __name__ == '__main__':
    app.run(host=webui_ip, port=webui_port, debug=webui_debug)
