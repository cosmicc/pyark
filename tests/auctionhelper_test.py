import sys
sys.path.append('/home/ark/pyark')
import auctionhelper


def test_fetchauctiondata():
    assert auctionhelper.fetchauctiondata('76561198408657294') is False
