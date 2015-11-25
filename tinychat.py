#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from rtmp import rtmp_protocol

import requests             # http://www.python-requests.org/
requests.packages.urllib3.disable_warnings() # For python < 2.7.9

import random
import os
import sys
import traceback            # https://docs.python.org/2/library/traceback.html
import time
from urllib import quote, quote_plus    # Handles URLs.
import json
import re

# Windows console fix, not necessary for everyone.
try:
    import codecs
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)
except:
    pass

from socket import *

import threading
ROOMS = []                  # First room should always be the main room & thread.

# Operation variables.
SETTINGS_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings", "")

# Delay before any (re)connection.
DELAY = 15

# Global bot settings.
SETTINGS = {
    # Client controls.
    "Run":                  True,           # Let a thread ask to exit process loop.
    "DebugConsole":         False,
    "DebugLog":             False,
    "ChatLog":              True,
    "ChatConsole":          True,
    "LastPM":               None,           # The nickname that last got a msg PM from bot.
    "IP":                   None,
    "PORT":                 None,
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
    "cauthBypass":              None,
    "disconnectExtend":         None,
    # Thread control.
    "LastRoomID":           0,
    "Reconnecting":         False,
    "SendCommands":         True,           # Disable sending messages to room.
    "KeepAlive":            None,           # The keepalive thread.
    # Input control.
    "RunningOnWindows":     False,
    "InteractiveConsole":   True,           # Has interactive console for user input.
    "UserInput":            None,
    "UserInputLast":        "",
    # Bot extra settings and controls.
    "ReadyMessage":         False,
    "FakeUser":             "Bot",          # Fake account name for /userinfo requests.
    "AutoOp":               None,
    "ProHash":              None,
    # Extra settings.
    "BanNewusers":          False,
    "MaxCharsMsg":          110,
    "MaxCharsPM":           90,
    "MaxCharsNotice":       160
}

# Running on a Windows machine, or otherwise.
if os.name == "nt": SETTINGS["RunningOnWindows"] = True

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

# The Login and RTMP connections arguments.
CONN_ARGS = {
    "room": "",
    "nickname": "Bot",
    "username": "",
    "password": ""
}

# Get connection arguments from command-line arguments:
# room=[tinychat*]ROOM, nick=NICK, user=USER, pass=PASS,
# ready=0/1, interactive=0/1, ip=IP, port=PORT.
try:
    if len(sys.argv) == 1:
        raise Exception("No arguments given to tinychat module...\n")
    
    # Default single argument is PASSWORD.
    if len(sys.argv) == 2 and sys.argv[1].find("=") == -1:
        CONN_ARGS["username"] = "tunebot"
        CONN_ARGS["password"] = sys.argv[1]
    else:
        for item in sys.argv:
            match = item.lower()
            
            if match.find("room=") == 0:
                val = item.split("=")[1]
                # Allow spaced room names.
                if val[0] == '"':
                    try:    val = val.split('"')[1]
                    except: pass
                CONN_ARGS["room"] = val
                continue
            
            if match.find("nick=") == 0 or match.find("nickname=") == 0:
                val = item.split("=")[1]
                CONN_ARGS["nickname"] = val
                continue
            
            if match.find("user=") == 0 or match.find("username=") == 0:
                val = item.split("=")[1]
                CONN_ARGS["username"] = val
                continue
            
            if match.find("pass=") == 0 or match.find("password=") == 0:
                val = item.split("=")[1]
                CONN_ARGS["password"] = val
                continue
            
            if match.find("ready=") == 0:
                val = item.split("=")[1]
                try:
                    SETTINGS["ReadyMessage"] = bool(int(val))
                except:
                    print("Argument READY must be 0 or 1, only.")
                continue
            
            if match.find("interactive=") == 0:
                val = item.split("=")[1]
                try:
                    SETTINGS["InteractiveConsole"] = bool(int(val))
                except:
                    print("Argument INTERACTIVE must be 0 or 1, only.")
                continue
except Exception as e:
    print(e)

# Time formats.
get_current_time = lambda: time.strftime("%H.%M.%S")
current_date = time.strftime("%d.%m.%Y")

# Logging.
try:
    LOG_BASE_DIRECTORY = os.environ["OPENSHIFT_LOG_DIR"] + "room_logs/"
except:
    LOG_BASE_DIRECTORY = "logs/"

LOG_FILENAME_POSTFIX = current_date + "_" + time.strftime("%H.%M.%S") + ".log"

# Handle debug verbosity.
def debugPrint(msg, room="unknown_room"):
    msg = msg.encode('ascii', 'ignore')
    if SETTINGS["DebugConsole"]:
        print("DEBUG: " + msg)
    if SETTINGS["DebugLog"]:
        d = LOG_BASE_DIRECTORY
        if not os.path.exists(d): os.makedirs(d)
        
        logfile = open(d + room + "_debug.log", "a")
        logfile.write(msg + "\n")
        logfile.close()

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

# Get the SC Client ID to track songs.
SCkey = ''
filename = SETTINGS_DIRECTORY + "scclientid.txt"
try:
    SCkey = open(filename)
    SCkey = SCkey.read().strip()
except:
    print("Failed to load the SoundCloud API key from " + filename + ".")

# Get the YT API Key to track videos.
YTkey = ''
filename = SETTINGS_DIRECTORY + "ytapikey.txt"
try:
    YTkey = open(filename)
    YTkey = YTkey.read().strip()
except:
    print("Failed to load the Youtube API key from " + filename + ".")

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
    def __init__(self, nick="", userID="", color="", lastMsg=""):
        self.nick = nick
        self.id = userID
        self.color = color
        self.lastMsg = lastMsg
        self.oper = False
        self.admin = False
        self.accountName = ""
        self.broadcasting = False   # Can't tell if stopped broadcasting.
        self.device = ""            # Tinychat identifies Android & iPhone users.
        self.pro = False

