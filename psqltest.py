import psycopg2

conn = psycopg2.connect(dbname='pyark', user='pyark', host='172.31.250.112', port='51432', sslmode='require', sslcert='/root/.postgresql/postgresql.crt', sslkey='/root/.postgresql/postgresql.key')

c = conn.cursor()

c.close()
conn.close()
