#!/usr/bin/env python2

import threading
import subprocess
import re
import time
from PySide.QtCore import *
from PySide.QtGui import *

class plots(QWidget):
    def __init__(self, parent=None):
        super(plots, self).__init__(parent)
        self.show()

    def update(self, key, x, y):
        pass

class stats(threading.Thread):
    def __init__(self):
        super(stats, self).__init__(None)
        self.end = threading.Event()
        self.samples = {}
        self.interval = 1
        self.gui = None

        self.start_time = time.time()
        self.timestamps = None
        self.vals = {}
        self.diff = {}
        self.diff_last = {}
        self.bytes = {}
        self.bytes_last = {}
        self.ratio = [0]*60
        self.coded_last = 0
        self.fwd_last = 0

    def set_gui(self, gui):
        self.gui = gui

    def run(self):
        while not self.end.is_set():
            # Time stamp
            start = time.time()
            self.add_timestamp(start)

            # Sample
            self.sample_stats()
            self.sample_iw()

            # Process
            self.process_samples()

            # Sleep interval minus processing time
            sleep = self.interval - (time.time() - start)
            if sleep > 0:
                time.sleep(sleep)

    def stop(self):
        self.end.set()

    def add_sample(self, sample):
        self.samples.update(sample)

    def process_samples(self):
        self.process_rate("forward_bytes")
        self.process_rate("mgmt_tx_bytes")
        self.process_rate("iw tx bytes")
        print(self.bytes["iw tx bytes"][-1])

    def add_timestamp(self, timestamp):
        if self.timestamps:
            # Just add new timestamp to ringbuffer
            self.timestamps.pop(0)
            self.timestamps.append(timestamp - self.start_time)
            return

        # Initialize timestamps from first sample
        rel_time = int(timestamp - self.start_time)
        times = range(rel_time - 60, rel_time)
        self.timestamps = times

    def process_rate(self, key):
        this_bytes = self.samples[key]*8 / 1024
        if key not in self.bytes_last:
            self.bytes_last[key] = this_bytes
            self.bytes[key] = [0]*60
            return

        this_time = self.timestamps[-1]
        last_time = self.timestamps[-2]
        bytes = (this_bytes - self.bytes_last[key]) / (this_time - last_time)
        self.bytes_last[key] = this_bytes
        self.bytes[key].pop(0)
        self.bytes[key].append(bytes)

        if self.gui:
            self.gui.update(key, self.timestamps, self.bytes[key])

    def process_diff(self, key):
        diff = self.samples[key]

        # Initialize last sample
        if key not in self.diff_last:
            self.diff_last[key] = diff
            self.diff[key] = [0]*60
            return

        # Calculate number and ratio since last sample
        this_diff = diff - self.diff_last[key]

        # Save values for use in next calculation
        self.diff_last[key] = diff

        # Update plot data
        self.diff[key].pop(0)
        self.diff[key].append(this_diff)

        if self.gui:
            self.gui.update(key, self.timestamps, self.bytes[key])

    def sample_stats(self):
        cmd = ["gksudo", "ethtool -S bat0"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()

        sample = {}
        for line in out.split("\n"):
            match = re.findall("\s+(\w+): (\d+)", line)
            if not match:
                continue
            key = match[0][0]
            val = match[0][1]
            sample[key] = int(val)
        self.add_sample(sample)

    def sample_iw(self):
        sample = {}

        # Run the command
        cmd = ["iw", "dev", "wlan0", "station", "dump"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        out,err = p.communicate()
        if not out:
            return

        # Parse the output
        for line in out.split('\n'):
            # Find the mac address for the next set of counters
            match = re.findall("((?:[0-9a-f]{2}:){5}[0-9a-f]{2})", line)
            if match:
                mac = "iw " + match[0]
                continue

            # Read out the counter for this line (for this mac)
            match = re.findall("\s+(.+):\s+(.+)", line)
            if not match:
                continue

            # Generate a key specific to this mac and counter
            mac_key = mac + " " + match[0][0]

            # We want integers to be integers
            try:
                # Try to convert
                val = int(match[0][1])

                # Okay, the convert did not fail, so compose the key
                key = "iw " + match[0][0]

                # Update or set the value for this counter
                if key in sample:
                    sample[key] += val
                else:
                    sample[key] = val
            except ValueError:
                # The convert failed, so just use the string version
                val = match[0][1]
            finally:
                # Set the value for this mac
                sample[mac_key] = val

        # Add the sample to the set
        self.add_sample(sample)


if __name__ == "__main__":
    app = QApplication([])
    p = plots()
    s = stats()
    s.set_gui(p)
    s.start()
    app.exec_()
    s.stop()
