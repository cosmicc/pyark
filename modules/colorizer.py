from colored import attr, bg, fg

RST = attr('reset')
RED = attr('reset') + fg(1)
YEL = attr('reset') + fg(3)
BYEL = attr('reset') + fg(11)
CYN = attr('reset') + fg(6)
BCYN = attr('reset') + fg(14)
BLU = attr('reset') + fg(32)
WHT = attr('reset') + fg(7)
BWHT = attr('reset') + fg(15)
MGT = attr('reset') + fg(5)
BMGT = attr('reset') + fg(13)
GRN = attr('reset') + fg(2)
BGRN = attr('reset') + fg(10)
PNK = attr('reset') + fg(9)
BRED = attr('reset') + fg(9)
PUR = attr('reset') + fg(99)
BRN = attr('reset') + fg(130)
BGN = attr('reset') + fg(86)
ORG = attr('reset') + fg(208)
SKN = attr('reset') + fg(222)
MAU = attr('reset') + fg(147)
RMY = attr('reset') + fg(100)
SLT = attr('reset') + fg(109)
DREV = attr('reverse')
LREV = bg(15) + attr('reverse')
UDL = attr('underlined')

def main():
    print(f'{RST}{RED}RED\n{RED}{LREV}RRED{RST}\n{BRED}BRED\n{BLU}BLUE\n{CYN}CYAN\n{BCYN}BCYAN\n{YEL}YELLOW\n{BYEL}BYELLOW\n{WHT}WHITE\n{BWHT}BWHITE\n{PNK}PINK \
        \n{PUR}PURPLE\n{BRN}BROWN\n{GRN}GREEN\n{BGRN}BGREEN\n{BGN}BLUGREEN\n{ORG}ORANGE\n{SKN}SKIN\n{MAU}MAUVE\n{MGT}MAGENTA\n{BMGT}BMAGENTA \
        \n{RMY}ARMY\n{SLT}SLATE{RST}')

if __name__ == "__main__":
    main()
