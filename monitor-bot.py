#!/usr/bin/python3
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
PERIOD = 10.0

def tg_start(bot, update):
  """Greeting"""
  update.message.reply_text('ServerMonitor v0.2 bot\n/poll to enable polling.\n/stoppoll to disable\n'+\
                            '/add <IP> to add server\n/remove <N> to remove server by its number in list\n'+\
                            '/list to show list of servers\n/clear to clear list\n/save to save changes to file')


def tg_authorized(update):
  global chatId
  if not (chatId == update.message.chat.id):
    update.message.reply_text('You are not authorized. Type /password <pass> to authorize.')
    return False
  else:
    return True


def tg_poll(bot, update):
  """Starts polling servers every PERIOD seconds"""
  global chatId #Store chat ID
  global threads_stopped #Store boolean to stop running threads
  if tg_authorized(update):
    threads_stopped = False #Don't stop threads
    update.message.reply_text('Servers polling enabled.')
    serversPoll() #Start new thread
  

def tg_pass(bot, update, args):
  global chatId
  global config
  if args[0] == config['password']:
    if not (chatId == 0): updater.bot.send_message(chatId, 'You\'ve been deauthorized.')
    chatId = update.message.chat.id
    update.message.reply_text('You\'re successfully authorized!\nType /poll to start polling servers.')
  else:
    update.message.reply_text('Password incorrect!')


def tg_stopPoll(bot, update):
  """Stops polling"""
  global threads_stopped
  threads_stopped = True #Stop all threads
  update.message.reply_text('Stopping servers polling...')


def tg_alarm(message):
  """Send message to last user, entered /poll command"""
  if not (chatId == 0):
    updater.bot.send_message(chatId, message)
  

def tg_add(bot, update, args):
  """Add server to the list in config['list'] dicitonary"""
  global config
  if tg_authorized(update):
    try:
      ip = parseIP(args[0])
      config['list'].append(ip)
      update.message.reply_text('%s added to servers list.' % args[0])
    except KeyError:
      update.message.reply_text('Invalid IP address!')
    pass


def tg_rem(bot, update, args):
  """Remove server from the list in config['list'] dicitonary"""
  if tg_authorized(update):
    try:
      config['list'].pop(int(args[0]))
      update.message.reply_text('Server #%i removed from the list.' % int(args[0]))
    except ValueError:
      update.message.reply_text('Please enter number of server.')
    except IndexError:
      update.message.reply_text('Index out of list range.')


def tg_list(bot, update):
  """Show servers list from config['list'] dicitonary"""
  if tg_authorized(update):
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
  """Clear config['list'] dicitonary"""
  global config
  if tg_authorized(update):
    config['list'] = []
    update.message.reply_text('Servers list cleared.')


def tg_save(bot, update):
  """Save config dicitonary to file"""
  if tg_authorized(update):
    with open(args.config, 'w') as json_file:
      json.dump(config, json_file)
    update.message.reply_text('Config saved to file.')


def parseIP(string):
  """Parsing IP from string to list with IP and port. If it's not matching regex, raising exception"""
  if re.match(r'^([0-9A-Za-z\.]+):?(\d{0,4})$', string):
    return re.findall(r'([0-9A-Za-z\.]+):?(\d{0,4})', string)[0]
  else:
    raise KeyError('Invalid IP!')

def serversPoll():
  """Threading function to poll servers"""
  global t
  if threads_stopped:
    return
  t = threading.Timer(PERIOD, serversPoll)
  t.start()
  for ip in config['list']:
    try:
      sock = socket.socket()
      sock.settimeout(TIMEOUT)
      sock.connect((ip[0], 8000 if ip[1]=='' else int(ip[1])))  #Trying to connect
      sock.close()                                              #Disconnecting immediately if connected 
    except ConnectionRefusedError:                              #What if port is closed
      tg_alarm('Error connecting to %s!\nConnection refused.' % ip[0])      
    except socket.timeout:                                      #What if time is out
      tg_alarm('Error connecting to %s!\nConnection timed out.' % ip[0])
    except socket.gaierror:                                     #What if IP is incorrect(e.g. octet > 255)
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
  dp.add_handler(CommandHandler("help",    tg_start))
  dp.add_handler(CommandHandler("poll",     tg_poll))
  dp.add_handler(CommandHandler("stoppoll", tg_stopPoll))
  dp.add_handler(CommandHandler("add",      tg_add, pass_args=True))
  dp.add_handler(CommandHandler("list",     tg_list))
  dp.add_handler(CommandHandler("remove",   tg_rem, pass_args=True))
  dp.add_handler(CommandHandler("clear",    tg_clear))
  dp.add_handler(CommandHandler("save",     tg_save))
  dp.add_handler(CommandHandler("password",   tg_pass, pass_args=True))
  updater.start_polling()
  updater.idle()

if __name__ == '__main__':
  main()
