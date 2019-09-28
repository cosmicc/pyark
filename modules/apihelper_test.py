import sys

import pytest
import modules.apihelper


sys.path.append("/home/ark/pyark")


@pytest.mark.last
async def test_asyncfetchclusterauctiondata(testsession):
    assert (
        type(await modules.apihelper.asyncfetchclusterauctiondata(testsession)) == dict
    )
    print(await modules.apihelper.asyncfetchclusterauctiondata(testsession))


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
