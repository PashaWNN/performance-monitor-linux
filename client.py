import socket
import json
import sys
import argparse
import re
from PyQt5.QtWidgets import (QWidget, QLabel,
    QComboBox, QApplication, QPushButton, QInputDialog)
from PyQt5.QtCore import QTimer
from pathlib import Path

class MonitorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    def initUI(self):
        self.setGeometry(50, 50, 415, 500)
        self.setWindowTitle('Monitor')
        self.combo = QComboBox(self)
        self.combo.setGeometry(5, 5, 200, 25)
        self.combo.activated[str].connect(self.onActivated)
        self.addBtn = QPushButton('Add server', self)
        self.addBtn.setGeometry(5, 35, 200, 25)
        self.addBtn.clicked.connect(self.addServerDialog)
        
        self.remBtn = QPushButton('Remove server', self)
        self.remBtn.setGeometry(5, 65, 200, 25)
        self.remBtn.clicked.connect(self.remCurrentServer)

        self.disBtn = QPushButton('Disconnect', self)
        self.disBtn.setGeometry(5, 470, 200, 25)
        self.disBtn.clicked.connect(self.disconnect)

        self.rebBtn = QPushButton('Reboot server', self)
        self.rebBtn.setGeometry(210, 5, 200, 25)
        self.rebBtn.clicked.connect(lambda: self.send('reboot'))

        self.kilBtn = QPushButton('Kill server monitor', self)
        self.kilBtn.setGeometry(210, 35, 200, 25)
        self.kilBtn.clicked.connect(lambda: self.send('kill'))

        self.wolBtn = QPushButton('Send Wake-On-Lan to server LAN', self)
        self.wolBtn.setGeometry(210, 65, 200, 25)
        self.wolBtn.clicked.connect(self.sendwol)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch)
        
        self.hstLbl = QLabel('Disconnected', self)
        self.hstLbl.setGeometry(5, 95, 405, 15)

        self.uptLbl = QLabel('', self)
        self.uptLbl.setGeometry(5, 115, 405, 15)

        self.avgLbl = QLabel('', self)
        self.avgLbl.setGeometry(5, 135, 405, 15)


        self.setBtnEnabled(False)
        self.show()

    def send(self, message):
        try:
            self.sock.send(bytes(message, 'utf-8'))
        except socket.error:
            self.connectionLost()
        result = json.loads(str(self.sock.recv(4096), 'utf-8'))
        print(result)
        return result


    def connectionLost():
        self.hstLbl.setText('Connection lost.')
        self.timer.stop()

        
    def sendwol(self):
        text, ok = QInputDialog.getText(self, 'Send Wake-On-Lan magic packet', 'Enter MAC:')
        if ok:
            self.send(checkmac(text))

    def fetch(self):
        info = self.send('fetch')
        self.hstLbl.setText(info['hostname'])
        self.uptLbl.setText(info['uptime'])
        self.avgLbl.setText('Load avg.: ' + info['load_avg'] + ' Time: ' + info['time'])
        pass

    
    def setBtnEnabled(self, en):
        self.disBtn.setEnabled(en)
        self.kilBtn.setEnabled(en)
        self.wolBtn.setEnabled(en)
        self.rebBtn.setEnabled(en)
        if en:
            self.timer.start(700)
        else:
            self.timer.stop()

    def disconnect(self):
        self.sock.close()
        self.setBtnEnabled(False)


    def onActivated(self, text):
        print('Connecting to ', text)
        self.sock = socket.socket()
        ip = parseIP(text)
        self.sock.connect((ip[0], int(ip[1])))
        if self.sock:
            self.sock.settimeout(1)
            self.setBtnEnabled(True)


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


def checkmac(string):
    if re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', string):
        return string
    else:
        raise KeyError('Invalid MAC!')


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
            string = input('Enter command(fetch, reboot, kill or WOL MAC addr): ')
            sock.send(bytes(string, 'utf-8'))
            result = json.loads(str(sock.recv(4096), 'utf-8'))
            sock.close()
            print(result)
        else:
            w.addServer(ip)

    if not args.textMode:
        sys.exit(app.exec_())
    
