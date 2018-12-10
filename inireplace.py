import os
from tempfile import NamedTemporaryFile

eventfile = '/home/ark/shared/config/GameUserSettings-evo.ini'
basefile = '/home/ark/shared/config/GameUserSettings-base.ini'

'''
fe = open(eventfile, 'r')
eventline = fe.readline()
while eventline:
    with open(basefile, 'U') as fb:
        baseline = fb.readline()
        while baseline:
            # print(eventline.split('=')[0])
            if eventline.split('=')[0] == baseline.split('=')[0]:
                print(eventline.strip())
                baseline = baseline.replace(baseline, eventline.strip())
            # sys.stdout.write(baseline)
            baseline = fb.readline()
    eventline = fe.readline()

fe.close()
fb.close()
'''


def replace_line(filepath, oldline, newline):
    # quick parameter checks
    assert os.exists(filepath)          # !
    assert (oldline and str(oldline))  # is not empty and is a string
    assert (newline and str(newline))
    replaced = False
    written = False
    try:
        with open(filepath, 'r+') as f:    # open for read/write -- alias to f
            lines = f.readlines()            # get all lines in file
            if oldline not in lines:
                pass                         # line not found in file, do nothing
            else:
                tmpfile = NamedTemporaryFile(delete=True)  # temp file opened for writing
                for line in lines:           # process each line
                    if line == oldline:        # find the line we want
                        tmpfile.write(newline)   # replace it
                        replaced = True
                    else:
                        tmpfile.write(oldline)   # write old line unchanged
                if replaced:                   # overwrite the original file
                    f.seek(0)                    # beginning of file
                    f.truncate()                 # empties out original file
                    for tmplines in tmpfile:
                        f.write(tmplines)          # writes each line to original file
                    written = True
            tmpfile.close()              # tmpfile auto deleted
            f.close()                          # we opened it , we close it

    except IOError as ioe:                 # if something bad happened.
        print("ERROR", ioe)
        f.close()
        return False

    return replaced and written        # replacement happened with no errors = True
