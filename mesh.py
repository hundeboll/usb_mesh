#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import subprocess
import re
import time
import subprocess
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

        mail_edit  = QLineEdit()
        mail_label = QLabel("&Email:")
        mail_label.setBuddy(mail_edit)
        self.registerField("user_mail", mail_edit)

        org_edit  = QLineEdit()
        org_label = QLabel("&Organisation:")
        org_label.setBuddy(org_edit)
        self.registerField("user_org", org_edit)

        self.add_networks_combo()

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
        QTimer.singleShot(10, self.find_devices)
        dev_label = QLabel("&Device:")
        dev_label.setBuddy(self.dev_combo)
        self.parent.set_object("network_dev", self.dev_combo)



        grid = QGridLayout()
        grid.addWidget(name_label, 0,0)
        grid.addWidget(name_edit,  0,1)
        grid.addWidget(mail_label, 1,0)
        grid.addWidget(mail_edit,  1,1)
        grid.addWidget(org_label,  2,0)
        grid.addWidget(org_edit,   2,1)
        grid.addWidget(dev_label,  3,0)
        grid.addWidget(self.dev_combo,  3,1)
        grid.addWidget(filter_label, 4,0)
        grid.addLayout(filter_hbox, 4,1)
        grid.addWidget(ssid_label,  5,0)
        grid.addWidget(self.box, 5,1)
        grid.addWidget(self.key_label, 6,0)
        grid.addWidget(self.key_edit, 6,1)
        self.setLayout(grid)

    def find_devices_(self):
        # Read devices from "iw"
        cmd = ["nm-tool"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()

        # Parse devices from output
        match = re.findall("Device: (\w+)\s.+\s+Type:\s+802\.11 WiFi\s+Driver:\s+(\w+)", out)
        for dev,drv in match:
            # Parse network from output
            nets = re.findall(ur"Device: {}.+?Wireless Access Points.+?$(.+?)^$".format(dev),
                    out, re.DOTALL | re.MULTILINE)
            ssids = []
            for line in nets[0].split("\n"):
                ssid = re.findall("\s+([\w -æøå]+):\s+([\w-]+?), ([A-F0-9:]{17}), Freq (\d+) MHz, Rate (\d+\.?\d?) Mb/s, Strength (\d+) ?(\w+)?", line)
                if ssid:
                    ssids.extend(ssid)
            self.dev_combo.addItem("{} - {}".format(dev, drv), [dev, ssids])

    def find_devices(self):
        # Get devices
        cmd = ["iw", "dev"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()

        devs = re.findall("Interface (\w+)", out)
        for dev in devs:
            # Get drivername
            cmd = ["ethtool", "-i", dev]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()
            out,err = p.communicate()
            drv = re.findall("driver: ([\w\- ]+)", out)

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
            for net in nets[1:]:
                # Read data about SSID
                ssid = []
                data = re.findall("([a-f0-9:]{17}).+?freq: (\d+).+?capability: (\w+).+?signal: ([-\.\d]+).+?SSID: ([\w -]+)", net, re.DOTALL)
                if not data:
                    continue

                # Get encryption
                enc = re.findall("(WPA|WEP)", net) or ["None"]
                ssid.extend(data[0])
                ssid.extend(enc)
                ssids.append(ssid)
            self.dev_combo.addItem("{} - {}".format(dev, drv[0]), [dev, ssids])

    def update_networks(self, idx):
        self.model.removeRows(0, self.model.rowCount())

        data = self.dev_combo.itemData(idx)
        for row in data[1]:
            ssid = row[4]
            mode = "Ad-hoc" if row[2] == "IBSS" else "Infra"
            enc  = row[5]
            signal = row[3]
            items = [QStandardItem(data) for data in [ssid, mode, signal, enc]]
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
        model.setHorizontalHeaderLabels(["SSID", "Mode", "Signal", "Enc"])
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
        self.enc_proxy.setFilterKeyColumn(3)
        self.view.resizeColumnsToContents()


class finish_page(QWizardPage):
    def __init__(self, parent=None):
        super(finish_page, self).__init__(parent)
        self.parent = parent
        self.config = "/tmp/wpa_tmp.conf"

        self.setTitle("Applying Configuration")
        self.setSubTitle("Making your choices real.")

        status_label = QLabel("Status:")
        self.status_text  = QLabel("Please Wait")

        grid = QGridLayout()
        grid.addWidget(status_label, 0,0)
        grid.addWidget(self.status_text,  0,1)
        self.setLayout(grid)

    def initializePage(self):
        QTimer.singleShot(100, self.apply_config)

    def apply_config(self):
        self.status_text.setText("Connecting to wireless")
        self.status_text.repaint()

        dev,data = self.get_data()
        self.ifdown(dev)
        self.write_wpa_config(data)
        self.start_wpa(dev)
        self.config_dev(dev)
        self.config_bat0(dev)
        self.ifup(dev)
        self.ifup("bat0")

        self.status_text.setText("Sending information")

    def get_data(self):
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

        # Connect to network
        if data[2] == 'ESS':
            data[2] = "Managed"
        elif data[2] == 'IBSS':
            data[2] = "Ad-hoc"

        return dev,data

    def ifdown(self, dev):
        cmd = ['gksudo', 'ifconfig', dev, 'down']
        p = subprocess.Popen(cmd)
        p.wait()

    def ifup(self, dev):
        cmd = ['gksudo', 'ifconfig', dev, 'up']
        p = subprocess.Popen(cmd)
        p.wait()

    def write_wpa_config(self, data):
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

        f = open(self.config, 'w')
        f.write(n)
        f.close()

    def start_wpa(self, dev):
        cmd = ['ps', 'ax']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()
        pid = re.findall("^(\d+).+?wpa_supplicant -B -i {} -c {}".format(dev, self.config), out, re.MULTILINE)

        if pid:
            print(pid)
            cmd = ['gksudo', 'kill', pid[0]]
            p = subprocess.Popen(cmd)
            p.wait()

        cmd = ['gksudo', 'wpa_supplicant -B -i {} -c {}'.format(dev, self.config)]
        p = subprocess.Popen(cmd)
        p.wait()

    def config_dev(self, dev):
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
        cmd = ['gksudo', 'batctl', 'if', 'add', dev]
        p = subprocess.Popen(cmd)
        p.wait()

        cmd = ['gksudo', 'avahi-autoipd --kill --force-bind --daemonize --wait bat0']
        p = subprocess.Popen(cmd)
        p.wait()


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
