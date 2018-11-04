import sys
sys.path.append('/home/ark/pyark')
import arkserversnet


def test_fetchurldata():
    assert type(arkserversnet.fetchurldata('https://ark-servers.net/api/?object=servers&element=detail&key=xcmOgkKFziAjDNhSAdTIH0w6fBMjOo50dpk')) is dict
