

def run():
    try:
        a = 1 / 1
    except:
        print('except')
        return False
        print('except2')
    else:
        print('else')
        return True
        print('else2')
    finally:
        print('finally')
    return True


print(run())
