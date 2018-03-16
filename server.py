import socket
import asyncore
import json
import re
import struct
from subprocess import Popen, check_output, PIPE, run
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, default=-1,
                    help="Run monitoring server on a specific port")
parser.add_argument("-n", "--no-reboot", dest='noreboot', action='store_true',
                    help="Don't really reboot system")
args = parser.parse_args()

def getPort():
#Getting port from config, command line arguments or assuming default port(8000)
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
#Parsing utilites output with regular expressions
    result = {}
    result["uptime"] = re.search(r'up (.+),[ 0-9]+user', dic["uptime"]).group(1)
    result["time"] = re.search(r'([0-9+]+:[0-9+]+:[0-9]+) up', dic["uptime"]).group(1)
    result["load_avg"] = re.search(r'([0-9.]+, [0-9.]+, [0-9.]+)', dic["uptime"]).group(1)
    result["cpu"] = '{0:.2f}'.format(100 - float(re.search(r'([0-9.]+) id', dic["cpu"]).group(1)))
    result["total_memory"] = re.search(r'([0-9]+) K total memory', dic["ram"]).group(1)
    result["used_memory"] = re.search(r'([0-9]+) K used memory', dic["ram"]).group(1)
    result["free_memory"] = re.search(r'([0-9]+) K free memory', dic["ram"]).group(1)
    result["hostname"] = dic["host"]
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

print("Running server on %i port" % getPort())


def wol(string):
#Creating and sending Wake-On-LAN magic packet
    string = re.sub(r'-', ':', string)
    splitMac = str.split(string,':')
    print('Sending WOL magic packet to %s' % string)
        # Pack together the sections of the MAC address as binary hex
    hexMac = struct.pack(b'BBBBBB', int(splitMac[0], 16),
                             int(splitMac[1], 16),
                             int(splitMac[2], 16),
                             int(splitMac[3], 16),
                             int(splitMac[4], 16),
                             int(splitMac[5], 16))
    packet = '\xff' * 6 + string * 16 #create the magic packet from MAC address
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(bytes(packet, 'utf-8'),('255.255.255.255', 65535))
    s.close()


class SrvHandler(asyncore.dispatcher_with_send):

    def handle_read(self):
        data = self.recv(512)
        if data == b'fetch':
            out = {}
            out["uptime"] = str(check_output("uptime"), 'utf-8')
            out["df"]     = str(check_output("df"), 'utf-8')
            out["ram"]    = str(check_output(["vmstat", "-s"]), 'utf-8')
#top -b -n 1 |grep ^Cpu
            top          = check_output(["top", "-b", "-n", "1"])
            out["cpu"]    = str(run(["grep", 'Cpu'], stdout=PIPE, input=top).stdout, 'utf-8')
            out["host"]   = str(check_output("hostname"), 'utf-8')
            self.send(bytes(json.dumps(reg(out)), 'utf-8'))
        elif data == b'reboot':
            if not args.noreboot:
                check_output(['reboot'])
            self.send(bytes('{"reply":"Rebooting..."}', 'utf-8'))
        elif data == b'kill':
            self.send(bytes('{"reply":"Terminated by client."}', 'utf-8'))
            exit()
        elif re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', str(data, 'utf-8')): #If received MAC-address-like string
            self.send(bytes('{"reply":"Sending WOL."}', 'utf-8'))
            wol(str(data, 'utf-8'))
        else:
            print(data)

class MonServer(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print('Incoming connection from %s' % repr(addr))
            handler = SrvHandler(sock)

server = MonServer('', getPort())
asyncore.loop()
