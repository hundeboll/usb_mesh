#!/usr/bin/env python2

import sys
import avahi
import dbus
import dbus.mainloop.glib
from PySide.QtCore import *
from PySide.QtGui import *

import connect


class discover:
    def __init__(self, ):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.raw_server = self.bus.get_object('org.freedesktop.Avahi', '/')
        self.server = dbus.Interface(self.raw_server, 'org.freedesktop.Avahi.Server')

        dev = self.server.GetNetworkInterfaceIndexByName("bat0")
        path = self.server.ServiceBrowserNew(dev, avahi.PROTO_UNSPEC, '_workstation._tcp', 'local', 0)
        self.sbrowser = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, path), avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        self.sbrowser.connect_to_signal("ItemNew", self.myhandler)

    def service_resolved(self, *args):
        print 'service resolved'
        print 'name:', args[2]
        print 'address:', args[7]
        print 'port:', args[8]

    def print_error(self, *args):
        print 'error_handler'
        print args[0]

    def myhandler(self, interface, protocol, name, stype, domain, flags):
        print("Found service '{}' type '{}' domain '{}' ".format(name, stype, domain))

        self.server.ResolveService(interface, protocol, name, stype, domain, avahi.PROTO_UNSPEC, 0, reply_handler=self.service_resolved, error_handler=self.print_error)

class main_window(QMainWindow):
    def __init__(self, parent=None):
        super(main_window, self).__init__(parent)
        self.setWindowTitle("Node Browser")

        #self.wizard = connect.wizard()
        #self.wizard.exec_()

        self.discover = discover()

        self.show()


if __name__ == "__main__":
    a = QApplication(sys.argv)
    m = main_window()
    a.exec_()
