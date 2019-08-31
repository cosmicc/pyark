import sys

import modules.auctionhelper as auctionhelper

sys.path.append('/home/ark/pyark')


def test_fetchauctiondata():
    assert auctionhelper.fetchauctiondata('76561198408657294') is False
