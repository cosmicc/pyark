import sys
sys.path.append('/home/ark/pyark')
import modules.auctionhelper


def test_fetchauctiondata():
    assert auctionhelper.fetchauctiondata('76561198408657294') is False