# A single room connection.
class TinychatRoom():
    def __init__(self, room, nick=None, username=None, passwd=None, roomPassword=None,
        instructions=None, printOverride=None, doConnect=None, replaceIndex=None, 
        noRecaptcha=None):
        # Put reference to room, in the list.
        if replaceIndex:
            ROOMS.insert(replaceIndex, self)
        else:
            ROOMS.append(self)
        
        self.noRecaptcha = noRecaptcha
        
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
        
        self.type = "show"                                      # Default, but also check in API.
        
        self.cookies = {}                                       # Holds requests session cookies.
        
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
        
        self.s = requests.session()
        self.__authHTTP()
        
        # Connect immediately, after initialization.
        self.doConnect = doConnect
        # Ignore print queueing, and print immediately.
        self.printOverride = printOverride
        
        self.roomPage = self.__getRoomPage(room)                # The room's HTML content.
        self.autoop = self.__getAutoOp(room)
        self.prohash = self.__getProHash(room)
        
        # Optionally filled in __getRTMPInfo().
        self.bpass = None
        self.greenroom = False
        
        self.tcurl = self.__getRTMPInfo()
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
        self.swfurl = "http://tinychat.com/embed/Tinychat-11.1-1.0.0.0640.swf?version=1.0.0.0640/[[DYNAMIC]]/8" #static
        self.flashVer = "WIN 18,0,0,232"                        # static
        self.pc = "Desktop 1.0.0.0640"
        
        # Overrides.
        if SETTINGS["IP"]: self.ip = SETTINGS["IP"]
        if SETTINGS["PORT"]: self.port = int(SETTINGS["PORT"])
        
        # Check Recaptcha, ask to fill if needed, and set cauthTimestamp.
        self.doTimestampRecaptcha()
        
        self.color = TINYCHAT_COLORS["black"]
        self.topic = ""
        self.users = {}     # self.users[NICK] = USER OBJECT
        self.user = None    # Holds the bot's user object.
        self.nextFails = 0  # Count .next() failures, to avoid infinite loop.
        self.banlist = []
        self.forgives = []
        
        # Connect immediately, after finished initialization.
        if self.doConnect:
            self.connect()
    
