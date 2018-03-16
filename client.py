import socket
import json
import sys
import argparse
import re
from PyQt5.QtWidgets import (QWidget, QLabel,
  QComboBox, QApplication, QPushButton, QInputDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QTimer
from pathlib import Path
import pyqtgraph as pg

graph = {
     'cpu': [0]*60,
     'mem': [0]*60,
     'ntx': [0]*60,
     'nrx': [0]*60,
    }
curRx = 0
curTx = 0

class MonitorUI(QWidget):
  def __init__(self):
    super().__init__()
    self.initUI()
  def closeEvent(self, event):
    if save: #If we have to save config(it was loaded), do it.
      with open(args.config, 'w') as json_file:
        json.dump(ips, json_file)
        print("Config saved to %s." % args.config)
    event.accept()
  def initUI(self):
    self.setGeometry(50, 50, 820, 615)
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
    self.disBtn.setGeometry(5, 585, 200, 25)
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

    self.cpu = pg.PlotWidget(self, name='cpu_plot')
#    self.cpu.setLabel(text='CPU usage:')
    self.cpu.setMouseEnabled(x=False, y=False)
    self.cpu.setGeometry(5, 155, 200, 200)
    self.cpu.setXRange(1, len(graph['cpu'])-1)
    self.cpu.setYRange(0, 100)
    self.cpu.hideButtons()
    self.cpuPlot = self.cpu.plot()

    self.mem = pg.PlotWidget(self, name='mem_plot')
#    self.mem.setLabel(text='RAM usage:')
    self.mem.setMouseEnabled(x=False, y=False)
    self.mem.setGeometry(205, 155, 205, 200)
    self.mem.setXRange(1, len(graph['mem'])-1)
    self.mem.setYRange(0, 100)
    self.mem.hideButtons()
    self.memPlot = self.mem.plot()

    self.net = pg.PlotWidget(self, name='net_plot')
#    self.net.setLabel(text='NET usage:')
    self.net.setMouseEnabled(x=False, y=False)
    self.net.setGeometry(415, 155, 400, 200)
    self.net.setXRange(1, len(graph['ntx'])-1)
    self.nrxPlot = self.net.plot(pen='#3875d8')
    self.ntxPlot = self.net.plot(pen='#1cb226')

    self.cpuLbl = QLabel('', self)
    self.cpuLbl.setGeometry(5, 360, 200, 15)

    self.memLbl = QLabel('', self)
    self.memLbl.setGeometry(210, 360, 200, 15)

    self.nrxLbl = QLabel('', self)
    self.nrxLbl.setGeometry(415, 360, 200, 15)
    self.ntxLbl = QLabel('', self)
    self.ntxLbl.setGeometry(615, 360, 200, 15)

    self.dskTbl = QTableWidget(self)
    self.dskTbl.setColumnCount(6)
    self.dskTbl.setHorizontalHeaderLabels(['Filesystem', '1K-blocks', 'Used', 'Available', 'Use%', 'Mounted on'])
    self.dskTbl.setGeometry(5, 380, 805, 200)   
    self.setBtnEnabled(False)
    self.show()

  def send(self, message):
    try:
      self.sock.send(bytes(message, 'utf-8'))
    except socket.error:
      self.connectionLost()
    result = json.loads(str(self.sock.recv(4096), 'utf-8'))
    return result


  def connectionLost():
    self.hstLbl.setText('Connection lost.')
    self.timer.stop()

    
  def sendwol(self):
    text, ok = QInputDialog.getText(self, 'Send Wake-On-Lan magic packet', 'Enter MAC:')
    if ok:
      self.send(checkmac(text))


  def fetch(self):
    global curRx
    global curTx
    info = self.send('fetch')
    self.hstLbl.setText(info['hostname'])
    self.uptLbl.setText(info['uptime'])
    self.avgLbl.setText('Load avg.: %s Time: %s' % (info['load_avg'], info['time']))
    self.memLbl.setText('RAM usage: %sK / %sK' % (info['total_memory'], info['used_memory']))
    self.cpuLbl.setText('CPU usage: %s%%' % (info['cpu']))
    updateGraph('cpu', float(info['cpu']))                                         #Update cpu usage graph info
    updateGraph('mem', float(info['used_memory'])/float(info['total_memory'])*100) #Update graph info about memory usage in percents
    self.cpuPlot.setData(y=graph['cpu'], clear=True)
    self.memPlot.setData(y=graph['mem'], clear=True)
    lastRx = curRx
    lastTx = curTx    
    curRx = int(info['net_rx'])
    curTx = int(info['net_tx'])
    if not lastRx == 0:
        updateGraph('nrx', (curRx-lastRx)/1024/1024)
        updateGraph('ntx', (curTx-lastTx)/1024/1024)
    self.nrxPlot.setData(y=graph['nrx'])
    self.ntxPlot.setData(y=graph['ntx'])
    self.net.autoRange()
    self.nrxLbl.setText('RX speed: {0:.2f} Mbps'.format((curRx-lastRx)/1024/1024))
    self.ntxLbl.setText('TX speed: {0:.2f} Mbps'.format((curTx-lastTx)/1024/1024))
    self.dskTbl.setRowCount(len(info['disks']))
    for i, d in enumerate(info['disks']):
        self.dskTbl.setItem(i, 0, QTableWidgetItem(info['disks'][str(i)]['filesystem']))
        self.dskTbl.setItem(i, 1, QTableWidgetItem(info['disks'][str(i)]['1k_blocks']))
        self.dskTbl.setItem(i, 2, QTableWidgetItem(info['disks'][str(i)]['used']))
        self.dskTbl.setItem(i, 3, QTableWidgetItem(info['disks'][str(i)]['available']))
        self.dskTbl.setItem(i, 4, QTableWidgetItem(info['disks'][str(i)]['use']))
        self.dskTbl.setItem(i, 5, QTableWidgetItem(info['disks'][str(i)]['mounted_on']))

  
  def setBtnEnabled(self, en):
    self.disBtn.setEnabled(en)
    self.kilBtn.setEnabled(en)
    self.wolBtn.setEnabled(en)
    self.rebBtn.setEnabled(en)
    if en:
      self.timer.start(1000)
    else:
      self.timer.stop()

  def disconnect(self):
    self.sock.close()
    self.setBtnEnabled(False)


  def onActivated(self, text):
    print('Connecting to ', text)
    self.sock = socket.socket()
    ip = parseIP(text)
    self.sock.connect((ip[0], 9080 if ip[1]=='' else int(ip[1]) ))
    if self.sock:
      self.sock.settimeout(1)
      self.setBtnEnabled(True)


  def addServerDialog(self):
    text, ok = QInputDialog.getText(self, 'Add server', 'Enter server IP:')
    if ok:
      self.addServer(parseIP(text))


  def addServer(self, ip, dontInsert=False):
    string = ip[0]
    if not ip[1] == '': string += ':' + ip[1]
    if not dontInsert:
      ips['list'].append(ip)
    self.combo.addItems([string])
    print('Added %s to the list' % string)


  def remCurrentServer(self):
    print('Deleting server from the list')
    self.combo.removeItem(self.combo.currentIndex())


def updateGraph(g, value):
  graph[g].pop(0)
  graph[g].append(value)


def parseIP(string):
# Parsing IP from string to list with IP and port. If it's not matching regex, raising exception
  if re.match(r'^([0-9A-Za-z\.]+):?(\d{0,4})$', string):
    return re.findall(r'([0-9A-Za-z\.]+):?(\d{0,4})', string)[0]
  else:
    raise KeyError('Invalid IP!')


def checkmac(string):
#Checking if input string is really MAC address(6 2-digit hex values, splitted with "-" or ":"
#Returning input string if it does and raising exception if doesn't
  if re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', string):
    return string
  else:
    raise KeyError('Invalid MAC!')


if __name__ == '__main__':
  save = False
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
        print("Config loaded from %s" % args.config)
        save = True
    else: 
      ips = {'list':[]}
      save = True
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
      w.addServer(ip, dontInsert=True)

  if not args.textMode:
    sys.exit(app.exec_())
  
