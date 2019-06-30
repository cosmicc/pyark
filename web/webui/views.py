from datetime import datetime, timedelta, time, date
from flask import render_template, Response, request, redirect, url_for, flash, Blueprint
from flask_security import login_required, logout_user, current_user, roles_required, RegisterForm, SQLAlchemyUserDatastore
from flask_security.utils import hash_password
from flask_wtf import FlaskForm
from itertools import chain, zip_longest
from lottery import isinlottery, getlotteryplayers, getlotteryendtime
from modules.configreader import psql_statsdb, psql_user, psql_host, psql_pw, psql_port
from modules.dbhelper import dbquery, dbupdate
from modules.instances import instancelist, isinstanceup, isinrestart, restartinstance, getlog, iscurrentconfig, serverchat, enableinstance, disableinstance
from modules.messages import validatelastsent, validatenumsent, getmessages, sendmessage
from modules.players import getplayersonline, getlastplayersonline, isplayerbanned, getplayer, banunbanplayer, isplayeronline, isplayerold, kickplayer
from modules.timehelper import elapsedTime, Now, playedTime, epochto, Secs, datetimeto, joinedTime
from wtforms import StringField, IntegerField
from wtforms.validators import InputRequired, Length
from clusterevents import getcurrenteventtitle, iseventtime
from ..models import User, Role
from ..database import db
import json
import pandas as pd
import psycopg2
import pytz

webui = Blueprint('webui', __name__)

user_datastore = SQLAlchemyUserDatastore(db, User, Role)


class ExtendedRegisterForm(RegisterForm):
    timezone = StringField('Time Zone')


# @app.before_first_request
# def initdb():
# db.create_all()
# user_datastore.find_or_create_role(name='admin', description='Administrator')
# user_datastore.find_or_create_role(name='player', description='Player')
# user_datastore.add_role_to_user('admin', 'admin')
# db.session.commit()


class LotteryForm(FlaskForm):
    buyinpoints = IntegerField('buyinpoints', validators=[InputRequired()])
    length = IntegerField('length', validators=[InputRequired()])

class EventForm(FlaskForm):
    buyinpoints = IntegerField('buyinpoints', validators=[InputRequired()])
    length = IntegerField('length', validators=[InputRequired()])


class MessageForm(FlaskForm):
    message = StringField('message', validators=[InputRequired(), Length(min=1, max=30)])


@webui.context_processor
def _gettimezones():
    def ui_gettimezones():
        return pytz.common_timezones
    return dict(ui_gettimezones=ui_gettimezones)


@webui.context_processor
def _utctolocal():
    def ui_utctolocal(utc_dt, short=False):
        if utc_dt is None:
            return 'Never'
        local_tz = pytz.timezone(current_user.timezone)
        newdt = pytz.utc.localize(utc_dt).astimezone(local_tz)
        if not short:
            return newdt.strftime('%m-%d-%Y %-I:%M %p')
        else:
            return newdt.strftime('%m-%d %-I:%M %p')
    return dict(ui_utctolocal=ui_utctolocal)


@webui.context_processor
def _Now():
    def Now():
        return datetime.now()
    return dict(Now=Now)


@webui.context_processor
def _str2time():
    def ui_str2time(strtime):
        return datetime.strptime(strtime, '%m-%d %I:%M%p')
    return dict(ui_str2time=ui_str2time)


@webui.context_processor
def _getmessages():
    def ui_getmessages(steamid, fmt, sent=False):
        if not sent:
            return dbquery("SELECT * FROM messages WHERE to_player = '%s'" % (steamid,), fmt=fmt)
        else:
            return dbquery("SELECT * FROM messages WHERE from_player = '%s'" % (steamid,), fmt=fmt)
    return dict(ui_getmessages=ui_getmessages)


@webui.context_processor
def database_processor():
    def ui_getplayersonline(instance, fmt):
        return getplayersonline(instance, fmt=fmt, case='title')
    return dict(ui_getplayersonline=ui_getplayersonline)


@webui.context_processor
def database_processor2():
    def ui_getlastplayersonline(instance, fmt):
        return getlastplayersonline(instance, fmt=fmt, case='title')
    return dict(ui_getlastplayersonline=ui_getlastplayersonline)


