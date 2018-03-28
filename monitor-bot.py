import socket
import json
import argparse
import re
import logging
import threading
from pathlib import Path
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


chatId = 0
TIMEOUT = 1

def tg_start(bot, update):
  update.message.reply_text('ServerMonitor v0.1 bot\nType /poll to enable polling.')


def tg_poll(bot, update):
  global chatId
  global threads_stopped
  threads_stopped = False
  update.message.reply_text('Servers polling enabled.')
  chatId = update.message.chat.id
  serversPoll()
  


def tg_stopPoll(bot, update):
  global threads_stopped
  serversPoll(stop=True)
  threads_stopped = True
  update.message.reply_text('Stopping servers polling...')


def tg_alarm(message):
  updater.bot.send_message(chatId, message)
  

def tg_add(bot, update, args):
  global config
  try:
    ip = parseIP(args[0])
    config['list'].append(ip)
    update.message.reply_text('%s added to servers list.' % args[0])
  except KeyError:
    update.message.reply_text('Invalid IP address!')
  pass


def tg_rem(bot, update, args):
  try:
    config['list'].pop(int(args[0]))
    update.message.reply_text('Server #%i removed from the list.' % int(args[0]))
  except ValueError:
    update.message.reply_text('Please enter number of server.')
  except IndexError:
    update.message.reply_text('Index out of list range.')


def tg_list(bot, update):
  string = 'List of servers to poll:\n'
  if len(config['list'])<1: 
    update.message.reply_text('There is no servers to poll.')
  else:
    for i, ip in enumerate(config['list']):
      s = ip[0]
      if not ip[1]=='': s += ':' + ip[1]
      string+='%i) %s\n' % (i, s)
    update.message.reply_text(string)


def tg_clear(bot, update):
  global config
  config['list'] = []
  update.message.reply_text('Servers list cleared.')


def tg_save(bot, update):
  with open(args.config, 'w') as json_file:
    json.dump(config, json_file)
  update.message.reply_text('Config saved to file.')


def parseIP(string):
# Parsing IP from string to list with IP and port. If it's not matching regex, raising exception
  if re.match(r'^([0-9A-Za-z\.]+):?(\d{0,4})$', string):
    return re.findall(r'([0-9A-Za-z\.]+):?(\d{0,4})', string)[0]
  else:
    raise KeyError('Invalid IP!')

def serversPoll(stop=False):
  global t
  if threads_stopped:
    return
  t = threading.Timer(10.0, serversPoll)
  if not stop:
    t.start()
    for ip in config['list']:
      try:
        sock = socket.socket()
        sock.settimeout(TIMEOUT)
        sock.connect((ip[0], 8000 if ip[1]=='' else int(ip[1])))
        sock.close()
      except ConnectionRefusedError:
        tg_alarm('Error connecting to %s!\nConnection refused.' % ip[0])      
      except socket.timeout:
        tg_alarm('Error connecting to %s!\nConnection timed out.' % ip[0])
      except socket.gaierror:
        tg_alarm('Error connecting to %s!\nMaybe, invalid IP?' % ip[0])


def main():
  global updater
  global config
  global args
  logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                      level=logging.INFO)
  logger = logging.getLogger(__name__)

  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--config", type=str, default='config.json',
                      help="Load config from specific file.\nDefault is config.json")
  args = parser.parse_args()
  file = Path(args.config)
  if file.is_file():
    with open(args.config, "r") as json_file:
      config = json.load(json_file)
      print("Config loaded from %s" % args.config)
  else: 
    print("Error loading config file!")
    return
  api_token = config['api_token']
  updater = Updater(api_token)
  dp = updater.dispatcher
  dp.add_handler(CommandHandler("start",    tg_start))
  dp.add_handler(CommandHandler("poll",     tg_poll))
  dp.add_handler(CommandHandler("stoppoll", tg_stopPoll))
  dp.add_handler(CommandHandler("add",      tg_add, pass_args=True))
  dp.add_handler(CommandHandler("list",     tg_list))
  dp.add_handler(CommandHandler("remove",   tg_rem, pass_args=True))
  dp.add_handler(CommandHandler("clear",    tg_clear))
  dp.add_handler(CommandHandler("save",     tg_save))
  updater.start_polling()
  updater.idle()

if __name__ == '__main__':
  main()
