data = 'someshit: my steamname (t(o.o)t): some more shit'

data2 = data.split(':')

print(data2[1])

data3 = data2[1].split(' (')

print(data3[1][:-1])


