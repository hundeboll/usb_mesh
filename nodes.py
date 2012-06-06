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

import os
import sys
import avahi
import dbus
import dbus.mainloop.glib
import subprocess
import threading
import signal
import re
from PySide.QtCore import *
from PySide.QtGui import *


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
        mac = args[2].rsplit("[")[1].strip("]")
        args += (self.client_to_orig(mac), False, False, False, False)
        item = QListWidgetItem(name, self.node_list)
        item.setData(Qt.UserRole, args)
        item.setIcon(QIcon.fromTheme("network-idle"))

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
        print("Service removed")

    def client_to_orig(self, mac):
        tg = open("/sys/kernel/debug/batman_adv/bat0/transtable_global").read()
        for line in tg.split("\n"):
            if mac in line:
                break
        else:
            return None

        match = re.findall(" \* [0-9a-f:]{17}  \( +\d+\) via ([0-9a-f:]{17})", line)
        return match[0] if match else None


class node_info(QWidget):
    def __init__(self, parent=None):
        super(node_info, self).__init__(parent)
        self.fields = {}
        self.fields_list = []

        self.add_field("Name")
        self.add_field("MAC")
        self.add_field("IPv4")
        self.add_field("Orig")

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
        self.fields[n][1].setText(str(text))

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
        self.set_field("orig", data[11])


class node_actions(QWidget):
    ping_log = Signal(str)

    def __init__(self, node_list, log, parent=None):
        super(node_actions, self).__init__(parent)
        self.node_list = node_list
        self.log = log
        self.buttons = []
        self.block_path = "/sys/kernel/debug/batman_adv/bat0/block_ogm"
        self.allow_count = 0
        self.add_button("Ping", self.ping_node, checkable=True)
        self.add_button("Block path", self.block_node, checkable=True)
        self.add_button("Pass path", self.pass_node, checkable=True)
        self.ping_log.connect(self.ping_node_line)
        self.do_layout()

    def add_button(self, name, handler, checkable=False):
        b = QPushButton(name)
        b.clicked.connect(handler)
        if checkable: b.setCheckable(True)
        self.buttons.append(b)

    def get_button(self, name):
        for button in self.buttons:
            if button.text() == name:
                return button

    def set_buttons(self, data):
        i = 0
        for button in self.buttons:
            button.setChecked(data[12+i])
            i += 1

    def do_layout(self):
        vbox = QVBoxLayout()
        for b in self.buttons:
            vbox.addWidget(b)
        self.setLayout(vbox)

    def ping_node(self):
        button = self.get_button("Ping")
        item = self.node_list.currentItem()
        data = item.data(Qt.UserRole)
        data[12] = button.isChecked()
        item.setData(Qt.UserRole, data)
        if button.isChecked():
            t = threading.Thread(None, self.ping_node_thread, kwargs={'data': data})
            t.start()
        else:
            self.ping_process.send_signal(signal.SIGINT)

    def ping_node_thread(self, data):
        ip = data
        cmd = ["ping", data[7]]
        self.ping_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while self.ping_process.poll() == None:
            line = self.ping_process.stdout.readline()
            self.ping_log.emit(line)

        stdout,stderr = self.ping_process.communicate()
        for line in stdout.split("\n"):
            self.ping_log.emit(line)

    @Slot(str)
    def ping_node_line(self, line):
            self.log.appendPlainText(line.strip())

    def block_node_exec(self, mac):
        cmd = ['gksudo', '{} {} drop'.format(os.path.join(sys.path[0], 'block.py'), mac)]
        p = subprocess.Popen(cmd)
        p.wait()

    def allow_node_exec(self, mac):
        cmd = ['gksudo', '{} {} allow'.format(os.path.join(sys.path[0], 'block.py'), mac)]
        p = subprocess.Popen(cmd)
        p.wait()

    def del_node_exec(self, mac):
        cmd = ['gksudo', '{} {} del'.format(os.path.join(sys.path[0], 'block.py'), mac)]
        p = subprocess.Popen(cmd)
        p.wait()

    def block_node(self):
        button = self.get_button("Block path")
        item = self.node_list.currentItem()
        data = item.data(Qt.UserRole)
        data[13] = button.isChecked()
        item.setData(Qt.UserRole, data)
        if button.isChecked():
            pass_button = self.get_button("Pass path")
            if pass_button.isChecked():
                pass_button.setChecked(False)
                self.pass_node()

            self.block_node_exec(data[11])
            item.setIcon(QIcon.fromTheme("stock_delete"))
            self.log.appendPlainText("Blocking OGMs directly from '{}'".format(item.text()))
        else:
            self.del_node_exec(data[11])
            item.setIcon(QIcon.fromTheme("network-idle"))
            self.log.appendPlainText("Unblocking OGMs directly from '{}'".format(item.text()))

    def pass_node(self):
        button = self.get_button("Pass path")
        item = self.node_list.currentItem()
        data = item.data(Qt.UserRole)
        data[14] = button.isChecked()
        item.setData(Qt.UserRole, data)
        if button.isChecked():
            button = self.get_button("Block path")
            if button.isChecked():
                button.setChecked(False)
                self.block_node()

            self.allow_node_exec(data[11])
            item.setIcon(QIcon.fromTheme("emblem-default"))
            self.allow_count += 1
            if self.allow_count == 1:
                self.log.appendPlainText("Allowing OGMs directly from '{}' only".format(item.text()))
            else:
                self.log.appendPlainText("Allowing OGMs direclty from '{}' also".format(item.text()))
        else:
            self.del_node_exec(data[11])
            item.setIcon(QIcon.fromTheme("network-idle"))
            self.allow_count -= 1
            if self.allow_count == 0:
                self.log.appendPlainText("Allowing OGMs from all non-blocked nodes")
            else:
                self.log.appendPlainText("Disallowing OGMs directly from '{}'".format(item.text()))


class nodelist(QMainWindow):
    def __init__(self, parent=None):
        super(nodelist, self).__init__(parent)
        self.setWindowTitle("Node Browser")

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

    def add_plotter(self, plotter):
        self.plotter = plotter
        l = self.centralWidget().layout()
        l.addWidget(self.plotter)
        l.setStretch(l.count()-1, 1)

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
        vbox.setStretch(0, 1.5)
        vbox.setStretch(1, 1.5)

        w = QWidget()
        w.setLayout(vbox)

        self.setCentralWidget(w)
        self.resize(800,600)
        self.show()

    def node_selected(self, idx):
        node_text = self.node_list.currentItem().text()
        node_data = self.node_list.currentItem().data(Qt.UserRole)
        self.node_info.set_node(node_text, node_data)
        self.node_actions.set_buttons(node_data)


if __name__ == "__main__":
    a = QApplication(sys.argv)
    m = nodelist()
    a.exec_()
