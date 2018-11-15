from active_alchemy import ActiveAlchemy, create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker


class Bookmarks(object):
    pass


def loadSession():
    db = "postgresql+pg8000://pyark:nGXaQ2x6UzSx396EYvgSfv54BX7w8x2X@172.31.250.112:51432/pyark_test"
    engine = create_engine(db)
    metadata = MetaData(engine)

    general = Table('players', metadata, autoload=True)
    mapper(Bookmarks, general)

    Session = sessionmaker(bind=engine)
    session = Session()
    return session

if __name__ == "__main__":
    session = loadSession()
    res = session.query(Bookmarks).all()
    print(res)
