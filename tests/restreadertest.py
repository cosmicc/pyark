import urllib.request, json
from configreader import restapi_ip, restapi_port

apiurl = f'http://{restapi_ip}:{restapi_port}'


def getapidata(apipath):
    url = f'{apiurl}/{apipath}'
    try:
        response = urllib.request.urlopen(url)
        apiresponse = json.loads(response.read().decode("utf-8"))
        return apiresponse
    except:
        print('Error fetching API data')
        return None


clusterinfo = getapidata('clusterinfo')
print(clusterinfo['players'])
