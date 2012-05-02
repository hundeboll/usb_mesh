#!/usr/bin/env python2

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
