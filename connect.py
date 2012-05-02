#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import re
import threading
from PySide.QtCore import *
from PySide.QtGui import *

class combobox(QComboBox):
    def __init__(self, parent=None):
        super(combobox, self).__init__(parent)

    def currentData(self):
        return self.itemData(self.currentIndex())


class intro_page(QWizardPage):
    def __init__(self, parent=None):
        super(intro_page, self).__init__(parent)

        self.setTitle("Mesh Configuration Wizard")
        self.setSubTitle("This wizard will help you configure your network.")

        layout = QVBoxLayout()
        self.setLayout(layout)


class config_page(QWizardPage):
    def __init__(self, parent=None):
        super(config_page, self).__init__(parent)
        self.parent = parent

        self.setTitle("Personal Information")
        self.setSubTitle("Your information visible to other users.")
        self.setCommitPage(True)

        name_edit  = QLineEdit()
        name_label = QLabel("&Name:")
        name_label.setBuddy(name_edit)
        self.registerField("user_name*", name_edit)

        org_edit  = QLineEdit()
        org_label = QLabel("&Organisation:")
        org_label.setBuddy(org_edit)
        self.registerField("user_org", org_edit)

        self.add_networks_combo()
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_button.clicked.connect(self.find_devices_thread)

        adhoc_check = QCheckBox()
        adhoc_check.stateChanged.connect(self.filter_adhoc_networks)
        adhoc_check.setChecked(True)
        adhoc_label = QLabel("&Ad-Hoc Only:")
        adhoc_label.setBuddy(adhoc_check)
        enc_check   = QCheckBox()
        enc_check.stateChanged.connect(self.filter_enc_networks)
        enc_check.setChecked(True)
        enc_check.setChecked(True)
        enc_label   = QLabel("En&cryption Off:")
        enc_label.setBuddy(enc_check)
        filter_label = QLabel("Filters:")
        filter_hbox = QHBoxLayout()
        filter_hbox.addWidget(adhoc_label)
        filter_hbox.addWidget(adhoc_check)
        filter_hbox.addWidget(enc_label)
        filter_hbox.addWidget(enc_check)

        self.key_edit = QLineEdit()
        self.key_label = QLabel("&Key phrase")
        self.key_label.setBuddy(self.key_edit)
        self.registerField("network_psk", self.key_edit)


        ssid_label = QLabel("Ne&twork:")
        ssid_label.setBuddy(self.box)
        self.ssid_current = None
        self.parent.set_object("network_ssid", self.box)
        self.parent.set_object("network_item", self.ssid_current)

        self.dev_combo = combobox()
        self.dev_combo.currentIndexChanged.connect(self.update_networks)
        self.find_devices_thread()
        dev_label = QLabel("&Device:")
        dev_label.setBuddy(self.dev_combo)
        self.parent.set_object("network_dev", self.dev_combo)


        ssid_hbox = QHBoxLayout()
        ssid_hbox.addWidget(self.box)
        ssid_hbox.addWidget(self.refresh_button)
        ssid_hbox.setStretch(0, 1)
        ssid_hbox.setStretch(1, 0)

        grid = QGridLayout()
        grid.addWidget(name_label, 0,0)
        grid.addWidget(name_edit,  0,1)
        grid.addWidget(org_label,  1,0)
        grid.addWidget(org_edit,   1,1)
        grid.addWidget(dev_label,  2,0)
        grid.addWidget(self.dev_combo,  2,1)
        grid.addWidget(filter_label, 3,0)
        grid.addLayout(filter_hbox, 3,1)
        grid.addWidget(ssid_label,  4,0)
        grid.addLayout(ssid_hbox, 4,1)
        grid.addWidget(self.key_label, 5,0)
        grid.addWidget(self.key_edit, 5,1)
        self.setLayout(grid)

    def find_devices_thread(self):
        if hasattr(self, "t") and self.t.is_alive():
            return
        self.t = threading.Thread(None, self.find_devices)
        self.t.start()

    def find_devices(self):
        # Clear devices
        self.refresh_button.setEnabled(False)
        self.dev_combo.clear()
        self.dev_combo.addItem("Please wait...")

        # Get devices
        cmd = ["iw", "dev"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()

        devs = re.findall("Interface (\w+)", out)
        for dev in devs:
            drv = self.find_driver(dev)
            ssids = self.find_networks(dev)
            self.dev_combo.addItem("{} - {}".format(dev, drv), [dev, ssids])
        self.dev_combo.removeItem(0)
        self.dev_combo.setCurrentIndex(0)
        self.refresh_button.setEnabled(True)

    def find_driver(self, dev):
        # Get drivername
        cmd = ["ethtool", "-i", dev]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()
        drv = re.findall("driver: ([\w\- ]+)", out)
        return drv[0] if drv else "Unknown"

    def find_networks(self, dev):
        # Get scan result
        cmd = ["gksudo", "ip", "link", "set", "dev", dev, "up"]
        p = subprocess.Popen(cmd)
        cmd = ["gksudo", "iw", "dev", dev, "scan"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()

        # Split for each SSID
        nets = re.split("\nBSS", out)
        ssids = []
        for net in nets:
            # Read data about SSID
            ssid = []
            data = re.findall("([a-f0-9:]{17}).+?freq: (\d+).+?capability: (\w+).+?signal: ([-\.\d]+).+?SSID: ([\w -æøå]+)", net, re.DOTALL)
            if not data:
                continue

            # Get encryption
            enc = re.findall("(WPA|WEP|PSK)", net) or ["None"]
            ssid.extend(data[0])
            ssid.extend(enc)
            ssids.append(ssid)
        return ssids

    def update_networks(self, idx):
        self.model.removeRows(0, self.model.rowCount())

        data = self.dev_combo.itemData(idx)
        if not data:
            return
        for row in data[1]:
            ssid = row[4]
            mode = "Ad-hoc" if row[2] == "IBSS" else "Infra"
            enc  = row[5]
            signal = row[3]
            items = [QStandardItem(data) for data in [ssid, mode, enc]]
            [item.setData(row) for item in items]
            self.model.appendRow(items)

        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.resizeColumnsToContents()
        self.view.selectRow(0)

    def add_networks_combo(self):
        box = combobox()
        box.setObjectName('somename')
        box.currentIndexChanged.connect(self.update_index)

        view = QTableView()
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["SSID", "Mode", "Enc"])
        adhoc_proxy = QSortFilterProxyModel()
        adhoc_proxy.setSourceModel(model)
        enc_proxy = QSortFilterProxyModel()
        enc_proxy.setSourceModel(adhoc_proxy)
        view.setModel(enc_proxy)

        # Do with the view whatever you like
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.verticalHeader().setVisible(False)
        #view.horizontalHeader().hide()
        view.setShowGrid(False)
        self.parent.set_object("network_view", view)

        # The important part: First set the model, then the view on the box
        box.setModel(enc_proxy)
        box.setView(view)

        self.box = box
        self.model = model
        self.adhoc_proxy = adhoc_proxy
        self.enc_proxy = enc_proxy
        self.view = view

    def update_index(self, idx):
        self.view.selectRow(idx)

        model = self.enc_proxy
        idx = self.view.currentIndex()
        while hasattr(model, 'sourceModel'):
            idx = model.mapToSource(idx)
            model = model.sourceModel()

        if not model.itemFromIndex(idx):
            return

        data = model.itemFromIndex(idx).data()

        if data[5] != "None":
            self.key_edit.setVisible(True)
            self.key_label.setVisible(True)
        else:
            self.key_edit.setVisible(False)
            self.key_label.setVisible(False)

    def filter_adhoc_networks(self, b):
        f = "Ad-hoc" if b else ""
        self.adhoc_proxy.setFilterRegExp(QRegExp(f))
        self.adhoc_proxy.setFilterKeyColumn(1)
        self.view.resizeColumnsToContents()

    def filter_enc_networks(self, b):
        f = "None" if b else ""
        self.enc_proxy.setFilterRegExp(QRegExp(f))
        self.enc_proxy.setFilterKeyColumn(2)
        self.view.resizeColumnsToContents()


class finish_page(QWizardPage):
    def __init__(self, parent=None):
        super(finish_page, self).__init__(parent)
        self.parent = parent
        self.complete = False
        self.pidgin = None

        self.setTitle("Applying Configuration")
        self.setSubTitle("Making your choices real.")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.appendPlainText("Please wait...")

        grid = QGridLayout()
        grid.addWidget(self.log)
        self.setLayout(grid)

    def initializePage(self):
        QTimer.singleShot(100, self.apply_config)

    def isComplete(self):
        return self.complete

    def setComplete(self, b):
        self.complete = b
        self.completeChanged.emit()
        self.log.appendPlainText("Configuration complete")

    def apply_config_thread(self):
        self.t = threading.Thread(None, self.apply_config)
        self.t.start()

    def apply_config(self):
        dev,data = self.get_data()
        self.construct_config_paths(dev)
        self.ifdown(dev)
        self.write_wpa_config(data)
        self.start_wpa(dev)
        self.config_dev(dev)
        self.config_bat0(dev)
        self.ifup(dev)
        self.ifup("bat0")
        self.write_avahi_config()
        self.start_avahi()
        self.write_pidgin_config()
        self.start_pidgin()
        self.setComplete(True)

    def get_data(self):
        self.log.appendPlainText("Getting config data")
        # Get device name
        dev_combo = self.parent.get_object("network_dev")
        dev = dev_combo.currentData()[0]

        # Get network data
        ssid_combo = self.parent.get_object("network_ssid")
        view = self.parent.get_object("network_view")
        model = view.model()
        idx = view.currentIndex()
        while hasattr(model, 'sourceModel'):
            idx = model.mapToSource(idx)
            model = model.sourceModel()
        data = model.itemFromIndex(idx).data()

        if data[2] == 'ESS':
            data[2] = "Managed"
        elif data[2] == 'IBSS':
            data[2] = "Ad-hoc"

        return dev,data

    def construct_config_paths(self, dev):
        self.wpa_config = "/tmp/wpa_{}_tmp.conf".format(dev)
        self.avahi_config = "/tmp/avahi_{}_tmp.conf".format(dev)
        self.pidgin_path = "/tmp/purple_{}_tmp".format(dev)
        self.pidgin_config = self.pidgin_path + "/accounts.xml"
        if not os.path.exists(self.pidgin_path):
            os.mkdir(self.pidgin_path)

    def ifdown(self, dev):
        cmd = ['gksudo', 'ifconfig', dev, 'down']
        p = subprocess.Popen(cmd)
        p.wait()

    def ifup(self, dev):
        cmd = ['gksudo', 'ifconfig', dev, 'up']
        p = subprocess.Popen(cmd)
        p.wait()

    def write_wpa_config(self, data):
        self.log.appendPlainText("Writing configuration for wpa_supplicant")
        n  = 'network={\n'
        n += '\tssid="{}"\n'.format(data[4])
        if data[2] == 'Ad-hoc':
            n += '\tmode=1\n'
            n += '\tfrequency={}\n'.format(data[1])
            n += '\tkey_mgmt=NONE\n'
        else:
            n += '\tmode=0\n'
            if data[5] != "None":
                n += '\tpsk="{}"\n'.format(self.field("network_psk"))
        n += '}\n'

        f = open(self.wpa_config, 'w')
        f.write(n)
        f.close()

    def start_wpa(self, dev):
        self.log.appendPlainText("Connecting to network")
        cmd = ['ps', 'ax']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()
        pid = re.findall("^(\d+).+?wpa_supplicant -B -i {} -c {}".format(dev, self.wpa_config), out, re.MULTILINE)

        if pid:
            cmd = ['gksudo', 'kill', pid[0]]
            p = subprocess.Popen(cmd)
            p.wait()

        cmd = ['gksudo', 'wpa_supplicant -B -i {} -c {}'.format(dev, self.wpa_config)]
        p = subprocess.Popen(cmd)
        p.wait()

    def config_dev(self, dev):
        self.log.appendPlainText("Configuring interface")
        cmd = ['gksudo', 'ip', 'link', 'set', 'dev', dev, 'promisc', 'on']
        p = subprocess.Popen(cmd)
        p.wait()
        cmd = ['gksudo', 'ip', 'link', 'set', 'dev', dev, 'mtu', '1600']
        p = subprocess.Popen(cmd)
        p.wait()
        cmd = ['gksudo', 'ip', 'link', 'set', 'dev', dev, 'txqueuelen', '100']
        p = subprocess.Popen(cmd)
        p.wait()

    def config_bat0(self, dev):
        self.log.appendPlainText("Configuring batman-adv")
        cmd = ['gksudo', 'batctl', 'if', 'add', dev]
        p = subprocess.Popen(cmd)
        p.wait()

        cmd = ['gksudo', 'batctl', 'nc', 'st', '1']
        p = subprocess.Popen(cmd)
        p.wait()

        self.log.appendPlainText("Acquiring IP address")
        cmd = ['gksudo', 'avahi-autoipd --force-bind --daemonize --wait bat0']
        p = subprocess.Popen(cmd)
        p.wait()

    def write_avahi_config(self):
        self.log.appendPlainText("Writing Avahi configuration")

        n  = "[server]\n"
        n += "host-name={} {}\n".format(self.field("user_name"), self.field("user_org"))
        n += "use-ipv4=yes\n"
        n += "use-ipv6=no\n"
        n += "allow-interfaces=bat0\n"
        n += "ratelimit-interval-usec=1000000\n"
        n += "ratelimit-burst=1000\n"
        n += "\n"
        n += "[wide-area]\n"
        n += "enable-wide-area=no\n"
        n += "\n"
        n += "[publish]\n"
        n += "disable-publishing=no\n"
        n += "disable-user-service-publishing=no\n"
        n += "add-service-cookie=no\n"
        n += "publish-addresses=yes\n"
        n += "publish-hinfo=no\n"
        n += "publish-workstation=yes\n"
        n += "publish-domain=no\n"
        n += "publish-resolv-conf-dns-servers=no\n"
        n += "publish-aaaa-on-ipv4=no\n"
        n += "publish-a-on-ipv6=no\n"
        n += "\n"
        n += "[rlimits]\n"
        n += "rlimit-core=0\n"
        n += "rlimit-data=4194304\n"
        n += "rlimit-fsize=0\n"
        n += "rlimit-nofile=768\n"
        n += "rlimit-stack=4194304\n"
        n += "rlimit-nproc=3\n"

        f = open(self.avahi_config, "w")
        f.write(n)
        f.close()

    def start_avahi(self):
        self.log.appendPlainText("Publishing node")
        cmd = ['gksudo', 'avahi-daemon -f {} --daemonize'.format(self.avahi_config)]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

    def write_pidgin_config(self):
        self.log.appendPlainText("Writing Pidgin configuration")

        s = "<?xml version='1.0' encoding='UTF-8' ?>\n"
        s += "\n"
        s += "<account version='1.0'>\n"
        s += "\t<account>\n"
        s += "\t\t<protocol>prpl-bonjour</protocol>\n"
        s += "\t\t<name>mesh</name>\n"
        s += "\t\t<settings>\n"
        s += "\t\t\t<setting name='port' type='int'>5298</setting>\n"
        s += "\t\t\t<setting name='first' type='string'>{} {}</setting>\n".format(self.field("user_name"), self.field("user_org"))
        s += "\t\t</settings>\n"
        s += "\t\t<settings ui='gtk-gaim'>\n"
        s += "\t\t\t<setting name='auto-login' type='bool'>1</setting>\n"
        s += "\t\t</settings>\n"
        s += "\t</account>\n"
        s += "</account>\n"

        f = open(self.pidgin_config, "w")
        f.write(s)
        f.close()

    def start_pidgin(self):
        self.log.appendPlainText("Starting Pidgin")
        cmd = ["pidgin", "-m", "-c", self.pidgin_path]
        self.pidgin = subprocess.Popen(cmd)

    def stop(self):
        if self.pidgin:
            self.pidgin.kill()


class wizard(QWizard):
    def __init__(self, parent=None):
        super(wizard, self).__init__(parent)
        self.setWindowTitle("Mesh Configuration Wizard")
        self.setOption(QWizard.NoBackButtonOnStartPage, True)

        self.objects = {}

        self.intro_id  = self.addPage(intro_page(self))
        self.config_id = self.addPage(config_page(self))
        self.finish_id = self.addPage(finish_page(self))

        self.show()

    def stop(self):
        self.page(self.finish_id).stop()

    def set_object(self, name, obj):
        self.objects[name] = obj

    def get_object(self, name):
        return self.objects.get(name, None)


class mesh(QApplication):
    def __init__(self, argv):
        super(mesh, self).__init__(argv)
        self.w = wizard()
        self.exec_()


if __name__ == "__main__":
    try:
        m = mesh(sys.argv)
    except KeyboardInterrupt:
        pass
