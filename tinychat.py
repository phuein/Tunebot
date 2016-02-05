#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Coded in Sublime Text 3 beta, latest.

from rtmp import rtmp_protocol

import requests             # http://www.python-requests.org/
try:
    requests.packages.urllib3.disable_warnings()    # For python < 2.7.9
except:
    pass

import random
import os, sys, signal
import traceback            # https://docs.python.org/2/library/traceback.html
import time
time.mstime = lambda: int(round(time.time() * 1000))    # Get current time in milliseconds.
from urllib import quote, quote_plus    # Handles URLs.
import json
import re

# Handle linux SIGTERM; cleanup.
def signalHandler(signum, frame):
    print "Signal handler called with signal "+str(signum)+"."
    # Print all queued messages. Cleanup properly.
    try:
        room = ROOMS[0]         # Only main room.
        room._chatlogFlush()
        room.disconnect()
    except:
        pass
    SETTINGS["Run"] = False
    sys.exit()
signal.signal(signal.SIGTERM, signalHandler)

# Windows console fix, not necessary for everyone.
try:
    import codecs
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)
except:
    pass

import socket               # https://docs.python.org/2/library/socket.html
import socks                # https://github.com/Anorov/PySocks 1.5.4

import threading
ROOMS = []                  # First room should always be the main room & thread.

# Operation variables.
try:
    LOCAL_DIRECTORY     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
except:
    LOCAL_DIRECTORY     = ""
# Holds further private modules and settings files.
SETTINGS_DIRECTORY      = os.path.join(LOCAL_DIRECTORY, "settings", "")

SETTINGS_FILE           = False  # Default to no settings file.

# Delay before any (re)connection.
DELAY = 10

# Returns a new internet socket().
# Optionally reusable.
def getSocket(reusable=False, keepalive=True):
    s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)   # Default values.
    
    # Looks like TC uses some MQTT thing. No idea.
    # if keepalive:
    #     s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    #     # Linux only.
    #     try:
    #         # Activate after seconds idle.
    #         # Overrides value shown by sysctl net.ipv4.tcp_keepalive_time.
    #         s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 15)   # socket.IPPROTO_TCP
    #         # Ping interval.
    #         # Overrides value shown by sysctl net.ipv4.tcp_keepalive_intvl.
    #         s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 15)  # socket.IPPROTO_TCP
    #         # Max fails.
    #         # Overrides value shown by sysctl net.ipv4.tcp_keepalive_probes.
    #         s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 4)     # socket.IPPROTO_TCP
    #     except:
    #         pass
    
    if reusable:
        # The SO_REUSEADDR flag tells the kernel to reuse a local socket
        # in TIME_WAIT state, without waiting for its natural timeout to expire.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    return s

# Global bot settings.
# This includes everything from the settings file!
SETTINGS = {
    # Client controls.
    "Run":                  True,           # Let a thread ask to exit process loop.
    "ReconnectOnBan":       False,          # Reconnect when banned.
    "DebugConsole":         False,
    "DebugLog":             False,
    "ChatLog":              True,
    "ChatConsole":          True,
    "LastPM":               None,           # The nickname that last got a msg PM from bot.
    "IP":                   None,
    "PORT":                 None,
    "PROXY":                None,           # Optional proxy option to use, proxy or "list".
    "SOCK":                 getSocket(),    # Connection socket used for all actions.
    "Recaptcha":            "",             # The text file holding recaptcha info.
    "NoRecaptcha":          False,          # Don't bother with reCaptcha.
    "ReceiveCams":          False,          # Whether to receive webcam streams from other users.
    "SCKey":                None,
    "YTKey":                None,
    # Optional event handling extensions, for bots.
    "onJoinExtend":             None,
    "onJoinsdoneExtend":        None,
    "onQuitExtend":             None,
    "onNoticeExtend":           None,
    "onMessageExtend":          None,
    "onPMExtend":               None,
    "onNickChangeExtend":       None,
    "onUserinfoReceivedExtend": None,
    "onBanlistExtend":          None,
    "onBroadcastExtend":        None,
    "disconnectExtend":         None,
    # Thread control.
    "LastRoomID":           0,
    "SendCommands":         True,           # Disable sending messages to room.
    "KeepAlive":            None,           # The keepalive thread.
    # Input control.
    "RunningOnWindows":     False,
    "InteractiveConsole":   True,           # Has interactive console for user input.
    "UserInput":            None,           # None means msvcrt() lib isn't loaded.
    "UserInputLast":        "",
    # Extra settings.
    "BanNewusers":          False,
    "MaxCharsMsg":          110,
    "MaxCharsPM":           90,
    "MaxCharsNotice":       160,            # 360 total max per /notice.
    "Instructions":         False           # Execute module at joinsdone().
}

# The Login and RTMP connections arguments.
CONN_ARGS = {
    "room": "",
    "nickname": "",
    "username": "",
    "password": ""
}

# Get connection arguments from command-line arguments.
try:
    if len(sys.argv) == 1:
        raise Exception("No arguments given to tinychat module...\n")
    
    # Each item is a word, unless surrounded by "quotes".
    for item in sys.argv:
        parts = item.split("=", 1)
        
        try:
            # All names are lower-case.
            name = parts[0].lower()
        except:
            # Must have a name.
            continue
        
        try:
            val = parts[1]
        except:
            # Value can be empty.
            val = ""
        
        if name == "room":
            CONN_ARGS["room"] = val
        
        elif name in {"nick", "nickname"}:
            CONN_ARGS["nickname"] = val
        
        elif name in {"user", "username"}:
            CONN_ARGS["username"] = val
        
        elif name in {"pass", "password"}:
            CONN_ARGS["password"] = val
        
        # Using an interactive console or not, like command prompt.
        elif name == "interactive":
            try:
                SETTINGS["InteractiveConsole"] = bool(int(val))
            except:
                print("Argument INTERACTIVE must be 0 or 1, only.")
        
        # Override main room IP.
        elif name == "ip":
            SETTINGS["IP"] = val
        # Override main room PORT.
        elif name == "port":
            try:
                SETTINGS["PORT"] = int(val)
            except:
                print("Argument PORT must be an integer number.")
        
        # All the module's connections go through proxy.
        elif name == "proxy":
            SETTINGS["PROXY"] = val
        
        # Reconnect on ban.
        elif name == "reonban":
            try:
                SETTINGS["ReconnectOnBan"] = bool(int(val))
            except:
                print("Argument REONBAN must be 0 or 1, only.")
        
        elif name == "norecaptcha":
            try:
                SETTINGS["NoRecaptcha"] = bool(int(val))
            except:
                print("Argument NORECAPTCHA must be 0 or 1, only.")
        
        elif name == "instructions":
            try:
                SETTINGS["Instructions"] = int(val)
            except:
                print("Argument INSTRUCTIONS must be an integer number.")
        
        elif name == "settings":
            try:
                SETTINGS_FILE = bool(int(val))
            except:
                SETTINGS_FILE = val
            print("Settings file set: "+str(SETTINGS_FILE))
except Exception as e:
    print(e)

# If command-line argument for settings is True, try to find by room name.
if SETTINGS_FILE is True:
    s = "settings_"+CONN_ARGS["room"]+".txt"
    if os.path.isfile(LOCAL_DIRECTORY + s):
        SETTINGS_FILE = s

# Append and override further settings from file.
# Supports unicode.
try:
    if type(SETTINGS_FILE) not in {str, unicode}:
        raise Exception()
    
    with open(LOCAL_DIRECTORY + SETTINGS_FILE) as f:
        data = f.read().splitlines()
    
    # Handle unicode.
    try:
        lines = lines.decode("utf-8", "replace")
    except:
        pass
    
    # Convert to dict{}.
    d = {}
    for line in data:
        # Remove trailing whitespaces.
        line = line.strip()
        # Skip comments and empty lines.
        if line.startswith("//") or line == "":
            continue
        
        words = line.split()
        name = words.pop(0)
        value = " ".join(words)
        
        # Optionally parse True/False.
        if value == "True":
            value = True
        elif value == "False":
            value = False
        
        # Optionally parse as number.
        elif value.startswith("###"):
            try:
                value = float(value)
            except:
                pass
        elif value.startswith("##"):
            try:
                value = int(value)
            except:
                pass
        
        # Optional CONN_ARGS. Doesn't override command-line arguments.
        if name in CONN_ARGS and not CONN_ARGS[name] and name != "room":
            CONN_ARGS[name] = value
        else:
            # Override into SETTINGS.
            d[name] = value
    
    # Apply.
    SETTINGS.update(d)
except Exception as e:
    if str(e):
        print "Failed to load SETTINGS from "+SETTINGS_FILE+"!"
        print str(e)

# Media handling - audio & video streams.
try:
    from settings import media as MEDIA
except:
    MEDIA = None

# Access bypass.
try:
    from settings import bypassAccess as BYPASS_ACCESS
except:
    BYPASS_ACCESS = None

# Captcha bypass.
try:
    from settings import bypass_captcha as BYPASS_CAPTCHA
except:
    BYPASS_CAPTCHA = None

# Proxy module.
try:
    from settings import proxy as PROXY_MODULE
except:
    PROXY_MODULE = None
    PROXY = None

# Instructions module.
try:
    import instructions as INSTRUCTIONS
    doInstructions = INSTRUCTIONS.do
except:
    traceback.print_exc()
    INSTRUCTIONS = None

# Running on a Windows machine, or otherwise.
if os.name == "nt":
    SETTINGS["RunningOnWindows"] = True

# Console input control.
if SETTINGS["RunningOnWindows"]:
    try:
        import msvcrt       # https://docs.python.org/2/library/msvcrt.html#console-i-o
        SETTINGS["UserInput"] = []
    except:
        pass
else:
    # For linux...
    pass

# Time formats.
get_current_time = lambda: time.strftime("%H.%M.%S")
current_date = time.strftime("%d.%m.%Y")

# Logging.
try:
    LOG_BASE_DIRECTORY = os.environ["OPENSHIFT_LOG_DIR"] + "room_logs/"
except:
    LOG_BASE_DIRECTORY = "logs/"

LOG_FILENAME_POSTFIX = current_date + "_" + time.strftime("%H.%M.%S") + ".log"

TINYCHAT_COLORS = {
    'blue'       : '#1965b6',
    'cyan'       : '#32a5d9',
    'lightgreen' : '#7db257',
    'yellow'     : '#a78901',
    'pink'       : '#9d5bb5',
    'purple'     : '#5c1a7a',
    'red'        : '#c53332',
    'darkred'    : '#821615',
    'green'      : '#487d21',
    'lightpink'  : '#c356a3',
    'lightblue'  : '#1d82eb',
    'turquoise'  : '#a990',
    'skinpink'   : '#b9807f',
    'leafgreen'  : '#7bb224',
    # Non-official TC colors...
    'black'      : '#0',
    # Pro colors...
    'brightred'  : '#e62430',
    'orange'     : '#fba91a'
}

# Handle tracking videos and songs.
YTqueue = {
    "history":          [],     # Videos played by bot, only.
    "current":          "",     # Currently tracked video, not only from bot.
    # Track the last played (or playing) video.
    "start":            0,      # The time() when started.
    "length":           0,      # The length of the video in seconds.
    "skip":             0,      # The skip amount in seconds.
    "paused":           0       # The time() when paused.
}

SCqueue = {
    "history":          [],     # Tracks played by bot, only.
    "current":          "",     # Currently tracked track, not only from bot.
    # Track the last played (or playing) video.
    "start":            0,      # The time() when started.
    "length":           0,      # The length of the video in seconds.
    "skip":             0,      # The skip amount in seconds.
    "paused":           0       # The time() when paused.
}

