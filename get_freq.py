#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 TOPTICA Photonics AG

import sys
import os
import subprocess
import select
import time
import optparse

t = None
dt_bl = None


def freq_print(msg, pattern):
    global t, dt_bl
    s = msg.decode().strip('\n')
    _found = False
    if pattern in s:
        _found = True
        _t = time.time()
        i = _t - t if t is not None else 0
        dt_bl = dt_bl * 0.9 + i * 0.1 if dt_bl is not None and dt_bl > 0 else i
        t = _t
    if _found:
        print(s)
        print('dT: %.3f, dT_bl: %.3f |-----------------------------'
              % (i, dt_bl))


def run_script(script_args):
    parser = optparse.OptionParser()
    parser.add_option("-p", "--pattern", dest="pattern",
                      default="",
                      help="pattern to look for", metavar="STRING")

    (options, args) = parser.parse_args()

    _process = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                bufsize=0)

    _to_poll = [_process.stdout.fileno()]

    while True:
        if _process.poll() is not None:
            for l in _process.stdout.readlines():
                freq_print(l, options.pattern)
            break

        _ret = select.select(_to_poll, [], [])
        freq_print(_process.stdout.readline(), options.pattern)

    return _process.returncode


if __name__ == '__main__':
    sys.exit(run_script(sys.argv[1:]))
