#!/usr/bin/python2

import subprocess
import json

def get_vis_data():
    cmd = ['sudo', 'batctl', 'vd', 'json']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    (stdout,stderr) = p.communicate()
    return stdout

def parse_vis_data(data):
    d = []
    for line in data.split("\n"):
        if not line:
            continue
        d.append(json.loads(line))
    return d

def print_vis_data(data):
    print("Content-type: application/json\n")
    print(json.dumps(data))

if __name__ == "__main__":
    data = get_vis_data()
    j = parse_vis_data(data)
    print_vis_data(j)
