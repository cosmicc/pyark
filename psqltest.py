import psycopg2

#conn = psycopg2.connect(dbname='pyark', user='pyark', host='172.31.250.112', port='51432', sslmode='require', sslcert='/root/.postgresql/postgresql.crt', sslkey='/root/.postgresql/postgresql.key')

conn = psycopg2.connect(dbname='pyark', user='pyark', host='172.31.250.112', port='51432', password='SchVS#An8d86T!Mg')


c = conn.cursor()

c.execute("UPDATE players SET banned = '%s' WHERE playername = '%s'" % (1,'rykker'))
conn.commit()
c.close()
conn.close()