# Core connectivity functions.
    def connect(self, force=None):
        self._chatlog("Connecting to " + self.room + "...", True)
        
        if not self.connected or force:
            debugPrint("\n === NEW CONNECTION ===", self.room)
            debugPrint("Server: " + str(self.ip), self.room)
            debugPrint("Port: " + str(self.port), self.room)
            debugPrint("Tinychat URL: " + str(self.tcurl), self.room)
            debugPrint("URL: " + str(self.pageurl), self.room)
            debugPrint("App: " + str(self.app), self.room)
            debugPrint("Room: " + self.room, self.room)
            debugPrint("AutoOp: " + str(self.autoop), self.room)
            debugPrint("Time Cookie: " + str(self.timecookie), self.room)
            self.connection = rtmp_protocol.RtmpClient(self.ip, self.port, self.tcurl, 
                self.pageurl, self.swfurl, self.app, self.flashVer)
            try:
                self.connection.connect([self.room, self.autoop, self.type, self.site, self.username, "", self.timecookie])
                self.connected = True
                SETTINGS["Reconnecting"] = False
                self._chatlog(" === Connected to " + self.room + " === ", True)
                # Start listening to server.
                self._listen()
            except Exception as e:
                traceback.print_exc()
                self.connected = False
                self._chatlog("Failed to connect to " + self.room + "...", True)
    
    def _listen(self):
        while self.connected and not self.reconnecting:
            # Read next possible packet.
            try:
                msg = self.connection.reader.next()
            except timeout:
                # Only applies for the connect() attempt.
                if ROOMS[0] == self:
                    self.reconnect()
                else:
                    self.disconnect()
                break
            except:
                self.nextFails += 1
                self._chatlog("Failed to read next() packet...", True)
                # Kill after consecutive fails.
                if self.nextFails == 5:
                    # Main room reconnects immediately.
                    if ROOMS[0] == self:
                        self.reconnect()
                    else:
                        self.disconnect()
                    break
            else:
                # Reset count on success.
                self.nextFails = 0
            
            # Handle RTMP packets.
            try:
                debugPrint("SERVER: " + str(msg), self.room)
                
                if msg['msg'] == rtmp_protocol.DataTypes.COMMAND:
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
                        if not message: continue
                        
                        m = self._decodeMessage(message)
                        
                        if len(m) > 0:
                            if recipient[0] == "#":
                                recipient = "^".join(recipient.split("^")[1:])
                            else:
                                recipient = "-".join(recipient.split("-")[1:])
                            
                            user = self._getUser(nick)
                            if not user:
                                print("< Caught empty user at privmsg: "+nick+" >")
                            if not user:    user = self._makeUser(nick)
                            
                            message = TinychatMessage(m, nick, user, recipient, color)
                            user.lastMsg = message
                            user.color = color
                            # UNTESTED: Removed .lower() from both sides.
                            if recipient == self.nick.lower():
                                message.pm = True
                                if message.msg.startswith("/msg ") and len(message.msg.split(" ")) >= 2:
                                    message.msg = " ".join(message.msg.split(" ")[2:])
                                
                                self.onPM(user, message)
                            else:
                                # Ignore public userinfo requests.
                                if not message.msg.startswith("/userinfo "):
                                    self.onMessage(user, message)
                        continue
                    
                    if cmd == "registered":
                        continue
                    
                    if cmd == "join":
                        userID = pars[0]
                        nick = pars[1]
                        
                        # First join event is my own. Get my user object.
                        if not self.user:
                            user = self._getUser(nick)
                            if not user:    user = self._makeUser(nick)
                            user.id = userID
                            user.nick = nick
                            # Apply user object to bot.
                            self.user = user
                            # cauth required to use privmsg().
                            self.sendCauth(self.user.id)
                            continue
                        
                        self.onJoin(userID, nick)
                        continue
                    
                    if cmd == "joins":
                        if type(pars) is not list: continue
                        
                        # First item is like: u'#txt-tinychat^ROOMNAME'.
                        pars = pars[1:]
                        
                        # Empty.
                        if len(pars) <= 1: continue
                        
                        for i in range(0, len(pars), 2):
                            userid = pars[i]
                            nick = pars[i+1]
                            
                            user = self._getUser(nick)
                            if not user:    user = self._makeUser(nick)
                            user.id = userid
                        continue
                    
                    if cmd == "joinsdone":
                        self.onJoinsdone()
                        continue
                    
                    if cmd == "topic":
                        topic = pars[0]
                        self.topic = topic
                        self._chatlog("Topic set to: " + self.topic, True)
                        continue
                    
                    if cmd == "nick":
                        old = pars[0]
                        new = pars[1]
                        
                        # Replaces reference in room object, and handles event.
                        self.onNickChange(old, new)
                        continue
                    
                    if cmd == "notice":
                        event = pars[0]
                        
                        if event == "avon":
                            userid = pars[1]
                            nick = pars[2]
                            self.onBroadcast(nick, userid)
                        continue
                    
                    if cmd == "avons":
                        if type(pars) is not list: continue
                        
                        # First item is None.
                        pars = pars[1:]
                        
                        # Empty.
                        if len(pars) <= 1: continue
                        
                        for i in range(0, len(pars), 2):
                            userid = pars[i]
                            nick = pars[i+1]
                            
                            self.onBroadcast(nick, userid)
                        continue
                    
                    if cmd == "quit":
                        nick = pars[0]
                        
                        self.onQuit(nick)
                        continue
                    
                    if cmd == "kick":
                        userID = pars[0]
                        nick = pars[1]
                        
                        self._chatlog(nick + " ("+userID+") has been banned.", True)
                        continue
                    
                    if cmd == "oper":
                        nick = pars[1]
                        
                        user = self._getUser(nick)
                        user.oper = True
                        self._chatlog(user.nick + " is oper.", True)
                        continue
                    
                    if cmd == "deop":
                        nick    = pars[1]
                        
                        user = self._getUser(nick)
                        user.oper = False
                        self._chatlog(user.nick + " has lost their oper.", True)
                        continue
                    
                    if cmd == "banlist":
                        self.onBanlist(pars)
                        continue
                    
                    if cmd == "banned":
                        self._chatlog("Bot just got banned!!", True)
                        continue
                    
                    if cmd == "doublesignon":
                        try:
                            self._chatlog("The account "+self.user.accountName+
                                " is already being used by: ["+pars[1]+","+pars[0]+"].", True)
                        except:
                            self._chatlog("The account "+self.user.accountName+
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
                    
                    if cmd == "onstatus":
                        self._chatlog("onstatus: "+str(pars), True)
                        continue
                    
                    if cmd == "account":
                        userid = pars[0]["id"]
                        account = pars[0]["account"]
                        
                        # User asked is not logged in.
                        if account == "$noinfo" or userid == 0:
                            continue
                        
                        self.onUserinfoReceived(userid, account)
                        continue
                    
                    if cmd == "pros":
                        for userid in pars:
                            user = self._getUser(userid)
                            
                            if not user:
                                self._chatlog('Failed to _getUser() in pros, userid: '+str(userid), True)
                                continue
                            
                            user.pro = True
                            self._chatlog(user.nick + " is on a pro account.", True)
                        continue
                    
                    # Uncaught command! Ignore commands I don't care about.
                    if cmd not in {"onbwdone", "startbanlist", "owner", "giftpoints"}:
                        self._chatlog("UNHANDLED COMMAND: " + str(cmd) + " " + str(pars), True)
            except:
                self._chatlog("Error handling incoming packet...", True)
                traceback.print_exc()
    
    def disconnect(self):
        if self.connected:
            self.connected = False
            self._chatlogFlush()
            try:
                self.connection.socket.shutdown(1)
                self.connection.socket.close()
            except:
                self._chatlog("Failed to gracefully disconnect...", True)
            self._chatlog("=== Disconnected ===", True)
            
            try: ROOMS.pop(ROOMS.index(self))
            except: pass
            
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
        
        # Keep to index in ROOMS.
        try:    i = ROOMS.index(self)
        except: i = None
        
        # Close previous connection.
        self.disconnect()
        
        time.sleep(DELAY)
        
        room = TinychatRoom(CONN_ARGS["room"], self.nick, 
            CONN_ARGS["username"], CONN_ARGS["password"], replaceIndex=i)
        
        thread = threading.Thread(target=room.connect, args=())
        thread.daemon = True
        thread.start()
    
    # Adds a new user from nickname.
    # Returns the new user object.
    def _makeUser(self, nick):
        self.users[nick] = TinychatUser(nick=nick)
        return self.users[nick]
    
    # Gets an existing user by nick or id number,
    # or returns False if not found.
    def _getUser(self, identifier):
        if type(identifier) in [str, unicode]:
            try:
                return self.users[identifier]
            except:
                pass
        elif type(identifier) is int:
            for user in self.users.values():
                try:
                    if int(user.id) == identifier:
                        return user
                except:
                    self._chatlog('_getUser found user with invalid user.id: '+str(user), True)
                    traceback.print_exc()
        # No match.
        return False
    
    # Removes an existing user by nick from the bot listing,
    # or False if user doesn't exist.
    def _deleteUser(self, nick):
        if nick not in self.users:
            return False
        else:
            del self.users[nick]
            return True
    
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
        if not SETTINGS["SendCommands"]: return
        
        msg = {"msg": rtmp_protocol.DataTypes.COMMAND, "command": [u"" + cmd, 0, None,] + pars}
        debugPrint("CLIENT: " + str(msg), self.room)
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
        
        msg = ("["+get_current_time()+"]["+ str(self.roomID)+"]["+self.room+"] " + msg)
        
        if self.chatVerbose:
            if (not self.connected or self.printOverride or
                not SETTINGS["RunningOnWindows"] or SETTINGS["UserInput"] is None):
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
            
            logfile = open(d + self.room + "_" + LOG_FILENAME_POSTFIX, "a")
            try:
                logfile.write(msg.encode("unicode-escape") + "\n")
            except:
                logfile.write(msg.encode("ascii", "replace") + "\n")
            logfile.close()
    
    # Flushes into console, all queues messages, by addition order.
    def _chatlogFlush(self):
        for msg in self.chatlogQueue:
            try:
                print(msg.encode("unicode-escape"))     # .encode("string-escape")
            except:
                # traceback.print_exc()
                print(msg.encode("ascii", "replace"))
        self.chatlogQueue = []
    
# Events.
    # When a user joins, before supplying a nickname.
    def onJoin(self, userID, nick):
        user = self._getUser(nick)
        if not user:
            user = self._makeUser(nick)
        
        user.id = userID
        
        self._chatlog(user.nick + " has joined.", True)
        
        # Request account name.
        self.requestUserinfo(user)
        
        # Further handling.
        if SETTINGS['onJoinExtend']:
            try:
                SETTINGS['onJoinExtend'](self, user)
            except:
                traceback.print_exc()
    
    # After finishing all the connection events. Ready for action!
    def onJoinsdone(self):
        # Humane delay.
        time.sleep(1.5)
        
        if self.nick:
            self.setNick()
        
        # Instructions or further handling.
        if SETTINGS['onJoinsdoneExtend']:
            try:
                SETTINGS['onJoinsdoneExtend'](self)
            except:
                traceback.print_exc()
        
        # Otherwise, do things when done entering room.
        self._sendCommand("banlist", [])
        
        # Verbose to room.
        if SETTINGS["ReadyMessage"]: self.notice("I am now available. All systems go.")
    
    # When a user has left the room, for any reason.
    def onQuit(self, nick):
        self._chatlog(nick + " has left.", True)
        
        # Further handling.
        if SETTINGS['onQuitExtend']:
            try:
                SETTINGS['onQuitExtend'](self, nick)
            except:
                traceback.print_exc()
        
        # Remove from room.users{}.
        self._deleteUser(nick)
    
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
        
        # Track YT events.
        self.trackYT(msg, user)
        # Track SC events.
        self.trackSC(msg, user)
    
    # Handles commands sent by PM to bot.
    def onPM(self, user, message):
        self._chatlog("(pm) " + user.nick + ": " + message.msg)
        
        if msg == "/reported":
            reported = True
            acct = "Not Logged-In"
            if user.accountName:
                acct = user.accountName
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
    def onNickChange(self, old, new):
        # Update user object.
        user = self._getUser(old)
        if not user:
            user = self._makeUser(old)
        
        user.nick = new
        
        # Update room users[] list references.
        self.users[new] = user
        del self.users[old]
        
        self._chatlog(old + " is now known as " + new + ".", True)
        
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
            # Make sure we got the account name.
            if not user.accountName and self.user.nick != new:
                self.requestUserinfo(user)
    
    # IRRELEVANT.
    def onUserinfoRequest(self, user):
        return
        # self.sendUserInfo(user.nick, SETTINGS["FakeUser"]) # Or self.username
    
    def onUserinfoReceived(self, userid, account):
        # Get user object.
        user = self._getUser(userid)
        if not user:
            print("< Caught empty user at onUserinfoReceived: "+str(userid)+" >")
            return
        
        # Ignore repeats.
        if user.accountName == account:
            return
        
        user.accountName = account
        
        # Not logged-in.
        if user.accountName == "$noinfo": return
        
        self._chatlog(user.nick + " is logged in as " + account + ".", True)
        
        # Further handling.
        if SETTINGS['onUserinfoReceivedExtend']:
            try:
                SETTINGS['onUserinfoReceivedExtend'](self, user, account)
            except:
                traceback.print_exc()
        
        # Mark admin.
        if self.room == account:
            user.admin = True
    
    # Get banlist, and forgive matching users from queue.
    def onBanlist(self, banlist):
        if type(banlist) is not list: return
        if len(banlist) <= 1: return
        
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
        
        # Forgive from queue, if found.
        if len(self.forgives) == 1 and self.forgives[0] is True:
            # Forgive all.
            # i = 0
            for user in self.banlist:
                userID = user[0]
                userNick = user[1]
                # time.sleep(0.2)
                self.forgive(userID)
                # i += 1
                # Limit.
                # if i > 50: break
            # If done forgiving all, then empty list.
            if len(self.banlist) == 0:
                self.forgives = []
        elif len(self.forgives) > 0:
            i = 0
            # j = 0
            for nick in self.forgives:
                # First forgives all partial results.
                # Second forgives only first result.
                if type(nick) is list:
                    word = nick[0]
                    
                    for user in self.banlist:
                        userID = user[0]
                        userNick = user[1]
                        
                        if word in userNick:
                            # time.sleep(0.2)
                            self.forgive(userID)
                            if self.forgives[i]:
                                self.forgives[i] = None
                            # j += 1
                else:
                    for user in self.banlist:
                        userID = user[0]
                        userNick = user[1]
                        
                        if userNick == nick:
                            self.forgive(userID)
                            self.forgives[i] = None
                            break
                i += 1
                # Limit.
                # if j > 50: break
            # Remove the emptied items.
            self.forgives = filter(None, self.forgives)
    
    # When a user goes on cam.
    def onBroadcast(self, nick, userid):
        # Phone users get have a :android or :iphone in their broadcast id.
        try:
            userid = str(int(userid))
            device = None
        except:
            col = userid.find(":")
            device = userid[col+1:]
            userid = userid[:col]
        
        user = self._getUser(nick)
        if not user:
            user = self._makeUser(nick)
            user.id = userid
        user.device = device
        
        # Further handling.
        if SETTINGS['onBroadcastExtend']:
            try:
                SETTINGS['onBroadcastExtend'](self, user)
            except:
                traceback.print_exc()
        
        self._chatlog(nick + " is now broadcasting.", True)
        user.broadcasting = True
    
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
    
    # Track all the room's YT events.
    def trackYT(self, msg, user):
        # pause   /mbpa youTube
        # resume  /mbpl youTube 4397070
        # close   /mbc youTube
        # start   /mbs youTube SMsquUcea-E 0
        # skip    /mbsk youTube 67000
        
        try:
            if msg[0] != "/": return
            
            # Remove trailing slash.
            msg = msg[1:]
            
            parts = msg.split()
            cmd = parts[0]
            target = parts[1]
        except:
            return
        
        # Only for youtubes.
        if target != "youTube": return
        
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
            # Track the video (for !py mode.)
            try:
                duration = getYTduration(vid)
                
                if not duration: raise Exception()
                
                t = int(time.time())
                YTqueue["start"]    = t
                YTqueue["skip"]     = skip
                YTqueue["length"]   = duration
                YTqueue["paused"]   = 0
                YTqueue["current"]  = vid
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
            if msg[0] != "/": return
            
            # Remove trailing slash.
            msg = msg[1:]
            
            parts = msg.split()
            cmd = parts[0]
            target = parts[1]
        except:
            return
        
        # Only for soundclouds.
        if target != "soundCloud": return
        
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
            # Track the song (for !py mode.)
            try:
                duration = getSCduration(track)
                
                if not duration: raise Exception()
                
                t = int(time.time())
                SCqueue["start"]    = t
                SCqueue["skip"]     = skip
                SCqueue["length"]   = duration
                SCqueue["paused"]   = 0
                SCqueue["current"]  = track
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

# Actions.
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
        
        self._chatlog(self.nick +to+": " + msg)
    
    # Send a private message to another user by nickname or user obj.
    # Returns False if user not found, True on success.
    def pm(self, user, msg):
        # Only to existing users, to hide it from others.
        if type(user) is str or type(user) is unicode:
            user = self._getUser(user)
            if not user: return False
        
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
                    "b"+user.id+"-"+user.nick])
                # Can't figure when someone stops broadcasting, so gotta send both.
                self._sendCommand("privmsg", 
                    [self._encodeMessage("/msg "+user.nick+" "+curmsg), 
                    self.color+",en", 
                    "n"+user.id+"-"+user.nick])
            else:
                self._sendCommand("privmsg", 
                    [self._encodeMessage("/msg "+user.nick+" "+curmsg), 
                    self.color+",en", 
                    "n"+user.id+"-"+user.nick])
        
        self._chatlog("(@" + user.nick +") "+ str(self.nick) +": "+msg)
        
        return True
    
    # Send a nameless notice message to room.
    # If not oper, default to say().
    def notice(self, msg):
        if not self.user.oper:
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
                        encodedMsg += quote_plus(char)
                    elif num == 37:
                        encodedMsg += "%25"
                    elif num == 32:
                        encodedMsg += "%20"
                    else:
                        # Normal character.
                        encodedMsg += char
                except:
                    # Special character.
                    try:
                        encodedMsg += quote_plus(char.encode('utf8'), safe='/')
                    except:
                        pass
            
            self._sendCommand("owner_run", [u"notice" + encodedMsg])
        
        self._chatlog("*"+self.nick+"*: " + msg)
    
    # Sends a /userinfo request, or returns False if user not found.
    # user can be a nickname to _getUser(), or an existing user object.
    def requestUserinfo(self, user):
        if type(user) is str or type(user) is unicode:
            user = self._getUser(user)
        
        if not user: return False
        
        # self._sendCommand("privmsg", [u"" + self._encodeMessage("/userinfo $request"), 
        #     "#0,en", "b"+user.id+"-"+user.nick])
        # self._sendCommand("privmsg", [u"" + self._encodeMessage("/userinfo $request"), 
        #     "#0,en", "n"+user.id+"-"+user.nick])
        
        self._sendCommand("account", [str(user.id)])
    
    # IRRELEVANT.
    # Sends the bot's userinfo to another user, or return False if user not found.
    def sendUserInfo(self, user, username):
        return
        # user = self._getUser(user)
        # if not user: return False
        
        # self._sendCommand("privmsg", [self._encodeMessage("/userinfo "+username),
        #     "#0,en"+"n"+user.id+"-"+user.nick])
        # self._sendCommand("privmsg", [self._encodeMessage("/userinfo "+username),
        #     "#0,en"+"b"+user.id+"-"+user.nick])
    
    # Does nothing, if has illegal characters.
    def setNick(self, nick=""):
        # On join done, set up first nick.
        if not nick: nick = self.nick
        
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
    
    # Close a camera.
    def uncam(self, nick):
        self._sendCommand("owner_run", [ u"_close" + nick])
    
    # Bans a user by nickname or reference, and returns True.
    # Returns False if user not found.
    # Returns error message if user is oper or botter.
    def ban(self, user, override=False):
        if not user: return False
        
        if type(user) is str or type(user) is unicode:
            user = self._getUser(user)
            if not user: return False
        
        if not override and user.oper:
            return "I do not ban moderators..."
        
        self._sendCommand("kick", [user.nick, user.id])
        return True
    
    def forgive(self, userid):
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
        if (YTqueue["paused"]): cmd = "mbsp"
        
        # Bot must have played something, already.
        if not YTqueue["history"]: return
        
        # Either not in history, because played by a mod,
        # Or not tracking current, for any reason, so don't send it.
        if YTqueue["current"] != YTqueue["history"][-1]:
            return
        
        vid = YTqueue["history"][-1]
        skip = getTimeYT()              # Also checks, and resets queue, if no vid playing.
        
        if not skip: return
        
        self._sendCommand("privmsg", [u"" + self._encodeMessage("/" + cmd +" youTube " + vid + " " + str(skip*1000)), 
                            "#0" + ",en", "n" + user.id + "-" + user.nick])
    
    # Sends a start-SC msg with current time and pause state.
    # Assumes user exists.
    def sendSC(self, user):
        cmd = "mbs"
        if (SCqueue["paused"]): cmd = "mbsp"
        
        # Bot must have played something, already.
        if not SCqueue["history"]: return
        
        # Either not in history, because played by a mod,
        # Or not tracking current, for any reason, so don't send it.
        if SCqueue["current"] != SCqueue["history"][-1]:
            return
        
        track = SCqueue["history"][-1]
        skip = getTimeSC()              # Also checks, and resets queue, if no track playing.
        
        if not skip: return
        
        self._sendCommand("privmsg", [u"" + self._encodeMessage("/" + cmd +" soundCloud " + track + " " + str(skip*1000)), 
                            "#0" + ",en", "n" + user.id + "-" + user.nick])
    
    # Try to play a YT video, or relegate to SC.
    # Returns False or error message on failure, otherwise True.
    def startYT(self, video, skip=0):
        # Catch invalid video.
        if not video: return False
        
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
            self.startSC(video, skip)
            return True
        
        # Also, might get an SC ID, which is a very big number.
        # Youtube IDs are [seems to be] never a number.
        try:
            track = int(video)
            self.startSC(video, skip)
            return True
        except:
            pass
        
        vid = getYTid(video)
        
        # Failure getting ID.
        if not vid: return False
        
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
        
        # Clear out the previous state.
        YTqueue["start"] = 0
        YTqueue["paused"] = 0
        
        # Further requires an API key.
        if not YTkey: return True
        
        # Track the video.
        duration = getYTduration(vid)
        
        if not duration: return True
        
        t = int(time.time())
        YTqueue["start"]    = t
        YTqueue["length"]   = duration
        YTqueue["skip"]     = skip
        YTqueue["current"]  = vid
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
        
        if not skip: return
        
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
    # Returns False or error message on failure, otherwise True.
    def startSC(self, track, skip=0):
        # Catch invalid video.
        if not track: return False
        
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
        SCqueue["length"]   = duration
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
        
        if not skip: return
        
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

