from modules.configreader import webui_ip
from web.views import app


if __name__ == '__main__':
    app.run(host=webui_ip, port=51501, debug=True)