# Proxies for spoofing the connection - requests and RTMP. Optional.
# Turns PROXY into an object with methods, or to None on failure.
try:
    # Need both module and a proxy or list.
    if not PROXY_MODULE or not SETTINGS["PROXY"]:
        raise Exception()
    
    # Either a given .txt file, single proxy, or nothing.
    if SETTINGS["PROXY"].endswith(".txt"):
        # List of proxies.
        try:
            with open(SETTINGS_DIRECTORY + SETTINGS["PROXY"]) as f:
                d = f.read().splitlines()
        except:
            raise Exception("Failed to open proxies list from "+SETTINGS["PROXY"]+"...")
        proxies = filter(lambda x: x.strip() and not x.startswith("//"), d)
    elif SETTINGS["PROXY"]:
        # Single proxy.
        proxies = SETTINGS["PROXY"]
    
    # Set as object from class. Proxies are shuffled, and made a tuple (not list!)
    l = threading.Lock()
    PROXY = PROXY_MODULE.proxy(proxies, requests, getSocket, l, loopOver=True)
    # Invalid single proxy.
    if not PROXY.proxies:
        raise Exception("Proxy "+SETTINGS["PROXY"]+" is not a valid proxy format! "+
            "Using local connection...")
except Exception as e:
    PROXY = None
    if str(e):
        print str(e)

# Format Room and PM messages.
class TinychatMessage():
    def __init__(self, msg, nick, user=None, recipient=None, color=None, pm=False):
        self.msg = msg
        self.nick = nick
        self.user = user
        self.recipient = recipient
        self.color = color
        self.pm = pm
    
    def printFormatted(self):
        if self.pm:
            pm = "(PM) "
        else:
            pm = ""
        print(pm + self.recipient + ": " + self.nick + ": " + self.msg)

# User properties object.
class TinychatUser():
    def __init__(self, userID=0, nick="", color=""):
        self.joinTime = time.time()
        
        self.nick = nick
        self.id = userID            # int()
        self.color = color
        self.lastMsg = ""
        self.mod = False
        self.admin = False
        self.account = ""
        
        self.broadcasting = False   # Can't tell if stopped broadcasting, unless closed by mod.
        self.device = ""            # Tinychat identifies Android & iPhone users.
        self.pro = False            # User is on a Pro account.
        # self.btype = ''
        # self.stype = 0
        self.lurking = False        # User is on "guest" mode, and can't send anything to room.
        
        self.gp = 0                 # Giftpoints. int()
        self.alevel = ""            # Gifts Achievement level (image url: http://tinychat.com/gifts/images/achievement/new/star_y_32.png)

