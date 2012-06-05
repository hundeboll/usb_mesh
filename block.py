#!/usr/bin/env python2

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