# RTMP Connection Helper Functions.
    def __authHTTP(self):
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
            res = self._login()
            
            # Failed to establish connection or get proper response.
            if not res:
                self._chatlog("Failed to connect to tinychat.com for login. Quitting...", True)
                sys.exit()
            
            # Failure to login, if only 1 cookie added.
            if len(self.s.cookies) == 1:
                self._chatlog("Failed to login! Check your username and password. Quitting...", True)
                sys.exit()
    
    # Logins to Tinychat account, aquiring login cookies into session.
    # Returns True on successful login.
    def _login(self, username="", password=""):
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
        
        self.s = requests.session()
        try:
            # TODO: Remove empty cookies?
            raw = self.s.request(method='POST', url=url, data=data, headers=self.headers, cookies=self.cookies, timeout=20)
            if raw.status_code != 200:
                raise Exception()
        except:
            traceback.print_exc()
            return False
        
        return True
    
    # Returns the rtmp url, and sets .roomTime and .type.
    def __getRTMPInfo(self):
        if self.roomPassword:
            pwurl = ("http://apl.tinychat.com/api/find.room/"+self.room+"?site="+self.site+
                "&url=tinychat.com&password="+self.roomPassword)
            raw = self.s.get(pwurl, timeout=15)
        else:
            url = "http://apl.tinychat.com/api/find.room/"+self.room+"?site="+self.site
            # TODO: Remove empty cookies?
            raw = self.s.request(method="GET", url=url, headers=self.headers, cookies=self.cookies, timeout=15)
            if "result='PW'" in raw.text:
                self.roomPassword = raw_input("Enter the password for room " + self.room + ": ")
                return self.__getRTMPInfo()
            else:
                if raw.text.find("time=") >= 0:
                    self.roomTime = raw.text.split("time='")[1].split("'")[0]
                # For greenroom broadcast approval.
                if raw.text.find("bpassword=") >= 0:
                    self.bpass = raw.text.split("bpassword='")[1].split("'")[0]
                if raw.text.find('greenroom="1"') >= 0:
                    self.greenroom = True
                
                # Return rtmp address.
                return raw.text.split("rtmp='")[1].split("'")[0]
    
    # Gets the room's HTML for AutoOp and ProHash.
    # Returns empty string if failed.
    def __getRoomPage(self, room):
        url = "http://tinychat.com/" + self.room
        try:
            # TODO: Remove empty cookies?
            raw = self.s.request(method="GET", url=url, headers=self.headers, cookies=self.cookies, timeout=15)
            return raw.text
        except:
            return ""
    
    def __getAutoOp(self, room):
        if SETTINGS["AutoOp"]:
            r = SETTINGS["AutoOp"]
        else:
            if ", autoop: \"" in self.roomPage:
                r = self.roomPage.split(", autoop: \"")[1].split("\"")[0]
                return r
            else:
                return ""
    
    def __getProHash(self, room):
        if SETTINGS["ProHash"]:
            r = SETTINGS["ProHash"]
        else:
            if ", prohash: \"" in self.roomPage:
                r = self.roomPage.split(", prohash: \"")[1].split("\"")[0]
                return r
            else:
                return ""
    
    def __getEncMills(self):
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
        r = self.s.get(url, timeout=15)
        
        res = None
        try:
            res = r.text.split('{"cookie":"')[1].split('"')[0]
            # self._chatlog("Got CauthTimestamp:\t" + res)
        except:
            self._chatlog("Failed to get CauthTimestamp!")
        return res
    
    def __solveRecaptcha(self):
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
        r = self.s.get(url, timeout=15)
        
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
        url = ("http://tinychat.com/api/captcha/check.php?room="+
            self.site+"^"+self.room+"&guest_id="+self.user.id)
        raw = self.s.get(url, timeout=15)
        if 'key":"' in raw.text:
            r = raw.text.split('key":"')[1].split('"')[0]
            rr = r.replace("\\", "")
            self._sendCommand("cauth", [u"" + rr])
        else:
            self._chatlog("Failed to pass chat captcha! " +
                "Bot will be unable to send messages to room.", True)
            # sys.exit()
                    
    def doTimestampRecaptcha(self):
        recaptcha = self.__solveRecaptcha()
        
        if recaptcha is False:
            self._chatlog("Failed to get Recaptcha token!")
        elif recaptcha == 0:
            self._chatlog("No need to solve Recaptcha...")
        else:
            self._chatlog("Please solve this Recaptcha in your browser:")
            self._chatlog("tinychat.com/cauth/recaptcha?token=" + recaptcha)
            print "tinychat.com/cauth/recaptcha?token=" + recaptcha
            
            link = "http://www.tinychat.com/cauth/recaptcha?token="+recaptcha
            
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
                verboseHTTP(string)
                
                # Check Recaptcha completion, to move on.
                while True:
                    time.sleep(i*60)
                    
                    recaptcha = self.__solveRecaptcha()
                    
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
                        verboseHTTP(string)
        
        # Clear out recaptcha, when done.
        verboseHTTP()
        
        self.timecookie = self.__getEncMills()

