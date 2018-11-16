from active_alchemy import ActiveAlchemy
from datetime import datetime, timedelta
from flask import Flask, render_template, Response, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField
from wtforms.validators import InputRequired, Email, Length
import sys
sys.path.append('/home/ark/pyark')
from modules.configreader import webui_ip, webui_port, webui_debug, psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb
from modules.dbhelper import dbquery, dbupdate
from modules.instances import instancelist, isinstanceup, isinrestart, restartinstance, getlog, iscurrentconfig, serverchat
from modules.players import getplayersonline, getlastplayersonline, isplayerbanned, getplayer, banunbanplayer, isplayeronline, isplayerold, kickplayer
from modules.timehelper import elapsedTime, Now, playedTime, epochto, Secs, datetimeto
from lottery import isinlottery, getlotteryplayers, getlotteryendtime
import json
sys.path.append('/home/ark/pyark/webui')
app = Flask(__name__)
app.config['SECRET_KEY'] = '4CZywb8pQMxNCwB25TCpxYay'

db = ActiveAlchemy(f"postgresql+pg8000://{psql_user}:{psql_pw}@{psql_host}:{psql_port}/{psql_db}", app=app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class users(UserMixin, db.Model):
    username = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(80))
    email = db.Column(db.String(50), unique=True)


@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))


class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')


class LotteryForm(FlaskForm):
    buyinpoints = IntegerField('buyinpoints', validators=[InputRequired()])
    length = IntegerField('length', validators=[InputRequired()])


class MessageForm(FlaskForm):
    message = StringField('message', validators=[InputRequired(), Length(min=1, max=30)])


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
def _getplayer():
    def ui_getplayer(playername):
        return dbquery("SELECT * FROM players WHERE playername = '%s'" % (playername,), fmt='dict', fetch='one')
    return dict(ui_getplayer=ui_getplayer)


@app.context_processor
def _getlotteryplayers():
    def ui_getlotteryplayers(fmt='list'):
        return dbquery("SELECT playername FROM lotteryplayers", fmt=fmt, fetch='all', single=True)
    return dict(ui_getlotteryplayers=ui_getlotteryplayers)


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
def _iscurrentconfig():
    def ui_iscurrentconfig(inst):
        return iscurrentconfig(inst)
    return dict(ui_iscurrentconfig=ui_iscurrentconfig)


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
        retime = dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1" % (inst,), db='statsdb', fetch='one')[0]
        if datetime.now() - retime > timedelta(seconds=300):
            return f'{elapsedTime(Now(), datetimeto(retime, "epoch"))} ago'
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


def setannouncement(msg):
    if msg != '':
        dbupdate("UPDATE general SET announce = '%s'" % (msg,))
    else:
        dbupdate("UPDATE general SET announce = NULL")


def getlastlottery():
    return dbquery("SELECT * FROM lotteryinfo WHERE winner != 'Incomplete' ORDER BY timestamp DESC", fmt='dict', fetch='one')


def getcurrentlottery():
    return dbquery("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'", fmt='dict', fetch='one')


def getcurrentevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND startime < '%s' ORDER BY endtime DESC" % (Now(),), fmt='dict', fetch='one')


def getfutureevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND startime > '%s' ORDER BY endtime DESC" % (Now(),), fmt='dict', fetch='one')


def startthelottery(buyin, length):
    litm = str(buyin * 10)
    # lottostart = datetime.fromtimestamp(Now() + (3600 * int(length))).strftime('%a, %b %d %I:%M%p')
    dbupdate("INSERT INTO lotteryinfo (type,payoutitem,timestamp,buyinpoints,lengthdays,players,winner,announced) VALUES ('%s','%s','%s','%s','%s',0,'Incomplete',False)" % ('points', litm, Now(), buyin, length))


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


