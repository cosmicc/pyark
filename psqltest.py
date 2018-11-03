from configreader import psql_pyark
import psycopg2

#conn = psycopg2.connect(dbname='pyark', user='pyark', host='172.31.250.112', port='51432', sslmode='require', sslcert='/root/.postgresql/postgresql.crt', sslkey='/root/.postgresql/postgresql.key')

print(psql_pyark)

#conn = psycopg2.connect(psql_pyark)
conn = psycopg2.connect(dbname='pyark', user='pyark', host='172.31.250.112', port='51432', password='SchVS#An8d86T!Mg')

c = conn.cursor()

c.execute("SELECT * FROM players")
allplayers = c.fetchall()
for each in allplayers:
    print(each)


c.close()
conn.close()