@webui.context_processor
def database_processor3():
    def ui_getplayerserver(player):
        return dbquery("SELECT server FROM players WHERE playername = '%s'" % (player.lower(),), fmt='string', fetch='one')
    return dict(ui_getplayerserver=ui_getplayerserver)


@webui.context_processor
def database_processor4():
    def ui_getplayerlasttime(player):
        return elapsedTime(Now(), int(dbquery("SELECT lastseen FROM players WHERE playername = '%s'" % (player.lower(),), fmt='string', fetch='one')))
    return dict(ui_getplayerlasttime=ui_getplayerlasttime)


@webui.context_processor
def _getplayer():
    def ui_getplayer(playername, steamid=False):
        if not steamid:
            return dbquery("SELECT * FROM players WHERE playername = '%s'" % (playername,), fmt='dict', fetch='one')
        else:
            return dbquery("SELECT * FROM players WHERE steamid = '%s'" % (playername,), fmt='dict', fetch='one')
    return dict(ui_getplayer=ui_getplayer)


@webui.context_processor
def _getlotteryplayers():
    def ui_getlotteryplayers(fmt='list'):
        return dbquery("SELECT playername FROM lotteryplayers", fmt=fmt, fetch='all', single=True)
    return dict(ui_getlotteryplayers=ui_getlotteryplayers)