# A single room connection.
class TinychatRoom():
    # self.sock is None if using a bad socket().
    # Each connection has its own room() with socket(), by design.
    def __init__(self, room, nick=None, username=None, passwd=None, roomPassword=None,
        instructions=None, printOverride=None, doConnect=None,
        replaceIndex=None, autoBot=None, noRecaptcha=None):
        # Put reference to room, in the list.
        if replaceIndex is not None:
            ROOMS.insert(replaceIndex, self)
        else:
            ROOMS.append(self)
        
        self.autoBot = autoBot
        self.noRecaptcha = SETTINGS["NoRecaptcha"]
        
        # Optional room type for RTMP connect().
        if room.find("*") >= 0:
            parts = room.split("*")
            self.site = parts[0]
            self.room = parts[1]
        elif room.find("^") >= 0:
            # Command-line argument can't use ^, so optional check.
            parts = room.split("^")
            self.site = parts[0]
            self.room = parts[1]
        else:
            self.site = "tinychat"
            self.room = room
        
        self.type = "show"              # Default, but also check in API.
        
        self.cookies = {}               # Holds requests session cookies.
        
        if username == None:
            self.username = ""
        else:
            self.username = username
        self.nick = nick
        self.passwd = passwd
        self.roomPassword = roomPassword
        
        self.connected = False
        self.reconnecting = False
        
        SETTINGS["LastRoomID"] += 1
        self.roomID = SETTINGS["LastRoomID"]
        
        self.chatVerbose = SETTINGS["ChatConsole"]
        self.chatLogging = SETTINGS["ChatLog"]
        self.chatlogQueue = []
        
        # Optionally filled in getRTMPInfo().
        self.bpass = None
        self.greenroom = False
        self.timecookie = None
        
        # Each room() has its own socket(), representing an IP address.
        self.sock       = None
        self.proxies    = None
        self.proxy      = None
        self.PROXY      = PROXY         # Modular access.
        self.getSocket  = getSocket     # ...
        self.setSocket()                # Sets the above variables, or not on failure.
        
        try:
            if not self.sock:
                raise Exception("Bad socket from setSocket()...")
            
            self.s = requests.session()
            self.authHTTP()
            self.tcurl = self.getRTMPInfo()
            self.doTimestampRecaptcha()         # Sets self.timecookie, as well.
        except Exception as e:
            # traceback.print_exc()
            # Failed socket. Probably bad proxy.
            self.reconnect()
            return
        
        # Work bot - advertising.
        self.instructions = instructions
        # Connect immediately, after initialization.
        self.doConnect = doConnect
        # Ignore print queueing, and print immediately.
        self.printOverride = printOverride
        
        tcurlsplits = self.tcurl.split("/tinyconf")             # >>['rtmp://127.0.0.1:1936', '']
        tcurlsplits1 = self.tcurl.split("/")                    # >>['rtmp:', '', '127.0.0.1:1936', 'tinyconf']
        tcurlsplits2 = self.tcurl.split(":")                    # >>['rtmp', '//127.0.0.1', '1936/tinyconf']
        tcurlsplits3 = tcurlsplits1[2].split(":")               # >>[127.0.0.1', '1936']
        self.url = tcurlsplits[0]                               # Defining Full RTMP URL "rtmp://127.0.0.1:1936"
        self.protocol = tcurlsplits2[0]                         # Defining RTMP Type [RTMP/RTMPE,etc]
        self.ip = tcurlsplits3[0]                               # Defining RTMP Server IP
        self.port = int(tcurlsplits3[1])
        self.app = tcurlsplits1[3]                              # Defining Tinychat FMS App
        self.pageurl = "http://tinychat.com/"+room              # Definging Tinychat's Room HTTP URL
        self.swfurl = "http://tinychat.com/embed/Tinychat-11.1-1.0.0.0651.swf?version=1.0.0.0651/[[DYNAMIC]]/8" #static
        self.flashVer = "WIN 20,0,0,267"                        # static
        self.pc = "Desktop 1.0.0.0651"
        
        # Overrides.
        if SETTINGS["IP"]:
            self.ip = SETTINGS["IP"]
        if SETTINGS["PORT"]:
            self.port = int(SETTINGS["PORT"])
        
        self.color = TINYCHAT_COLORS["black"]
        self.topic = ""
        self.users = {}             # self.users[NICK] = USER OBJECT
        self.user = None            # Holds the bot's user object.
        self.nextFails = 0          # Count .next() failures, to avoid infinite loop.
        self.banlist = []
        self.forgives = []
        self.onCam = False
        self.keepAlive = True       # Toggles on disconnect() and connect().
        
        # Avoid sending more than 10 msgs per 1 second.
        self.limitMsgs = {
            "msgs":     0,
            "first":    time.time()
        }
        
        # Connect immediately, after finishing initialization.
        if self.doConnect:
            self.connect()
    
    # Core connectivity functions.
    def connect(self, force=None):
        self._chatlog("Connecting to "+self.room+"...", True)
        
        if not self.connected or force:
            try:
                self.connection = rtmp_protocol.RtmpClient(self.ip, self.port, self.tcurl,
                    self.pageurl, self.swfurl, self.app, self.flashVer, self.sock,
                    self.username, self.site, self.room, self.pc, self.type, self.timecookie)
                
                self.connection.connect()
                self.connected = True
                self.keepAlive = True
                SETTINGS["Reconnecting"] = False
                
                if self.proxy:
                    if type(PROXY.proxies) is tuple:
                        p = self.proxy+" ("+PROXY.getCountString(self.proxyIndex)+")"
                    else:
                        p = self.proxy
                else:
                    p = ""
                self._chatlog("== Connected "+(self.nick if self.nick else "bot")+" == "+p)
                
                printFile(self.room+".connected", "connected", local=True)
                # Start listening to server.
                self._listen()
            except Exception as e:
                # traceback.print_exc()
                self.connected = False
                self._chatlog("Failed to connect! Reconnecting...", True)
                self.reconnect()
    
    def _listen(self):
        while self.connected and not self.reconnecting:
            # Read next possible packet.
            try:
                msg = self.connection.reader.next()
            except socket.timeout:
                # Only applies for the connect() attempt.
                self.disconnect()
                self._chatlog("Socket().timeout! Reconnecting...", True)
                self.reconnect()
                break
            except:
                self.nextFails += 1
                self._chatlog("Failed to read next() packet...", True)
                # Kill after consecutive fails.
                if self.nextFails == 5:
                    self.disconnect()
                    self._chatlog("Can't read next()! Reconnecting...", True)
                    self.reconnect()
                    break
                # Otherwise, skip it.
                continue
            else:
                # Reset count on success.
                self.nextFails = 0
            
            # Handle RTMP packets.
            try:
                if msg['msg'] == rtmp_protocol.DataTypes.USER_CONTROL:
                    # Ping, normally.
                    # self._chatlog("USER CONTROL: "+str(msg['event_type'])+", "+str(msg['event_data'])+".", True)
                    return
                
                elif msg['msg'] == rtmp_protocol.DataTypes.SHARED_OBJECT:
                    # Useless.
                    # self._chatlog("SHARED OBJECT: "+str(msg['obj_name'])+", "+str(msg['curr_version'])+
                    #     ", "+msg['flags']+", "+msg['events']+".", True)
                    return
                
                elif msg['msg'] == rtmp_protocol.DataTypes.DATA_MESSAGE:
                    # Useless.
                    # self._chatlog("DATA MESSAGE: "+str(msg['event_data'])+".", True)
                    return
                
                elif msg['msg'] == rtmp_protocol.DataTypes.VIDEO_MESSAGE:
                    try:
                        pass
                        # self.videoDatas[msg['streamid']].append(msg['control'], msg['video'])
                    except:
                        pass
                
                elif msg['msg'] == rtmp_protocol.DataTypes.COMMAND:
                    pars = msg['command']
                    cmd = pars[0].encode("ascii", "ignore").lower() # pars[0].encode("ascii", "ignore").lower()
                    
                    if len(pars) > 3:
                        pars = pars[3:]
                    else:
                        pars = []
                    
                    # for i in range(len(pars)):
                    #     if type(pars[i]) == str: pars[i] = pars[i].encode("ascii", "ignore")
                    
                    # Incoming RTMP event.
                    if cmd == "privmsg":
                        recipient = pars[0]
                        message = pars[1]
                        color = pars[2].lower().split(",")[0]
                        nick = pars[3]
                        
                        # Ignore empty messages.
                        if not message:
                            continue
                        
                        m = self._decodeMessage(message)
                        
                        if len(m) > 0:
                            if recipient[0] == "#":
                                recipient = "^".join(recipient.split("^")[1:])
                            else:
                                recipient = "-".join(recipient.split("-")[1:])
                            
                            user = self._getUser(nick)
                            if not user:
                                print("< Caught empty user at privmsg: "+nick+" >")
                                print str(message)
                                continue
                            
                            message = TinychatMessage(m, nick, user, recipient, color)
                            user.lastMsg = message
                            user.color = color
                            
                            if recipient == self.nick:
                                message.pm = True
                                if message.msg.startswith("/msg ") and len(message.msg.split(" ")) >= 2:
                                    message.msg = " ".join(message.msg.split(" ")[2:])
                                
                                self.onPM(user, message)
                            else:
                                self.onMessage(user, message)
                        continue
                    
                    # Event for self joining?
                    if cmd == "registered":
                        u = pars[0]
                        
                        # Get my user object.
                        self.onJoin(u, myself=True)
                        continue
                    
                    if cmd == "join":
                        u = pars[0]
                        
                        self.onJoin(u)
                        continue
                    
                    if cmd == "topic":
                        topic = pars[0]
                        if not self.topic:
                            # On join.
                            msg = "Topic: "
                        else:
                            msg = "Topic set as: "
                        self.topic = topic
                        self._chatlog(msg + self.topic, True)
                        continue
                    
                    if cmd == "joins":
                        for u in pars:
                            self.onJoin(u, joins=True)
                        continue
                    
                    if cmd == "joinsdone":
                        self.onJoinsdone()
                        continue
                    
                    if cmd == "deop":
                        userid  = int(pars[0])
                        nick    = pars[1]
                        
                        user = self._getUser(userid)
                        user.mod = False
                        self._chatlog(user.nick + " have lost their oper.", True)
                        continue
                    
                    if cmd == "nick":
                        old     = pars[0]
                        new     = pars[1]
                        userid  = int(pars[2])
                        
                        # Replaces reference in room object, and handles event.
                        self.onNickChange(old, new, userid)
                        continue
                    
                    if cmd == "notice":
                        event = pars[0]
                        
                        if event == "avon":
                            userid = pars[1]
                            nick = pars[2]
                            self.onBroadcast(nick, userid)
                        continue
                    
                    if cmd == "avons":
                        # First item is None.
                        pars = pars[1:]
                        
                        # Empty.
                        if not pars:
                            continue
                        
                        for i in range(0, len(pars), 2):
                            userid = pars[i]
                            nick = pars[i+1]
                            
                            self.onBroadcast(nick, userid)
                        continue
                    
                    if cmd == "quit":
                        nick = pars[0]
                        userid = int(pars[1])
                        
                        self.onQuit(nick, userid)
                        continue
                    
                    if cmd == "kick":
                        userID = pars[0]
                        nick = pars[1]
                        
                        self.onBanned(userID, nick)
                        continue
                    
                    if cmd == "banlist":
                        self.onBanlist(pars)
                        continue
                    
                    if cmd == "banned":
                        self.onBanned(bot=True)
                        continue
                    
                    if cmd == "doublesignon":
                        try:
                            self._chatlog("The account "+self.user.account+
                                " is already being used by: ["+pars[1]+","+pars[0]+"].", True)
                        except:
                            self._chatlog("The account "+self.user.account+
                                " is already being used in this room.", True)
                        continue
                    
                    if cmd == "nickinuse":
                        self._chatlog("The nickname "+self.nick+" is already being used. Adding X.", True)
                        self.setNick(self.nick+"X")
                        continue
                    
                    if cmd == "from_owner":
                        # Format: noticeword%20word
                        # or _closebob
                        s = pars[0]
                        
                        # A notice message.
                        if s.startswith("notice"):
                            notice = pars[0][len("notice"):].replace("%20", " ")
                            self.onNotice(notice)
                        # Someone was uncammed.
                        elif s.startswith("_close"):
                            target = s[len("_close"):]
                            self.onCamClosed(target)
                        else:
                            self._chatlog("UNHANDLED from_owner: "+str(pars), True)
                        continue
                    
                    if cmd == "_error":
                        self._chatlog(str(pars), True)
                        continue
                    
                    if cmd == "_result":
                        pars = msg['command'][1:]
                        # self._chatlog("_result: "+str(pars))
                        localStreamID   = pars[0]
                        remoteStreamID  = pars[2]
                        try:
                            self.onResult(localStreamID, remoteStreamID)
                        except:
                            pass
                        continue
                    
                    if cmd == "onstatus":
                        # self._chatlog("onstatus: "+str(pars), True)
                        statusObj = pars[0]
                        try:
                            self.onStatus(statusObj)
                        except:
                            pass
                        continue
                    
                    if cmd == "gift":
                        self._chatlog("Gift: " + str(pars))
                        continue
                    
                    # Uncaught command! Ignore commands I don't care about.
                    if cmd not in {"onbwdone", "startbanlist", "owner"}:
                        self._chatlog("UNHANDLED COMMAND: " + str(cmd) + " " + str(pars), True)
            except:
                self._chatlog("Error handling incoming packet...", True)
                traceback.print_exc()
    
    def disconnect(self):
        if self.connected:
            self.connected = False
            # Flush all chat messages in backlog.
            self._chatlogFlush()
            try:
                self.connection.socket.shutdown(1)
                self.connection.socket.close()
            except:
                self._chatlog("Failed to gracefully disconnect...", True)
            self._chatlog("=== Disconnected ===", True)
            
            # Delete recaptcha file, in case closed during wait loop.
            printFile(SETTINGS["Recaptcha"], local=True)
            
            # Delete connection file.
            printFile(self.room+".connected", local=True)
            
            # Instructions or further handling.
            if SETTINGS['disconnectExtend']:
                try:
                    SETTINGS['disconnectExtend'](self)
                except:
                    traceback.print_exc()
    
    # diconnect() and make a new connection at the same ROOMS index.
    def reconnect(self):
        # Setup new repeat connection.
        SETTINGS["Reconnecting"] = True
        self.keepAlive = False
        
        # Keep to index in ROOMS.
        try:
            i = ROOMS.index(self)
        except:
            i = None
        
        # Close previous connection.
        self.disconnect()
        
        # Remove room from list.
        ROOMS.remove(self)
        
        try:
            nick = self.user.nick
        except:
            nick = self.nick
        
        # Make new room with new proxy, with a new socket().
        t = threading.Thread(target=makeRoom, args=(nick, i,))
        t.daemon = True
        t.start()
    
    # Sets a local or proxified socket, or None.
    # Sets: self.sock. Optionally: self.proxies, self.proxy.
    def setSocket(self):
        self.sock = getSocket()
    
    # Makes a new user from userid, and adds it to self.users.
    # Return the new user object.
    def _makeUser(self, userid):
        user = TinychatUser(userID=userid)
        self.users[userid] = user
        return user
    
    # Gets an existing user by userid or nickname,
    # or optionally by account name.
    # Return False if not found.
    def _getUser(self, identifier, account=False):
        # By account name.
        if account:
            for user in self.users.values():
                if user.account == identifier:
                    return user
        else:
            if type(identifier) is int:
                # By userid.
                try:
                    user = self.users[identifier]
                    return user
                except:
                    pass
            else:
                # By nickname.
                for user in self.users.values():
                    if user.nick == identifier:
                        return user
        
        # No match.
        return False
    
    # Removes an existing user by userid or nickname,
    # and return True, or False if user doesn't exist.
    def _deleteUser(self, identifier):
        if type(identifier) is int:
            # By userid.
            try:
                del self.users[identifier]
                return True
            except:
                pass
                # self._chatlog("< Tried to _deleteUser from unavailable userid: "+str(identifier)+" >", True)
        else:
            # By nickname.
            for user in self.users.values():
                if user.nick == identifier:
                    try:
                        del self.users[user.id]
                        return True
                    except:
                        pass
                        # self._chatlog("< Tried to _deleteUser from unavailable userid: "+str(identifier)+" >", True)
        
        # No match.
        return False
    
    # Returns a unicode string.
    def _decodeMessage(self, msg):
        chars = msg.split(",")
        msg = ""
        for i in chars:
            try:
                msg += unichr(int(i))
            except:
                pass
        return msg
    
    def _encodeMessage(self, msg):
        # Handle unicode (special characters).
        try:    msg = msg.decode("utf-8")
        except: pass
        
        msg2 = []
        for i in msg:
            try:
                msg2.append(str(ord(i)))
            except:
                pass
        return ",".join(msg2)
    
    def _sendCommand(self, cmd, pars=[]):
        if not SETTINGS["SendCommands"]:
            return
        
        msg = {"msg": rtmp_protocol.DataTypes.COMMAND, "command": [u"" + cmd, 0, None,] + pars}
        # Ignore, if disconnected.
        if self.connected:
            # Apply a limit of 10 privmsg's/notices (& uncam) in 1 second.
            if cmd in {"privmsg", "owner_run"}:
                self.limitMsgs["msgs"] += 1
                # Set first msg time().
                if self.limitMsgs["msgs"] == 1:
                    self.limitMsgs["first"] = time.time()
                # Complete 1 second if needed, and reset count.
                elif self.limitMsgs["msgs"] == 10:
                    d = time.time() - self.limitMsgs["first"]
                    if d < 1:
                        time.sleep(1-d)
                    self.limitMsgs["msgs"] = 0
            # Send command.
            self.connection.writer.write(msg)
            self.connection.writer.flush()
    
    # Adds timestamp to log messages, prints to console, and saves to file.
    def _chatlog(self, msg, alert=False):
        # When getting strings with Unicode.
        try:
            msg = msg.decode("utf-8", "replace")
        except:
            pass
        
        # Normal chat messages have a prefix, to emphasise them.
        if not alert:
            msg = "> " + msg
        
        msg = ("["+get_current_time()+"]["+str(self.roomID)+"]["+self.room+"] " + msg)
        
        if self.chatVerbose:
            if (not self.connected or self.printOverride or
                not SETTINGS["RunningOnWindows"] or not SETTINGS["UserInput"]):
                try:
                    print(msg.encode("unicode-escape"))     # .encode("string-escape")
                except:
                    # traceback.print_exc()
                    print(msg.encode("ascii", "replace"))
            else:
                self.chatlogQueue.append(msg)
        
        if self.chatLogging:
            d = LOG_BASE_DIRECTORY
            if not os.path.exists(d):
                os.makedirs(d)
            
            with open(d + self.room + "_" + LOG_FILENAME_POSTFIX, "a") as logfile:
                try:
                    logfile.write(msg.encode("unicode-escape") + "\n")
                except:
                    logfile.write(msg.encode("ascii", "replace") + "\n")
    
    # Flushes into console, all queues messages, by addition order.
    def _chatlogFlush(self):
        for msg in self.chatlogQueue:
            try:
                print(msg.encode("unicode-escape"))     # .encode("string-escape")
            except:
                # traceback.print_exc()
                print(msg.encode("ascii", "replace"))
        self.chatlogQueue = []
    
    # Checks if the bot is in the room's user list, from TC API.
    # Does reconnect() if not in the room.
    def _keepAlive(self):
        i = 0
        while self.keepAlive:
            time.sleep(120)
            
            try:
                raw = requests.get("http://api.tinychat.com/"+self.room+".xml", timeout=15)
                text = raw.text
                
                # Page not available.
                available = raw.status_code == 200
                
                # PW rooms deny this function.
                ps = 'error="Password required"' in text
                
                # Either nick, or assume reconnection if no user().
                try:
                    nick = self.user.nick
                    res = nick in text
                except:
                    nick = "is"
                    res = False
                
                if available and not pw and not res:
                    i += 1
                    # Consecutive not-in-room only apply.
                    if i == 2:
                        room._chatlog("Bot "+nick+" not in room "+self.room+"! Reconnecting...", True)
                        room.reconnect()
                else:
                    i = 0
            except:
                pass
    
    # Events #
    
    # When a user joins, before supplying a nickname. First join() is self.
    # Or from a the joins event, from users already in the room.
    def onJoin(self, u, joins=False, myself=False):
        user = self._makeUser(u.id)
        user.nick = u.nick
        user.account = u.account
        user.mod = u.mod
        if u.stype:
            user.pro = True
        user.admin = u.own
        user.gp = u.gp
        user.alevel = u.alevel
        user.broadcasting = u.bf
        user.lurking = u.lf
        s = user.nick + " ["+str(user.id)+"]"
        if user.lurking:
            s += " (Guest-Mode)"
        if user.account:
            s += " ("+user.account+")"
        if user.mod:
            s += " (MOD)"
        if user.pro:
            s += " (PRO)"
        if user.gp:
            s += " ("+str(user.gp)+" gp)"
        
        if myself:
            self.user = user
            # cauth required to use privmsg().
            self.sendCauth(user.id)
            self._chatlog("You have joined the room as "+s+".", True)
        else:
            if joins:
                self._chatlog(s + " is in the room.", True)
            else:
                self._chatlog(s + " has joined the room.", True)
        
        # Further handling.
        if SETTINGS['onJoinExtend']:
            try:
                SETTINGS['onJoinExtend'](self, user, joins, myself)
            except:
                traceback.print_exc()
        
        # Handle cammed users.
        if user.broadcasting:
            self.onBroadcast(user.nick, user.id, True)
    
    # After finishing all the connection events. Ready for action!
    def onJoinsdone(self):
        # Internal instructions for further handling.
        if self.instructions or (SETTINGS["Instructions"] and INSTRUCTIONS):
            doInstructions(self)
        
        # Keepalive.
        t = threading.Thread(target=self._keepAlive, args=())
        t.daemon = True
        t.start()
        
        # Set first nick.
        if self.nick and self.user.nick.startswith("guest-"):
            time.sleep(1.4)     # Humane delay.
            self.setNick()
        
        # Instructions or further handling.
        if SETTINGS['onJoinsdoneExtend']:
            try:
                SETTINGS['onJoinsdoneExtend'](self)
            except:
                traceback.print_exc()
        
        # Otherwise, do things when done entering room.
        self._sendCommand("banlist", [])
    
    # When a user has left the room, for any reason.
    # userID is int().
    def onQuit(self, nick, userID):
        user = self._getUser(userID)
        # Server sends double quits.
        if not user:
            # print "No user object from onQuitHandle(): "+nick+" ["+str(userID)+"]"
            return
        
        self._chatlog(nick + " ["+str(userID)+"] has left.", True)
        
        # Further handling.
        if SETTINGS['onQuitExtend']:
            try:
                SETTINGS['onQuitExtend'](self, user)
            except:
                traceback.print_exc()
        
        # Remove from room.users{}.
        self._deleteUser(userID)
    
    # A notice message event.
    def onNotice(self, notice):
        self._chatlog("*"+notice+"*")
        
        # Further handling.
        if SETTINGS['onNoticeExtend']:
            try:
                SETTINGS['onNoticeExtend'](self, notice)
            except:
                traceback.print_exc()
    
    # Handles commands sent in room, and YTqueue.
    def onMessage(self, user, message):
        msg = message.msg
        
        self._chatlog(user.nick + ": " + msg)
        
        # Further handling.
        if SETTINGS['onMessageExtend']:
            try:
                SETTINGS['onMessageExtend'](self, user, msg)
            except:
                traceback.print_exc()
        
        # Further events must only come from opers!
        if not user.mod:
            return
        
        # Track YT events.
        self.trackYT(msg, user)
        # Track SC events.
        self.trackSC(msg, user)
    
    # Handles commands sent by PM to bot.
    def onPM(self, user, message):
        msg = message.msg
        
        if msg == "/reported":
            reported = True
            acct = "Not Logged-In"
            if user.account:
                acct = user.account
            self._chatlog("You have been REPORTED for abuse by "+
                user.nick+" ("+str(user.id)+") ("+acct+")!", True)
        else:
            reported = False
            self._chatlog("(pm) " + user.nick + ": " + msg)
        
        # Further handling.
        if SETTINGS['onPMExtend']:
            try:
                SETTINGS['onPMExtend'](self, user, msg, reported)
            except:
                traceback.print_exc()
    
    # Handle all finished-joining-room events.
    def onNickChange(self, old, new, userid):
        # Update user object.
        user = self._getUser(userid)
        
        user.nick = new
        
        self._chatlog(old+" ["+str(user.id)+"] is now known as "+new+".", True)
        
        # Further handling.
        if SETTINGS['onNickChangeExtend']:
            try:
                SETTINGS['onNickChangeExtend'](self, user, new, old)
            except:
                traceback.print_exc()
        
        # Send currently playing YT and SC from bot to newcomers.
        if old.find("guest-") == 0 and new != self.user.nick:
            if YTqueue["start"] != 0:
                self.sendYT(user)
            if SCqueue["start"] != 0:
                self.sendSC(user)
    
    # Get banlist, and forgive matching users from queue.
    def onBanlist(self, banlist):
        if type(banlist) is not list:
            return
        if len(banlist) <= 1:
            return
        
        # ID, Nickname.
        if len(banlist) == 2:
            self.banlist.append([banlist[0], banlist[1]])
        else:
            for i in range(0, len(banlist), 2):
                self.banlist.append([banlist[i], banlist[i+1]])
        
        # Further handling.
        if SETTINGS['onBanlistExtend']:
            try:
                SETTINGS['onBanlistExtend'](self)
            except:
                traceback.print_exc()
        
        # Forgive all.
        if len(self.forgives) == 1 and self.forgives[0] is True:
            # i = 0
            for user in self.banlist:
                userID = int(user[0])
                userNick = user[1]
                # time.sleep(0.2)
                self.forgive(userID)
                # i += 1
                # Limit.
                # if i > 50: break
            # If done forgiving all, then empty list.
            if len(self.banlist) == 0:
                self.forgives = []
        
        # Forgive any in forgives list.
        elif len(self.forgives) > 0:
            i = 0
            # j = 0
            for nick in self.forgives:
                # Forgive all partial matches.
                if type(nick) is list:
                    word = nick[0]
                    
                    for user in self.banlist:
                        userID = int(user[0])
                        userNick = user[1]
                        
                        if word in userNick:
                            # time.sleep(0.2)
                            self.forgive(userID)
                            if self.forgives[i]:
                                self.forgives[i] = None
                            # j += 1
                # Forgive all exact matches (multiple instances of same nick.)
                else:
                    for user in self.banlist:
                        userID = int(user[0])
                        userNick = user[1]
                        
                        if userNick == nick:
                            self.forgive(userID)
                            self.forgives[i] = None
                            # break
                i += 1
                # Limit.
                # if j > 50: break
            # Remove the emptied items.
            self.forgives = filter(None, self.forgives)
    
    # When a user goes on cam.
    def onBroadcast(self, nick, userid, fromJoin=False):
        # Phone users get have a :android or :iphone in their broadcast id.
        try:
            userid = int(userid)
            device = None
        except:
            col = userid.find(":")
            device = userid[col+1:]
            userid = int(userid[:col])
        
        user = self._getUser(userid)
        if not user:
            user = self._makeUser(userid)
            user.nick = nick
        user.device = device
        
        # Further handling.
        if SETTINGS['onBroadcastExtend']:
            try:
                SETTINGS['onBroadcastExtend'](self, user)
            except:
                traceback.print_exc()
        
        if not fromJoin:
            self._chatlog(nick + " is now broadcasting.", True)
        else:
            self._chatlog(nick + " is broadcasting.", True)
        user.broadcasting = True
        
        if user == self.user or not SETTINGS["ReceiveCams"]:
            return
        
        try:
            self.createStream(user.id, "down")
        except:
            pass
    
    # When any cam is closed (by mod), in the room.
    def onCamClosed(self, nick=None):
        if not nick:
            return
        
        self._chatlog(nick+" has been uncammed.", True)
        
        if nick == self.user.nick:
            self.onCam = False
        else:
            user = self._getUser(nick)
            if not user:
                return
            
            user.broadcasting = False
    
    # When bot or someone gets banned.
    def onBanned(self, userID=None, nick=None, bot=False):
        if bot:
            self.disconnect()
            self._chatlog("Bot just got banned!!!", True)
            if SETTINGS["ReconnectOnBan"]:
                self._chatlog("Reconnecting...", True)
                self.reconnect()
            else:
                # Don't bother reconnecting, in any form.
                self.keepAlive = False
        else:
            self._chatlog(nick+" ["+str(userID)+"] has been banned!", True)
    
    # Track all the room's YT events.
    def trackYT(self, msg, user):
        # pause   /mbpa youTube
        # resume  /mbpl youTube 4397070
        # close   /mbc youTube
        # start   /mbs youTube SMsquUcea-E 0
        # skip    /mbsk youTube 67000
        
        try:
            if msg[0] != "/":
                return
            
            # Remove trailing slash.
            msg = msg[1:]
            
            parts = msg.split()
            cmd = parts[0]
            target = parts[1]
        except:
            return
        
        # Only for youtubes.
        if target != "youTube":
            return
        
        # Only skip/resume/start have values here.
        try:
            val = parts[2]
            try:
                # resume
                skip = int(float(val) / 1000)         # To seconds.
            except:
                # start
                vid = val
                skip = int(float(parts[3]) / 1000)    # To seconds.
        except:
            pass
        
        # Respond to command.
        if cmd == "mbs":
            # Track the video (for queue mode.)
            try:
                t = int(time.time())
                YTqueue["start"]    = t
                YTqueue["skip"]     = skip
                YTqueue["paused"]   = 0
                YTqueue["current"]  = vid
                YTqueue["length"]   = 0
                
                duration = getYTduration(vid)
                
                if not duration:
                    raise Exception()
                
                YTqueue["length"] = duration
            except:
                pass
            return
        
        if cmd == "mbc":
            # Video closed.
            YTqueue["start"] = 0
            return
        
        if cmd == "mbsk":
            # Skip time in video.
            t = int(time.time())
            
            if YTqueue["start"]:
                YTqueue["skip"] = skip
        
        if cmd == "mbpl":
            # Resume video at time.
            if YTqueue["start"] and YTqueue["paused"]:
                # Restore by delta since paused.
                t = int(time.time())
                YTqueue["start"]    = t
                YTqueue["skip"]     = skip
                YTqueue["paused"]   = 0
        
        if cmd == "mbpa":
            # Pause video.
            if YTqueue["start"] and not YTqueue["paused"]:
                # Save pausing time.
                YTqueue["paused"] = int(time.time())
    
    # Track all the room's SC events.
    def trackSC(self, msg, user):
        try:
            if msg[0] != "/":
                return
            
            # Remove trailing slash.
            msg = msg[1:]
            
            parts = msg.split()
            cmd = parts[0]
            target = parts[1]
        except:
            return
        
        # Only for soundclouds.
        if target != "soundCloud":
            return
        
        # Only skip/resume/start have values here.
        try:
            val = parts[2]
            try:
                # resume
                skip = int(float(val) / 1000)         # To seconds.
            except:
                # start
                vid = val
                skip = int(float(parts[3]) / 1000)    # To seconds.
        except:
            pass
        
        # Respond to command.
        if cmd == "mbs":
            # Track the song (for queue mode.)
            try:
                t = int(time.time())
                SCqueue["start"]    = t
                SCqueue["skip"]     = skip
                SCqueue["paused"]   = 0
                SCqueue["current"]  = track
                SCqueue["length"]   = 0
                
                duration = getSCduration(track)
                
                # Unstreamable track.
                if type(duration) is str:
                    raise Exception()
                
                SCqueue["length"]   = duration
            except:
                pass
            return
        
        if cmd == "mbc":
            # Track closed.
            SCqueue["start"] = 0
            return
        
        if cmd == "mbsk":
            # Skip time in track.
            t = int(time.time())
            
            if SCqueue["start"]:
                SCqueue["skip"] = skip
        
        if cmd == "mbpl":
            # Resume track at time.
            if SCqueue["start"] and SCqueue["paused"]:
                # Restore by delta since paused.
                t = int(time.time())
                SCqueue["start"]    = t
                SCqueue["skip"]     = skip
                SCqueue["paused"]   = 0
        
        if cmd == "mbpa":
            # Pause track.
            if SCqueue["start"] and not SCqueue["paused"]:
                # Save pausing time.
                SCqueue["paused"] = int(time.time())
    
    # Actions #
    
    # Send message to room.
    # Can filter to specific user, and return error message if failed.
    def say(self, msg, to=None):
        # Split message into several, if too long.
        # Avoid burdening say() - instead use notice().
        if len(msg) > SETTINGS["MaxCharsMsg"]:
            maxLines = 3
            maxChars = maxLines * SETTINGS["MaxCharsMsg"] + 10
            # Slice for efficiency, if needed.
            if len(msg) > maxChars:
                msg = msg[:maxChars]
            
            words = msg.split()
            msgs = [""]
            i = 0
            for word in words:
                if word == "": continue
                
                # Either add word, or move to next msg.
                if len(msgs[i]) + len(word) < SETTINGS["MaxCharsMsg"]:
                    msgs[i] += word + " "
                else:
                    # If there's more than max lines, then end with three dots.
                    if i == maxLines-1:
                        if len(msgs[i]) >= SETTINGS["MaxCharsMsg"]-3:
                            msgs[i] = msgs[i][:-3] + "..."
                        else:
                            msgs[i] = msgs[i].strip() + "..."
                        # End loop!
                        break
                    # Move to next msg.
                    i += 1
                    msgs.append(word + " ")
        else:
            # Or just send one.
            msgs = []
            msgs.append(msg)
        
        if to:
            res = self._getUser(to)
            if not res:
                return "User "+to+" was not found..."
            to = res
        
        # Send all msgs.
        for curmsg in msgs:
            if not to:
                self._sendCommand("privmsg",
                    [u"" + self._encodeMessage(curmsg),
                    u"" + self.color + ",en"])
            else:
                if to.broadcasting:
                    self._sendCommand("privmsg",
                        [u"" + self._encodeMessage(curmsg),
                        u"" + self.color + ",en",
                        "b"+to.id+"-"+to.nick])
                    self._sendCommand("privmsg",
                        [u"" + self._encodeMessage(curmsg),
                        u"" + self.color + ",en",
                        "n"+to.id+"-"+to.nick])
                else:
                    self._sendCommand("privmsg",
                        [u"" + self._encodeMessage(curmsg),
                        u"" + self.color + ",en",
                        "n"+to.id+"-"+to.nick])
        
        if to:
            to = " ("+to.nick+")"
        else:
            to = ""
        
        self._chatlog(self.user.nick +to+": " + msg)
    
    # Send a private message to another user by nickname, id, or user obj.
    # Returns False if user not found, True on success.
    def pm(self, user, msg):
        # Only to existing users, to hide it from others.
        if type(user) in {str, unicode, int}:
            user = self._getUser(user)
            if not user:
                return False
        
        # Split message into several, if too long.
        if len(msg) > SETTINGS["MaxCharsPM"]:
            maxLines = 9
            maxChars = maxLines * SETTINGS["MaxCharsPM"] + 10
            # Slice for efficiency, if needed.
            if len(msg) > maxChars:
                msg = msg[:maxChars]
            
            words = msg.split()
            msgs = [""]
            
            i = 0
            for word in words:
                if word == "": continue
                
                # Either add word, or move to next msg.
                if len(msgs[i]) + len(word) < SETTINGS["MaxCharsPM"]:
                    msgs[i] += word + " "
                else:
                    # If there's more than max lines, then end with three dots.
                    if i == maxLines-1:
                        if len(msgs[i]) >= SETTINGS["MaxCharsPM"]-3:
                            msgs[i] = msgs[i][:-3] + "..."
                        else:
                            msgs[i] = msgs[i].strip() + "..."
                        # End loop!
                        break
                    # Move to next msg.
                    i += 1
                    msgs.append(word + " ")
        else:
            # Or just send one. Mimic split-msg structure.
            msgs = []
            msgs.append(msg)
        
        # Send all msgs.
        for curmsg in msgs:
            if user.broadcasting:
                self._sendCommand("privmsg",
                    [self._encodeMessage("/msg "+user.nick+" "+curmsg),
                    self.color+",en",
                    "b"+str(user.id)+"-"+user.nick])
                # Can't figure when someone stops broadcasting, so gotta send both.
                self._sendCommand("privmsg",
                    [self._encodeMessage("/msg "+user.nick+" "+curmsg),
                    self.color+",en",
                    "n"+str(user.id)+"-"+user.nick])
            else:
                self._sendCommand("privmsg",
                    [self._encodeMessage("/msg "+user.nick+" "+curmsg),
                    self.color+",en",
                    "n"+str(user.id)+"-"+user.nick])
        
        self._chatlog("(@" + user.nick +") "+ str(self.user.nick) +": "+msg)
        
        return True
    
    # Send a nameless notice message to room.
    # If not oper, default to say().
    def notice(self, msg):
        if not self.user.mod:
            self.say(msg)
            return
        
        # Split message into several, if too long.
        if len(msg) > SETTINGS["MaxCharsNotice"]:
            maxLines = 6
            maxChars = maxLines * SETTINGS["MaxCharsNotice"] + 10
            # Slice for efficiency, if needed.
            if len(msg) > maxChars:
                msg = msg[:maxChars]
            
            words = msg.split()
            msgs = [""]
            i = 0
            for word in words:
                if word == "": continue
                
                # Either add word, or move to next msg.
                if len(msgs[i]) + len(word) < SETTINGS["MaxCharsNotice"]:
                    msgs[i] += word + " "
                else:
                    # If there's more than max lines, then end with three dots.
                    if i == maxLines-1:
                        if len(msgs[i]) >= SETTINGS["MaxCharsNotice"]-3:
                            msgs[i] = msgs[i][:-3] + "..."
                        else:
                            msgs[i] = msgs[i].strip() + "..."
                        # End loop!
                        break
                    # Move to next msg.
                    i += 1
                    msgs.append(word + " ")
        else:
            # Or just send one.
            msgs = []
            msgs.append(msg)
        
        # Send all msgs, properly encoded.
        for curmsg in msgs:
            # Encode only unusual characters to URL Encoded.
            encodedMsg = ""
            for char in curmsg:
                try:
                    num = ord(char)
                    if num < 32 or num > 126:
                        # Special character.
                        # encodedMsg += quote_plus(char)
                        encodedMsg += quote_plus(char.encode("utf-8", "replace"), safe='/')
                    elif num == 37:
                        encodedMsg += "%25"
                    elif num == 32:
                        encodedMsg += "%20"
                    else:
                        # Normal character.
                        encodedMsg += char
                except:
                    pass
            
            self._sendCommand("owner_run", [u"notice" + encodedMsg])
        
        # Back to unicode() for string manipulation.
        try:
            msg = msg.decode("utf-8", "replace")
        except:
            pass
        self._chatlog("*"+self.user.nick+"*: " + msg)
    
    # Does nothing, if has illegal characters.
    def setNick(self, nick=""):
        # Force limit nicks to 32 characters.
        if len(nick) > 32:
            nick = nick[:32]
        
        # On join done, set up first nick.
        if not nick:
            nick = self.nick
        
        # Nicks can only be certain characters.
        # 'yes' if re.search(r'[^\w\-\[\]\{\}]', "f432fgre_-[]{}") else 'no'
        if re.search(r'[^\w\-\[\]\{\}]', nick):
            return "My nickname can only include alphanumeric characters, dash, and square & curly brackets."
        
        # Must not be named the same as the room!
        if nick.lower() == self.room.lower():
            nick += "X"
        
        self.nick = nick
        
        self._sendCommand("nick", [u"" + self.nick])
    
    def setTopic(self, topic=""):
        self._sendCommand("topic", [topic])
    
    # Ask for the latest banlist.
    def getBanlist(self):
        self._sendCommand("banlist", [])
    
    # Close a camera by nick, userid, or user obj.
    def uncam(self, user):
        if type(user) in {int, str, unicode}:
            user = self._getUser(user)
            if not user:
                return False
            nick = user.nick
        else:
            nick = user.nick
        
        self._sendCommand("owner_run", [ u"_close" + nick])
    
    # Bans a user by nick, userid, or user obj, and returns True.
    # Returns False if user not found.
    # Returns error message if user is oper or botter.
    # Will NEVER ban itself (it is possible, yes.)
    def ban(self, user, override=False):
        if not user:
            return False
        
        if type(user) in {str, unicode, int}:
            user = self._getUser(user)
            if not user:
                return False
        
        # Except self.
        if user is self.user:
            return False
        
        if not override and user.mod:
            return "I do not ban moderators..."
        
        self._sendCommand("kick", [user.nick, str(user.id)])
        return True
    
    # Forgives a user by nick, userid, or user obj.
    def forgive(self, user):
        if type(user) is int:
            userid = user
        elif type(user) in {str, unicode}:
            user = self._getUser(user)
            if not user:
                return False
            userid = user.id
        else:
            userid = user.id
        
        self._sendCommand("forgive", [u"" + str(userid)])
    
    # If nick is True, forgive all.
    # Otherwise forgive a single nickname, or many by a partial string.
    # Will be forgiven when next banlist is received.
    # Case-sensitive.
    def forgiveNick(self, nick, allPartials = False):
        if nick is True:
            # Forgive all users in banlist.
            self.forgives = [True]
        elif allPartials:
            # Forgive all partial matches.
            self.forgives.append([nick])
        else:
            # Forgive first full match.
            self.forgives.append(nick)
    
    # Sends a start-YT msg with current time and pause state.
    # Assumes user exists.
    def sendYT(self, user):
        cmd = "mbs"
        if (YTqueue["paused"]):
            cmd = "mbsp"
        
        # Bot must have played something, already.
        if not YTqueue["history"]:
            return
        
        # Either not in history, because played by a mod,
        # Or not tracking current, for any reason, so don't send it.
        if YTqueue["current"] != YTqueue["history"][-1]:
            return
        
        vid = YTqueue["history"][-1]
        skip = getTimeYT()              # Also checks, and resets queue, if no vid playing.
        
        if not skip:
            return
        
        self._sendCommand("privmsg", [u"" + self._encodeMessage("/" + cmd +" youTube " + 
            vid + " " + str(skip*1000)), "#0" + ",en", "n" + str(user.id) + "-" + user.nick])
    
    # Sends a start-SC msg with current time and pause state.
    # Assumes user exists.
    def sendSC(self, user):
        cmd = "mbs"
        if (SCqueue["paused"]):
            cmd = "mbsp"
        
        # Bot must have played something, already.
        if not SCqueue["history"]:
            return
        
        # Either not in history, because played by a mod,
        # Or not tracking current, for any reason, so don't send it.
        if SCqueue["current"] != SCqueue["history"][-1]:
            return
        
        track = SCqueue["history"][-1]
        skip = getTimeSC()              # Also checks, and resets queue, if no track playing.
        
        if not skip:
            return
        
        self._sendCommand("privmsg", [u"" + self._encodeMessage("/" + cmd +" soundCloud " + 
            track + " " + str(skip*1000)), "#0" + ",en", "n" + str(user.id) + "-" + user.nick])
    
    # Try to play a YT video, or relegate to startSC().
    # Returns True on success.
    # Returns str() error message on failure.
    def startYT(self, video, skip=0):
        # Catch invalid video.
        if not video:
            return "No video given to startYT()..."
        
        # Make certain of skip.
        if not skip:
            skip = 0
        elif type(skip) is str:
            try:
                skip = int(skip)
            except:
                skip = 0
        
        # Relegate to playSoundcloud() if SC link matched.
        if "soundcloud.com/" in video:
            return self.startSC(video, skip)
        
        # Also, might get an SC ID, which is a very big number.
        # Youtube IDs are [seems to be] never a number.
        try:
            track = int(video)
            return self.startSC(video, skip)
        except:
            pass
        
        vid = getYTid(video)
        
        # Failure getting ID.
        if not vid:
            return "Failed to get video ID..."
        
        # I could verify the video ID legit, if I really wanted.
        # http://gdata.youtube.com/feeds/api/videos/VIDEOIDHERE
        
        # Success.
        try:
            # Validate skip.
            skip = int(skip)
        except:
            # Otherwise, default to...
            skip = 0
        
        self.say("/mbs youTube " + vid + " " + str(skip*1000))
        
        # Don't add, if it's the same as the last video.
        if not YTqueue["history"] or YTqueue["history"][-1] != vid:
            YTqueue["history"].append(vid)
        
        # Reset the previous state.
        t = int(time.time())
        YTqueue["start"]    = t
        YTqueue["paused"]   = 0
        YTqueue["skip"]     = skip
        YTqueue["current"]  = vid
        YTqueue["length"]   = 0
        
        # Further requires an API key.
        if not SETTINGS["YTKey"]:
            return True
        
        # Track the video.
        duration = getYTduration(vid)
        
        if type(duration) is str:
            return duration
        
        YTqueue["length"] = duration
        return True
    
    def closeYT(self):
        self.say("/mbc youTube")
        YTqueue["start"] = 0
    
    def pauseYT(self):
        self.say("/mbpa youTube")
        # Save pausing time.
        if not YTqueue["paused"]:
            YTqueue["paused"] = int(time.time())
    
    def resumeYT(self):
        # In seconds.
        skip = getTimeYT()
        
        if not skip:
            return
        
        self.say("/mbpl youTube " + str(skip*1000))
        
        # Replay with current skip.
        t = int(time.time())
        YTqueue["start"]    = t
        YTqueue["skip"]     = skip
        YTqueue["paused"]   = 0
    
    # Returns False on bad skip value.
    def skipYT(self, skip):
        try:
            # Either seconds.
            skip = int(skip)
        except:
            # Or a string to convert to seconds.
            try:
                skip = toSeconds(skip)
            except:
                return False
        
        # Skip to time.
        self.say("/mbsk youTube " + str(skip*1000))
        
        if YTqueue["start"]:
            t = int(time.time())
            YTqueue["skip"] = skip
    
    # Try to play a SC track.
    # Returns True on success.
    # Returns str() error message on failure.
    def startSC(self, track, skip=0):
        # Catch invalid video.
        if not track:
            return "No track given to startSC()..."
        
        # Never 0 in skip, and make certain of it.
        # if not skip or skip == "0": skip = 1
        # elif type(skip) is str:
        #     try:
        #         skip = int(skip)
        #     except:
        #         skip = 1
        
        res = getSCid(track)
        
        # Failure.
        if type(res) is str:
            return res
        
        # Success.
        trackID = res[0]
        duration = res[1]
        
        try:
            # Validate skip.
            skip = int(skip)
        except:
            # Otherwise, default to...
            skip = 0
        
        self.say("/mbs soundCloud " + trackID + " " + str(skip*1000))
        
        # Don't add, if it's the same as the last track.
        if not SCqueue["history"] or SCqueue["history"][-1] != trackID:
            SCqueue["history"].append(trackID)
        
        t = int(time.time())
        SCqueue["start"]    = t
        SCqueue["length"]   = duration      # Will be 0, if no duration from API.
        SCqueue["skip"]     = skip
        SCqueue["current"]  = trackID
        SCqueue["paused"]   = 0
        return True
    
    def closeSC(self):
        self.say("/mbc soundCloud")
        SCqueue["start"] = 0
    
    def pauseSC(self):
        self.say("/mbpa soundCloud")
        # Save pausing time.
        if not SCqueue["paused"]:
            SCqueue["paused"] = int(time.time())
    
    def resumeSC(self):
        skip = getTimeSC()
        
        if not skip:
            return
        
        self.say("/mbpl soundCloud " + str(skip*1000))
        
        # Replay with current skip.
        t = int(time.time())
        SCqueue["start"]    = t
        SCqueue["skip"]     = skip
        SCqueue["paused"]   = 0
    
    # Returns False on failure.
    def skipSC(self, skip):
        try:
            # Either seconds.
            skip = int(skip)
        except:
            # Or a string to convert to seconds.
            try:
                skip = toSeconds(skip)
            except:
                return False
        
        # Skip to time.
        self.say("/mbsk soundCloud " + str(skip*1000))
        
        if SCqueue["start"]:
            t = int(time.time())
            SCqueue["skip"] = skip
    
    # Changes self.color to ar andom color.
    # Returns the selected color (key) name.
    def cycleColor(self):
        keys = TINYCHAT_COLORS.keys()
        key = keys[random.randint(0, len(keys) - 1)]
        self.color = TINYCHAT_COLORS[key]
        return key
    
    # API (partial) #
    
    def authHTTP(self):
        # self.headers = {'Host': 'tinychat.com',
        #                 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0',
        #                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        #                 "Referer": "http://tinychat.com/start/",
        #                 'Accept-Language': 'en-US,en;q=0.5',
        #                 'DNT': 1,
        #                 'Connection': 'keep-alive'}
        
        self.headers = {'Host': 'tinychat.com',
        # 'Connection': 'keep-alive',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Origin': 'http://tinychat.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36 OPR/32.0.1948.25',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'http://tinychat.com/login?frame=true',
        'Accept-Encoding': 'gzip, deflate, lzma',
        'Accept-Language': 'en-US,en;q=0.8'}
        
        # Only if login data available.
        if self.username and self.passwd:
            res = self.login()
            
            # Failed to establish connection or get proper response.
            if not res:
                self._chatlog("Failed to connect to tinychat.com for login...", True)
                raise Exception()   # Kill this connection attempt.
            
            # Failure to login, if only 1 cookie added.
            if len(self.s.cookies) == 1:
                self._chatlog("Failed to login! Check your username and password...", True)
                raise Exception()   # Kill this connection attempt.
    
    # Logins to Tinychat account, aquiring login cookies into session.
    # Returns True on successful login.
    def login(self, username="", password=""):
        if not username:
            username = self.username
        if not password:
            password = self.passwd
        
        data = {"form_sent": "1",
                "referer": "",
                "next": "",
                "remember": "1",
                "username": username,
                "password": password,
                "passwordfake": "Password"}
        url = "http://tinychat.com/login"
        
        # self.s = requests.session()
        try:
            # TODO: Remove empty cookies?
            raw = self.s.request(method='POST', url=url, data=data, headers=self.headers,
                cookies=self.cookies, timeout=20, proxies=self.proxies)
            if raw.status_code != 200:
                raise Exception("Status code: "+str(raw.status_code))
        except:
            # traceback.print_exc()
            return False
        
        return True
    
    # Returns the rtmp url, and sets .roomTime and .type.
    def getRTMPInfo(self):
        if self.roomPassword:
            pwurl = ("http://apl.tinychat.com/api/find.room/"+self.room+"?site="+self.site+
                "&url=tinychat.com&password="+self.roomPassword)
            raw = self.s.get(pwurl, timeout=15, proxies=self.proxies)
        else:
            url = "http://apl.tinychat.com/api/find.room/"+self.room+"?site="+self.site
            # TODO: Remove empty cookies?
            raw = self.s.request(method="GET", url=url, headers=self.headers,
                cookies=self.cookies, timeout=15, proxies=self.proxies)
        
        if "result='PW'" in raw.text:
            self.roomPassword = raw_input("Enter the password for room " + self.room + ": ")
            return self.getRTMPInfo()
        else:
            # Set some vars.
            # if raw.text.find("name=") >= 0:
            #     self.site = raw.text.split("name='")[1].split("'")[0].split("^")[0]
            if raw.text.find("time=") >= 0:
                self.roomTime = raw.text.split("time='")[1].split("'")[0]
            if raw.text.find("roomtype=") >= 0:
                self.type = raw.text.split("roomtype='")[1].split("'")[0]
            # For greenroom broadcast approval.
            if raw.text.find("bpassword=") >= 0:
                self.bpass = raw.text.split("bpassword='")[1].split("'")[0]
            if raw.text.find('greenroom="1"') >= 0:
                self.greenroom = True
            
            # Return rtmp address.
            return raw.text.split("rtmp='")[1].split("'")[0]
    
    def getEncMills(self):
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': 1}
        mills = int(float(time.time()))
        # mills = self.roomTime
        url = "http://tinychat.com/cauth?room="+self.room+"&t="+str(mills)
        # r = self.s.request(method="GET", url=url, headers=headers, timeout=15)
        r = self.s.get(url, timeout=15, proxies=self.proxies)
        
        res = None
        try:
            res = r.text.split('{"cookie":"')[1].split('"')[0]
            # self._chatlog("Got CauthTimestamp:\t" + res)
        except:
            self._chatlog("Failed to get CauthTimestamp!")
        return res
    
    def solveRecaptcha(self):
        # Optional request to skip recaptcha.
        if self.noRecaptcha:
            return 0
        
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': 1}
        url = "http://tinychat.com/cauth/captcha" # Should have a number, like: ?0.5732091250829399 or ?0.2929161135107279
        # r = self.s.request(method="GET", url=url, headers=headers, timeout=15)
        r = self.s.get(url, timeout=15, proxies=self.proxies)
        
        # False stands for general failure.
        # 0 Stands for no need to do recaptcha.
        # A token string stands for need to do recaptcha!
        result = False
        
        if '"need_to_solve_captcha":0' in r.text:
            result = 0
        else:
            string = "token"
            i = r.text.find(string)
            
            if i >= 0:
                start = i + len(string) + 3
                end = r.text.find('"', start)
                result = r.text[start:end]
        
        return result
    
    def sendCauth(self, userID):
        url = "http://tinychat.com/api/captcha/check.php?room="+self.site+"^"+self.room+"&guest_id="+str(self.user.id)
        raw = self.s.get(url, timeout=15, proxies=self.proxies)
        if 'key":"' in raw.text:
            r = raw.text.split('key":"')[1].split('"')[0]
            rr = r.replace("\\", "")
            self._sendCommand("cauth", [u"" + rr])
        else:
            # Bypass Captcha.
            if BYPASS_CAPTCHA:
                try:
                    res = BYPASS_CAPTCHA.main(self)
                    if res:
                        self._sendCommand("cauth", [u"" + res])
                        self._chatlog("Captcha bypassed...")
                        return
                except:
                    traceback.print_exc()
            
            msg = "Failed to bypass room Captcha... Unable to send messages..."
            if self.autoBot:
                if type(self.autoBot) is list:
                    nick = self.autoBot[0]
                    ROOMS[0].pm(nick, msg)
                else:
                    ROOMS[0].notice(msg)
            else:
                self._chatlog(msg)
    
    def doTimestampRecaptcha(self):
        recaptcha = self.solveRecaptcha()
        
        if recaptcha is False:
            self._chatlog("Failed to get Recaptcha token!")
        elif recaptcha == 0:
            self._chatlog("No need to solve Recaptcha...")
        else:
            self._chatlog("Please solve this Recaptcha in your browser:")
            self._chatlog("tinychat.com/cauth/recaptcha?token=" + recaptcha)
            print "tinychat.com/cauth/recaptcha?token=" + recaptcha
            
            link = "http://www.tinychat.com/cauth/recaptcha?token="+recaptcha
            
            # Autobots, assuming from !advertise, should send link on main room or user.
            if self.autoBot:
                i = 1
                minstr = "minute"
                if i > 1:
                    minstr += "s"
                
                self._chatlog("Waiting for Recaptcha to be solved. " +
                    "You have "+str(i)+" "+minstr+", before Recaptcha token expires.")
                
                msg = "You have "+str(i)+" "+minstr+" to solve this Recaptcha: " + link
                if type(self.autoBot) is list:
                    nick = self.autoBot[0]
                    ROOMS[0].pm(nick, msg)
                else:
                    ROOMS[0].notice(msg)
                
                time.sleep(i * 60)
                
                recaptcha = self.solveRecaptcha()
                if recaptcha != 0:
                    msg = "Recaptcha failed (too late), disconnecting..."
                    if type(self.autoBot) is list:
                        nick = self.autoBot[0]
                        ROOMS[0].pm(nick, msg)
                    else:
                        ROOMS[0].notice(msg)
                    self.disconnect()
            else:
                if SETTINGS["InteractiveConsole"]:
                    # Windows only! Starts default browser.
                    if SETTINGS["RunningOnWindows"]:
                        e = os.system("start "+link)
                    
                    self._chatlog("And then press Enter to continue connecting...")
                    if not SETTINGS["RunningOnWindows"] or SETTINGS["UserInput"] is None:
                        raw_input()
                    else:
                        while True:
                            # Continue, after any key hit.
                            char = None
                            while msvcrt.kbhit():
                                char = msvcrt.getch()
                            if char: break
                else:
                    i = 1
                    minstr = "minute"
                    if i > 1:
                        minstr += "s"
                    self._chatlog("Waiting for Recaptcha to be solved, " +
                        "You have "+str(i)+" "+minstr+", before Recaptcha token expires.")
                    
                    string = ("Creation of link: <b>" + get_current_time() + "</b> " + current_date +
                        "<br> You have "+str(i)+" "+minstr+" to solve this Recaptcha, " +
                        "before page (token) expires and requires refreshing.<br><br>" +
                        "<a href='"+link+"'>Click here to open Recaptcha in a new window.</a><br><br>" +
                        "<iframe src='"+link+"' height='600' width='600' frameborder='0'></iframe>")
                    printFile(SETTINGS["Recaptcha"], string, local=True)
                    
                    # Check Recaptcha completion, to move on.
                    while True:
                        time.sleep(i*60)
                        
                        # Clear out previous recaptcha.
                        printFile(SETTINGS["Recaptcha"], local=True)
                        
                        recaptcha = self.solveRecaptcha()
                        
                        if recaptcha == 0:
                            self._chatlog("Recaptcha verified, connecting...")
                            break
                        elif recaptcha is False:
                            self._chatlog("Recaptcha token expired. " +
                                "Failed to get new Recaptcha token!")
                        else:
                            self._chatlog("Recaptcha token expired. New token generated:")
                            self._chatlog("tinychat.com/cauth/recaptcha?token=" + recaptcha)
                            print "tinychat.com/cauth/recaptcha?token=" + recaptcha
                            
                            link = "http://www.tinychat.com/cauth/recaptcha?token="+recaptcha
                            string = ("Creation of link: <b>" + get_current_time() + "</b> " + current_date +
                                "<br> You have "+str(i)+" "+minstr+" to solve this Recaptcha, " +
                                "before page (token) expires and requires refreshing.<br><br>" +
                                "<a href='"+link+"'>Click here to open Recaptcha in a new window.</a><br><br>" +
                                "<iframe src='"+link+"' height='600' width='600' frameborder='0'></iframe>")
                            printFile(SETTINGS["Recaptcha"], string, local=True)
        
        # Clear out recaptcha, when done.
        printFile(SETTINGS["Recaptcha"], local=True)
        
        self.timecookie = self.getEncMills()

