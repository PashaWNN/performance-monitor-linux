import socket
import json
import sys
import argparse
import re
from PyQt5.QtWidgets import (QWidget, QLabel,
    QComboBox, QApplication, QPushButton, QInputDialog, QErrorMessage, QMessageBox)
from pathlib import Path

class MonitorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    def initUI(self):
        self.setGeometry(50, 50, 500, 500)
        self.setWindowTitle('Monitor')
        addBtn = QPushButton('Add server', self)
        addBtn.setGeometry(5, 40, 200, 25)
        addBtn.clicked.connect(self.addServerDialog)
        remBtn = QPushButton('Remove server', self)
        remBtn.setGeometry(5, 70, 200, 25)
        remBtn.clicked.connect(self.remCurrentServer)
        self.combo = QComboBox(self)
        self.combo.setGeometry(5, 5, 200, 30)
        self.combo.activated[str].connect(self.onActivated)
        self.show()

        
    def onActivated(self, text):
        print('Connecting to ', text)
######################TODO
    def addServerDialog(self):
        text, ok = QInputDialog.getText(self, 'Add server', 'Enter server IP:')
        if ok:
            self.addServer(parseIP(text))
    def addServer(self, ip):
        string = ip[0]
        if not ip[1] == '': string += ':' + ip[1]
        self.combo.addItems([string])
        print('Added ', string, ' to the list')
    def remCurrentServer(self):
        print('Deleting server from the list')
        self.combo.removeItem(self.combo.currentIndex())


def parseIP(string):
    if re.match(r'^([0-9A-Za-z\.]+):?(\d{0,4})$', string):
        return re.findall(r'([0-9A-Za-z\.]+):?(\d{0,4})', string)[0]
    else:
        raise KeyError('Invalid IP!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", type=str, default='no',
                        help="Connect to specific address instead of listed in config\nE.g. 127.0.0.1:8000")
    parser.add_argument("-c", "--config", type=str, default='config.json',
                        help="Load config from specific file.\nDefault is config.json")
    parser.add_argument("-t", "--text", dest='textMode', action='store_true',
                        help="Don't initialize UI, work in terminal")
    args = parser.parse_args()
    if not args.textMode:
        app = QApplication(sys.argv)
        w = MonitorUI()
    if args.address == 'no':
        file = Path(args.config)
        if file.is_file():
            with open(args.config, "r") as json_file:
                ips = json.load(json_file)
        else: ips = {'list':[]}
    else: ips = {'list': [parseIP(args.address)]}
    
    for ip in ips['list']:
        if args.textMode:
            print(ip[0], ':', ip[1], '\n')
            sock = socket.socket()
            sock.connect((ip[0], int(ip[1])))
            print('Connected.')
            string = input('Enter command(fetch, reboot, wol-multicast, kill): ')
            sock.send(bytes(string, 'utf-8'))
            result = json.loads(str(sock.recv(4096), 'utf-8'))
            sock.close()
            print(result)
        else:
            w.addServer(ip)

    if not args.textMode:
        sys.exit(app.exec_())
    