@webui.context_processor
def database_processor5():
    def ui_getinstver(inst):
        return dbquery("SELECT arkversion FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    return dict(ui_getinstver=ui_getinstver)


@webui.context_processor
def database_processor6():
    def ui_getrestartleft(inst):
        return dbquery("SELECT restartcountdown FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    return dict(ui_getrestartleft=ui_getrestartleft)


@webui.context_processor
def database_processor7():
    def ui_isinlottery():
        return isinlottery()
    return dict(ui_isinlottery=ui_isinlottery)


@webui.context_processor
def _isinevent():
    def ui_isinevent():
        return iseventtime()
    return dict(ui_isinevent=ui_isinevent)


@webui.context_processor
def database_processor8():
    def ui_getlotteryplayers(fmt):
        return getlotteryplayers(fmt=fmt)
    return dict(ui_getlotteryplayers=ui_getlotteryplayers)


@webui.context_processor
def database_processor9():
    def ui_getlotteryendtime():
        return getlotteryendtime()
    return dict(ui_getlotteryendtime=ui_getlotteryendtime)


@webui.context_processor
def database_processor10():
    def ui_isinstanceup(inst):
        return isinstanceup(inst)
    return dict(ui_isinstanceup=ui_isinstanceup)


@webui.context_processor
def database_processor11():
    def ui_isinrestart(inst):
        return isinrestart(inst)
    return dict(ui_isinrestart=ui_isinrestart)


@webui.context_processor
def _iscurrentconfig():
    def ui_iscurrentconfig(inst):
        return iscurrentconfig(inst)
    return dict(ui_iscurrentconfig=ui_iscurrentconfig)


@webui.context_processor
def _elapsedTime():
    def ui_elapsedTime(etime):
        if isinstance(etime, int):
            return elapsedTime(Now(), etime)
        elif isinstance(etime, str):
            return elapsedTime(Now(), int(etime))
        elif isinstance(etime, date):
            ftime = datetime.combine(etime, time.min)
            gtime = datetimeto(ftime, fmt='epoch')
            return elapsedTime(Now(), int(gtime))
    return dict(ui_elapsedTime=ui_elapsedTime)


@webui.context_processor
def _playedTime():
    def ui_playedTime(etime):
        return playedTime(int(etime))
    return dict(ui_playedTime=ui_playedTime)


@webui.context_processor
def _joinedTime():
    def ui_joinedTime(etime):
        return joinedTime(Now() - int(etime))
    return dict(ui_joinedTime=ui_joinedTime)


@webui.context_processor
def _epochto():
    def ui_epochto(epoch, fmt=''):
        return epochto(int(epoch))
    return dict(ui_epochto=ui_epochto)


@webui.context_processor
def _isbanned():
    def ui_isbanned(steamid):
        return isplayerbanned(steamid=steamid)
    return dict(ui_isbanned=ui_isbanned)


@webui.context_processor
def _isplayeronline():
    def ui_isplayeronline(steamid):
        return isplayeronline(steamid=steamid)
    return dict(ui_isplayeronline=ui_isplayeronline)


@webui.context_processor
def _isplayerold():
    def ui_isplayerold(steamid):
        return isplayerold(steamid=steamid)
    return dict(ui_isplayerold=ui_isplayerold)


@webui.context_processor
def _length():
    def ui_len(alist):
        return len(alist)
    return dict(ui_len=ui_len)


@webui.context_processor
def _lastactive():
    def ui_lastactive(inst):
        retime = dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1" % (inst,), db='statsdb', fetch='one')[0]
        if datetime.now() - retime > timedelta(seconds=300):
            return f'{elapsedTime(Now(), datetimeto(retime, "epoch"))} ago'
        else:
            return 'Now'
    return dict(ui_lastactive=ui_lastactive)


@webui.context_processor
def _statpull():
    def ui_last24avg(inst, dtype):
        if dtype == 'chart1':
            hours = 24
            rate = 'H'
            tstr = '%-I%p'
        elif dtype == 'chart2':
            hours = 720
            rate = 'D'
            tstr = '%b %-d'
        elif dtype == 'chart3':
            hours = 4320
            rate = 'W'
            tstr = '%b %-d'
        conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        if inst == 'all':
            statavglist = []
            for each in instancelist():
                #print('processing instance: {}'.format(each))
                statlist = []
                navglist = []
                datelist = []
                c = conn.cursor()
                c.execute("SELECT * FROM {} WHERE date > '{}' ORDER BY date DESC".format(each, datetime.now() - timedelta(hours=hours)))
                alllist = c.fetchall()
                for y in alllist:
                    statlist.append(y[1])
                    datelist.append(y[0])
                if statavglist == []:
                    statavglist = statlist
                else:
                    navglist = [sum(pair) for pair in zip_longest(statlist, statavglist, fillvalue=0)]
                    statavglist = navglist
            c.close()
            conn.close()
            print('datelist: {}'.format(datelist))
            print('statavglist: {}'.format(statavglist))
            ret = list(zip_longest(datelist, statavglist))
            df = pd.DataFrame.from_records(ret, columns=['date', 'value'])
            df = df.set_index(pd.DatetimeIndex(df['date']))
        else:
            df = pd.read_sql("SELECT * FROM {} WHERE date > '{}' ORDER BY date DESC".format(inst, datetime.now() - timedelta(hours=hours)), conn, parse_dates=['date'], index_col='date')
            conn.close()
        df = df.tz_localize(tz='UTC')
        df = df.tz_convert(tz=current_user.timezone)
        df = df.resample(rate).mean()
        ndatelist = []
        print(df.to_string())
        for each in df.index:
            ndatelist.append(each.strftime(tstr))
        return (ndatelist, list(chain.from_iterable(df.values.round(1).tolist())))
    return dict(ui_last24avg=ui_last24avg)


@webui.context_processor
def _playerlastactive():
    def ui_playerlastactive(lastseen):
        if Now() - lastseen > 40:
            return f'{elapsedTime(Now(), lastseen)} ago'
        else:
            return 'Now'
    return dict(ui_playerlastactive=ui_playerlastactive)


@webui.context_processor
def _getannouncement():
    def ui_getannouncement():
        return dbquery("SELECT announce FROM general ", fmt='string', fetch='one')
    return dict(ui_getannouncement=ui_getannouncement)

@webui.context_processor
def _currenteventtitle():
    def ui_currenteventtitle():
        return getcurrenteventtitle()
    return dict(ui_currenteventtitle=ui_currenteventtitle)


@webui.context_processor
def _haswebaccount():
    def haswebaccount(steamid):
        webuser = User.query.filter_by(steamid=steamid).first()
        if not hasattr(webuser, 'email'):
            return False
        else:
            return True
    return dict(haswebaccount=haswebaccount)


def instances():
    return dbquery("SELECT name FROM instances", fmt='list', fetch='all')


def instanceinfo(inst):
    return dbquery("SELECT * FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='dict', fetch='one')


def getplayernames():
    return dbquery("SELECT playername FROM players ORDER BY playername ASC", fmt='list', single=True)


def getautoevents():
    return dbquery("SELECT title FROM autoevents", fmt='list', single=True)


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
    return dbquery("SELECT * FROM lotteryinfo WHERE completed = True ORDER BY startdate DESC", fmt='dict', fetch='one')


def getcurrentlottery():
    return dbquery("SELECT * FROM lotteryinfo WHERE completed = False", fmt='dict', fetch='one')


def getcurrentevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND starttime <= '%s'" % (Now(fmt='dtd'),), fmt='dict', fetch='one')


def getfutureevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND (starttime > '%s' OR starttime = '%s') ORDER BY endtime ASC" % (Now(fmt='dtd'),Now(fmt='dtd')), fmt='dict', fetch='one')


def startthelottery(buyin, length):
    litm = buyin * 20
    dbupdate("INSERT INTO lotteryinfo (payout,startdate,buyin,days,players,winner,announced,completed) VALUES ('%s','%s','%s','%s',0,'Incomplete',False,False)" % (litm, Now(fmt="dt"), buyin, length))


@webui.context_processor
def _getlog():
    def ui_getlog(instance, wlog):
        chatlog = getlog(instance, wlog)
        return chatlog[::-1]
    return dict(ui_getlog=ui_getlog)


@webui.route('/WBUI-standard.json')
def WBUI_standard():
    with open('/home/ark/shared/config/WBUI-standard.json') as json_file:
        rdata = json.load(json_file)
    data = json.dumps(rdata)
    return Response(data)


@webui.route('/WBUI-coliseum.json')
def WBUI_alt():
    with open('/home/ark/shared/config/WBUI-coliseum.json') as json_file:
        rdata = json.load(json_file)
    data = json.dumps(rdata)
    return Response(data)



@webui.route('/manifest.json')
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
    return Response(data, mimetype='application/x-web-app.manifest+json')

# @webui.errorhandler(403)
# def forbidden(error):
#    return render_template('error/403.html', title='Forbidden'), 403

# @webui.errorhandler(404)
# def page_not_found(error):
#    return render_template('error/404.html', title='Page Not Found'), 404

# @webui.errorhandler(500)
# def internal_server_error(error):
#    db.session.rollback()
#    return render_template('error/500.html', title='Server Error'), 500


@webui.route('/', methods=['POST', 'GET'])
@login_required
def dashboard():
    if request.method == 'POST':
        setannouncement(request.form["message"])
        flash(f'Login Announcement Set', 'info')
        return redirect(url_for('webui.dashboard'))
    return render_template('dashboard.html', loginname=current_user.email, instances=instancelist())


@webui.route('/logout')
@login_required
def logout():
    logout_user()
    flash(u'You have been logged out', 'info')
    return redirect(url_for('security.login'))


@webui.route('/serverinfo/<instance>')
@login_required
def serverinfo(instance):
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@webui.route('/playersearch', methods=['POST', 'GET'])
@login_required
def result():
    if request.method == 'POST':
        return render_template("playerinfo.html", playerinfo=getplayer(playername=request.form['player'].lower(), fmt='dict'))


@webui.route('/startlottery', methods=['POST', 'GET'])
@login_required
@roles_required('admin')
def startlottery():
    form = LotteryForm()
    if form.validate_on_submit():
        startthelottery(form.buyinpoints.data, form.length.data)
        flash(u'New Lottery has been Started', 'info')
        return redirect(url_for('webui._lottery'))
    return render_template('startlottery.html', form=form)

@webui.route('/startevent', methods=['POST', 'GET'])
@login_required
@roles_required('admin')
def startevent():
    if request.method == 'POST':
        eventname = request.form['eventname']
        startdate = request.form['startdate'].split(' GMT')[0]
        enddate = request.form['enddate'].split(' GMT')[0]
        edate = datetime.strptime(enddate, '%a %b %d %Y %H:%M:%S').date()
        sdate = datetime.strptime(startdate, '%a %b %d %Y %H:%M:%S').date()
        einfo = dbquery("SELECT * FROM autoevents WHERE title = '%s'" % (eventname,), fmt='dict', fetch='one')
        dbupdate("INSERT INTO events (completed, starttime, endtime, title, description, cfgfilesuffix) VALUES (0, '%s', '%s', '%s', '%s', '%s')" % (sdate, edate, einfo['title'], einfo['description'], einfo['cfgfilesuffix']))
        flash('New Event Added')
        return redirect(url_for('webui._events'))
    return render_template('startevent.html', autoevents=getautoevents())


@webui.route('/server/sendchat/<server>', methods=['POST'])
@login_required
@roles_required('admin')
def sendchat(server):
    form = MessageForm()
    if form.validate_on_submit():

        flash(f'Message sent to {server.title()}', 'info')
        return redirect(url_for('webui._chatlog', instance=server))
    flash(f'Message failed to {server.title()}', 'error')
    return redirect(url_for('webui._chatlog', instance=server))


@webui.route('/playerinfo/<player>', methods=['POST', 'GET'])
@login_required
def playerinfo(player):
    if request.method == 'POST':
        serverchat(request.form["message"], whosent=player.lower(), inst=getplayer(playername=player.lower(), fmt='dict')['server'], private=True)
        flash(f'Message Sent', 'info')
        return redirect(url_for('webui.playerinfo', player=player))
    return render_template('playerinfo.html', playerinfo=getplayer(playername=player.lower(), fmt='dict'))


@webui.route('/messages/delete/<messageid>', methods=['POST'])
@login_required
def deletemessage(messageid):
    if request.method == 'POST':
        miq = dbquery("SELECT * FROM messages WHERE id = '%s'" % (messageid,), fmt='dict', fetch='one')
        if miq['to_player'] == current_user.steamid:
            dbupdate("DELETE FROM messages WHERE id = '%s'" % (miq['id'],))
        else:
            flash(f'Access Denied', 'error')
        return render_template('messages.html', players=getplayernames())


@webui.route('/messages', methods=['POST', 'GET'])
@login_required
def messages():
    if request.method == 'POST':
        if request.form['player'] == getplayer(steamid=current_user.steamid, fmt='dict')['playername']:
            flash(f'You cannot send a message to yourself', 'error')
        elif request.form['message'] == '':
            flash(f'You cannot send a blank message', 'error')
        elif not validatelastsent(current_user.steamid):
            flash(f'You must wait before sending another message', 'error')
        elif not validatenumsent(current_user.steamid):
            flash(f"You cannot send more then 5 messages that haven't been read yet", 'error')
        else:
            sendmessage(current_user.steamid, getplayer(playername=request.form['player'], fmt='dict')['steamid'], request.form['message'])
            flash(f'Message Sent to {request.form["player"].title()}', 'info')
        return render_template('messages.html', players=getplayernames())
    return render_template('messages.html', players=getplayernames())


@webui.route('/webcreate/<steamid>', methods=['POST', 'GET'])
@login_required
@roles_required('admin')
def webcreate(steamid):
    if request.method == 'POST':
        user_datastore.create_user(email=request.form['email'], password=hash_password(request.form['password']), steamid=request.form['steamid'], timezone=request.form['timezone'])
        db.session.commit()
        flash(f'Web User Created', 'info')
        webuser = User.query.filter_by(steamid=steamid).first()
        return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
    return render_template('webcreate.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@webui.route('/changepass/<steamid>', methods=['POST', 'GET'])
@login_required
def changepass(steamid):
    if request.method == 'POST':
        if current_user.has_role('admin') or current_user.steamid == steamid:
            if request.form['password'] == "" or request.form['password_confirm'] == "":
                flash(f'Password cannot be blank', 'error')
                return redirect(url_for('webui.changepass', steamid=steamid))
            elif len(request.form['password']) < 7:
                flash(f'Password must be at least 7 characters long', 'error')
                return redirect(url_for('webui.changepass', steamid=steamid))
            elif request.form['password'] != request.form['password_confirm']:
                flash(f'Passwords do not match', 'error')
                return redirect(url_for('webui.changepass', steamid=steamid))
            elif request.form['password'] == request.form['password_confirm']:
                dbupdate("UPDATE web_users SET password = '%s' WHERE steamid = '%s'" % (hash_password(request.form['password']), steamid))
                flash(f'Password changed', 'success')
                webuser = User.query.filter_by(steamid=steamid).first()
                return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
    if current_user.has_role('admin') or current_user.steamid == steamid:
        return render_template('changepass.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@webui.route('/webinfo/<steamid>', methods=['POST', 'GET'])
@login_required
def webinfo(steamid):
    if request.method == 'POST':
        if request.form['btype'] == 'Update Settings':
            User.query.filter_by(steamid=steamid).update(dict(timezone=request.form["timezone"]))
            db.session.commit()
            flash(f'Settings Updated', 'success')
        elif request.form['btype'] == 'Toggle Active':
            user_datastore.activate_user(User.query.filter_by(email=request.form['email']).first())
            db.session.commit()
            flash(f'Toggled Account Access', 'success')
        elif request.form['btype'] == 'Change Password':
            return redirect(url_for('webui.changepass', steamid=steamid))
        webuser = User.query.filter_by(steamid=steamid).first()
        return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
    webuser = User.query.filter_by(steamid=steamid).first()
    if not hasattr(webuser, 'email'):
        flash(f'Player does not have a web account', 'warning')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))
    else:
        if current_user.has_role('admin') or current_user.steamid == steamid:
            return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
        else:
            flash(f'Invalid Access', 'error')
            return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@webui.route('/playerinfo')
@login_required
def _players():
    return render_template('playerselect.html', players=getplayernames(), bannedplayers=getbannedplayers(), expiredplayers=getexpiredplayers(), newplayers=getnewplayers('week'))


@webui.route('/events')
@login_required
def _events():
    return render_template('eventinfo.html', lastevent=getlastevent(), currentevent=getcurrentevent(), futureevent=getfutureevent())


@webui.route('/lottery')
@login_required
def _lottery():
    return render_template('lotteryinfo.html', lastlottery=getlastlottery(), currentlottery=getcurrentlottery())


@webui.route('/stats/<inst>')
@login_required
def _stats(inst):
    return render_template('stats.html', inst=inst)


@webui.route('/bantoggle/<steamid>')
@login_required
@roles_required('admin')
def _bantoggle(steamid):
    if isplayerbanned(steamid=steamid):
        banunbanplayer(steamid=steamid, ban=False)
        flash(u'Player has been Un-Banned', 'success')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))
    else:
        banunbanplayer(steamid=steamid, ban=True)
        flash(u'Player has been BANNED!', 'error')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@webui.route('/kickplayer/<steamid>/<instance>')
@login_required
@roles_required('admin')
def _kickplayer(steamid, instance):
    kickplayer(instance, steamid)
    flash(u'Kicking player from %s' % (instance,), 'info')
    return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@webui.route('/server/restart/<instance>')
@login_required
@roles_required('admin')
def _restartinstance(instance):
    restartinstance(instance, cancel=False)
    flash(u'Restarting Server', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@webui.route('/server/start/<instance>')
@login_required
@roles_required('admin')
def _startinstance(instance):
    enableinstance(instance)
    flash(u'Starting Server', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@webui.route('/server/stop/<instance>')
@login_required
@roles_required('admin')
def _stopinstance(instance):
    disableinstance(instance)
    flash(u'Sending Server Shutdown', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@webui.route('/server/cancelrestart/<instance>')
@login_required
@roles_required('admin')
def _cancelrestartinstance(instance):
    restartinstance(instance, cancel=True)
    flash(u'Cancelling Server Restart', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@webui.route('/server/chatlog/<instance>', methods=['POST', 'GET'])
@login_required
def _chatlog(instance):
    if request.method == 'POST':
        serverchat(request.form["message"], inst=instance)
        flash(f'Message Sent to {instance.title()}', 'info')
        return redirect(url_for('webui._chatlog', instance=instance))
    chatlog = getlog(instance, 'chat')
    return render_template('serverchatlog.html', serverinfo=instanceinfo(instance), chatlog=chatlog[::-1])