# Returns the duration from a video ID, as int() in seconds.
# None on failure. Error str() if not embeddable.
def getYTduration(vid):
    try:
        raw = requests.get("https://www.googleapis.com/youtube/v3/videos?key="+
            SETTINGS["YTKey"]+"&part=contentDetails,status&id="+vid, timeout=15)
        obj = raw.json()
        item = obj['items'][0]  # First item.
        
        # Must be embeddable.
        if not item["status"]["embeddable"]:
            return "Video "+vid+" is not embeddable..."
        
        duration = StringifiedToSeconds(item["contentDetails"]["duration"])
    except:
        return "Failed to get video "+vid+" duration from YT API..."
    
    # Success.
    return duration

# Returns the duration from a track ID, as int() in seconds.
# None on failure.
def getSCduration(track):
    try:
        raw = requests.get("http://api.soundcloud.com/tracks?client_id="+
            SETTINGS["SCKey"]+"&ids="+track)
        trackObjs = raw.json()
        trackObj = trackObjs[0]
        
        duration = int(float(trackObj["duration"]) / 1000)     # To seconds.
        
        # Must be streamable.
        if not trackObj["streamable"]:
            return "Track is not streamable..."
    except:
        # NOTICE: This is a bug on SoundCloud's site!
        duration = 4 * 60
    
    # Success.
    return duration

