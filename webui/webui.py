from flask import Flask, render_template
#import sys
#sys.path.append('/home/ark/pyark')
from modules.configreader import webui_ip, webui_port, webui_debug
from modules.dbhelper import dbquery
from modules.instances import instancelist
from modules.players import getplayersonline, getlastplayersonline
#sys.path.append('/home/ark/pyark/webui')
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


@app.route('/')
def clusterinfo():

    return render_template('clusterinfo.html', instances=instancelist())


if __name__ == '__main__':
    app.run(host=webui_ip, port=webui_port, debug=webui_debug)
