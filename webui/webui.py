from flask import Flask, render_template, Response, request
import sys
sys.path.append('/home/ark/pyark')
from modules.configreader import webui_ip, webui_port, webui_debug
from modules.dbhelper import dbquery
from modules.instances import instancelist, isinstanceup, isinrestart
from modules.players import getplayersonline, getlastplayersonline
from modules.timehelper import elapsedTime, Now, playedTime
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


def instanceinfo(inst):
    return dbquery("SELECT * FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='dict', fetch='one')


def getplayerinfo(player):
    return dbquery("SELECT * FROM players WHERE playername = '%s'" % (player.lower(),), fmt='dict', fetch='one')


def getplayernames():
    return dbquery("SELECT playername FROM players ORDER BY playername ASC", fmt='list', single=True)


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
        "background_color": "#3367D6",
        "display": "standalone",
        "scope": "/",
        "theme_color": "#3367D6"
    })
    return Response(data, mimetype='application/x-web-app-manifest+json')


@app.route('/')
def dashboard():
    return render_template('dashboard.html', instances=instancelist())


@app.route('/serverinfo/<instance>')
def serverinfo(instance):
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance), instance=instance)


@app.route('/playerinfo', methods = ['POST', 'GET'])
def result():
   if request.method == 'POST':
      return render_template("playerinfo.html", playerinfo=getplayerinfo(request.form['player']))


@app.route('/playerinfo/<player>')
def playerinfo(player):
    return render_template('playerinfo.html', playerinfo=getplayerinfo(player))


@app.route('/players')
def _players():
    return render_template('playerselect.html', players=getplayernames())


if __name__ == '__main__':
    app.run(host=webui_ip, port=webui_port, debug=webui_debug)
