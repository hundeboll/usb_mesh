#!/usr/bin/env python2

import sys
import avahi
import dbus
import dbus.mainloop.glib
import subprocess
import time
from PySide.QtCore import *
from PySide.QtGui import *

import connect


class discover:
    def __init__(self, node_list):
        self.node_list = node_list
        self.check_avahi()
        self.connect_avahi()

    def check_avahi(self):
        cmd = ["avahi-daemon", "--check"]
        p = subprocess.Popen(cmd)
        if p.wait():
            print("Avahi Daemon is not startet. Please run configuration wizard again.")
            sys.exit(1)

    def connect_avahi(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.raw_server = self.bus.get_object('org.freedesktop.Avahi', '/')
        self.server = dbus.Interface(self.raw_server, 'org.freedesktop.Avahi.Server')

        dev = self.server.GetNetworkInterfaceIndexByName("bat0")
        path = self.server.ServiceBrowserNew(dev, avahi.PROTO_UNSPEC, '_workstation._tcp', 'local', 0)
        self.sbrowser = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, path), avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        self.sbrowser.connect_to_signal("ItemNew", self.add_service)
        self.sbrowser.connect_to_signal("ItemRemove", self.rm_service)

    def add_node(self, *args):
        name = args[2].rsplit("[")[0].strip()
        item = QListWidgetItem(name, self.node_list)
        item.setData(Qt.UserRole, args)

    def rm_node(self, *args):
        name = args[2].rsplit("[")[0]
        items = self.node_list.findItems(name, Qt.MatchExactly)
        for item in items:
            # Check if data fields match
            data = item.data(Qt.UserRole)
            if data[2] != args[2] or data[7] != args[7]:
                continue
            row = self.node_list.row(item)
            self.node_list.takeItem(row)

    def print_error(self, *args):
        print 'error_handler'
        print args[0]

    def add_service(self, interface, protocol, name, stype, domain, flags):
        self.server.ResolveService(interface, protocol, name, stype, domain, avahi.PROTO_UNSPEC, 0, reply_handler=self.add_node, error_handler=self.print_error)

    def rm_service(self, interface, protocol, name, stype, domain, flags):
        self.server.ResolveService(interface, protocol, name, stype, domain, avahi.PROTO_UNSPEC, 0, reply_handler=self.rm_node, error_handler=self.print_error)


class node_info(QWidget):
    def __init__(self, parent=None):
        super(node_info, self).__init__(parent)
        self.fields = {}
        self.fields_list = []

        self.add_field("Name")
        self.add_field("MAC")
        self.add_field("IPv4")

        self.do_layout()

    def add_field(self, name):
        n = name.lower()
        if n in self.fields:
            print("Field already exists: {}".format(name))
            return

        t = (QLabel("{}:".format(name)), QLabel(""))
        self.fields[n] = t
        self.fields_list.append(t)

    def set_field(self, name, text):
        n = name.lower()
        if n not in self.fields:
            print("Field not found: {}".format(name))
            return
        self.fields[n][1].setText(text)

    def do_layout(self):
        grid = QGridLayout()
        i = 0
        for field in self.fields_list:
            grid.addWidget(field[0], i,0)
            grid.addWidget(field[1], i,1)
            i += 1
        self.setLayout(grid)

    def set_node(self, name, data):
        mac = data[2].rsplit("[")[1].strip("]")
        self.set_field("name", name)
        self.set_field("mac", mac)
        self.set_field("ipv4", data[7])


class node_actions(QWidget):
    def __init__(self, node_list, log, parent=None):
        super(node_actions, self).__init__(parent)
        self.node_list = node_list
        self.log = log
        self.buttons = []
        self.add_button("Ping", self.ping_node)
        self.do_layout()

    def add_button(self, name, handler):
        b = QPushButton(name)
        b.clicked.connect(handler)
        self.buttons.append(b)

    def do_layout(self):
        vbox = QVBoxLayout()
        for b in self.buttons:
            vbox.addWidget(b)
        self.setLayout(vbox)

    def ping_node(self):
        item = self.node_list.currentItem()
        data = item.data(Qt.UserRole)
        self.log.appendPlainText("Pinging {} ({})".format(item.text(), data[7]))

    def send_file(self):
        item = self.node_list.currentItem()
        data = item.data(Qt.UserRole)
        self.log.appendPlainText("Pinging {} ({})".format(item.text(), data[7]))


class main_window(QMainWindow):
    def __init__(self, parent=None):
        super(main_window, self).__init__(parent)
        self.setWindowTitle("Node Browser")

        #self.wizard = connect.wizard()
        #if not self.wizard.exec_():
        #    print("Configuration canceled.")
        #    sys.exit(0)

        self.add_log()
        self.node_list = QListWidget(self)
        self.node_list.clicked.connect(self.node_selected)
        self.node_info = node_info(self)
        self.node_actions = node_actions(self.node_list, self.log, self)
        self.discover = discover(self.node_list)
        self.do_layout()

    def add_log(self):
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.appendPlainText("Select node from list")

    def do_layout(self):
        vbox_left = QVBoxLayout()
        vbox_left.addWidget(QLabel("<strong>Nodes</strong>"))
        vbox_left.addWidget(self.node_list)
        left = QWidget()
        left.setLayout(vbox_left)

        vbox_middle = QVBoxLayout()
        vbox_middle.addWidget(QLabel("<strong>Node Info</strong>"))
        vbox_middle.addWidget(self.node_info)
        vbox_middle.addStretch()
        middle = QWidget()
        middle.setLayout(vbox_middle)

        vbox_right = QVBoxLayout()
        vbox_right.addWidget(QLabel("<strong>Actions</strong>"))
        vbox_right.addWidget(self.node_actions)
        vbox_right.addStretch()
        right = QWidget()
        right.setLayout(vbox_right)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(middle)
        splitter.addWidget(right)
        splitter.setSizes([1,1,1])

        vbox = QVBoxLayout()
        vbox.addWidget(splitter)
        vbox.addWidget(self.log)

        w = QWidget()
        w.setLayout(vbox)

        self.setCentralWidget(w)
        self.resize(800,600)
        self.show()

    def node_selected(self, idx):
        node_text = self.node_list.currentItem().text()
        node_data = self.node_list.currentItem().data(Qt.UserRole)
        self.node_info.set_node(node_text, node_data)


if __name__ == "__main__":
    a = QApplication(sys.argv)
    m = main_window()
    a.exec_()