# Returns the duration from a video ID, as int() in seconds.
# None on failure.
def getYTduration(vid):
    try:
        raw = requests.get("https://www.googleapis.com/youtube/v3/videos?id="+
            vid+"&part=contentDetails&key="+YTkey, timeout=15)
        obj = raw.json()
        
        duration = StringifiedToSeconds(obj['items'][0]["contentDetails"]["duration"])
    except:
        return
    
    # Success.
    return duration

# Returns the duration from a track ID, as int() in seconds.
# None on failure.
def getSCduration(track):
    try:
        raw = requests.get("http://api.soundcloud.com/tracks?client_id="+SCkey+"&ids="+track)
        trackObjs = raw.json()
        trackObj = trackObjs[0]
        duration = int(float(trackObj["duration"]) / 1000)     # To seconds.
    except:
        # NOTICE: This is a bug on SoundCloud's site!
        duration = 4 * 60
    
    # Success.
    return duration

# Returns the video ID from a string, usually a URL.
# Or False on failure.
def getYTid(vid):
    vid = vid.strip()
    
    if vid == "": return False
    
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
    # Requires access to the API.
    if not SCkey:
        return "A SoundCloud Client ID is required to fetch the track ID from a link..."
    
    # A number may be a track ID.
    # Expected from an automated lister in the bot;
    # Users are /not/ expected to give track IDs!
    try:
        trackID = str(int(track))
        duration = getSCduration(trackID)
    except:
        # Get track ID.
        try:
            # url must be full.
            if track.startswith(("soundcloud.com/", "www.soundcloud.com/")):
                track = "http://"+track
            raw = requests.get("http://api.soundcloud.com/resolve?client_id="+SCkey+"&url="+track)
            trackObj = raw.json()
            trackID = trackObj["id"]
            duration = int(float(trackObj["duration"]) / 1000) # To seconds.
        except Exception as e:
            # NOTICE: This is a bug on SoundCloud's site!
            # Getting correct details from track's page.
            try:
                raw = requests.get(track, timeout=15)
                text = raw.text
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
    if not YTqueue["start"]: return False
    
    t = int(time.time())
    
    # Current position in time, relative to video.
    lapsed = t - YTqueue["start"] + YTqueue["skip"]
    
    # Check that the video hasn't ended by itself.
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
    if not SCqueue["start"]: return False
    
    t = int(time.time())
    
    # Current position in time, relative to video.
    lapsed = t - SCqueue["start"] + SCqueue["skip"]
    
    # Check that the video hasn't ended by itself.
    if not SCqueue["paused"] and lapsed > SCqueue["length"]:
        SCqueue["start"] = 0
        return False
    
    # Ignore time it was paused.
    if SCqueue["paused"]:
        d = t - SCqueue["paused"]
        lapsed -= d
    
    return lapsed

