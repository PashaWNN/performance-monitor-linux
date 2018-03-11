import socket
import json
import re
from subprocess import Popen, check_output, PIPE, run
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, default=-1,
                    help="Run monitoring server on a specific port")
parser.add_argument("-n", "--no-reboot", dest='noreboot',
                    help="Don't really reboot system")
args = parser.parse_args()

def getPort():
    file = Path("config.json")
    if file.is_file():
        with open("config.json", "r") as json_file:
            j = json.load(json_file)
    else:
        j = {}
    if args.port == -1:
        try:
            port = j["port"]
        except KeyError:
            port = 8000
    else:
        port = args.port
    return port

def reg(dic):
    result = {}
    result["uptime"] = re.search(r'up (.+),[ 0-9]+user', dic["uptime"]).group(1)
    result["time"] = re.search(r'([0-9+]+:[0-9+]+:[0-9]+) up', dic["uptime"]).group(1)
    result["load_avg"] = re.search(r'([0-9.]+, [0-9.]+, [0-9.]+)', dic["uptime"]).group(1)
    result["cpu"] = dic["cpu"]
    result["total_memory"] = re.search(r'([0-9]+) K total memory', dic["ram"]).group(1)
    result["used_memory"] = re.search(r'([0-9]+) K used memory', dic["ram"]).group(1)
    result["free_memory"] = re.search(r'([0-9]+) K free memory', dic["ram"]).group(1)
    disks = {}
    for i, m in enumerate(re.findall(r'([^ \\]+)[ ]+([0-9]+)[ ]+([0-9]+)[ ]+([0-9]+)[ ]+([0-9]+)%[ ]+([^ ]+)\n', dic["df"])):
        disk = {}
        disk["filesystem"] = m[0]
        disk["1k_blocks"]  = m[1]
        disk["used"]       = m[2]
        disk["available"]  = m[3]
        disk["use"]        = m[4]
        disk["mounted_on"] = m[5]
        disks[str(i)] = disk
    result["disks"] = disks
    return result

sock = socket.socket()
sock.bind(('', getPort()))
print("Running server on %i port" % getPort())

while True:
    sock.listen(1)
    conn, addr = sock.accept()
    print('Connected:', addr)
    data = conn.recv(1024)
    if data == b'fetch':
        out = {}
        out["uptime"] = str(check_output("uptime"), 'utf-8')
        out["df"] =  str(check_output("df"), 'utf-8')
        out["ram"] =    str(check_output(["vmstat", "-s"]), 'utf-8')
        grep =          check_output(["grep", "cpu ", "/proc/stat"])
        out["cpu"] =    str(run(["awk", '{usage=($2+$4)*100/($2+$4+$5)} END {print usage "%"}'], stdout=PIPE, input=grep).stdout, 'utf-8')
        conn.send(bytes(json.dumps(reg(out)), 'utf-8'))
    elif data == b'reboot':
        #TODO: Reboot
        if not args.noreboot:
            check_output(['reboot'])
        conn.send(bytes('{"reply":"Rebooting..."}', 'utf-8'))
    elif data == b'kill':
        conn.send(bytes('{"reply":"Terminated by client."}', 'utf-8'))
        break
    elif data == b'wol-multicast':
        conn.send(bytes('{"reply":"Sending WOL."}', 'utf-8'))
        #TODO: Wake-On-Lan to 255.255.255.255
    else:
        print(data)
conn.close()
