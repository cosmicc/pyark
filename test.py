
from ansi2html import Ansi2HTMLConverter


class AnsiConverter(Ansi2HTMLConverter):
    def __init__(self):
        Ansi2HTMLConverter.__init__(self,
                                    latex=False,
                                    inline=True,
                                    dark_bg=True,
                                    line_wrap=False,
                                    font_size='normal',
                                    linkify=True,
                                    escaped=True,
                                    markup_lines=False,
                                    output_encoding='utf-8',
                                    scheme='ansi2html',
                                    title=''
                                    )

ansiconv = AnsiConverter()


print(ansiconv(line))