# Update the recaptcha.txt file loaded in HTTP with status.
def verboseHTTP(string=None):
    # Delete file.
    if not string:
        try:
            os.remove("recaptcha.txt")
        except:
            pass
        return
    
    # Append, if file exists.
    if os.path.isfile("recaptcha.txt"):
        writing = "a"
    else:
        writing = "w"
    
    res = open("recaptcha.txt", writing)
    res.write(string)
    res.close()

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

# Checks if the main-room bot is in the room's user list, from TC API.
# Does reconnect() if not in the room.
def keepAlive():
    counter = 0
    
    while True:
        time.sleep(120)
        
        try:
            room = ROOMS[0]
            
            raw = requests.get("http://api.tinychat.com/"+room.room+".xml", timeout=15)
            text = raw.text
            
            # Page not available.
            if raw.status_code != 200:
                available = False
            else:
                available = True
            
            # PW rooms deny this function.
            pw = text.find('error="Password required"')
            if pw >= 0:
                pw = True
            else:
                pw = False
            
            res = text.find(room.user.nick)
            
            if available and not pw and res == -1:
                counter += 1
                # Consecutive not-in-room only apply.
                if counter == 2:
                    room._chatlog("Bot not in room! Reconnecting...", True)
                    room.reconnect()
            else:
                counter = 0
        except:
            pass