# Returns the video ID from a string, usually a URL.
# Or False on failure.
def getYTid(vid):
    vid = vid.strip()
    
    if vid == "":
        return False
    
    find = vid.find("v=")
    if find >= 0:
        vid = vid.split("v=")[1][:11]
        return vid
    
    find = vid.find("youtu.be/")
    if find >= 0:
        vid = vid.split("youtu.be/")[1][:11]
        return vid
    
    if len(vid) == 11:
        return vid
    
    # Nothing matches, failure.
    return False

# Find the track ID from SC link, or use a given track ID.
# Returns [trackID, duration] first as str(), second as int() in seconds,
# Or an error message on failure.
def getSCid(track):
    # A number may be a track ID.
    # Expected from an automated lister in the bot;
    # Users are /not/ expected to give track IDs!
    try:
        trackID = str(int(track))
        
        # Requires access to the API.
        if SETTINGS["SCKey"]:
            duration = getSCduration(trackID)
            if type(duration) is str:
                return duration
        else:
            duration = 0
    except:
        # Requires access to the API.
        if not SETTINGS["SCKey"]:
            return "A SoundCloud Client ID is required to fetch the track ID from a link..."
        
        # Get track ID.
        try:
            # url must be full.
            if track.startswith(("soundcloud.com/", "www.soundcloud.com/")):
                track = "http://"+track
            raw = requests.get("http://api.soundcloud.com/resolve?client_id="+
                SETTINGS["SCKey"]+"&url="+track)
            trackObj = raw.json()
            
            # Must be streamable.
            if not trackObj["streamable"]:
                return "Track is not streamable..."
            
            trackID = trackObj["id"]
            duration = int(float(trackObj["duration"]) / 1000) # To seconds.
        except Exception as e:
            # NOTICE: This is a bug on SoundCloud's site!
            # Getting correct details from track's page.
            try:
                raw = requests.get(track, timeout=15)
                text = raw.text
                
                # Must be streamable.
                if "\"streamable\":true" not in b:
                    return "Track is not streamable..."
                
                trackID = b.split("soundcloud://sounds:")[1].split('"')[0]
                duration = b.split('<meta itemprop="duration" content="')[1].split('"')[0]
                duration = StringifiedToSeconds(duration)
            except:
                return "Failed to resolve track from SoundCloud API..."
    
    return [str(trackID), duration]

