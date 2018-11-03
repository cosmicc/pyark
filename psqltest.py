from configreader import psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb
import psycopg2

#conn = psycopg2.connect(dbname='pyark', user='pyark', host='172.31.250.112', port='51432', sslmode='require', sslcert='/root/.postgresql/postgresql.crt', sslkey='/root/.postgresql/postgresql.key')


#conn = psycopg2.connect(psql_pyark)
conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)

c = conn.cursor()

c.execute("SELECT * FROM players")
allplayers = c.fetchall()
for each in allplayers:
    print(each)


c.close()
conn.close()
