#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# <mhu@es.aau.dk> wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.
#
# This code is proof-of-concept and is meant for demonstration purposes only.
# I apologize for any eye-damage caused by the low quality of the code below.
#
# - Martin Hundebøll
# ----------------------------------------------------------------------------

import sys
import os

path = "/sys/kernel/debug/batman_adv/bat0/block_ogm"

if not os.path.exists(path):
    sys.stderr.write("No such file or directory: {}\n".format(path))
    sys.exit(1)

if len(sys.argv) != 3:
    blocks = open(path).read()
    sys.stdout.write(blocks)
    sys.exit(0)

text = "{} {}\n".format(sys.argv[1], sys.argv[2])
open(path, "w").write(text)
sys.exit(0)
