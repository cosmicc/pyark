first_file = '/home/ark/shared/config/GameUserSettings.ini'
second_file = '/home/ark/shared/config/GameUserSettings-hellonark.ini'


def filecompare(first_file, second_file, diff=True):
    with open(first_file, 'r') as file1:
        with open(second_file, 'r') as file2:
            if diff:
                output = set(file1).difference(file2)
            else:
                output = set(file1).intersection(file2)
    #output.discard('\n')
    return output
#    with open('diff.txt', 'w') as file_out:
#        for line in output:
#            file_out.write(line)


#print(filecompare(first_file, second_file))
for each in filecompare(first_file, second_file):
    print(each)
