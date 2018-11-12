f = open ('test3.txt')
lineList = f.readlines()
f.close()
print (lineList)
print ("The last line is:")
print (lineList[len(lineList)-1])
# or simply
print (lineList[-1])
