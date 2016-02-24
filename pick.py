#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Frans Fuerst


""" pick - highlight matchings

    todo:
        pick [-i] [-p] <pattern> /path/to/textfile
        <command> | hl [-f] [-i] <pattern>
        [x] rename to 'pick'
        [x] highlight findings
        [ ] check for pipe
        [ ] support -i case insensitivity
        [ ] support time measurement
        [ ] show status line with pattern and timing
        [ ] support -l logging (parse /var/log/*)
        [ ] support -v invert
        [ ] support -f file poll (can be substituted with tail -f | pick)
        [ ] support regex
        [ ] python2/3
        [ ] setup for PIP
"""

"""
from http://misc.flogisoft.com/bash/tip_colors_and_formatting:
1 	Bold/Bright 	echo -e "Normal \e[1mBold"
2 	Dim 	        echo -e "Normal \e[2mDim"
4 	Underlined 	    echo -e "Normal \e[4mUnderlined"
5 	Blink 1) 	    echo -e "Normal \e[5mBlink"
7 	Reverse         echo -e "Normal \e[7minverted"
8 	Hidden          echo -e "Normal \e[8mHidden"

0 	Reset all attributes 	echo -e "\e[0mNormal Text"
21 	Reset bold/bright 	    echo -e "Normal \e[1mBold \e[21mNormal"
22 	Reset dim 	            echo -e "Normal \e[2mDim \e[22mNormal"
24 	Reset underlined 	    echo -e "Normal \e[4mUnderlined \e[24mNormal"
25 	Reset blink 	        echo -e "Normal \e[5mBlink \e[25mNormal"
27 	Reset reverse 	        echo -e "Normal \e[7minverted \e[27mNormal"
28 	Reset hidden 	        echo -e "Normal \e[8mHidden \e[28mNormal"

8/16 Colors

39 	Default foreground color 	echo -e "Default \e[39mDefault"
30 	Black 	                    echo -e "Default \e[30mBlack"
31 	Red 	                    echo -e "Default \e[31mRed"
32 	Green 	                    echo -e "Default \e[32mGreen"
33 	Yellow                      echo -e "Default \e[33mYellow"
34 	Blue 	                    echo -e "Default \e[34mBlue"
35 	Magenta                     echo -e "Default \e[35mMagenta"
36 	Cyan 	                    echo -e "Default \e[36mCyan"
37 	Light gray 	                echo -e "Default \e[37mLight gray"
90 	Dark gray 	                echo -e "Default \e[90mDark gray"
91 	Light red 	                echo -e "Default \e[91mLight red"
92 	Light green 	            echo -e "Default \e[92mLight green"
93 	Light yellow 	            echo -e "Default \e[93mLight yellow"
94 	Light blue 	                echo -e "Default \e[94mLight blue"
95 	Light magenta 	            echo -e "Default \e[95mLight magenta"
96 	Light cyan 	                echo -e "Default \e[96mLight cyan"
97 	White 	                    echo -e "Default \e[97mWhite"

Background
Code 	Color 	Example 	Preview
49 	Default background color 	echo -e "Default \e[49mDefault"
40 	Black 	                    echo -e "Default \e[40mBlack"
41 	Red 	                    echo -e "Default \e[41mRed"
42 	Green 	                    echo -e "Default \e[42mGreen"
43 	Yellow 	                    echo -e "Default \e[43mYellow"
44 	Blue 	                    echo -e "Default \e[44mBlue"
45 	Magenta 	                echo -e "Default \e[45mMagenta"
46 	Cyan 	                    echo -e "Default \e[46mCyan"
47 	Light gray 	                echo -e "Default \e[47mLight gray"
100 	Dark gray 	            echo -e "Default \e[100mDark gray"
101 	Light red 	            echo -e "Default \e[101mLight red"
102 	Light green 	        echo -e "Default \e[102mLight green"
103 	Light yellow 	        echo -e "Default \e[103mLight yellow"
104 	Light blue 	            echo -e "Default \e[104mLight blue"
105 	Light magenta 	        echo -e "Default \e[105mLight magenta"
106 	Light cyan 	            echo -e "Default \e[106mLight cyan"
107 	White 	                echo -e "Default \e[107mWhite"


http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
https://pypi.python.org/pypi/colorama
"""