# Converts a user readable string to seconds.
# E.g. 5h4m3s
def toSeconds(d):
    d = d.lower()
    
    h = 0
    m = 0
    s = 0
    
    # Match and remove from string; repeat.
    find = d.find("h")
    if find >= 0:
        h = int(d[:find]) * 60 * 60     # Convert to seconds.
        d = d[find+1:]
    
    find = d.find("m")
    if find >= 0:
        m = int(d[:find]) * 60          # Convert to seconds.
        d = d[find+1:]
    
    # Only seconds left now, with or without the "s".
    find = d.find("s")
    if find >= 0:
        s = int(d[:find])
    elif d: # Only if it has seconds.
        s = int(d)
    
    t = h + m + s
    return t

# Converts stringified duration into seconds.
# Format is: XX#h#m#s
def StringifiedToSeconds(d):
    # Remove the postfix of "PT".
    d = d[2:]
    # Return the converted result.
    return toSeconds(d)

# Return the current time of playing YT video in seconds, or FALSE.
# Checks if a YT is started, and if it hasn't ended normally.
def getTimeYT():
    # Nothing playing.
    if not YTqueue["start"]:
        return False
    
    t = int(time.time())
    
    # Current position in time, relative to video.
    lapsed = t - YTqueue["start"] + YTqueue["skip"]
    
    # Check that the video hasn't ended by itself.
    if YTqueue["length"]:
        if not YTqueue["paused"] and lapsed > YTqueue["length"]:
            YTqueue["start"] = 0
            return False
    
    # Ignore time it was paused.
    if YTqueue["paused"]:
        d = t - YTqueue["paused"]
        lapsed -= d
    
    return lapsed