@app.route('/', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = users.query().filter_by(username=form.username.data).first()
        if user:
            if form.password.data == user.password:
                login_user(user, remember=form.remember.data)
                return redirect(url_for('dashboard'))
        flash(u'Invalid Login', 'error')
        return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/dashboard', methods=['POST', 'GET'])
@login_required
def dashboard():
    if request.method == 'POST':
        setannouncement(request.form["message"])
        flash(f'Login Announcement Set', 'info')
        return redirect(url_for('dashboard'))
    return render_template('dashboard.html', loginname=current_user.username, instances=instancelist())


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(u'You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/serverinfo/<instance>')
@login_required
def serverinfo(instance):
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/playersearch', methods=['POST', 'GET'])
@login_required
def result():
    if request.method == 'POST':
        return render_template("playerinfo.html", playerinfo=getplayer(playername=request.form['player'].lower(), fmt='dict'))


@app.route('/startlottery', methods=['POST', 'GET'])
@login_required
def startlottery():
    form = LotteryForm()
    if form.validate_on_submit():
        startthelottery(form.buyinpoints.data, form.length.data)
        flash(u'New Lottery has been Started', 'info')
        return redirect(url_for('_lottery'))
    return render_template('startlottery.html', form=form)


@app.route('/server/sendchat/<server>', methods=['POST'])
@login_required
def sendchat(server):
    form = MessageForm()
    if form.validate_on_submit():

        flash(f'Message sent to {server.title()}', 'info')
        return redirect(url_for('_chatlog', instance=server))
    flash(f'Message failed to {server.title()}', 'error')
    return redirect(url_for('_chatlog', instance=server))


@app.route('/playerinfo/<player>', methods=['POST', 'GET'])
@login_required
def playerinfo(player):
    if request.method == 'POST':
        serverchat(request.form["message"], whosent=player.lower(), inst=getplayer(playername=player.lower(), fmt='dict')['server'], private=True)
        flash(f'Message Sent', 'info')
        return redirect(url_for('playerinfo', player=player))
    return render_template('playerinfo.html', playerinfo=getplayer(playername=player.lower(), fmt='dict'))


@app.route('/playerinfo')
@login_required
def _players():
    return render_template('playerselect.html', players=getplayernames(), bannedplayers=getbannedplayers(), expiredplayers=getexpiredplayers(), newplayers=getnewplayers('week'))


@app.route('/events')
@login_required
def _events():
    return render_template('eventinfo.html', lastevent=getlastevent(), currentevent=getcurrentevent(), futureevent=getfutureevent())


@app.route('/lottery')
@login_required
def _lottery():
    return render_template('lotteryinfo.html', lastlottery=getlastlottery(), currentlottery=getcurrentlottery())


@app.route('/stats')
@login_required
def _stats():
    return render_template('stats.html')


@app.route('/bantoggle/<steamid>')
@login_required
def _bantoggle(steamid):
    if isplayerbanned(steamid=steamid):
        banunbanplayer(steamid=steamid, ban=False)
        flash(u'Player has been Un-Banned', 'success')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))
    else:
        banunbanplayer(steamid=steamid, ban=True)
        flash(u'Player has been BANNED!', 'error')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@app.route('/kickplayer/<steamid>/<instance>')
@login_required
def _kickplayer(steamid, instance):
    kickplayer(instance, steamid)
    flash(u'Kicking player from %s' % (instance,), 'info')
    return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@app.route('/server/restart/<instance>')
@login_required
def _restartinstance(instance):
    restartinstance(instance, cancel=False)
    flash(u'Restarting Server', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/server/cancelrestart/<instance>')
@login_required
def _cancelrestartinstance(instance):
    restartinstance(instance, cancel=True)
    flash(u'Cencelling Server Restart', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/server/chatlog/<instance>', methods=['POST', 'GET'])
@login_required
def _chatlog(instance):
    if request.method == 'POST':
        serverchat(request.form["message"], inst=instance)
        flash(f'Message Sent to {instance.title()}', 'info')
        return redirect(url_for('_chatlog', instance=instance))
    chatlog = getlog(instance, 'chat')
    return render_template('serverchatlog.html', serverinfo=instanceinfo(instance), chatlog=chatlog[::-1])


if __name__ == '__main__':
    app.run(host=webui_ip, port=51501, debug=webui_debug)