import sys
import subprocess
import select
import time
import logging as log

class col:
    INVERT = '\033[7m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'
    RESET = '\033[0m'

    FG_DEFAULT = '\033[39m'
    FG_RED = '\033[31m'

    BG_DEFAULT = '\033[49m'
    BG_RED = '\033[41m'

class unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class picker:
    def __init__(self, args):
        self._args = args
        self._out = unbuffered(sys.stdout.detach())
        self._pattern = args.pattern.split('|')

    def _colorize(self, line: str):
        for p in self._pattern:
            line = line.replace(p, col.BG_RED + p + col.BG_DEFAULT)
        return line

    def output(self, line):
        _line = line.decode()
        for p in self._pattern:
            if p in _line:
                if not self._args.invert:
                    line = self._colorize(_line).encode('utf-8')
                self._out.write(col.INVERT.encode())
                self._out.write(line)
                self._out.write(col.RESET.encode())
                return
        self._out.write(line)

    def start_process(self, command):
        log.warning('command:      %s', command)

        _process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            bufsize=0)

        _to_poll = [_process.stdout.fileno()]

        while True:
            if _process.poll() is not None:
                for l in _process.stdout.readlines():
                    self.output(l)
                break

            if _process.stdout.fileno() in select.select(_to_poll, [], [])[0]:
                self.output(_process.stdout.readline())

        return _process.returncode

    def read_stdin(self):
        for line in sys.stdin.detach():
            self.output(line)

def main():

    # we should use argparse here but I don't know how
    # to split program arguments from the program to run
    class args:
        pass
    args = args()
    _args = sys.argv[1:]
    args.case_insensitiv = False
    args.invert = False
    args.file_poll = False
    args.pattern = None
    while True:
        if len(_args) == 0:
            break
        elif _args[0] == '-i':
            args.case_insensitiv = True
            _args = _args[1:]
        elif _args[0] == '-v':
            args.invert = True
            _args = _args[1:]
        elif _args[0] == '-p':
            args.pattern = _args[1]
            _args = _args[2:]
        elif _args[0] == '-f':
            args.file_poll = True
            _args = _args[1:]
        else:
            break

    if args.pattern is None:
        if len(_args) == 0:
            print('no pattern given')
            return -1
        else:
            args.pattern = _args[0]
            _args = _args[1:]

    _command = _args if len(_args) > 1 else None

    log.warning('test pattern: "%s"', args.pattern)

    _picker = picker(args)
    if _command:
        return _picker.start_process(_command)
    else:
        return _picker.read_stdin()

def write_iostats():
    # http://stackoverflow.com/questions/13442574
    # http://stackoverflow.com/questions/4265057
    import stat, os
    pipe = sys.stdout
    mode = os.fstat(pipe.fileno()).st_mode
    log.warning("stdout isatty:       %s",
                "True" if pipe.isatty() else "False")
    log.warning("stdout S_ISFIFO:     %s",
                "True" if stat.S_ISFIFO(mode) else "False")
    log.warning("stdout S_ISREG:      %s",
                "True" if stat.S_ISREG(mode) else "False")

    pipe = sys.stdin
    mode = os.fstat(pipe.fileno()).st_mode
    log.warning("stdin isatty:        %s",
                "True" if pipe.isatty() else "False")
    log.warning("stdin S_ISFIFO:      %s",
                "True" if stat.S_ISFIFO(mode) else "False")
    log.warning("stdin S_ISREG:       %s",
                "True" if stat.S_ISREG(mode) else "False")

    log.warning("TERM is set:         %s",
                "True" if 'TERM' in os.environ else "False")

def test_process():
    while True:
        print('pattern 123')
        time.sleep(.5)
        print('pattern 321')
        time.sleep(.5)
        print('bad pattern')
        time.sleep(.5)
    return 0


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--test-process']:
            sys.stdout = unbuffered(sys.stdout)
            sys.exit(test_process())

        sys.exit(main())
    except KeyboardInterrupt:
        pass

