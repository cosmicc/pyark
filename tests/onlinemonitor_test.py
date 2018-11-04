import sys
sys.path.append('/home/ark/pyark')
import onlinemonitor


def test_checkifbanned():
    assert onlinemonitor.checkifbanned('76561198408657294') is False
    assert onlinemonitor.checkifbanned('99999999999999999') is True
