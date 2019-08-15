from modules.instances import serverchat


def loggerchat(chatline):
    cmd = chatline.split(' ')[0][:1].strip()
    who = chatline.split(' ')[0][1:].strip().lower()
    cmdremove = len(who) + 1
    msg = chatline[cmdremove:].strip()
    if (cmd == '@' and who == 'all') or (cmd == '#' and who == 'all'):
        serverchat(msg, inst='ALL', whosent='Admin', private=False, broadcast=False)
    elif cmd == '#':
        serverchat(msg, inst=who, whosent='Admin', private=False, broadcast=False)
    elif cmd == '@':
        serverchat(msg, inst='ALL', whosent=who, private=True, broadcast=False)
    elif cmd == '!':
        serverchat(msg, inst=who, whosent='Admin', private=False, broadcast=True)


loggerchat('@admin hi')
