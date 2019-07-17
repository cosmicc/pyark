import urllib.request, json
from modules.configreader import webserver_ip, webserver_port

apiurl = f'http://{webserver_ip}:{webserver_port}/api'


def getapidata(apipath):
    url = f'{apiurl}/{apipath}'
    print(f'Request: {url}')
    try:
        response = urllib.request.urlopen(url)
        apiresponse = json.loads(response.read().decode("utf-8"))
        return apiresponse
    except:
        print('Error fetching API data')
        return None


clusterinfo = getapidata('players/online')
if clusterinfo is None:
    print('None')
else:
    print(clusterinfo['players'])