# Return the current time of playing SC track in seconds, or FALSE.
# Checks if a SC is started, and if it hasn't ended normally.
def getTimeSC():
    # Nothing playing.
    if not SCqueue["start"]:
        return False
    
    t = int(time.time())
    
    # Current position in time, relative to video.
    lapsed = t - SCqueue["start"] + SCqueue["skip"]
    
    # Check that the video hasn't ended by itself.
    if SCqueue["length"]:
        if not SCqueue["paused"] and lapsed > SCqueue["length"]:
            SCqueue["start"] = 0
            return False
    
    # Ignore time it was paused.
    if SCqueue["paused"]:
        d = t - SCqueue["paused"]
        lapsed -= d
    
    return lapsed

# Write text to file, Overwrites. Removes file if s is empty.
def printFile(f="", s="", local=False):
    if not f:
        return
    
    # Directory.
    if local:
        d = LOCAL_DIRECTORY
    else:
        d = ""
    
    if not s:
        try:
            os.remove(d+f)
        except:
            pass
        return
    
    # Append, if file exists.
    # if os.path.isfile(f):
    #     writing = "a"
    # else:
    #     writing = "w"
    
    with open(d+f, "w") as res:
        res.write(s)

# Remove HTML tags from text.
# Anything between < and >, including arrows.
def removeTags(string=""):
    if type(string) not in [str, unicode]:
        string = unicode(string)
    
    start = "<"
    end = ">"
    
    found = string.find(start)
    
    while found >= 0:
        foundEnd = string.find(end)
        
        # Must have an ending arrow for tag.
        if foundEnd == -1:
            break
        
        # Remove from string.
        string = string[:found] + string[foundEnd+1:]
        
        found = string.find(start)
    
    return string

