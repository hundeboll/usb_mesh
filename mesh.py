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
from PySide.QtCore import *
from PySide.QtGui import *
import connect
import nodes
import graph

def main():
    a = QApplication(sys.argv)

    wizard = connect.wizard()
    if not wizard.exec_():
        print("Configuration canceled.")
        sys.exit(0)

    plotter = graph.plotter()
    stats = graph.stats()
    stats.add_plotter(plotter)
    plotter.show()
    nodelist = nodes.nodelist()
    nodelist.add_plotter(plotter)

    a.exec_()
    stats.stop()
    wizard.stop()


if __name__ == "__main__":
    main()
