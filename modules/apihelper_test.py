import sys

import pytest
import modules.apihelper
import pprint


sys.path.append("/home/ark/pyark")


@pytest.mark.last
async def test_asyncfetchclusterauctiondata(testsession):
    # assert (
    #    type(await modules.apihelper.asyncfetchclusterauctiondata(testsession)) == dict
    #)
    nd = await modules.apihelper.asyncfetchclusterauctiondata(testsession)
    pp = pprint.PrettyPrinter(indent=4)
    print(len(nd))
    for each in nd:
        pp.pprint(each)

'''
@pytest.mark.last
async def test_getsteaminfo(testsession):
    assert (
        await modules.apihelper.getsteaminfo("76561198408657294", "admin", testsession)
        is True
    )


@pytest.mark.last
async def test_getsteambans(testsession):
    assert (
        await modules.apihelper.getsteambans("76561198408657294", "admin", testsession)
        is True
    )


@pytest.mark.last
async def test_asyncfetchauctiondata(testsession):
    assert (
        await modules.apihelper.asyncfetchauctiondata(
            testsession, "76561198408657294", "admin"
        )
        is None
    )
'''