# Starts the bot, and listens to console input.
def main():
    # Must be given a room name to enter.
    while not CONN_ARGS["room"]:
        CONN_ARGS["room"] = raw_input("Give me a room name to enter: ")
        CONN_ARGS["room"] = CONN_ARGS["room"].strip()
        if CONN_ARGS["room"]:
            CONN_ARGS["room"] = CONN_ARGS["room"].split()[0]
    
    # Make sure there's no connect() event soon after a previous one,
    # In same room and account.
    time.sleep(DELAY)
    
    # Room name, [Nickname], [Username], [Password], [Room password].
    room = TinychatRoom(CONN_ARGS["room"], CONN_ARGS["nickname"], 
        CONN_ARGS["username"], CONN_ARGS["password"])
    
    # start_new_thread(room.connect, ())
    thread = threading.Thread(target=room.connect, args=())
    thread.daemon = True
    thread.start()
    
    while not room.connected: time.sleep(1)
    
    # Track uncaught disconnection from client-side, for main thread.
    SETTINGS["KeepAlive"] = threading.Thread(target=keepAlive, args=())
    SETTINGS["KeepAlive"].daemon = True
    SETTINGS["KeepAlive"].start()
    
    # Keep alive without input, if no console.
    if not SETTINGS["InteractiveConsole"]:
        while SETTINGS["Run"]:
            time.sleep(1)
    
    # Handle user input, when connected.
    while SETTINGS["Run"]:
        # Transition to reconnection.
        if SETTINGS["Reconnecting"]:
            time.sleep(1)
            continue
        
        room = ROOMS[0]
        
        # Reset input variables on new input line.
        userInput = ""
        charOrd = 0
        
        try:
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
        except SystemExit:
            # Print all queued message.
            try:
                room._chatlogFlush()
                room.disconnect()
            except:
                pass
            sys.exit()
        except KeyboardInterrupt:
            # Print all queued message.
            try:
                room._chatlogFlush()
                room.disconnect()
            except:
                pass
            sys.exit()
        else:
            # Print all queued message.
            try:    room._chatlogFlush()
            except: continue
                
        
        # Ignore empty input.
        if len(userInput) == 0: continue
        
        # Default to room message.
        if userInput[0] != "/":
            room.say(userInput)
            continue
        
        # Available commands.
        userInput = userInput[1:]
        
        if userInput.strip() == "": continue
        
        args = userInput.split()
        
        cmd = args.pop(0)
        msg = " ".join(args)
        
        if args: target = args[0]
        else:    target = None
        
        try:
            if cmd == "say":
                if not msg: continue
                room.say(msg)
                continue
            
            if cmd == "sayto":
                if not msg: continue
                
                res = room.say(" ".join(args[1:]), to=target)
                
                if type(res) in {str, unicode}:
                    print(res)
                continue
            
            if cmd in {"pm", "tell"}:
                user = args.pop(0)
                msg = " ".join(args)
                
                if not user or not msg: continue
                
                res = room.pm(user, msg)
                
                if not res: print("User "+user+" not found.")
                else: SETTINGS["LastPM"] = user
                continue
            
            # Send to the last PM target, again.
            if cmd == "r":
                if not SETTINGS["LastPM"]:
                    print("You haven't PM'd anyone, yet.")
                    continue
                
                msg = " ".join(args)
                if not msg: continue
                res = room.pm(SETTINGS["LastPM"], msg)
                if not res: print("User "+SETTINGS["LastPM"]+" not found.")
                continue
            
            if cmd in {"pmall"}:
                if not msg: continue
                
                i = 0
                for user in room.users.values():
                    if user.id == room.user.id: continue    # Skip self.
                    avoid = ["guest", "newuser"]
                    if any(x in user.nick for x in avoid): continue     # Skip shit users.
                    
                    i += 1
                    room.pm(user.nick, msg)
                    time.sleep(0.3) # Avoid looking like a bot to the server by being too fast.
                room._chatlog("Finished sending PM's to " + str(i) + " users!", True)
                continue
            
            if cmd in "notice":
                if not msg: continue
                room.notice(msg)
                continue
            
            if cmd == "userinfo":
                if not target: continue
                room.requestUserinfo(target)
                continue
               
            if cmd in {"list", "userlist"}:
                print("--- Users list: ---")
                users = room.users.items()
                
                i = 0
                userslist = []
                for user in users:
                    i += 1
                    user = user[1]
                    
                    text = "#"+str(i)+". " + str(user.nick) + " ("+str(user.id)+")"
                    if user.accountName:
                        text += " ["+str(user.accountName)+"]"
                    if user.oper:
                        text += " (Moderator)"
                    if user.admin:
                        text += " (Admin)"
                    
                    userslist.append(text)
                    
                    if i == 100: break
                
                # Verbose result.
                print(" ".join(userslist))
                print("--- End of Userlist @ "+str(i)+"/"+str(len(users))+" users. ---")
                continue
               
            if cmd in {"nick", "rename"}:
                if not target: continue
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
                sys.exit()
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
                if len(room.banlist) == 0: continue
                
                print("--- Banlist by nickname: ---")
                nicks = []
                for user in room.banlist:
                    nicks.append(user[1])
                print(", ".join(nicks))
                print("--- End of " + str(len(room.banlist)) + " users in Banlist. ---")
                continue
               
            if cmd == "forgive":
                if not target: continue
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
                if not msg: continue
                room.setTopic(msg)
                continue
            
            if cmd in {"publish", "camup"}:
                room._sendCreateStream()
                room._sendPublish()
            
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
            traceback.print_exc()

# For listing purposes.
CMDS = ["say", "sayto", "pm", "r", "pmall", "userinfo", "list", "nick",
        "color", "ban", "uncam", "quit", "reconnect", "yt", "close", "sc",
        "sclose", "banlist", "forgive", "forgiveall", "topic", "notice",
        "global", "local"]

# Run standalone, without any bot extensions like Tunebot.
if __name__ == "__main__":
    main()