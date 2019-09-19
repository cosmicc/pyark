

def run():
    try:
        1 / 0
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


run()
