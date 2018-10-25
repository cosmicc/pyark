import sqlite3
from configreader import statsdb
import pandas as pd

conn = sqlite3.connect(statsdb)

df = pd.read_sql('SELECT * FROM ragnarok', conn, parse_dates=['date'], index_col='date')

conn.close()

# Daily Averages
df = df.tz_localize(tz='UTC')
df = df.tz_convert(tz='US/Eastern')
print(df.resample('H').mean())