# Make a room() and connect() it, with its retry mechanism.
def makeRoom(nick=None, replaceIndex=None):
    if not nick:
        nick = CONN_ARGS["nickname"]
    
    # Room name, [Nickname], [Username], [Password], [Room password].
    room = TinychatRoom(CONN_ARGS["room"], nick,
        CONN_ARGS["username"], CONN_ARGS["password"],
        replaceIndex=replaceIndex, doConnect=True)

# Starts the bot, and listens to console input.
def main():
    # Must be given a room name to enter.
    while not CONN_ARGS["room"]:
        CONN_ARGS["room"] = raw_input("Give me a room name to enter: ")
        CONN_ARGS["room"] = CONN_ARGS["room"].strip()
        if CONN_ARGS["room"]:
            CONN_ARGS["room"] = CONN_ARGS["room"].split()[0]
    
    SETTINGS["Recaptcha"] = "recaptcha_" + CONN_ARGS["room"] + ".txt"
    
    # Apply method injections.
    if MEDIA:
        TinychatRoom.getBauth           = MEDIA.getBauth
        TinychatRoom.createStream       = MEDIA.createStream
        TinychatRoom.closeStream        = MEDIA.closeStream
        TinychatRoom.deleteStream       = MEDIA.deleteStream
        TinychatRoom.onResult           = MEDIA.onResult
        TinychatRoom.publish            = MEDIA.publish
        TinychatRoom.play               = MEDIA.play
        TinychatRoom.onStatus           = MEDIA.onStatus
        TinychatRoom.downloadVideo      = MEDIA.downloadVideo
        TinychatRoom.uploadVideo        = MEDIA.uploadVideo
        TinychatRoom.uploadAudio        = MEDIA.uploadAudio
    
    if PROXY_MODULE:
        TinychatRoom.setSocket          = PROXY_MODULE.setSocket
    
    if BYPASS_ACCESS:
        TinychatRoom.getRTMPInfo        = BYPASS_ACCESS.getRTMPinfo
        TinychatRoom.getBauth           = BYPASS_ACCESS.getBauth
    
    if INSTRUCTIONS:
        INSTRUCTIONS.load(globals())
    
    # Make sure there's no connect() event soon after a previous one,
    # In same room and account.
    time.sleep(DELAY)
    
    # Create room() and connect(), with its retry mechanism.
    t = threading.Thread(target=makeRoom, args=())
    t.daemon = True
    t.start()
    
    try:
        while True:
            time.sleep(0.1)
            if ROOMS and ROOMS[0].connected:
                break
    except (SystemExit, KeyboardInterrupt):
        return
    
    # Keep alive without input, if no console.
    if not SETTINGS["InteractiveConsole"]:
        try:
            while SETTINGS["Run"]:
                time.sleep(1)
        except (SystemExit, KeyboardInterrupt):
            # Try to close connection cleanly; cleanup.
            try:
                # Keep to main room reference.
                ROOMS[0].disconnect()
            except:
                pass
            return
    
    # Handle user input, when connected.
    try:
        while SETTINGS["Run"]:
            # Limit loop speed.
            time.sleep(0.01)
            
            # Keep to main room reference. Halt while no room established.
            try:
                room = ROOMS[0]
            except:
                continue
            
            # Reset input variables on new input line.
            userInput = ""
            charOrd = 0
            
            if not SETTINGS["RunningOnWindows"] or SETTINGS["UserInput"] is None:
                userInput = raw_input()
            else:
                while msvcrt.kbhit():
                    char = msvcrt.getch()
                    charOrd += ord(char)
                
                if charOrd:
                    # Up. Repeat previous sending.
                    # if charOrd == 296:
                    #     if not SETTINGS["UserInputLast"]: continue
                    #     sys.stdout.write(SETTINGS["UserInputLast"])
                    if charOrd < 32 or charOrd > 126:
                        # Only normal printable characters are accepted.
                        continue
                    else:
                        SETTINGS["UserInput"].append(chr(charOrd))
                        sys.stdout.write(chr(charOrd))
                        # Reset input character.
                        charOrd = 0
                
                # Got one char? Pause output, and get more.
                while SETTINGS["UserInput"]:
                    while msvcrt.kbhit():
                        char = msvcrt.getch()
                        charOrd += ord(char)
                    
                    if charOrd:
                        # Either normal printable characters, or an event key.
                        if charOrd < 32 or charOrd > 126:
                            # Enter
                            if charOrd == 13:
                                userInput = "".join(SETTINGS["UserInput"])
                                SETTINGS["UserInputLast"] = userInput
                                del SETTINGS["UserInput"][:]
                                sys.stdout.write("\n\r")
                                break
                            # Backspace
                            if charOrd == 8:
                                SETTINGS["UserInput"] = SETTINGS["UserInput"][:-1]
                                sys.stdout.write("\b"+" "+"\b")
                            # Ctrl+C
                            if charOrd == 3:
                                del SETTINGS["UserInput"][:]
                                print("")
                                break
                        else:
                            SETTINGS["UserInput"].append(chr(charOrd))
                            sys.stdout.write(chr(charOrd))
                        # Reset input character.
                        charOrd = 0
            
            # Print all queued message.
            room._chatlogFlush()
            
            # Ignore empty input.
            if len(userInput) == 0:
                continue
            
            # Default to room message.
            if userInput[0] != "/":
                room.say(userInput)
                continue
            
            # Available commands.
            userInput = userInput[1:]
            
            if userInput.strip() == "":
                continue
            
            args = userInput.split()
            
            cmd = args.pop(0)
            msg = " ".join(args)
            
            if args:
                target = args[0]
            else:
                target = None
            
            try:
                if cmd == "say":
                    if not msg:
                        continue
                    room.say(msg)
                    continue
                
                if cmd == "sayto":
                    if not msg:
                        continue
                    
                    res = room.say(" ".join(args[1:]), to=target)
                    
                    if type(res) in {str, unicode}:
                        print(res)
                    continue
                
                if cmd in {"pm", "tell"}:
                    user = args.pop(0)
                    msg = " ".join(args)
                    
                    if not user or not msg:
                        continue
                    
                    res = room.pm(user, msg)
                    
                    if not res:
                        print("User "+user+" not found.")
                    else:
                        SETTINGS["LastPM"] = user
                    continue
                
                # Send to the last PM target, again.
                if cmd == "r":
                    if not SETTINGS["LastPM"]:
                        print("You haven't PM'd anyone, yet.")
                        continue
                    
                    msg = " ".join(args)
                    if not msg:
                        continue
                    res = room.pm(SETTINGS["LastPM"], msg)
                    if not res:
                        print("User "+SETTINGS["LastPM"]+" not found.")
                    continue
                
                if cmd in {"pmall"}:
                    if not msg:
                        continue
                    
                    i = 0
                    for user in room.users.values():
                        if user.id == room.user.id:
                            continue    # Skip self.
                        avoid = ["guest", "newuser"]
                        if any(x in user.nick for x in avoid):
                            continue     # Skip shit users.
                        
                        i += 1
                        room.pm(user.nick, msg)
                        time.sleep(0.3) # Avoid looking like a bot to the server by being too fast.
                    room._chatlog("Finished sending PM's to " + str(i) + " users!", True)
                    continue
                
                if cmd in "notice":
                    if not msg:
                        continue
                    room.notice(msg)
                    continue
                
                if cmd in {"list", "userlist"}:
                    print("--- Users list: ---")
                    users = room.users.items()
                    
                    i = 0
                    userslist = []
                    for user in users:
                        i += 1
                        user = user[1]
                        
                        text = "#"+str(i)+". " + user.nick + " ("+str(user.id)+")"
                        if user.account:
                            text += " ["+str(user.account)+"]"
                        if user.mod:
                            text += " (Moderator)"
                        if user.admin:
                            text += " (Admin)"
                        
                        userslist.append(text)
                        
                        if i == 100:
                            break
                    
                    # Verbose result.
                    print(" ".join(userslist))
                    print("--- End of Userlist @ "+str(i)+"/"+str(len(users))+" users. ---")
                    continue
                
                if cmd in {"nick", "rename"}:
                    if not target:
                        continue
                    room.setNick(target)
                    continue
                
                if cmd == "color":
                    prevColor = room.color
                    target = target.lower()
                    
                    if not target:
                        key = room.cycleColor()
                    elif target in TINYCHAT_COLORS:
                        room.color = TINYCHAT_COLORS[target]
                        key = target
                    
                    if (key == prevColor):
                        print("You are already using the color " + key.title() + ".")
                    else:
                        print("Your text color is now " + key.title() + ".")
                    continue
                
                if cmd == "ban":
                    if not target: continue
                    room.ban(target)
                    continue
                
                if cmd == "uncam":
                    if not target: continue
                    room.uncam(target)
                    continue
                
                if cmd in {"quit", "exit"}:
                    room.disconnect()
                    SETTINGS["Run"] = False
                    continue
                
                if cmd == "reconnect":
                    room.reconnect()
                    continue
                
                if cmd == "yt":
                    room.startYT(target)
                    continue
                
                if cmd == "close":
                    room.closeYT()
                    continue
                
                if cmd == "sc":
                    room.startSC(target)
                    continue
                
                if cmd == "sclose":
                    room.closeSC()
                    continue
                
                if cmd == "banlist":
                    if len(room.banlist) == 0:
                        continue
                    
                    print("--- Banlist by nickname: ---")
                    nicks = []
                    for user in room.banlist:
                        nicks.append(user[1])
                    print(", ".join(nicks))
                    print("--- End of " + str(len(room.banlist)) + " users in Banlist. ---")
                    continue
                
                if cmd == "forgive":
                    if not target:
                        continue
                    room.forgiveNick(target)        # Case-sensitive.
                    room.getBanlist()               # Update banlist.
                    continue
                
                if cmd == "forgiveall":
                    for pair in room.banlist:
                        userid = pair[0]
                        room.forgive(userid)
                    room.getBanlist()               # Update banlist.
                    continue
                
                if cmd == "topic":
                    if not msg:
                        continue
                    room.setTopic(msg)
                    continue
                
                if cmd in {"publish", "camup"}:
                    try:
                        room.createStream()
                        room.publish()
                    except:
                        pass
                
                if cmd == "global":
                    if not target:
                        print(globals())
                    else:
                        try:
                            print(globals()[target])
                        except:
                            print("Global variable " + target + " not found.")
                    continue
                
                if cmd in {"room", "local"}:
                    if not target:
                        print(room)
                    else:
                        try:
                            print(getattr(room, target))
                        except:
                            print("Room variable " + target + " not found.")
                    continue
                
                if cmd == "note":
                    if not msg: continue
                    try:
                        room._chatlog(msg, True)
                    except:
                        print(msg)
                    continue
                
                if cmd in {"help", "commands"}:
                    print("Available console commands: " + ", ".join(CMDS))
                    continue
            except:
                # Console commands should not fail.
                traceback.print_exc()
    except:
        # Try to close connection cleanly; cleanup.
        try:
            room = ROOMS[0]         # Only main room.
            room._chatlogFlush()
            room.disconnect()
        except:
            pass
        return

# For listing purposes.
CMDS = ["say", "sayto", "pm", "r", "pmall", "who", "list", "nick",
        "color", "ban", "uncam", "quit", "reconnect", "yt", "close", "sc",
        "sclose", "banlist", "forgive", "forgiveall", "topic", "notice",
        "global", "local"]

# Run standalone, without any bot extensions like Tunebot.
if __name__ == "__main__":
    main()
