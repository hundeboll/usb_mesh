#!/usr/bin/env python2

import threading
import subprocess
import re
import time
import os
os.environ["QT_API"] = "pyside"
from PySide.QtCore import *
from PySide.QtGui import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import gridspec

class live_fig(QWidget):
    def __init__(self, title, ylabel, ylabel2=None, parent=None):
        super(live_fig, self).__init__(parent)
        self.gs = gridspec.GridSpec(1, 2, width_ratios=[1,5])
        self.clear_data()

        self.layout = QHBoxLayout()
        self.add_fig(title, ylabel, ylabel2)
        self.setLayout(self.layout)

    def on_draw(self, event):
        self.bg = self.canvas.copy_from_bbox(self.ax.bbox)

    def add_fig(self, title, ylabel, ylabel2=None):
        c = self.parent().palette().button().color()

        self.fig = Figure(facecolor=(c.redF(), c.greenF(), c.blueF()), edgecolor=(0,0,0))
        self.ax = self.fig.add_subplot(self.gs[1])
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True)
        self.ax.xaxis.set_ticks([])
        self.ax.set_aspect("auto")

        if ylabel2:
            ax2 = self.ax.twinx()
            ax2.set_ylabel(ylabel2)

        #self.ax.set_color_cycle(color_cycle.values())
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect('draw_event', self.on_draw)
        self.layout.addWidget(self.canvas, 10)

    def add_line(self, key):
        ax = self.fig.add_subplot(self.gs[0])
        ax.set_axis_off()
        ax.set_aspect("auto")
        self.lines[key], = self.ax.plot([0], [0], label=key.title(), animated=True)
        l = ax.legend(self.lines.values(), self.lines.keys(), "right")
        for t in l.get_texts():
            t.set_fontsize('medium')
        self.canvas.draw()

    def update_lines(self):
        if not self.bg:
            return

        self.canvas.restore_region(self.bg)
        for key in self.data:
            x,y = self.data[key]
            self.ax.set_xlim(x[0], x[-1])
            self.lines[key].set_data(x, y)
            self.ax.draw_artist(self.lines[key])

        self.canvas.blit(self.ax.bbox)

    def update_data(self, key, x, y):
        self.data[key] = (x, y)
        self.rescale(max(y))

    def clear_data(self):
        if hasattr(self, "lines"):
            # Remove lines from figure and reset color cycle
            for line in self.lines.values():
                line.remove()
            self.ax.set_color_cycle(color_cycle.values())

        # Clear data
        self.bg = None
        self.lines = {}
        self.data = {}

    def rescale(self, new_max):
        if not self.ax._cachedRenderer:
            return

        # Read minimum (d) and maximum (max_view) from plot
        d,max_view = self.ax.get_ybound()
        current_max = self.current_max()

        if new_max > max_view or (max_view > 10 and current_max*2 < max_view):
            # Scale axes if new maximum has arrived
            self.ax.relim()
            self.ax.autoscale_view(scalex=False)
            self.ax.draw_artist(self.ax.yaxis)
            self.update_lines()
            self.canvas.draw()

    def current_max(self):
        current_max = 0
        for line in self.lines.values():
            m = max(line.get_ydata())
            current_max = m if m > current_max else current_max
        return current_max


class plotter(QWidget):
    update_data = Signal(str, list, list)

    def __init__(self, parent=None):
        super(plotter, self).__init__(parent)

        self.update_data.connect(self._update_data)
        self.add_fig("Samples", "kbit/s", "packets")
        self.add_legend()
        self.do_layout()
        self.startTimer(1000)

    def timerEvent(self, event):
        self.fig.update_lines()

    def add_fig(self, title, ylabel, ylabel2=None):
        fig = live_fig(title, ylabel, ylabel2, parent=self)
        self.fig = fig

    def add_legend(self):
        c = self.palette().button().color()
        legend = {}
        legend['fig'] = Figure(facecolor=(c.redF(), c.greenF(), c.blueF()), edgecolor=(0,0,0))
        legend['canvas'] = FigureCanvas(legend['fig'])
        self.legend = legend

    def do_layout(self):
        b = QHBoxLayout()
        b.addWidget(self.fig)
        self.setLayout(b)

    @Slot(str, list, list)
    def _update_data(self, key, x, y):
        if key not in self.fig.data:
            self.fig.add_line(key)
            self.add_line(key)
        self.fig.update_data(key, x, y)

    def add_line(self, key):
        handles,labels = self.fig.ax.get_legend_handles_labels()
        self.legend['fig'].legend(handles, labels, ncol=1, loc='center left')
        self.legend['canvas'].draw()


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

        self.start()

    def add_plotter(self, plotter):
        self.plotter = plotter

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
        self.process_rate("nc_code_bytes")
        self.process_rate("nc_decode_bytes")

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

        if self.plotter:
            self.plotter.update_data.emit(key, self.timestamps, self.bytes[key])

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

        if self.plotter:
            self.plotter.update_data.emit(key, self.timestamps, self.bytes[key])

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

            # Generate a key specific to this mac and count, ylim, scale, show, er
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
    p = plotter()
    s = stats()
    s.add_plotter(p)
    p.show()
    app.exec_()
    s.stop()
