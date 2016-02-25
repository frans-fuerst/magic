#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Frans Fuerst


""" pick - highlight matchings

    like `grep` `pick` is intended to find occurrences of pattern in a stream of
    text but in comparison to `grep` `pick` is used to highlight and to show the
    frequency of a pattern.

    run
        pick [-i] [-p] <pattern> <-c /path/to/executable | </path/to/textfile> >
        or
        <command> | pick [-i] [-p] <pattern>

    todo:
        pick [-i] [-p] <pattern> /path/to/textfile
        <command> | hl [-f] [-i] <pattern>
        [x] rename to 'pick'
        [x] highlight findings
        [x] support -i case insensitivity
        [x] support time measurement
        [ ] check for pipe
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
import re
import logging as log

class col:
    INVERT = '\033[7m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'
    RESET = '\033[0m'

    FG_DEFAULT = '\033[39m'
    FG_RED = '\033[31m'
    FG_GREEN = '\033[32m'
    FG_YELLOW = '\033[33m'
    FG_BLUE = '\033[31m'

    BG_DEFAULT = '\033[49m'
    BG_RED = '\033[41m'
    BG_YELLOW = '\033[42m'
    BG_GREEN = '\033[43m'
    BG_BLUE = '\033[44m'

class unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class picker:
    class error(Exception):
        pass

    def __init__(self, args):
        self._invert = args.invert
        self._case_insensitive = args.case_insensitive
        # save original and optionally lowercase version of search substrings
        if args.case_insensitive:
            self._pattern = tuple((p, p.lower()) for p in args.pattern.split('|'))
        else:
            self._pattern = tuple((p, p) for p in args.pattern.split('|'))
        self._freq_t_last = None
        self._freq_baseline = None
        self._occurrence_count = 0
        self._print_stats = args.print_stats
        if len(self._pattern) > 1 and self._print_stats:
            raise picker.error('stats currently work only with single pattern')
        self._out = unbuffered(sys.stdout.detach())

    def _colorize(self, line: str):
        if self._case_insensitive:
            for p, _ in self._pattern:
                line = self._case_insensitive_replace(
                    line, p, col.BG_RED + p + col.BG_DEFAULT)
        else:
            for p, _ in self._pattern:
                line = line.replace(p, col.BG_RED + p + col.BG_DEFAULT)
        return line

    def _case_insensitive_replace(self, string, str1, str2):
        _re = re.compile(re.escape(str1), re.IGNORECASE)
        return _re.sub(str2, string)

    def output(self, line):
        _decoded = line.decode()
        _search_line = _decoded.lower() if self._case_insensitive else _decoded

        for _, p in self._pattern:
            if p in _search_line:
                if not self._invert:
                    _decoded = self._colorize(_decoded)
                self._out.write(col.INVERT.encode())
                self._out.write(_decoded.encode())
                self._out.write(col.RESET.encode())
                if self._print_stats:
                    self._out.write(col.BOLD.encode())
                    _stats = self._stats_str()
                    if _stats:
                        self._out.write(
                            (col.FG_GREEN + _stats + col.FG_DEFAULT).encode())
                        self._out.write('\n'.encode())
                    self._out.write(col.RESET.encode())
                return
        self._out.write(line)

    def _stats_str(self):
        self._occurrence_count += 1
        _t = time.time()
        if self._freq_t_last is None:
            self._freq_t_last = _t
            return None
        _dur = _t - self._freq_t_last
        if self._freq_baseline is None:
            self._freq_baseline = _dur
        else:
            self._freq_baseline = self._freq_baseline * 0.9 + _dur * 0.1
        self._freq_t_last = _t
        return ('>>> count: %d, dT: %.3f, avg: %.3f'
                % (self._occurrence_count, _dur, self._freq_baseline))

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
    args.case_insensitive = False
    args.invert = False
    args.print_stats = False
    args.pattern = None
    while True:
        if len(_args) == 0:
            break
        elif _args[0] == '-i':
            args.case_insensitive = True
            _args = _args[1:]
        elif _args[0] == '-v':
            args.invert = True
            _args = _args[1:]
        elif _args[0] == '-p':
            args.pattern = _args[1]
            _args = _args[2:]
        elif _args[0] == '-s':
            args.print_stats = True
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
        print('Pattern 321')
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
    except picker.error as ex:
        print("ERROR: %s" % ex)
    except KeyboardInterrupt:
        pass

