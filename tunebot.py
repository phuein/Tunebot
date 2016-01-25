#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# The friendly Tunebot! [ by James Koss phuein@gmail.com ] January 24th, 2016.
# -------------------------------------------------------------------
# Started as Qbot in PHP, which was extensively modified and fixed,
# And then translated into Python, using the core code from Pinychat.

# This is a tinychat.py extension module,
# Expecting a patched version of tinychat.py to try/except its functions,
# Which are patched into it as globals.

# Unicode support is troublesome, and therefore not official.

# Coded in Sublime Text 3 beta, latest.

import tinychat

import requests                                 # http://www.python-requests.org/

requests.packages.urllib3.disable_warnings()    # For python < 2.7.9

import random
import traceback                                # https://docs.python.org/2/library/traceback.html
import re                                       # https://docs.python.org/2/library/re.html
import threading
import time
import os
import json
import sys
from urllib import quote, quote_plus            # Handles URLs.

# Return an unscaped string from an HTML string.
import HTMLParser

unescape = HTMLParser.HTMLParser().unescape

# Converts words to plural form.
from pluralize import pluralize

# The prefix for commands.
try:
    CMD = tinychat.SETTINGS["CMD"]
except:
    CMD = "!"

NICKNAME = "Tunebox"     # Default nickname.
# Absolute directory, so no confusion when loaded as a module.
try:
    LOCAL_DIRECTORY     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
except:
    LOCAL_DIRECTORY     = ""
# Holds further private modules and settings files.
SETTINGS_DIRECTORY = os.path.join(LOCAL_DIRECTORY, "settings", "")

START_TIME = time.time()    # Remember when script began, for !uptime.
SC_MIN_ID = 100000          # Number representing the minimum value for SoundCloud track ID.

# Further settings are loaded with the settings file, and maybe otherwise.
CONTROLS = {
    # Basics.
    "greet":            False,      # Smartly respond to people saying greetings.
    "defaultTopic":     "",         # Make it easier to revert topic.
    "botActive":        True,       # Whether bot responds to commands, at all.
    "playLock":         False,      # Doesn't let threads override each others startYT().
    "ReadyMessage":     None,       # Message room when bot is ready (joinsdone().)
    "BroadcastMessage": None,       # Message room when someone cams up.
    # Defenses.
    "camclose":         False,
    "camban":           False,
    "autoban":          False,
    "autokick":         False,
    "autoforgive":      False,
    "banSnapshots":     True,
    "banNewusers":      False,
    "banGuests":        True,       # Catches fakers who change nick to guest-#.
    "banPhones":        {
        "android":          False,
        "iphone":           False
    },
    "banCaps":          False,
    # Extras.
    "listUpdater":      None,       # Thread object for automatic list updater.
    "settingsUpdater":  None,       # Thread object for automatic settings updater.
    "filesUpdater":     None,
    "PrivateMode":      False,      # Kicks (not ban) any non-botter and non-modder.
    "AccountMode":      False,      # ... any non-logged in user.
    "gamesMode":        True        # Whether users can play games.
}

# Holds all the lists the bot users.
# All online lists will overwrite local ones!
class lists():
    def __init__(self):
        self.botters = []  # Users that can use basic bot commands.
        self.ignored = []  # Users denied from using room commands.
        
        self.commands = {}  # Commands that play YT/SC.
        self.playlists = {}  # Play from preset playlists.
        
        self.roomMessages = {}  # Sends a message to the room.
        self.asciiMessages = {}  # Sends an ASCII message to the room.
        self.randomMessages = {}  # Sends a random-selection response message to the room.
        self.dox = {}  # Sends a DOX message to the room.
        
        self.nickBans = []  # Nicknames (complex matching) to autoban.
        self.accountBans = []  # Accounts to autoban.
        self.autoForgives = []  # Nicknames & accounts (complex matching) to autoforgive.
        self.banWords = []  # Words (complex matching) to autoban.
        
        self.chucks = []  # Sends a random Chuck Norris joke to the room.
        
        # Store previously loaded lists,
        # to be able to filter out manually added items.
        self.sessionLists = {
            "botters": [],
            "nickBans": [],
            "accountBans": [],
            "autoForgives": [],
            "banWords": []
        }
    
    # Adds an item to a list. Expects only valid values! (May add duplicates!)
    def addItem(self, lst, item):
        # Get list by name.
        l = getattr(self, lst)
        
        l.append(item)
        # Match in session list.
        self.sessionLists[lst].append(item)
    
    # Removes an item from a list. Expects only valid values!
    def removeItem(self, lst, item):
        # Get list by name.
        l = getattr(self, lst)
        
        l.remove(item)
        # Match in session list.
        self.sessionLists[lst].remove(item)
    
    # Clearing a list means clearing the session list, only.
    # The file list is reloaded, anyways, so clearing it has little effect.
    # Expects only valid values!
    def clearList(self, lst):
        self.sessionLists[lst] = []

# Initialize.
LISTS = lists()

# Get extra (overriding) arguments from command-line.
try:
    for item in sys.argv:
        match = item.lower()
        
        if match.find("bot=") == 0:
            val = item.split("=")[1]
            try:
                CONTROLS["botActive"] = bool(int(val))
            except:
                print("Argument BOT must be 0 or 1, only.")
            continue
        
        # Display a ready message, when connected to room.
        elif name == "ready":
            try:
                CONTROLS["ReadyMessage"] = bool(int(val))
            except:
                CONTROLS["ReadyMessage"] = val
        
        if match.find("greet=") == 0:
            val = item.split("=")[1]
            try:
                CONTROLS["greet"] = bool(int(val))
            except:
                print("Argument GREET must be 0 or 1, only.")
            continue
        
        if match.find("snap=") == 0:
            val = item.split("=")[1]
            try:
                BAN_SNAPSHOTS = bool(int(val))
            except:
                print("Argument SNAP must be 0 or 1, only.")
            continue
        
        if match.find("private=") == 0:
            val = item.split("=")[1]
            try:
                CONTROLS["PrivateMode"] = bool(int(val))
            except:
                print("Argument PRIVATE must be 0 or 1, only.")
            continue
        
        if match.find("games=") == 0:
            val = item.split("=")[1]
            try:
                CONTROLS["gamesMode"] = bool(int(val))
            except:
                print("Argument GAMES must be 0 or 1, only.")
            continue
except:
    pass

# Get overrides from tinychat settings [file.]
for name in tinychat.SETTINGS:
    if name in CONTROLS:
        CONTROLS[name] = tinychat.SETTINGS[name]

# Timed thread checks for next track to play in list.
class party():
    def __init__(self):
        self.thread = None  # Holds the partyCheck() thread.
        self.room = None  # Holds the calling room() reference.
        self.list = []  # Currently queued items (tracks and playlists.)
        self.history = []  # Previously queued (played and removed) tracks.
        self.nextIndex = 0  # Mark the index to append() !next track into.
        
        self.mode = False  # Whether autoplay is active.
        self.locked = False  # True = Locks queue and plays for one track. 1 = Until toggled.
        self.shuffle = False  # Shuffle item selection in playlists.
    
    # When active, plays the next item in the playlist.
    def partyCheck(self):
        while True:
            time.sleep(5)
            
            # Must be active, and have track in list.
            if not self.mode or not self.list:
                continue
            
            # Room must be connected.
            if not self.room.connected:
                continue
            
            # If nothing is currently playing.
            if not tinychat.getTimeYT() and not tinychat.getTimeSC():
                # Permenant lock. Wait for unlocking.
                while self.locked is 1:
                    time.sleep(0.1)
                # Reset regular lock.
                if self.locked is True:
                    self.locked = False
                
                # Each item is a track{} or track str().
                itemType = type(self.list[0])
                
                if itemType is dict:
                    # Remove single track{} from playlist.
                    item = self.list.pop(0)
                    track = item["track"]
                    skip = item["skip"]
                else:
                    # Remove single track str() from playlist.
                    track = self.list.pop(0)
                    skip = 0
                    # Turn to proper item.
                    item = self.makeItem(track, skip)
                
                # Verify skip value.
                try:
                    skip = int(skip)
                except:
                    skip = 0
                
                # Update !next index.
                if self.nextIndex > 0:
                    self.nextIndex -= 1
                
                # Play next.
                res = playTrack(self.room, track, skip)
                
                # Skip tracks not tracked for duration, or other more severe failures.
                if type(res) is str:
                    self.room._chatlog("Playlist queue skipping track " + track + ": " + res, True)
                    self.queueSkip(self.room)
                    continue
                
                # Specifically, skip non-embeddable videos or non-streamable tracks.
                # if type(res) is str:
                #     if "not embeddable" in res or "not streamable" in res:
                #         self.room._chatlog("Playlist queue skipping track "+track+
                #             " as non-embeddable/non-streamable...", True)
                #         self.queueSkip(self.room)
                #         continue
                
                # Save in history, if played, and not same as last item in history.
                if not self.history or self.history[-1] != item:
                    self.history.append(item)
                
                time.sleep(3)  # Extra time to catch up.
    
    # Adds a single track [track, skip] or track-list[] to the playlist.
    # nexted tracks get priority in the queue.
    # Returns track position (not index) of added item.
    def addItem(self, room, item, position=None, skip=0, nexted=False):
        beforeLength = len(self.list)
        
        # Position of adding.
        if position is None:
            position = beforeLength
        else:
            # Verify given position. Default to LAST.
            try:
                position = int(position)
                if position < 0:
                    raise Exception()
            except:
                position = beforeLength
        
        # A dict{}.
        # Smart nexting. Overrides position!
        if nexted:
            position = self.nextIndex
            self.nextIndex += 1
        # An item within nextIndex adds one to it.
        elif position <= self.nextIndex:
            self.nextIndex += 1
        
        track = {"track": item, "skip": skip}
        self.list.insert(position, track)
        
        # Activate, if first item(s) added.
        if beforeLength == 0:
            self.mode = True
        
        # Return track number, not index.
        return position + 1
    
    # Removes a single track, or a range of tracks, by relative (track) indexes int().
    # Returns str() info message.
    def removeItem(self, room, track1=False, track2=False, inclusive=False):
        # Nothing to remove with empty playlist.
        l = self.getLength()
        ls = str(l)
        if not l:
            return "No tracks to remove. The playlist is already *empty*."
        
        # Range of tracks. Reverse, in case of, like: 7-3.
        if type(track1) is int and type(track2) is int and track1 > track2:
            t = track1
            track1 = track2
            track2 = t
        
        # Verify index values.
        if type(track1) is int:
            if track1 < 0:
                return "Track numbers must be 1 or greater!"
            if track1 >= l:
                return "The playlist only has " + ls + " " + pluralize("track", l) + " in it!"
        
        if type(track2) is int:
            if track2 < 0:
                return "Track numbers must be 1 or greater!"
            if track2 >= l:
                track2 = l - 1
        
        # Single track.
        if track2 is False or (track1 == track2 != None):
            # Pause queue.
            PARTY.mode = False
            
            # Remove it.
            del self.list[track1]
            
            # Update nextIndex.
            if track1 < self.nextIndex:
                self.nextIndex -= 1
            
            # Unpause queue.
            PARTY.mode = True
            
            l -= 1
            return ("Removed track #" + str(track1 + 1) + " from the playlist, with " +
                    str(l) + " " + pluralize("track", l) + " left. (Next slot at #" + 
                    str(self.nextIndex + 1) + ")")
        
        # Tracks range.
        if track1 == track2 == None:
            # Simple case of removing entire playlist.
            self.list = []
            self.nextIndex = 0
        else:
            # Convert None to index.
            if track1 is None:
                track1 = 0
            if track2 is None:
                track2 = l - 1
            
            # Update index to include last item.
            if inclusive:
                track2 += 1
            
            # Pause queue.
            PARTY.mode = False
            
            # Delete items from playlist.
            for i in range(track2 - 1, track1 - 1, -1):
                # Null it.
                self.list[i] = None
                
                # Update nextIndex.
                if i < self.nextIndex:
                    self.nextIndex -= 1
            
            # Remove emptied tracks.
            self.list = filter(None, self.list)
            
            # Unpause queue.
            PARTY.mode = True
            
            # Revert for both-case handling.
            if inclusive:
                track2 -= 1
        
        # Set for verbosity.
        if track1 == None or track1 == 0:
            track1 = "*start*"
        else:
            track1 = "#" + str(track1 + 1)
        
        if track2 == None or track2 == l - 1:
            track2 = "*end*"
        else:
            track2 = "#" + str(track2 + 1)
        
        l = self.getLength()
        return ("Removed tracks from " + track1 + " to " + track2 +
                " from the playlist, with " + str(l) + " " + pluralize("track", l) +
                " left. (Next slot at #" + str(self.nextIndex + 1) + ")")
    
    # Close all currently playing YT and SC,
    # so queue can continue to the next item.
    def queueSkip(self, room):
        # Close current, if any playing.
        if tinychat.getTimeYT():
            room.closeYT()
        if tinychat.getTimeSC():
            room.closeSC()
    
    # Returns the number int() of tracks in the list, in total.
    def getLength(self):
        return len(self.list)
    
    # Converts a keyword into a track index int(),
    # or convert track position number into index int().
    # Returns None if no match.
    def keywordPosition(self, word):
        if word in {"last", "end"}:
            return self.getLength() - 1
        
        if word in {"first", "next"}:
            return 0
        
        try:
            n = int(word) - 1
            return n
        except:
            pass
    
    # Returns a playlist item dict.
    def makeItem(self, track, skip=0):
        return {"track": track, "skip": skip}

# Initialize.
PARTY = party()

# Games module.
try:
    import games as GAMES
except:
    GAMES = None

class tokes():
    def __init__(self):
        self.room = None
        self.mode = False
        self.paused = False
        
        self.announce = 0               # Interval in seconds, announcing tokes incoming. Reusable.
        self.announceCheck = 0
        
        self.joined = []                # Nicks who joined in tokes.
        self.start = 0                  # time() started.
        self.end = 0                   # seconds from start() to end. Reusable.
        
        self.thread = threading.Thread(target=self.count, args=())
        self.thread.daemon = True
        self.thread.start()
    
    # Returns the time in minutes, until tokes.
    # Part of minute is a minute.
    def until(self):
        t = int(time.time())
        # Gets best minute approximation.
        d = int(round(float(self.start+self.end - t) / 60))
        # Left time minimum 1 minute rounding.
        if d == 0:
            d = 1
        return d
    
    # Start a new count!
    # end is in minutes -> seconds.
    # announce is in minutes -> seconds. Falsy value is no announcements.
    def startCount(self, room, end, announce=0):
        self.room = room
        self.mode = True
        
        t = int(time.time())
        
        self.announce = int(announce)*60
        self.announceCheck = t + self.announce
        
        self.joined = []
        
        self.start = t
        self.end = int(end) * 60
    
    # Clears out current count.
    def clearOut(self):
        self.room = None
        self.mode = False
        self.announceCheck = 0
        self.joined = []
        self.start = 0
    
    # At end, announces it's time for tokes!
    def count(self):
        while True:
            time.sleep(1)
            
            if not self.mode:
                time.sleep(5)
                continue
            
            t = time.time()
            
            # Count finished!
            if t > self.start+self.end:
                start = int((t - self.start) / 60)
                
                if len(self.joined) > 1:
                    if len(self.joined) == 2:
                        # Just one other person joined.
                        joined = self.joined[1]
                    else:
                        # Many joined.
                        joined = ""
                        j = 0
                        for name in self.joined[1:]:
                            if j == len(self.joined) - 2:
                                joined += "and " + name
                            else:
                                joined += name + ", "
                            j += 1
                    
                    self.room.notice(self.joined[0] + " called tokes " + str(start) +
                        " " + pluralize("minute", start) + 
                        " ago, and *" + joined + "* joined in. *TOKES NOW!*")
                else:
                    # Lonely toke.
                    self.room.notice(self.joined[0] + ", you called tokes " + str(start) +
                        " " + pluralize("minute", start) + 
                        " ago, and nobody joined in. Who cares... *TOKES NOW!*")
                
                # Clear out counter.
                self.clearOut()
                continue
            
            # Optional periodical announcements.
            if self.announce and t > self.announceCheck:
                self.announceCheck = t + self.announce
                
                start = int((t - self.start) / 60)
                self.room.notice(self.joined[0] + " called tokes " + str(start) +
                    " " + pluralize("minute", start) + " ago. Y'all better *!JOIN* in.")

# Initalize.
TOKES = tokes()

# Return an online or local file converted to a list or dictionary:
# Parts = 3: [cmd: [method, msg], ...] 2: [cmd: msg] 1: [item].
# Ignores empty lines and // comments. online=True for online files.
# One per line. Indexes 0 and 1 are forced lower-case.
# word Takes only one word per line. youtubes Allows many command words, lowercased.
# Returns None on failure. Returns empty list or dict, if no content.
def listLoader(link, online=False, parts=1, word=False, youtubes=False, unicode=False):
    if not link:
        return
    
    try:
        # Online file.
        if online:
            raw = requests.get(link, timeout=15)
            if not unicode:
                lines = raw.text.encode("ascii", "ignore").splitlines()
            else:
                lines = raw.text.splitlines()
                try:
                    lines = lines.decode("utf-8", "replace")
                except:
                    pass
        # Local file.
        else:
            with open(link) as raw:
                if not unicode:
                    lines = raw.read().encode("ascii", "ignore").splitlines()
                else:
                    lines = raw.read().splitlines()
                    try:
                        lines = lines.decode("utf-8", "replace")
                    except:
                        pass
    except:
        return
    
    # Remove BOM character. Incomplete.
    # https://en.wikipedia.org/wiki/Byte_order_mark#Representations_of_byte_order_marks_by_encoding
    # codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE, codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE
    if unicode:
        try:
            if lines[0][0] in {u'\ufeff', u'\ufffe'}:
                raise Exception()
        except:
            lines[0] = lines[0][1:]
    
    # Treat Google Docs page-break string as empty line.
    lines = map(lambda x: '' if x == '________________' else x, lines)
    
    result = None
    
    if parts == 1:
        result = []
        
        for line in lines:
            # Remove whitespaces.
            line = line.strip()
            # Skip comments and empty lines.
            if line.find("//") == 0 or line == "":
                continue
            
            # Only grab a word.
            if word:
                line = line.split()[0]
            
            # Otherwise, add it.
            result.append(line)
    
    if parts == 2:
        result = {}
        
        for line in lines:
            # Remove whitespaces.
            line = line.strip()
            # Skip comments and empty lines.
            if line.find("//") == 0 or line == "":
                continue
            
            # Get words.
            words = line.split()
            count = len(words)
            
            # Must have the command and msg.
            if count < 2:
                continue
            
            # Command must be lower-case.
            # Remove cmd from list.
            cmd = words.pop(0).lower()
            
            msg = " ".join(words)
            
            # Overrides.
            result[cmd] = msg
    
    if parts == 3:
        result = {}
        
        for line in lines:
            # Remove whitespaces.
            line = line.strip()
            # Skip comments and empty lines.
            if line.find("//") == 0 or line == "":
                continue
            
            # Get words.
            words = line.split()
            count = len(words)
            
            # For youtube video playlists.
            if youtubes:
                # Must have at least a command and video.
                if count < 2:
                    continue
                
                # Optional skip.
                try:
                    skip = int(words[-1])
                    # SoundCloud IDs are large numbers.
                    if skip > SC_MIN_ID:
                        raise Exception()
                    del words[-1]
                except:
                    skip = 0
                
                # Video ID or link.
                vid = words.pop()
                
                # Optional many cmd words.
                for word in words:
                    # Overrides.
                    result[word] = [vid, skip]
                # Next.
                continue
            
            # Must have the command, method, and msg.
            if count < 3:
                continue
            
            # Command and method must be lower-case.
            # Remove cmd and method from list.
            cmd = words.pop(0).lower()
            method = words.pop(0).lower()
            
            msg = " ".join(words)
            
            # Overrides.
            result[cmd] = [method, msg]
    
    # Success.
    return result

# Load botters that can access the bot.
filename = "botters.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, word=True)
if result is None:
    # print("Failed to load the Botters list from " + filename + ".")
    pass
else:
    LISTS.botters = result

# Load more botters from online list.
BottersText = {}
try:
    BottersText = tinychat.SETTINGS["Botters"]
    
    result = listLoader(BottersText, online=True, word=True)
    if result is None:
        # print("Failed to load the Extra Botters list from " + BottersText + ".")
        pass
    else:
        LISTS.botters = result
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Load Youtube commands from file.
filename = "youtubes.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, parts=3, youtubes=True)
if result is None:
    # print("Failed to load the Youtubes list from " + filename + ".")
    pass
else:
    LISTS.commands = result

# Load more Youtube commands from online file.
ExtraYTsText = {}
try:
    ExtraYTsText = tinychat.SETTINGS["Commands"]
    
    result = listLoader(ExtraYTsText, online=True, parts=3, youtubes=True)
    if result is None:
        # print("Failed to load the Extra Youtubes list from " + ExtraYTsText + ".")
        pass
    else:
        LISTS.commands = result
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Load the Playlists from online.
PlaylistsText = {}
try:
    PlaylistsText = tinychat.SETTINGS["Playlists"]
except:
    pass

def getPlaylists(PlaylistsText):
    if not PlaylistsText:
        return
    
    try:
        raw = requests.get(PlaylistsText, timeout=15)
        lines = raw.text.encode("ascii", "ignore").splitlines()
    except:
        return
    
    curPL = False
    l = {}
    for line in lines:
        # Remove whitespaces.
        line = line.strip()
        # Skip comments.
        if line.find("//") == 0:
            continue
        
        # Empty line marks end of playlist.
        if line == "":
            curPL = False
            continue
        
        # Get words.
        parts = line.split()
        
        # Start new playlist.
        if curPL is False:
            curPL = parts[0].lower()
            l[curPL] = []
            continue
        
        # Video followed by Title, with optional skip in seconds.
        count = len(parts)
        if count >= 2:
            # Remove video from list.
            vid = parts.pop(0)
            
            # Optional skip.
            try:
                skip = int(parts[-1])
                if skip < 1:
                    raise Exception()
            except:
                skip = 0
            
            # Reconstruct title.
            title = " ".join(parts)
        else:
            # Video without title, default to video as title.
            vid = parts.pop(0)
            title = vid
            skip = 0
        
        # Add to playlist.
        l[curPL].append([vid, title, skip])
    # Apply list.
    LISTS.playlists = l

getPlaylists(PlaylistsText)

# Dox commands from file. TODO: Replace with listLoader().
filename = "dox.txt"
doxLines = []
try:
    with open(SETTINGS_DIRECTORY + filename) as doxFile:
        doxLines = doxFile.read().encode("ascii", "ignore").splitlines()
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    # print("Failed to load the DOX list from " + filename + ".")
    pass

curDox = False
d = {}
for line in doxLines:
    # Skip comments.
    if line.find("//") == 0: continue
    
    # End of person.
    if line == "":
        curDox = False
        continue
    
    # New person.
    if not curDox:
        curDox = line
        d[curDox] = []
        continue
    
    # Add msgs for person.
    d[curDox].append(line)
# Apply list.
LISTS.dox = d

# Load more DOX from online.
moreDoxText = {}
try:
    moreDoxText = tinychat.SETTINGS["DOX"]
except:
    pass

def getExtraDOX(moreDoxText):
    if not moreDoxText:
        return
    
    try:
        raw = requests.get(moreDoxText, timeout=15)
        lines = raw.text.encode("ascii", "ignore").splitlines()
    except:
        return
    
    curDox = False
    d = {}
    for line in lines:
        # Skip comments.
        if line.find("//") == 0: continue
        
        # End of person.
        if line == "":
            curDox = False
            continue
        
        # New person.
        if not curDox:
            curDox = line
            d[curDox] = []
            continue
        
        # Add msgs for person. Override from file.
        d[curDox].append(line)
    # Apply list.
    LISTS.dox = d

getExtraDOX(moreDoxText)

# Autobans from file.
filename = "autoban.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    # print("Failed to load the AUTOBANS list from " + filename + ".")
    pass
else:
    for name in result:
        # Account ban.
        if name[0] == "@":
            n = name[1:]
            if n not in LISTS.accountBans:
                LISTS.accountBans.append(n)
        # Nick ban.
        else:
            if name not in LISTS.nickBans:
                LISTS.nickBans.append(name)

# Load more autobans from online list.
AutobansText = {}
try:
    AutobansText = tinychat.SETTINGS["AutoBans"]
    
    result = listLoader(AutobansText, online=True, word=True)
    if result is None:
        # print("Failed to load the Extra Autobans list from " + AutobansText + ".")
        pass
    else:
        # Override local lists.
        LISTS.accountBans = []
        LISTS.nickBans = []
        
        for name in result:
            # Account ban.
            if name[0] == "@":
                n = name[1:]
                if n not in LISTS.accountBans:
                    LISTS.accountBans.append(n)
            # Nick ban.
            else:
                if name not in LISTS.nickBans:
                    LISTS.nickBans.append(name)
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Autoforgives from file.
filename = "autoforgive.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    # print("Failed to load the AUTOFORGIVES list from " + filename + ".")
    pass
else:
    LISTS.autoForgives = result

# Load more autoforgives from online list.
AutoforgivesText = {}
try:
    AutoforgivesText = tinychat.SETTINGS["AutoForgives"]
    
    result = listLoader(AutoforgivesText, online=True, word=True)
    if result is None:
        # print("Failed to load the Extra Autoforgives list from " + AutoforgivesText + ".")
        pass
    else:
        LISTS.autoForgives = result
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Banwords from file.
filename = "banwords.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    # print("Failed to load the BANWORDS list from " + filename + ".")
    pass
else:
    LISTS.banWords = result

# Load more banwords from online list.
banwordsText = {}
try:
    banwordsText = tinychat.SETTINGS["BanWords"]
    
    result = listLoader(banwordsText, online=True)
    if result is None:
        # print("Failed to load the Extra Banwords list from " + banwordsText + ".")
        pass
    else:
        LISTS.banWords = result
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Room message commands from file.
filename = "messages.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, parts=2)
if result is None:
    print("Failed to load the ROOM MESSAGES list from " + filename + ".")
else:
    LISTS.roomMessages = result

# More messages from online page.
moreMessagesText = {}
try:
    moreMessagesText = tinychat.SETTINGS["Messages"]
    
    result = listLoader(moreMessagesText, online=True, parts=2)
    if result is None:
        # print("Failed to load the EXTRA ROOM MESSAGES list from " + moreMessagesText + ".")
        pass
    else:
        LISTS.roomMessages = result
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Funny ascii-art room user commands.
filename = "ascii.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, parts=2, unicode=True)
if result is None:
    # print("Failed to load the ASCII MESSAGES list from " + filename + ".")
    pass
else:
    LISTS.asciiMessages = result

# More ascii-art from online page.
asciiText = {}
try:
    asciiText = tinychat.SETTINGS["ASCII"]
    
    result = listLoader(asciiText, online=True, parts=2, unicode=True)
    if result is None:
        # print("Failed to load the EXTRA ASCII MESSAGES list from " + asciiText + ".")
        pass
    else:
        LISTS.asciiMessages = result
except (SystemExit, KeyboardInterrupt):
    sys.exit("Killed while loading lists...")
except:
    pass

# Load the random response commands from online file.
randomsText = {}
try:
    randomsText = tinychat.SETTINGS["RandomMessages"]
except:
    pass

def getRandoms(randomsText):
    if not randomsText:
        return
    
    try:
        raw = requests.get(randomsText, timeout=15)
        lines = raw.text.encode("ascii", "ignore").splitlines()
    except:
        return
    
    curCmd = False
    r = {}
    for line in lines:
        # Remove whitespaces.
        line = line.strip()
        # Skip comments.
        if line.find("//") == 0:
            continue
        
        # Empty line marks end of command.
        if line == "":
            curCmd = False
            continue
        
        # Start new command.
        if curCmd is False:
            parts = line.split()
            
            # Make further words point at the first.
            for word in parts:
                if word == parts[0]:
                    curCmd = word.lower()
                    r[curCmd] = []
                else:
                    r[word.lower()] = r[curCmd]
            continue
        
        # Add to command.
        r[curCmd].append(line)
    # Apply list.
    LISTS.randomMessages = r

getRandoms(randomsText)

###############################################################################
########################### Actions & Events ##################################
###############################################################################

# Handles all YT/SC immediate plays, using startYT().
# Blocks play overrides. Pauses PARTY() queue until done.
# Returns the startYT() response.
def playTrack(room, track, skip=0):
    # Disallow overrides.
    if CONTROLS["playLock"]:
        return
    
    # Pause queue.
    PARTY.mode = False
    # Lock play.
    CONTROLS["playLock"] = True
    
    res = room.startYT(track, skip)
    
    # Release play.
    CONTROLS["playLock"] = False
    # Unpause queue.
    PARTY.mode = True
    
    return res

# Handle bot disconnection cleanups.
def disconnectExtended(room):
    pass

# All actions to do, after bot in room.
def onJoinsdoneExtended(room):
    # Default nickname, to be able to say() in room.
    if not room.nick:
        room.setNick(NICKNAME)
    
    # Start the timed automatic user playlist player, on first connection.
    if PARTY:
        PARTY.room = room  # Set or update room reference.
        if not PARTY.thread:
            PARTY.thread = threading.Thread(target=PARTY.partyCheck, args=())
            PARTY.thread.daemon = True  # Exits when main thread quits.
            PARTY.thread.start()
    
    # Initialize room's quitlist.
    if not hasattr(room, "quitList"):
        room.quitList = []
    
    # Verbose to room.
    if CONTROLS["ReadyMessage"]:
        if CONTROLS["ReadyMessage"] is True:
            room.notice("I am active and ready for action!~ *<bow>*")
        else:
            room.notice(CONTROLS["ReadyMessage"])

# Notice bans, for autoforgive.
def onNoticeBans(room, notice):
    if notice.find(" was banned by ") >= 0:
        target = notice.split(" was banned by ")[0]
        
        user = room._getUser(target)
        if not user:
            return
        
        # Forgive all mode.
        if CONTROLS["autoforgive"]:
            try:
                room.forgive(user)
            except:
                pass
            return
        
        # Check for user account as well.
        acct = user.account
        
        # Exact nicks or accounts start with *.
        # Wildcard is ?.
        for string in LISTS.autoForgives:
            exact = False
            # Exact match.
            if string[0] == "*":
                string = string[1:]
                exact = True
            
            match = None
            # Try account name.
            if acct:
                match = isMatch(string, acct, exact=exact, case=True)
            # If not account name, then try nickname.
            if not match:
                match = isMatch(string, target, exact=exact)
            
            if match is True:
                room.forgive(user)
                room._chatlog(user.nick + " (" + str(user.id) +
                              ") has been forgiven from autoForgives: " + string, True)
            elif type(match) in {str, unicode}:
                room._chatlog(match, True)

# Room spam defenses and greets, and commands.
def onMessageExtended(room, user, msg):
    # Spam defenses for unrecognized users.
    if not user.mod and not isBotter(user):
        # Private mode. This is an extra to the userinfo event.
        if CONTROLS["PrivateMode"]:
            room.ban(user)
            room.forgive(user)
            return
        
        msgL = msg.lower()
        
        # Auto ban screenshotters and TC link spammers.
        if CONTROLS["banSnapshots"]:
            s = "I just took a video snapshot of this chatroom."
            if s in msg:
                room.ban(user)
                room._chatlog(user.nick + " (" + str(user.id) +
                              ") has been banned from SNAPSHOT.", True)
                return
        
        # Autoban TC room links.
        find = re.match(r'.*tinychat.com\/\w+($| |\/+ |\/+$).*', msg, re.I)
        if find:
            room.ban(user)
            room._chatlog(user.nick + " (" + str(user.id) +
                          ") has been banned from ROOM LINK.", True)
            return
        
        # Unicode banwords.
        try:
            if u"\u25b2" in msg or u"\x85" in msg:
                room.ban(user)
                room._chatlog(user.nick + " (" + str(user.id) +
                              ") has been banned from UNICODE BANWORDS.", True)
                return
        except:
            traceback.print_exc()
        
        # banCaps mode bans all msgs composed only of capital letters (no lowercase.)
        if CONTROLS["banCaps"]:
            letters = re.sub(r'[^A-Za-z]', '', msg)
            uppers = re.sub(r'[^A-Z]', '', letters)
            lu = len(uppers)
            lowers = re.sub(r'[^a-z]', '', letters)
            ll = len(lowers)
            
            if lu > 0 and ll == 0:
                room.ban(user)
                room._chatlog(user.nick + " (" + str(user.id) +
                              ") has been banned from banCaps!", True)
                return
        
        # Banwords, by substring.
        for words in LISTS.banWords:
            # PM only banwords start with @.
            if words[0] == "@":
                continue
            
            # Regexp banwords start with r".
            if words.startswith('r"'):
                words = words[2:]
                try:
                    r = re.compile(r"" + words)
                except Exception as e:
                    room._chatlog("Error compiling banWords regexp: " + words +
                                  " - " + str(e), True)
                    continue
                # If the rule matches the msg, then ban.
                if r.match(msg):
                    room.ban(user)
                    room._chatlog(user.nick + " (" + str(user.id) +
                                  ") has been banned from banWords regexp: r\"" + words, True)
                    return
            else:
                words = words.lower()
                
                if words in msgL:
                    room.ban(user)
                    room._chatlog(user.nick + " (" + str(user.id) +
                                  ") has been banned from banWords: " + words, True)
                    return
    
    # Room commands.
    handleUserCommand(room, user, msg)

# PM defenses and commands.
def onPMExtended(room, user, msg, reported):
    # The user reported bot to Tinychat. Autoban.
    if reported:
        room.ban(user)
        acct = "Not Logged-In"
        if user.account:
            acct = user.account
        room._chatlog(user.nick + " (" + str(user.id) + ") (" + acct + ") has been banned from REPORTED.", True)
        return
    
    # Spam defenses for unrecognized users.
    if not user.mod and not isBotter(user):
        msgL = msg.lower()
        
        # Banwords, by substring.
        for words in LISTS.banWords:
            # PM only banwords start with @.
            if words[0] != "@":
                continue
            
            # Remove the @.
            words = words[1:]
            
            # Regexp banwords start with r".
            if words.startswith('r"'):
                words = words[2:]
                try:
                    r = re.compile(r"" + words)
                except Exception as e:
                    room._chatlog("Error compiling PM banWords regexp: " + words +
                                  " - " + str(e), True)
                    continue
                # If the rule matches the msg, then ban.
                if r.match(msg):
                    room.ban(user)
                    room._chatlog(user.nick + " (" + str(user.id) +
                                  ") has been banned from PM banWords regexp: r\"" + words, True)
                    return
            else:
                # Case insensitive.
                words = words.lower()
                
                if words in msgL:
                    room.ban(user)
                    room._chatlog(user.nick + " (" + str(user.id) +
                                  ") has been banned from PM banWords: " + words, True)
                    return
    
    pmCommands(room, user, msg)

# Handle user commands to bot in PM.
def pmCommands(room, user, msg):
    if msg == "help" or msg == CMD + "help":
        if "helpLink" in tinychat.SETTINGS:
            room.pm(user, "*Tunebot's Instructions:* "+tinychat.SETTINGS["helpLink"])
        else:
            room.pm(user, "Sorry! I don't have any help file to give you.")
        return
    
    # Only for commands, from here on.
    if msg[0] != CMD:
        return
    
    msg = msg[1:]  # Remove mark.
    
    # If available, get the string without the command.
    hasArgs = msg.find(" ")
    userArgsStr = ""
    if (hasArgs >= 0):
        userArgsStr = msg[hasArgs + 1:]
    
    userArgs = msg.split()  # Split to words.
    
    userCmd = userArgs[0].lower()  # Get the cmd word as lowercase.
    del userArgs[0]  # Remove the cmd word from args list.
    
    # For ease of use.
    try:
        target = userArgs[0]
    except:
        target = False
    
    # Public commands.
    if userCmd == "mod" and not user.mod:
        if "modPass" in tinychat.SETTINGS and target == tinychat.SETTINGS["modPass"]:
            user.mod = True
            room.pm(user, "You are now recognized as a *moderator*!")
            return
    
    # Botter commands.
    if not user.mod and not isBotter(user):
        return
    
    if userCmd == "uptime":
        string = formatUptime(time.time() - START_TIME)
        room.pm(user, "I have been alive for *" + string + ".*")
        return
    
    # Mod commands.
    if not user.mod:
        return
    
    if userCmd == "bot":
        if CONTROLS["botActive"]:
            CONTROLS["botActive"] = False
            room.pm(user, "Bot is now deactivated!")
        else:
            CONTROLS["botActive"] = True
            room.pm(user, "Bot is now active.")
        return
    
    if userCmd == "say":
        if not target:
            room.pm(user, "Give me something to say...")
            return
        room.say(userArgsStr)
        return
    
    if userCmd == "pm":
        if len(userArgs) < 2:
            room.pm(user, "Give me a nickname and a message to send...")
            return
        
        res = room.pm(target, " ".join(userArgs[1:]))
        
        if not res:
            room.pm(user, "User " + target + " not found...")
        return
    
    if userCmd == "notice" or userCmd == "n":
        if not target:
            room.pm(user, "Give me something to announce...")
            return
        room.notice(userArgsStr)
        return
    
    # Change bot's text color.
    if userCmd == "color":
        prevColor = room.color
        target = target.lower()
        
        if not target:
            key = room.color
            while key == room.color:
                key = room.cycleColor()
        elif target in tinychat.TINYCHAT_COLORS:
            key = target
            room.color = tinychat.TINYCHAT_COLORS[key]
        
        if (key == prevColor):
            room.pm(user, "I am already using the color " + key.title() + ".")
        else:
            room.pm(user, "My text color is now " + key.title() + ".")
        return
    
    # Toggle identifying a user as an oper.
    if userCmd == "mod":
        if not target:
            room.pm(user, "Give me a user nickname to mod...")
        else:
            curUser = room._getUser(target)
            if not curUser:
                room.pm(user, "Nickname " + target + " not found...")
                return
            if curUser.mod:
                curUser.mod = False
                room.pm(user, target.title() + " is *not* recognized as a moderator, anymore.")
            else:
                curUser.mod = True
                room.pm(user, target.title() + " is now recognized as a *moderator*!")
        return
    
    # Disconnect bot. Don't kill script.
    if userCmd == "disconnect":
        room.disconnect()
        return
    
    # Shut bot down. Kills script.
    if userCmd == "killbot":
        room.disconnect()
        tinychat.SETTINGS["Run"] = False
        return
    
    # Soft reconnect. Doesn't kill script.
    if userCmd == "reconnect":
        room.reconnect()
        return
    
    # Ban a user. Mods included.
    if userCmd == "ban":
        if not target:
            room.pm(user, "Give me a nickname to ban...")
            return
        
        res = room.ban(target, True)
        
        if res is False:
            room.pm(user, target + " was not found in the userlist...")
        elif res is not True:
            room.pm(user, res)
        else:
            room._chatlog(target + " has been PM banned by " + user.nick + " [" + str(user.id) + "]"
                          + (" (" + user.account + ")" if user.account else "") + ".", True)
        return
    
    # Forgive a user.
    if userCmd == "forgive":
        if not target:
            room.pm(user, "Give me a nickname to forgive...")
            return
        room.forgiveNick(target)
        return
    
    # Ignore room commands from a user, any user.
    if userCmd == "ignore":
        if not target:
            room.pm(user, "Give me a nickname to ignore...")
            return
        
        string = target.lower()
        
        # Toggle ignoring.
        try:
            LISTS.ignored.remove(string)
            room.pm(user, string + " has been removed from the ignore list.")
        except:
            LISTS.ignored.append(string)
            room.pm(user, string + " has been added to the ignore list!")
        return
    
    if userCmd == "who":
        if not target:
            u = user
        else:
            u = room._getUser(target)
            if not u:
                room.pm(user, "Failed to find user " + target + " in the room...")
                return
        
        if u.account:
            acct = "logged in as *" + u.account + "*"
        else:
            acct = "not logged in"
        
        t = formatTime(time.time() - u.joinTime)
        
        room.pm(user, "User *" + u.nick + "* [" + str(u.id) + "] is " + acct + ", and has been here for *" + t + "*.")
        return
    
    # Toggle substring in AUTOBANS.
    # Exact nicks start with *, otherwise partial string match.
    # Wildcards are ?.
    if userCmd == "autoban":
        l = "nickBans"
        
        if not target:
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.pm(user, "Nickbans added this session: *" + s + "*.")
            return
        
        # Clear list.
        if target == "!!":
            LISTS.clearList(l)
            room.pm(user, "The *" + l + "* list is now *empty*!")
            return
        
        # WARNING: Bans all joins! For extreme measures only.
        if target == CMD:
            if CONTROLS['autoban']:
                CONTROLS['autoban'] = False
                room.pm(user, "*Autoban mode is now OFF.* All users may join the room.")
            else:
                CONTROLS['autoban'] = True
                room.pm(user, "*Autoban mode is now ON!* All users who join the room will be banned!")
            return
        
        # Prevent excessive autobans, if not exact nick.
        if target[0] != "*":
            if len(target) <= 2:
                room.pm(user, "Give me a partial nick longer than 2 characters...")
                return
        
        # Don't allow certain strings.
        ignores = ["newuser"]
        for word in ignores:
            if target in word:
                return
        
        # Toggle from list, and ban if in room.
        if target not in LISTS.nickBans:
            # Ban matching nickname from room.
            name = target
            if name[0] == "*":
                name = name[1:]
            room.ban(name)
            
            # Verify regular expression.
            if target.startswith('r"'):
                s = target[2:]
                try:
                    re.compile(s)
                except Exception as e:
                    room.pm(user, "*Failed to compile():* " + s + " - " + str(e))
                    return
            
            LISTS.addItem(l, target)
            room.pm(user, target + " has been added to the *" + l + "* list.")
        else:
            LISTS.removeItem(l, target)
            room.pm(user, target + " has been removed from the *" + l + "* list.")
        return
    
    # Auto ban by substring in user message.
    if userCmd in {"banword", "banwords"}:
        l = "banWords"
        
        if not target:
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.pm(user, "Banwords added this session: *" + s + "*.")
            return
        
        string = userArgsStr.lower()
        
        # Clear list.
        if string == CMD:
            LISTS.clearList(l)
            room.pm(user, "The *" + l + "* list is now *empty*.")
            return
        
        # Prevent excessive banwords.
        if len(string) <= 2:
            room.pm(user, "Give me a word longer than 2 characters...")
            return
        
        if string in LISTS.banWords:
            LISTS.removeItem(l, string)
            room.pm(user, "*" + string + "* has been removed from the *" + l + "* list.")
        else:
            LISTS.addItem(l, string)
            room.pm(user, "*" + string + "* has been added to the *" + l + "* list!")
        return
    
    # Toggle banning messages that are all in capital letters.
    if userCmd == "bancaps":
        if CONTROLS["banCaps"]:
            CONTROLS["banCaps"] = False
            room.pm(user, "BanCaps mode is now *off*.")
        else:
            CONTROLS["banCaps"] = True
            room.pm(user, "*BanCaps mode is now on!* " +
                    "Users sending messages containing only capital letters will be banned!")
        return

# Find and execute the first matching user command, from public to oper.
def handleUserCommand(room, user, msg):
    # Ignore surrounding spaces.
    msg = msg.strip()
    
    # Nothing to do, on empty message.
    if not msg:
        return
    
    # Ignore all commands, other than reset cmd, if deactivated!
    if not CONTROLS["botActive"] and msg[:4] != CMD + "bot":
        return
    
    # Ignore nick from list or command.
    if user.ignored or user.nick.lower() in LISTS.ignored:
        return
    
    # Not a command.
    if msg[0] != CMD:
        return
    
    userArgs = msg.split()  # Split to words.
    
    userCmd = userArgs.pop(0).lower()  # Get the cmd word as lowercase, and remove from args.
    if userCmd:
        userCmd = userCmd[1:]  # Remove sign.
    
    # Get args as string. Empty string if none.
    userArgsStr = " ".join(userArgs)
    
    # For ease of use.
    try:
        target = userArgs[0]
    except:
        target = None
    
    # Public commands.
    res = publicCommands(room, userCmd, userArgsStr, userArgs, target, user)
    # Overrides further commands, if matched.
    if not res:
        return
    
    # Botters and Opers.
    if not user.mod and not isBotter(user):
        return
    
    res = botterCommands(room, userCmd, userArgsStr, userArgs, target, user)
    # Overrides further commands, if matched.
    if not res:
        return
    
    # Opers only.
    if not user.mod:
        return
    
    res = operCommands(room, userCmd, userArgsStr, userArgs, target, user)
    # Overrides further commands, if matched.
    if not res:
        return

# Room commands available to everyone.
def publicCommands(room, userCmd, userArgsStr, userArgs, target, user):
    # Make sure an unidentified user isn't spamming public commands.
    if not user.account:
        t = time.time()
        try:
            # Detect spamming.
            attempt = False
            # Same-command time limit.
            if t - user.lastCommand["time"] < 1 and user.lastCommand["cmd"] == userCmd:
                attempt = True
            # Time limit on any command.
            if t - user.lastCommand["time"] < 2:
                attempt = True
            
            if attempt:
                user.lastCommand["attempts"] += 1
                # Ignore repeat offenders.
                if user.lastCommand["attempts"] == 7:
                    user.ignored = True
                    room.notice("*" + user.nick + "* has been added to the ignore list, " +
                                "for spamming commands!")
                return
            else:
                # Reset counters, if no problem.
                raise Exception()
        except:
            # Save first usage.
            user.lastCommand = {
                "cmd": userCmd,
                "time": t,
                "attempts": 0
            }
    
    # Get bot to PM you with noob tip.
    if userCmd == "help":
        if "helpLink" in tinychat.SETTINGS:
            room.notice("*Tunebot's Instructions:* "+tinychat.SETTINGS["helpLink"])
        else:
            room.notice("Sorry! I don't have any help file to give you.")
        return
    
    # Sends a response message, from file.
    for key, val in LISTS.roomMessages.items():
        if userCmd == key:
            msg = val
            
            # Replace bot nick, user nick, and target.
            if not target:
                t = user.nick
            else:
                t = target
            
            msg = msg.replace("$b", room.user.nick) \
                .replace("$n", user.nick) \
                .replace("$t", t)
            
            try:
                room.notice(msg)
            except:
                traceback.print_exc()
                room._chatlog("Failed to execute from roomMessages!")
                return
    
    # UTF-16 Unicode! Sends an ASCII response message, from file.
    try:
        for key, val in LISTS.asciiMessages.items():
            if u"" + userCmd == u"" + key:
                msg = u"" + val
                
                room.notice(msg)
                return
    except:
        room._chatlog(u"Failed to execute from asciiMessages!")
        traceback.print_exc()
        return
    
    # Random response from list commands.
    for key, val in LISTS.randomMessages.items():
        if userCmd == key:
            # r = random.randint(0, len(val)-1)
            # msg = val[r]
            msg = random.choice(val)
            
            # Replace bot nick, user nick, and target.
            if not target:
                t = user.nick
            else:
                t = target
            
            msg = msg.replace("$b", room.user.nick) \
                .replace("$n", user.nick) \
                .replace("$t", t)
            
            room.notice(msg)
            return
    
    # The only command that works for botters/opers only,
    # And only shows info for the public.
    if userCmd == "botter":
        if not user.mod and not isBotter(user):
            room.notice("You ain't a botter, " + user.nick + "... Kiss my shiny metal ass.")
            return
        
        if not target:
            if user.mod:
                room.notice("You are my glorious master, " + user.nick + "!")
            else:
                room.notice("I obey your commands, " + user.nick + ".")
            return
        
        l = "botters"
        
        # List session botters.
        if target == "?":
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.notice("Botters added this session: *" + s + "*.")
            return
        
        # Only mods can make account-bound modder or botter.
        if any(x in ["@", "*"] for x in target) and not user.mod:
            room.notice("Only moderators can assign account bound modders and botters!")
            return
        
        # Apply to user(), if in room.
        u = room._getUser(target)
        if isBotter(target):
            if u:
                u.botter = False
            
            LISTS.removeItem(l, target)
            room.notice("*" + target + "* has been removed from the *" + l + "* list.")
        else:
            if u:
                u.botter = True
            
            LISTS.addItem(l, target)
            room.notice("*" + target + "* has been added to the *" + l + "* list!")
        return
    
    # Select a random user (real nick) from cammers.
    if userCmd == "spin":
        # Make sure it's an interesting user.
        strings = {"guest", "newuser"}
        group = [x for x in room.users.values() if (x.account and
                                                    x.account != room.user.account and
                                                    not any(s in x.nick for s in strings))]
        
        # Include non-logged users if no accounts available.
        if not group:
            group = [x for x in room.users.values() if not any(s in x.nick for s in strings)]
            if not group:
                room.notice("Everybody sucks, desu!~")
                return
        
        r = random.randint(0, len(group) - 1)
        curUser = group[r]
        
        room.notice("*" + curUser.nick + " desu!~*")
        return
    
    if userCmd in {"toke", "tokes", "rip", "rips"}:
        # Tokes now, if not active.
        # If active, it will fall in further check.
        if not target:
            if not TOKES.mode:
                room.notice("Pack up! *TOKES NOW.*")
                return
        
        # Stop and remove tokes count.
        if TOKES.mode and target == CMD:
            TOKES.clearOut()
            room.notice("Tokes counter stopped and cleared.")
            return
        
        # Ignore more requests, if counter already running.
        if TOKES.mode:
            mins = TOKES.until()
            room.notice("Tokes counter is already up and will finish in "+str(mins)+" "+
                pluralize("minute", mins)+(", and is paused" if TOKES.paused else "")
                +". Do *"+CMD+"JOIN* to toke together.")
            return
        
        # Start new counter.
        try:
            end = int(target)
            if not 1 <= end <= 20:
                raise Exception()
        except:
            room.notice("Give me a time in minutes, between 1 and 20, until tokes...")
            return
        
        # Optional periodical announcements.
        announce = 0
        if len(userArgs) > 1:
            try:
                announce = int(userArgs[1])
            except:
                room.notice("Give me a time in minutes, to announce until tokes, periodically...")
                return
        
        TOKES.startCount(room, end, announce)
        
        TOKES.joined.append(user.nick)
        
        # Verbose.
        mins = TOKES.until()
        room.notice(str(mins) + " " + pluralize("minute", mins) + " until tokes! Type *" +
            CMD + "JOIN* in chat to toke together. (Do *"+CMD+"tokes "+CMD+"* to clear it out.)")
        return
    
    # Join on tokes.
    if userCmd == "join":
        if not TOKES.mode:
            room.notice("No one started a countdown... Do *!tokes #MINUTES* to start one.")
            return
        
        # No multiples. No removes.
        if user.nick in TOKES.joined:
            return
        
        TOKES.joined.append(user.nick)
        mins = TOKES.until()
        room.notice(user.nick + " joined tokes! "+str(mins)+" "+pluralize("minute", mins)+" left for rips...")
        return
    
    # No command match.
    return True

# Room commands available only to botters and opers.
# Contains some oper-limited options.
def botterCommands(room, userCmd, userArgsStr, userArgs, target, user):
    # Dox commands.
    try:
        for msg in LISTS.dox[userCmd]:
            msg = msg.replace("$n", user.nick) \
                .replace("$b", room.user.nick)
            room.notice(msg)
            return
    except:
        pass
    
    # Optional queuing or skip for play commands.
    q = False
    skip = 0
    try:
        if userArgs[-1] == CMD:
            q = True
        else:
            try:
                skip = int(userArgs[-1])
                try:
                    if userArgs[-2] == CMD:
                        q = True
                except:
                    pass
            except:
                skip = int(userArgs[-2])
    except:
        pass
    
    # Match command and play.
    try:
        track = LISTS.commands[userCmd][0]
        
        # Queue modifications disabled.
        if PARTY.locked:
            if user.mod:
                room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        if not skip:
            skip = LISTS.commands[userCmd][1]
        
        if q:
            pos = PARTY.addItem(room, track, skip=skip, position=0)
            room.notice("Track added to playlist as #" + str(pos) + ".")
        else:
            playTrack(room, track, skip)
        return
    except:
        pass
    
    # Close cam by nickname.
    if userCmd == "uncam":
        if not target:
            room.notice("Give me a nickname to close...")
            return
        
        room.uncam(target)
        return
    
    # Queue YT/SC by link, or SC track ID or YT title.
    if userCmd == "q":
        # Display state and instructions.
        if not target or target == "?":
            # State.
            if not PARTY.list:
                room.notice("The playlist is *empty*.")
            else:
                if PARTY.mode:
                    mode = "ON"
                else:
                    mode = "OFF"
                
                l = PARTY.getLength()
                if l == 1:
                    room.notice("There is 1 track in the playlist, and party mode is *" + mode + ".*")
                else:
                    room.notice("There are " + str(l) +
                                " tracks in the playlist, and party mode is *" + mode + ".*")
            return
        
        # Queue modifications disabled.
        if PARTY.locked:
            if user.mod:
                room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        # Against accidental whitespaces.
        s = userArgsStr.replace(" ", "")
        
        # Toggle mode.
        if s == CMD:
            if not user.mod:
                return
            
            if PARTY.mode:
                PARTY.mode = False
                room.notice("Party mode is now *OFF.*")
            else:
                l = PARTY.getLength()
                if not l:
                    room.notice("The playlist is *empty*.")
                else:
                    PARTY.mode = True
                    room.notice("Party mode is now *ON,* and has " + str(l) + " tracks queued.")
            return
        
        # Clear out.
        if s == "*":
            if not user.mod:
                return
            
            l = PARTY.getLength()
            if not l:
                room.notice("The playlist is already *empty*.")
            else:
                PARTY.removeItem(room, None, None)
                room.notice(str(l) + " " + pluralize("track", l) + " removed. The playlist is now *empty*.")
            return
        
        # Remove tracks from queue by track position or range.
        try:
            # Single track number, excepting possible SC track ID.
            n = int(s) - 1
            if n > SC_MIN_ID:
                raise Exception("sc")
            res = PARTY.removeItem(room, n)
            room.notice(res)
            return
        except Exception as e:
            if str(e) != "sc":
                # Acceptable keywords.
                qk = PARTY.keywordPosition(s)
                if qk is not None:
                    res = PARTY.removeItem(room, qk)
                    room.notice(res)
                    return
                
                # !q 5-7 or !q 7-5
                if "-" in s:
                    parts = s.split("-")
                    
                    p1 = PARTY.keywordPosition(parts[0])
                    p2 = PARTY.keywordPosition(parts[1])
                    
                    if p1 is not None and p2 is not None:
                        if not user.mod:
                            return
                        
                        res = PARTY.removeItem(room, p1, p2, True)  # Inclusive!
                        room.notice(res)
                        return
                
                elif "<" in s or ">" in s:
                    # !q <8 or !q >2.
                    if "<" in s:
                        x = "<"
                    else:
                        x = ">"
                    parts = s.split(x)
                    
                    # First part must be empty.
                    if parts[0] == "":
                        n = PARTY.keywordPosition(parts[1])
                        
                        # Exclusive!
                        if n is not None:
                            if not user.mod:
                                return
                            
                            if x == "<":
                                res = PARTY.removeItem(room, None, n)
                            else:
                                res = PARTY.removeItem(room, n + 1, None)
                            room.notice(res)
                            return
        
        # Link is queued as single track.
        links = {"soundcloud.com/", "youtube.com/", "youtu.be/"}
        if any(x in target for x in links):
            # Play or queue. CMD must be last argument.
            if userArgs[-1] == CMD:
                q = False
            else:
                # Default to q nexted, otherwise q last, or just play immediately.
                q = True
                nexted = True
                pos = None
                try:
                    # Position in queue by word.
                    if userArgs[1].lower() == "last":
                        nexted = False
                    else:
                        if userArgs[2].lower() == "last":
                            nexted = False
                        else:
                            raise Exception()
                except:
                    pass
            
            # Skip in seconds.
            try:
                try:
                    skip = int(userArgs[1])
                except:
                    skip = int(userArgs[2])
            except:
                skip = 0
            
            if q:
                pos = PARTY.addItem(room, target, position=pos, skip=skip, nexted=nexted)
                room.notice("Track added to playlist as #" + str(pos) + ".")
            else:
                PARTY.addItem(room, target, position=0, skip=skip)
                PARTY.queueSkip(room)
            return
        
        # Otherwise, search API results. Default to YT and first result.
        # Three options: ! - don't queue OR next - queue to next, # - skip results.
        q = True  # Queue by default,
        nexted = True  # to nexted position,
        pos = None  # or to last position, otherwise.
        n = 0  # Default to first search result.
        
        # Options only relevant if more than one query word.
        if len(userArgs) > 1:
            # Play instantly. CMD must be last argument.
            if userArgs[-1] == CMD:
                q = False
                del userArgs[-1]
            
            # Skip search results. Must be before CMD.
            try:
                i = -1
                num = int(userArgs[i])
            except:
                try:
                    i = -2
                    num = int(userArgs[i])
                except:
                    i = None
            # Validate number.
            if i:
                # Ignore negative and too large values.
                if 1 <= num <= 50:
                    n = num - 1
                    del userArgs[i]
            
            # If queued, optional last. Must be before CMD.
            if q and len(userArgs) > 1:
                if userArgs[-1].lower() == "last":
                    nexted = False
                    del userArgs[-1]
                elif len(userArgs) > 2:
                    if userArgs[-2].lower() == "last":
                        nexted = False
                        del userArgs[-2]
        
        s = " ".join(userArgs)  # Remake query.
        
        # Either a SC track ID, or YT title query.
        title = "Track"
        try:
            num = int(s.strip())
            if num < SC_MIN_ID:
                raise Exception()
            track = str(num)
        except:
            res = searchYT(s, n)
            # Failure.
            if type(res) is str:
                room.notice(res)
                return
            # Success.
            track = res[0]
            title = res[1]
        
        if q:
            # Add to queue.
            pos = PARTY.addItem(room, track, position=pos, nexted=nexted)
            room.notice("*" + title + "* added to playlist as #" + str(pos) + ".")
        else:
            # Play.
            PARTY.addItem(room, track, position=0)
            PARTY.queueSkip(room)
        return
    
    # YT controls.
    if False and userCmd in {"yt", "youtube"}:
        if not target:
            room.notice("Give me a Youtube link, like: " +
                        CMD + "yt www.youtube.com/watch?v=ZRCtkvlGjzo")
            return
        
        # Don't overplay within a time limit.
        if isOverplaying(5):
            return
        
        # Optional skip.
        try:
            skip = int(userArgs[1])
        except:
            skip = 0
        
        # Play videos from history.
        if target.lower() == "last":
            if not tinychat.YTqueue["history"]:
                room.notice("I haven't played any Youtube videos, yet...")
                return
            # Play last video.
            target = tinychat.YTqueue["history"][-1]
        elif target.lower() in {"prev", "previous"}:
            if len(tinychat.YTqueue["history"]) < 2:
                room.notice("I haven't played two Youtube videos, yet...")
                return
            # Play one-before last video.
            target = tinychat.YTqueue["history"][-2]
        else:
            # Play from history.
            try:
                v = int(target)
                l = len(tinychat.YTqueue["history"])
                if v > l:
                    room.notice("I have only played " + str(l) + " videos...")
                    return
                # Play counting from the end (most recent).
                target = tinychat.YTqueue["history"][-v]
            except:
                pass
        
        # Try to play.
        res = playTrack(room, target, skip)
        
        # On [partial] failure.
        if type(res) is str:
            if res == "Failed to get video ID...":
                room.notice("Give me a Youtube link, like: " +
                            CMD + "yt www.youtube.com/watch?v=ZRCtkvlGjzo")
            else:
                room.notice(res)
        return
    
    # Close YT, or with target close target cam.
    if userCmd == "close":
        # Closes a user cam.
        if target:
            room.uncam(target)
            return
        room.closeYT()
        return
    
    if userCmd in {"pause", "stop"}:
        room.pauseYT()
        return
    
    if userCmd in {"resume"}:
        if target:
            room.notice("Did you mean to use the " + CMD + "yt command to play a video?")
            return
        room.resumeYT()
        return
    
    if userCmd == "skip":
        if not target:
            room.notice("Give me a time to skip in *seconds*, or like: *" + CMD + "skip 1h2m3s*...")
            return
        res = room.skipYT(target)
        if res is False:
            room.notice("Give me a time to skip in *seconds*, or like: *" + CMD + "skip 1h2m3s*...")
        return
    
    # SC controls.
    if False and userCmd in {"sc", "soundcloud"}:
        if not target:
            room.notice("Give me a SoundCloud link, like: " +
                        CMD + "sc https://soundcloud.com/dumbdog-studios/senor-chang-gay-saying-ha-gay")
            return
        
        # Don't overplay within a time limit.
        if isOverplaying(5):
            return
        
        # Optional skip.
        try:
            skip = int(userArgs[1])
        except:
            skip = 0
        
        # Play tracks from history.
        if target == "last":
            if not tinychat.SCqueue["history"]:
                room.notice("I haven't played any SoundCloud tracks, yet...")
                return
            # Play last track.
            target = tinychat.SCqueue["history"][-1]
        elif target in {"prev", "previous"}:
            if len(tinychat.SCqueue["history"]) < 2:
                room.notice("I haven't played two SoundCloud tracks, yet...")
                return
            # Play one-before last track.
            target = tinychat.SCqueue["history"][-2]
        else:
            try:
                # Large numbers are assumed to be a song ID.
                v = int(target)
                if v < 1000:
                    l = len(tinychat.SCqueue["history"])
                    if v > l:
                        room.notice("I have only played " + str(l) + " tracks...")
                        return
                    # Play counting from the end (most recent).
                    target = tinychat.SCqueue["history"][-v]
            except:
                pass
        
        # Try to play.
        res = room.startSC(target, skip)
        
        # On failure.
        if type(res) is str:
            if res == "Failed to resolve track from SoundCloud API...":
                room.notice("Give me a SoundCloud link, like: " +
                            CMD + "sc https://soundcloud.com/dumbdog-studios/senor-chang-gay-saying-ha-gay")
            else:
                room.notice(res)
        return
    
    if userCmd == "sclose":
        room.closeSC()
        return
    
    if userCmd in {"spause", "sstop"}:
        room.pauseSC()
        return
    
    if userCmd in {"sresume"}:
        if target:
            room.notice("Did you mean to use the " + CMD + "sc command to play a song?")
            return
        room.resumeSC()
        return
    
    if userCmd == "sskip":
        if not target:
            room.notice("Give me a time to skip in *seconds*, or like: *" + CMD + "skip 1h2m3s*...")
            return
        res = room.skipSC(target)
        if res is False:
            room.notice("Give me a time to skip in *seconds*, or like: *" + CMD + "skip 1h2m3s*...")
        return
    
    # Either display all playlists, or list tracks in a single playlist.
    if userCmd == "pls" or userCmd == "playlists":
        if not target:
            pls = ""
            for pl in LISTS.playlists.keys():
                pls += "*" + pl.title() + "*, "
            room.notice("These playlists are available: " + pls)
        else:
            try:
                pl = LISTS.playlists[target.lower()]
                tracks = ""
                i = 1
                for track in pl:
                    tracks += str(i) + ". " + track[1].title() + ", "
                    i += 1
                room.notice("The playlist *" + target.title() + "* contains these tracks: " + tracks)
            except:
                room.say("*" + target.title() + "* playlist does not exist...")
        return
    
    if userCmd == "pl" or userCmd == "playlist":
        if not target:
            room.notice("Give me a playlist name to play... Use *" + CMD + "pls* to see a full listing...")
            return
        
        target = target.lower()
        
        # Validate playlist exists.
        try:
            pl = LISTS.playlists[target]
        except:
            room.notice("The *" + target.upper() + "* playlist does not exist...")
            return
        
        # Get track number or option.
        try:
            track = userArgs[1]
        except:
            track = None
        
        # Play random song next.
        if track is None:
            # Avoid selecting recently queued videos - in-queue or history.
            maxCheck = 20
            # Don't go into infinite loop.
            if maxCheck >= len(pl):
                maxCheck = len(pl) - 1
            
            item = None
            while not item or (item in PARTY.list[:maxCheck] or item in PARTY.history[-maxCheck:]):
                track = random.randint(0, len(pl) - 1)
                vid = pl[track][0]
                skip = pl[track][2]
                item = PARTY.makeItem(vid, skip)
            
            pos = PARTY.addItem(room, vid, skip=skip, nexted=True)
            room.notice("*Track #" + str(track + 1) + "* added to playlist as #" + str(pos) + ".")
            return
        
        # Convert track # to int(), if not option or invalid.
        try:
            track = int(track) - 1  # To index.
        except:
            pass
        
        # Play selected song next.
        if type(track) is int:
            # Optional play immediately.
            if userArgs[-1] == CMD:
                q = False
            else:
                q = True
            
            # Queue track as next, or play now.
            try:
                vid = pl[track][0]
                skip = pl[track][2]
                if q:
                    pos = PARTY.addItem(room, vid, skip=skip, nexted=True)
                    room.notice("*Track #" + str(track + 1) + "* added to playlist as #" + str(pos) + ".")
                else:
                    PARTY.addItem(room, vid, position=0, skip=skip)
                    PARTY.queueSkip(room)
            except:
                room.say("Track #" + str(track + 1) + " does not exist..." +
                         " Playlist " + target.upper() + " has " + str(len(pl)) + " tracks...")
            return
        
        # Invalid option.
        if track != "*":
            room.notice("Let me choose a *random* track, " +
                        "or give me a *track number* to queue next, like: " + 
                        CMD + "pl " + target + " 3")
        return
    
    # Displays a random ASCII cmd from list.
    if userCmd == CMD + CMD + CMD:
        # No ASCII commands available.
        if not LISTS.asciiMessages:
            return
        
        try:
            r = random.randint(0, len(LISTS.asciiMessages) - 1)
            
            cmd = LISTS.asciiMessages.keys()[r]
            msg = LISTS.asciiMessages[cmd]
            
            room.notice("*" + CMD + cmd + ":*     " + msg)
        except:
            room._chatlog("Failed to execute a random ASCII command!")
            traceback.print_exc()
        return
    
    # Plays first SC result from search.
    if userCmd in {"sl", "slucky"}:
        # Requires an API key.
        if not tinychat.SETTINGS["SCKey"]:
            return
        
        # Queue modifications disabled.
        if PARTY.locked:
            if user.mod:
                room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        if not target:
            room.notice("Give me a query to search for in SoundCloud...")
            return
        
        m = 10  # Max results.
        
        # Queue by default. Removes it from string.
        nexted = False
        if userArgs[-1] == CMD:
            userArgsStr = " ".join(userArgs[:-1])
            q = False
            # Don't overplay within a time limit.
            # if isOverplaying(5):
            #     return
        elif userArgs[-1].lower() == "next":
            q = True
            pos = 0
            nexted = True
        else:
            q = True
            pos = None
        
        # Optional item skip, default is first result.
        try:
            n = int(userArgs[-1])
            # Ignore negative and too large values.
            if n > m or n < 1:
                n = 0
            else:
                userArgsStr = " ".join(userArgs[:-1])
                n -= 1
        except:
            n = 0
        
        try:
            raw = requests.get("https://api.soundcloud.com/tracks?client_id=" +
                               tinychat.SETTINGS["SCKey"] + "&limit=" + str(m) + "&q=" +
                               quote_plus(userArgsStr.encode("utf-8", "replace"), safe=''),
                               timeout=15)
            obj = raw.json()
            
            # Optional title.
            try:
                title = obj[n]["title"]
            except:
                title = ""
            
            try:
                trackID = str(obj[n]["id"])
            except:
                room.notice("Failed to get any tracks from SoundCloud...")
                return
        except:
            traceback.print_exc()
            return
        
        if q:
            # Add to queue.
            pos = PARTY.addItem(room, trackID, position=pos, nexted=nexted)
            room.notice("*" + title + "* added to playlist as #" + str(pos) + ".")
        else:
            # Play.
            PARTY.addItem(room, trackID, position=0)
            PARTY.queueSkip(room)
        return
    
    if userCmd == "cam":
        # Self, if not on cam.
        if not target:
            res = approveCam(room, user)
            if type(res) is str:
                room.notice(res)
            return
        
        # Another.
        res = approveCam(room, target)
        if type(res) is str:
            room.notice(res)
        return
    
    if userCmd == "uptime":
        string = formatUptime(time.time() - START_TIME)
        room.notice("I have been alive for *" + string + ".*")
        return
    
    # Skip to next queued track.
    if userCmd == "next":
        # Queue modifications disabled.
        if PARTY.locked:
            if user.mod:
                room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        # Display nexted position.
        if target == "?":
            room.notice("Next available playlist slot is #" + str(PARTY.nextIndex+1) + ".")
            return
        
        # Close current, if any playing.
        PARTY.queueSkip(room)
        
        # Verbose, if playlist is empty.
        if not PARTY.list:
            room.notice("No *" + CMD + "next* track available. The playlist is *empty*.")
            return
        
        # Activate playlist, if inactive.
        # if not PARTY.mode:
        #     PARTY.mode = True
        return
    
    # Play the previous (one before currently/last played) queue item, queue next and skip,
    # or optionally select from recent tracks by number: 1 = prev, 2 = prev-1, ...
    if userCmd in {"prev", "previous"}:
        # Queue modifications disabled.
        if PARTY.locked:
            if user.mod:
                room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        # Nothing played yet.
        if not PARTY.history:
            room.notice("No tracks have been played, yet...")
            return
        # Only one track played, so use !last.
        if len(PARTY.history) == 1:
            room.notice("Only one track has been played. Use *"+CMD+"last* to replay it.")
            return
        
        if target:
            try:
                track = int(target) + 1
                # Track number must be in range.
                if track < 2:
                    raise Exception()
                l = len(PARTY.history)
                if track > l:
                    room.notice("Only " + str(l) + " tracks have been played...")
                    return
            except:
                track = 2
        else:
            track = 2
        
        # Get track from end of list.
        track *= -1
        
        item = PARTY.history[track]
        track = item["track"]
        skip = item["skip"]
        
        # Play - silently queue and skip.
        PARTY.addItem(room, track, position=0, skip=skip)
        PARTY.queueSkip(room)
    
    # Replay/restart currently playing/last played track, from queue.
    if userCmd in {"last", "replay"}:
        # Queue modifications disabled.
        if PARTY.locked:
            if user.mod:
                room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        # Nothing played yet.
        if not PARTY.history:
            room.notice("No tracks have been played, yet...")
            return
        
        item = PARTY.history[-1]
        track = item["track"]
        skip = item["skip"]
        
        # Play - silently queue and skip.
        PARTY.addItem(room, track, position=0, skip=skip)
        PARTY.queueSkip(room)
    
    # Say if the target, or self, is in the botters list.
    if userCmd == "isbotter":
        if not target:
            if user.mod:
                room.notice("You are my glorious master, " + user.nick + "!")
            elif isBotter(user):
                room.notice("I obey your commands, " + user.nick + ".")
            else:
                room.notice("You ain't a botter, " + user.nick + "... Suck my dick.")
            return
        
        # Check from user().
        u = room._getUser(target)
        if u:
            if u.mod:
                room.notice(u.nick + " is my glorious *master*!")
                return
            elif u.botter:
                room.notice(u.nick + " is identified as a *botter*!")
                return
        
        if isBotter(target):
            room.notice(target + " is identified as a *botter*!")
        else:
            room.notice(target + " is *not* identified as a botter.")
        return
    
    # No command match.
    return True

# Room commands available only to opers.
def operCommands(room, userCmd, userArgsStr, userArgs, target, user):
    if userCmd == "ban":
        if not target:
            room.notice("Give me a nickname to ban...")
            return
        
        if isBotter(target):
            room.notice("I do not ban botters...")
            return
        
        res = room.ban(target)
        
        if res is False:
            room.notice(target + " was not found in the userlist...")
        elif res is not True:
            room.notice(res)
        else:
            room._chatlog(target + " has been banned by " + user.nick + " [" + str(user.id) + "]"
                          + (" (" + user.account + ")" if user.account else "") + ".", True)
        return
    
    # Ban all users by substring.
    if userCmd in {"banall", "banthese"}:
        if not target:
            room.notice("Give me a part of a nickname, to ban all matching users...")
            return
        
        for usr in room.users.values():
            # Don't ban Botters.
            if isBotter(usr):
                continue
            
            if target in usr.nick:
                room.ban(usr)
        return
    
    # Bans and forgives.
    if userCmd == "kick":
        if not target:
            room.notice("Give me a nickname to kick...")
            return
        
        who = room._getUser(target)
        
        if not who:
            room.notice(target + " was not found in the userlist...")
            return
        
        # if isBotter(who):
        #     room.notice("I do not ban botters...")
        #     return
        
        userID = who.id  # Remember the ID for the forgive.
        
        res = room.ban(who)
        
        if res is not True:
            if not res:
                room.notice(target + " was not found in the userlist...")
            else:
                room.notice(res)
        else:
            room.forgive(userID)
            room._chatlog(target + " has been kicked by " + user.nick + " [" + str(user.id) + "]"
                          + (" (" + user.account + ")" if user.account else "") + ".", True)
            # room.notice(target + " has been banned and forgiven.")
        return
    
    if userCmd in {"kickall", "kickthese"}:
        if not target:
            room.notice("Give me a part of a nickname, to kick all matching users...")
            return
        
        for usr in room.users.values():
            # Don't ban Botters.
            if isBotter(usr):
                continue
            
            if target in usr.nick:
                room.ban(usr)
                room.forgive(usr)
        return
    
    if userCmd == "forgive":
        if not target:
            room.notice("Give me an exact nickname to forgive...")
            return
        
        room.forgiveNick(target)  # Case-sensitive.
        room.getBanlist()  # Update banlist.
        room.notice("*" + target + "* will be forgiven, momentarily...")
        return
    
    # Forgives all users in room.banlist, or by substring.
    if userCmd == "forgiveall":
        if not target:
            room.notice("Give me a partial string to forgive all matching nicknames, " +
                        "or ! to forgive all users...")
        elif target == CMD:
            room.forgiveNick(True)
            room.getBanlist()  # Update banlist.
            room.notice("*All users* in the banlist will be forgiven, momentarily...")
        else:
            room.forgiveNick(target, True)  # Case-sensitive.
            room.getBanlist()  # Update banlist.
            room.notice("All users with *" + target + "* in their nicks will be forgiven, momentarily...")
        return
    
    # Toggle substring in AUTOFORGIVES.
    # Exact nicks start with *, otherwise partial string match.
    # Wildcards are ?.
    if userCmd == "autoforgive":
        l = "autoForgives"
        
        if not target:
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.notice("Autoforgives added this session: *" + s + "*.")
            return
        
        if target == "?":
            if CONTROLS['autoforgive']:
                room.notice("*Autoforgive mode is ON!* All users who get banned will be forgiven!")
            else:
                room.notice("*Autoforgive mode is OFF.* All users may be banned.")
            return
        
        # Clear list.
        if target == CMD + CMD:
            LISTS.clearList(l)
            room.notice("The *" + l + "* list is now *empty*.")
            return
        
        # WARNING: Forgives all bans! For extreme measures only.
        if target == CMD:
            if CONTROLS['autoforgive']:
                CONTROLS['autoforgive'] = False
                room.notice("*Autoforgive mode is now OFF.* All users may be banned.")
            else:
                CONTROLS['autoforgive'] = True
                room.notice("*Autoforgive mode is now ON!* All users who get banned will be forgiven!")
            return
        
        # Prevent excessive autoforgives, if not exact nick.
        if target[0] != "*":
            if len(target) <= 2:
                room.notice("Give me a partial nick longer than 2 characters...")
                return
        
        # Don't allow certain strings.
        ignores = ["newuser"]
        for word in ignores:
            if target in word:
                return
        
        # Toggle from list.
        if target not in LISTS.autoForgives:
            LISTS.addItem(l, target)
            room.notice("*" + target + "* has been added to the *" + l + "* list!")
        else:
            LISTS.removeItem(l, target)
            room.notice("*" + target + "* has been removed from the *" + l + "* list.")
        return
    
    # Toggle substring in AUTOBANS.
    # Exact nicks start with *, otherwise partial string match.
    # Wildcards are ?.
    if userCmd == "autoban":
        l = "nickBans"
        
        if not target:
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.notice("Nickbans added this session: " + s + ".")
            return
        
        if target == "?":
            if CONTROLS['autoban']:
                room.notice("*Autoban mode is ON!* All users who join the room will be banned!")
            else:
                room.notice("*Autoban mode is OFF.* All users may join the room.")
            return
        
        # Clear list.
        if target == "!!":
            LISTS.clearList(l)
            room.notice("The *" + l + "* list is now *empty*!")
            return
        
        # WARNING: Bans all joins! For extreme measures only.
        if target == CMD:
            if CONTROLS['autoban']:
                CONTROLS['autoban'] = False
                room.notice("*Autoban mode is now OFF.* All users may join the room.")
            else:
                CONTROLS['autoban'] = True
                room.notice("*Autoban mode is now ON!* All users who join the room will be banned!")
            return
        
        # Prevent excessive autobans, if not exact nick.
        if target[0] != "*":
            if len(target) <= 2:
                room.notice("Give me a partial nick longer than 2 characters...")
                return
        
        # Don't allow certain strings.
        ignores = ["newuser"]
        for word in ignores:
            if target in word:
                return
        
        # Toggle from list, and ban if in room.
        if target not in LISTS.nickBans:
            # Ban matching nickname from room.
            name = target
            if name[0] == "*":
                name = name[1:]
            room.ban(name)
            
            # Verify regular expression.
            if target.startswith('r"'):
                s = target[2:]
                try:
                    re.compile(s)
                except Exception as e:
                    room.notice("*Failed to compile():* " + s + " - " + str(e))
                    return
            
            LISTS.addItem(l, target)
            room.notice(target + " has been added to the *" + l + "* list.")
        else:
            LISTS.removeItem(l, target)
            room.notice(target + " has been removed from the *" + l + "* list.")
        return
    
    if userCmd == "autokick":
        if target == "?":
            if CONTROLS['autokick']:
                room.notice("*Autokick mode is ON!* All users who join the room will be kicked!")
            else:
                room.notice("*Autokick mode is OFF.* All users may join the room.")
            return
        
        # WARNING: Kicks all joins! For extreme measures only.
        if target == CMD:
            if CONTROLS['autokick']:
                CONTROLS['autoban'] = False
                room.notice("*Autokick mode is now OFF.* All users may join the room.")
            else:
                CONTROLS['autokick'] = True
                room.notice("*Autokick mode is now ON!* All users who join the room will be kicked!")
            return
        return
    
    # Auto close a cam by partial nick, or all.
    if userCmd == "camclose":
        # Do it for everyone.
        if not target:
            if CONTROLS["camclose"]:
                CONTROLS["camclose"] = False
                room.notice("You can now go on cam, without being closed.")
            else:
                CONTROLS["camclose"] = True
                room.notice("All users going on cam will be closed!")
            return
        
        # Do it by a substring.
        string = target.lower()
        
        # Clear list.
        if string == CMD:
            del CONTROLS["camclose"][:]
            room.notice("The camclose list is now *empty*.")
            return
        
        # Prevent excessive camcloses.
        if len(string) <= 2:
            room.notice("Give me a partial nick longer than 2 characters...")
            return
        
        if type(CONTROLS["camclose"]) is not list:
            CONTROLS["camclose"] = []
        
        if string in CONTROLS["camclose"]:
            CONTROLS["camclose"].remove(string)
            room.notice(string + " cleared from having their cam closed.")
            # Optional, remove user remember.
            try:
                usr = room._getUser(target)
                usr.camclosed = False
            except:
                pass
        else:
            CONTROLS["camclose"].append(string)
            room.notice("All users with " + string + " in their nicks will be cam closed!")
            # Optional remember user, beyond nick.
            try:
                usr = room._getUser(target)
                usr.camclosed = True
            except:
                pass
    
    # Auto ban a cam by partial nick, or all.
    if userCmd == "camban":
        # Do it for everyone.
        if not target:
            if CONTROLS["camban"]:
                CONTROLS["camban"] = False
                room.notice("You can now go on cam, without being banned.")
            else:
                CONTROLS["camban"] = True
                room.notice("All users going on cam will be *banned*!")
            return
        
        # Do it by a substring.
        string = target.lower()
        
        # Clear list.
        if string == CMD:
            del CONTROLS["camban"][:]
            room.notice("The camban list is now *empty*.")
            return
        
        # Prevent excessive cambans.
        if len(string) <= 2:
            room.notice("Give me a partial nick longer than 2 characters...")
            return
        
        if type(CONTROLS["camban"]) is not list:
            CONTROLS["camban"] = []
        
        if string in CONTROLS["camban"]:
            CONTROLS["camban"].remove(string)
            room.notice(string + " cleared from having their cam banned.")
        else:
            CONTROLS["camban"].append(string)
            room.notice("All users with " + string + " in their nicks will be cam *banned*!")
    
    # Auto ban by substring in user message.
    if userCmd in {"banword", "banwords"}:
        l = "banWords"
        
        if not target:
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.notice("Banwords added this session: *" + s + "*.")
            return
        
        string = userArgsStr.lower()
        
        # Clear list.
        if string == CMD:
            LISTS.clearList(l)
            room.notice("The *" + l + "* list is now *empty*.")
            return
        
        # Prevent excessive banwords.
        if len(string) < 3:
            room.notice("Give me a word longer than 2 characters...")
            return
        
        if string in LISTS.banWords:
            LISTS.removeItem(l, string)
            room.notice("*" + string + "* has been removed from the *" + l + "* list.")
        else:
            LISTS.addItem(l, string)
            room.notice("*" + string + "* has been added to the *" + l + "* list!")
        return
    
    # Toggle identifying a user as an oper.
    if userCmd == "mod":
        if not target:
            room.say("Give me a nickname to mod...")
            return
        
        curUser = room._getUser(target)
        if not curUser:
            room.notice("Nickname " + target + " not found...")
            return
        
        if curUser.mod:
            curUser.mod = False
            room.notice(target + " is *not* recognized as a moderator, anymore.")
        else:
            curUser.mod = True
            room.notice(target + " is now recognized as a *moderator*!")
    
    # Toggle an account name to be automatically banned.
    if userCmd in {"banaccount", "accountban"}:
        l = "accountBans"
        
        if not target:
            s = "*, *".join(LISTS.sessionLists[l])
            if not s:
                s = "None"
            room.notice("Banned accounts added this session: *" + s + "*.")
            return
        
        if target in LISTS.accountBans:
            LISTS.removeItem(l, target)
            room.notice("*" + target + "* account has been removed from the *" + l + "* list.")
        else:
            LISTS.addItem(l, target)
            room.notice("*" + target + "* account has been added to the *" + l + "* list!")
        return
    
    # Rename the bot.
    if userCmd in {"rename", "nick"}:
        if "NickLock" in tinychat.SETTINGS:
            n = tinychat.SETTINGS["NickLock"]
            # Either full or partial lock.
            if n is True:
                return
            elif type(n) in {str, unicode}:
                # Nickname must start with given string.
                if not target.startswith(n):
                    room.notice("NickLock is *ON*, and requires bot's nickname to start with: "+n)
                    return
        
        if not target:
            return
        
        res = room.setNick(target)
        
        if type(res) in {str, unicode}:
            room.notice(res)
        return
    
    # Close all cams. Optionally, keep one open by nick.
    if userCmd == "uncamall":
        keepOpen = False
        if target:
            keepOpen = target
        
        for usr in room.users.values():
            if keepOpen and usr.nick == keepOpen:
                continue
            if usr.broadcasting:
                uncam(usr)
        return
    
    # Toggle bot's listening to room commands.
    if userCmd == "bot":
        if CONTROLS["botActive"]:
            CONTROLS["botActive"] = False
            room.notice("Bot is now deactivated!")
        else:
            CONTROLS["botActive"] = True
            room.notice("Bot is now active.")
        return
    
    # Disconnect bot. Don't kill script.
    if userCmd == "disconnect":
        room.disconnect()
        return
    
    # Kill the bot. Kill script.
    if userCmd == "killbot":
        room.disconnect()
        tinychat.SETTINGS["Run"] = False
        return
    
    # Soft reconnect. Doesn't kill script.
    if userCmd == "reconnect":
        room.reconnect()
        return
    
    # Clear the chatbox.
    if userCmd == "clear":
        try:
            if room.user.mod:
                room.notice("\n\n\n" +
                            "(\__/)\n" +
                            "(>'.'<)  *nom nom*\n" +
                            "(\")_(\")\n" +
                            ",___,\n" +
                            "[O.o]      *hoot hoot*\n" +
                            "/)__)\n" +
                            "-\"--\"-\n" +
                            "-(\(\\\n" +
                            "( =':')   *mmm*\n" +
                            "(..(\")(\")\n")
            else:
                text = "133,133,133,133,133,133,133,133,133,133" + \
                       room._encodeMessage("  -- Chat Cleared Aye Sir! ^_^ -- ")
                room._sendCommand("privmsg", [text, room.color + ",en"])
        except:
            traceback.print_exc()
        return
    
    # Print the repr() of userArgsStr.
    if userCmd == "print":
        try:
            print repr(userArgsStr)
        except:
            traceback.print_exc()
        return
    
    if userCmd in {"snapshot", "screenshot"}:
        if CONTROLS["banSnapshots"]:
            CONTROLS["banSnapshots"] = False
            room.notice("Auto Snapshot banning is now deactivated!")
        else:
            CONTROLS["banSnapshots"] = True
            room.notice("Auto Snapshot banning is now active.")
        return
    
    if userCmd in {"newuser", "newusers"}:
        if CONTROLS["banNewusers"]:
            CONTROLS["banNewusers"] = False
            room.notice("Auto Newuser banning is now deactivated!")
        else:
            CONTROLS["banNewusers"] = True
            room.notice("Auto Newuser banning is now active.")
        return
    
    if userCmd in {"android", "androids"}:
        if CONTROLS["banPhones"]["android"]:
            CONTROLS["banPhones"]["android"] = False
            room.notice("*Android* users can now broadcast.")
        else:
            CONTROLS["banPhones"]["android"] = True
            room.notice("*Android* users will now be *banned on broadcast*!")
        return
    
    if userCmd in {"iphone", "iphones"}:
        if CONTROLS["banPhones"]["iphone"]:
            CONTROLS["banPhones"]["iphone"] = False
            room.notice("*iPhone* users can now broadcast.")
        else:
            CONTROLS["banPhones"]["iphone"] = True
            room.notice("*iPhone* users will now be *banned on broadcast*!")
        return
    
    if userCmd in {"phone", "phones"}:
        # Only deactivate if both bans are ON.
        if not CONTROLS["banPhones"]["android"] or not CONTROLS["banPhones"]["iphone"]:
            CONTROLS["banPhones"]["android"] = True
            CONTROLS["banPhones"]["iphone"] = True
            room.notice("All *phone* users will now be *banned on broadcast*!")
        else:
            CONTROLS["banPhones"]["android"] = False
            CONTROLS["banPhones"]["iphone"] = False
            room.notice("All *phone* users can now broadcast.")
        return
    
    # Display or set room topic.
    if userCmd == "topic":
        if not target:
            room.notice("*Topic is:* " + room.topic)
            return
        
        if target == CMD:
            if "defaultTopic" in tinychat.SETTINGS:
                topic = tinychat.SETTINGS["defaultTopic"]
        else:
            l = len(userArgsStr)
            if l > 115:
                room.notice("The room topic cannot be longer than 115 characters! " +
                            "Yours is " + str(l) + " characters long.")
                return
            topic = userArgsStr
        
        room.setTopic(topic)
        room.notice("*Topic is now:* " + topic)
        return
    
    # Only lets botters and modders/mods into room.
    if userCmd == "privatemode":
        # Only show status.
        if target == "?":
            if CONTROLS["PrivateMode"]:
                room.notice("*PRIVATE MODE ON!* Only botters and modders/mods are allowed in the room.")
            else:
                room.notice("*Private Mode OFF.* All may enter the room.")
            return
        
        if not CONTROLS["PrivateMode"]:
            CONTROLS["PrivateMode"] = True
            room.notice("*PRIVATE MODE ON!* Only botters and modders/mods are allowed in the room.")
        else:
            CONTROLS["PrivateMode"] = False
            room.notice("*Private Mode OFF.* All may enter the room.")
        return
    
    # Only lets logged-in users into room.
    if userCmd == "accountmode":
        # Only show status.
        if target == "?":
            if CONTROLS["AccountMode"]:
                room.notice("*ACCOUNT MOD ON!* Only logged-in users (and lurkers) are allowed in the room.")
            else:
                room.notice("*Account Mode OFF.* All may enter the room.")
            return
        
        if not CONTROLS["AccountMode"]:
            CONTROLS["AccountMode"] = True
            room.notice("*ACCOUNT MOD ON!* Only logged-in users (and lurkers) are allowed in the room.")
        else:
            CONTROLS["AccountMode"] = False
            room.notice("*Account Mode OFF.* All may enter the room.")
        return
    
    # Ignore room commands from a user, any user.
    if userCmd == "ignore":
        if not target:
            room.notice(user, "Give me a name to ignore...")
            return
        
        t = target.lower()
        u = room._getUser(target)  # Try attaching to existing user.
        
        # Toggle ignoring.
        try:
            LISTS.ignored.remove(t)
            if u:
                u.ignored = False
            room.notice("*" + t + "* has been removed from the ignore list.")
        except:
            LISTS.ignored.append(t)
            if u:
                u.ignored = True
            room.notice("*" + t + "* has been added to the ignore list!")
    
    # Lock playlist to let a single track play,
    # so no one can play anything or change queue.
    # Optionally lock until unlocking.
    if userCmd == "qq":
        if target == "?":
            if PARTY.locked:
                if PARTY.locked == 1:
                    extra = ", until unlocking!"
                else:
                    extra = "!"
                room.notice("The playlist is *locked* and cannot be changed" + extra)
            else:
                room.notice("The playlist is *unlocked*.")
            return
        
        if PARTY.locked:
            PARTY.locked = False
            room.notice("The playlist is now *unlocked*.")
        else:
            if target == CMD:
                PARTY.locked = 1
                extra = ", until unlocking!"
            else:
                PARTY.locked = True
                extra = "!"
            room.notice("The playlist is now *locked* and cannot be changed" + extra)
        return
    
    # Plays a random track command, instantly: !!!
    if userCmd == CMD + CMD:
        # No videos available.
        if not LISTS.commands:
            room.notice("No YT & SC commands are available...")
            return
        
        # Queue modifications disabled.
        if PARTY.locked:
            room.notice("Party mode is *LOCKED!* Use *" + CMD + "qq* to unlock it.")
            return
        
        # Don't overplay within a time limit.
        # if isOverplaying(2):
        #     return
        
        # Avoid repeats.
        maxCheck = 20
        if maxCheck >= len(LISTS.commands):
            maxCheck = len(LISTS.commands) - 1  # Don't go into infinite loop.
        
        vid = None
        while (not vid or vid in tinychat.YTqueue["history"][-maxCheck:] or
                       vid in tinychat.SCqueue["history"][-maxCheck:]):
            # Get new one.
            r = random.randint(0, len(LISTS.commands) - 1)
            cmd = LISTS.commands.keys()[r]
            vid = LISTS.commands[cmd][0]
            skip = LISTS.commands[cmd][1]
        
        room.notice("Selected *" + CMD + cmd + "*...")
        playTrack(room, vid, skip)
        return
    
    # Toggle banning messages that are all in capital letters.
    if userCmd == "bancaps":
        if target == "?":
            if CONTROLS["banCaps"]:
                room.notice("*BanCaps mode is on!*")
            else:
                room.notice("BanCaps mode is *off*.")
            return
        
        if CONTROLS["banCaps"]:
            CONTROLS["banCaps"] = False
            room.notice("BanCaps mode is now *off*.")
        else:
            CONTROLS["banCaps"] = True
            room.notice("*BanCaps mode is now on!* " +
                        "Users sending messages containing only capital letters will be banned!")
        return
    
    # No command match.
    return True

# Delayed ban, so bots can change nick in time.
def delayedBan(room, user):
    time.sleep(2.5)
    if not isBotter(user) and not user.mod:
        room.ban(user)
        room.forgive(user)

# Extended join handling. From joins event, too. Bot's own join, too.
def onJoinHandle(room, user, joins, myself):
    ## Initialize extra user properties. Expected to happen before anything else! ##
    user.botter = False
    # Ignored property, for using bot commands.
    user.ignored = False
    
    # AccountMode, kicks all non-logged in users, except lurkers (cant send anything to room.)
    if CONTROLS["AccountMode"] and not user.account and not user.lurking:
        time.sleep(0.1)
        room.ban(user)
        room.forgive(user)
        return
    
    # Check account.
    if user.account in LISTS.accountBans:
        time.sleep(0.1)
        room.ban(user)
        room._chatlog(user.nick + " [" + str(user.id) + "] (" + user.account +
                      ") has been banned from accountBans.", True)
        return
    
    # Botter by account.
    if isBotter("@" + user.account):
        user.botter = True
    
    # Modders.
    if isBotter("*" + user.account):
        user.mod = True
    
    # Ban all joining mode.
    if CONTROLS['autoban'] and not joins and not user.mod and not isBotter(user):
        time.sleep(0.1)
        room.ban(user)
        return
    
    # Kick all joining mode.
    if CONTROLS['autokick'] and not joins and not user.mod and not isBotter(user):
        time.sleep(0.1)
        room.ban(user)
        room.forgive(user)
        return
    
    # Private mode.
    if CONTROLS["PrivateMode"] and not isBotter(user) and not user.mod:
        t = threading.Thread(target=delayedBan, args=(room, user,))
        t.daemon = True  # Exits when main thread quits.
        t.start()
        return

# User left the room.
def onQuitHandle(room, user):
    pass

# Autobans, by substring, or nickchange spammers.
def onNickChangeAutoban(room, user, new, old):
    # Don't overban.
    try:
        if user.banned == 2:
            return
    except:
        user.banned = 0;
    
    # Autocam approve for botters, if bpass exists.
    # if room.bpass and not user.mod and isBotter(user):
    #     approveCam(room, user)
    #     room._chatlog("Automatically approved botter "+user.nick+"'s cam." , True)
    
    # Except mods and botters.
    if user.mod or isBotter(user):
        return
    
    # AccountMode, kicks all non-logged in users. Extra check to join event.
    if CONTROLS["AccountMode"] and not user.account:
        room.ban(user)
        room.forgive(user)
        user.banned += 1
        return
    
    # Private mode. Extra check to join event.
    if CONTROLS["PrivateMode"] and not isBotter(user) and not user.mod:
        room.ban(user)
        room.forgive(user)
        user.banned += 1
        return
    
    # Ban newusers.
    if CONTROLS["banNewusers"] and new.startswith("newuser"):
        room.ban(user)
        user.banned += 1
        return
    
    # Ban fake guests.
    if CONTROLS["banGuests"] and new.startswith("guest"):
        room.ban(user)
        room._chatlog(user.nick + " [" + str(user.id) + 
            "] has been banned for changing nick to \"guest-\".", True)
        user.banned += 1
        return
    
    # Nickchange counter.
    t = int(time.time())
    
    try:
        user.nickSpam[0] += 1
    except:
        # Initialize counter.
        user.nickSpam = [1, t]
    
    # Ban & mark spammer and reset counts.
    if user.nickSpam[0] == 4:
        if t - user.nickSpam[1] < 10:
            room.ban(user)
            room._chatlog(user.nick + " [" + str(user.id) + 
                "] has been banned for nick spamming.", True)
            user.banned += 1
            return
        user.nickSpam[0] = 1
        user.nickSpam[1] = t
    
    # Exact nickbans start with *.
    # Wildcard is ?.
    for string in LISTS.nickBans:
        exact = False
        # Exact matching.
        if string[0] == "*":
            string = string[1:]
            exact = True
        
        match = isMatch(string, new, exact=exact)
        
        if match is True:
            room.ban(user)
            room._chatlog(user.nick + " [" + str(user.id) + 
                "] has been banned from nickBans: " + string, True)
            user.banned += 1
            return
        elif type(match) in {str, unicode}:
            room._chatlog(match, True)
            return

# Forgive from autoforgives.
def onBanlistAutoforgives(room):
    if LISTS.autoForgives:
        for user in room.banlist:
            userID = user[0]
            userNick = user[1]
            
            for nick in LISTS.autoForgives:
                if nick == userNick:
                    # time.sleep(0.2)
                    room.forgive(userID)

# Defense against cam spammers.
def onBroadcastDefense(room, user):
    # Don't overban.
    try:
        if user.banned == 2:
            return
    except:
        user.banned = 0;
    
    # Except mods and botters.
    if user.mod or isBotter(user):
        # Verbose.
        if CONTROLS["BroadcastMessage"]:
            room.notice(CONTROLS["BroadcastMessage"].replace("@n", user.nick))
        return
    
    # Auto ban phone users.
    if user.device:
        # Android.
        if CONTROLS["banPhones"]["android"] and user.device == "android":
            room.ban(user)
            user.banned += 1
            room._chatlog(user.nick + " [" + str(user.id) + 
                "] has been banned from BANPHONES ANDROID.", True)
            return
        # iPhone.
        if CONTROLS["banPhones"]["iphone"] and user.device == "ios":
            room.ban(user)
            user.banned += 1
            room._chatlog(user.nick + " [" + str(user.id) + 
                "] has been banned from BANPHONES IPHONE.", True)
            return
    
    # Auto cam close everyone.
    if CONTROLS["camclose"] is True:
        room.uncam(user.nick)
        return
    
    # Auto cam close by nick.
    if type(CONTROLS["camclose"]) is list:
        for name in CONTROLS["camclose"]:
            if name.lower() in user.nick.lower():
                room.uncam(user.nick)
                return
    # Or by user.
    try:
        if user.camclosed:
            room.uncam(user.nick)
            return
    except:
        pass
    
    # Auto cam ban everyone.
    if CONTROLS["camban"] is True:
        room.ban(user)
        user.banned += 1
        room._chatlog(user.nick + " [" + str(user.id) + 
            "] has been banned from AUTOCAMBAN.", True)
        return
    
    # Auto cam ban by nick.
    if type(CONTROLS["camban"]) is list:
        # Some guests leak through autoban.
        if "guest-" in user.nick:
            room.ban(user)
            user.banned += 1
            room._chatlog(user.nick + " [" + str(user.id) + 
                "] has been banned from 'guest-' CAMBANS.", True)
            return
        
        for name in CONTROLS["camban"]:
            if name.lower() in user.nick.lower():
                room.ban(user)
                user.banned += 1
                room._chatlog(user.nick + " [" + str(user.id) + 
                    "] has been banned from CAMBANS: " + name, True)
                return
    
    # Cam counter and intelligent camspam blocker.
    t = int(time.time())
    
    try:
        user.camSpam[0] += 1
    except:
        # Initialize counter.
        user.camSpam = [1, t]
    
    # Either ban spammer, or reset counter.
    if user.camSpam[0] == 2:
        if t - user.camSpam[1] < 15:
            room.ban(user)
            user.banned += 1
            room._chatlog(user.nick + " (" + str(user.id) + 
                ") has been banned for (2) cam spamming.", True)
            return
    
    if user.camSpam[0] == 3:
        if t - user.camSpam[1] < 40:
            room.ban(user)
            user.banned += 1
            room._chatlog(user.nick + " (" + str(user.id) + 
                ") has been banned for (3) cam spamming.", True)
            return
        # Reset count.
        user.camSpam[0] = 1
        user.camSpam[1] = t

# Remove all HTML tags from a string.
def removeTags(string=""):
    if type(string) not in [str, unicode]:
        string = unicode(string)
    
    tag = "<"
    endtag = ">"
    start = string.find(tag)
    
    while start >= 0:
        end = string.find(endtag, start)
        # Not a tag, if no closer.
        if end == -1:
            start = string.find(tag, start + 1)
            continue
        # Remove from string.
        string = string[0:start] + string[end + 1:]
        # Find next.
        start = string.find(tag)
    
    return string

# Return an HTML escaped string. Doesn't do whitespaces!
# Not for URLs, only for HTML code.
def escape(string):
    """Returns the given HTML with ampersands, quotes and carets encoded."""
    return (string.replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;'))

# Search Youtube by video title.
# Returns [videoID, title], or str() on failure.
def searchYT(search="", skip=0):
    # Requires an API key.
    if not tinychat.SETTINGS["YTKey"]:
        return "A Youtube API Key is required to search for videos by title..."
    
    if not search:
        return "Give me a query to search for in Youtube..."
    
    m = 50  # Max results.
    
    try:
        # https://developers.google.com/youtube/v3/docs/search/list
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': 1
        }
        
        raw = requests.get("https://www.googleapis.com/youtube/v3/search?" +
                           "maxResults=" + str(m) + "&part=snippet,id&key=" + tinychat.SETTINGS["YTKey"] +
                           "&type=video&safeSearch=none&videoEmbeddable=true&q=" +
                           quote_plus(search.encode("utf-8", "replace"), safe=''),
                           headers=header,
                           timeout=15)
        obj = raw.json()
        
        # Optional title.
        try:
            title = obj["items"][skip]["snippet"]["title"]
        except:
            title = ""
        
        try:
            vid = str(obj["items"][skip]["id"]["videoId"])
        except:
            raise Exception("Failed to get any videos from Youtube...")
    except Exception as e:
        # traceback.print_exc()
        return str(e)
    
    # Success.
    return [vid, title]

# Updates all the commands and defenses from online texts, by interval.
def updateOnlineTexts():
    while True:
        # Every interval.
        time.sleep(60 * 5)
        
        result = listLoader(BottersText, online=True, parts=1, word=True)
        if result:
            LISTS.botters = result + LISTS.sessionLists["botters"]
        
        result = listLoader(ExtraYTsText, online=True, parts=3, youtubes=True)
        if result:
            LISTS.commands = result
        
        getPlaylists(PlaylistsText)
        
        getExtraDOX(moreDoxText)
        
        result = listLoader(moreMessagesText, online=True, parts=2)
        if result:
            LISTS.roomMessages = result
        
        result = listLoader(asciiText, online=True, parts=2, unicode=True)
        if result:
            LISTS.asciiMessages = result
        
        getRandoms(randomsText)
        
        # Defenses.
        result = listLoader(AutobansText, online=True, word=True)
        if result:
            # Override previous loaded lists.
            LISTS.accountBans = []
            LISTS.nickBans = []
            # Apply online lists.
            for name in result:
                # Account ban.
                if name[0] == "@":
                    n = name[1:]
                    if n not in LISTS.accountBans:
                        LISTS.accountBans.append(n)
                # Nick ban.
                else:
                    if name not in LISTS.nickBans:
                        LISTS.nickBans.append(name)
            # Apply session lists.
            LISTS.accountBans += LISTS.sessionLists["accountBans"]
            LISTS.nickBans += LISTS.sessionLists["nickBans"]
        
        result = listLoader(AutoforgivesText, online=True, word=True)
        if result:
            LISTS.autoForgives = result + LISTS.sessionLists["autoForgives"]
        
        result = listLoader(banwordsText, online=True)
        if result:
            LISTS.banWords = result + LISTS.sessionLists["banWords"]

# Approve a cam waiting in the Greenroom,
# By user obj, nickname or userid.
# Returns str() on failure.
def approveCam(room, identifier):
    if not room.bpass:
        return
    
    if type(identifier) in [str, unicode, int]:
        user = room._getUser(identifier)
        if not user:
            return "User " + str(identifier) + " was not found..."
    
    if user.broadcasting:
        return
    
    room._sendCommand("privmsg", [room._encodeMessage("/allowbroadcast " + room.bpass),
        "#0,en" + "n" + str(user.id) + "-" + user.nick])

# Returns a nicely formatted string for time.time().
def formatTime(t=None):
    if not t:
        t = int(time.time())
    else:
        t = int(t)
    
    days = int(t / 60 / 60 / 24)
    hours = int((t / 60 / 60) - (days * 24))
    minutes = int((t / 60) - (hours * 60) - (days * 24 * 60))
    seconds = int(t - (minutes * 60) - (hours * 60 * 60) - (days * 24 * 60 * 60))
    
    string = ""
    
    if days:
        end = " "
        if days != 1:
            end = "s "
        string += str(days) + " day" + end
    if hours:
        end = " "
        if hours != 1:
            end = "s "
        string += str(hours) + " hour" + end
    if minutes:
        end = " "
        if minutes != 1:
            end = "s "
        string += str(minutes) + " minute" + end
    
    end = ""
    if seconds != 1:
        end = "s"
    string += str(seconds) + " second" + end
    
    return string

# Returns True if YT or SC was started within the time limit.
def isOverplaying(limit=1):
    t = time.time()
    
    if t - tinychat.YTqueue["start"] < limit or t - tinychat.SCqueue["start"] < limit:
        return True

# Return True if string is in name (as substring.)
# wildcard will match any character, but not nothing.
# exact checks full equality.
# case forces case-sensitivity, with either method.
def isMatch(string, name, exact=False, case=False, wildcard="?"):
    # RE string.
    if string.startswith('r"'):
        s = string[2:]
        # Compile.
        try:
            r = re.compile(s)
        except Exception as e:
            return "Failed to re.compile(): " + string + " - " + str(e)
        # Match.
        if r.match(name):
            return True
        # Fail.
        return
    
    # Case-sensitivity.
    if not case:
        name = name.lower()
        string = string.lower()
    
    # Exact match, handling wildcards and case.
    if exact:
        # Replace with wildcards in name.
        for i in range(len(string)):
            if string[i] == wildcard:
                # Replace char at index.
                name = name[:i] + wildcard + name[i + 1:]
        
        if name == string:
            return True
        
        return
    
    # Escape characters for RE, and replace wildcard with RE wildcard.
    stringFixed = ".".join(map(re.escape, string.split("?")))
    
    try:
        r = re.compile(stringFixed)
    except Exception as e:
        return "Failed to re.compile(): " + stringFixed + " - " + str(e)
    
    if r.search(name):
        return True

# Return True if user is botter,
# by nick or account. False otherwise.
# NOTICE: Must be passed an account, to check for account botter!
def isBotter(user):
    if not user:
        return False
    
    # Nickname.
    if type(user) in [unicode, str]:
        # In list.
        if user in LISTS.botters:
            return True
    # User object.
    else:
        # Property. Only applies to botter from account.
        if user.botter:
            return True
        
        # Nickname.
        if user.nick in LISTS.botters:
            return True
    
    # No match.
    return False

if __name__ == "__main__":
    # Apply extension functions.
    tinychat.SETTINGS["onJoinExtend"]       = onJoinHandle
    tinychat.SETTINGS["onJoinsdoneExtend"]  = onJoinsdoneExtended
    tinychat.SETTINGS["onQuitExtend"]       = onQuitHandle
    tinychat.SETTINGS["onNoticeExtend"]     = onNoticeBans
    tinychat.SETTINGS["onMessageExtend"]    = onMessageExtended
    tinychat.SETTINGS["onPMExtend"]         = onPMExtended
    tinychat.SETTINGS["onNickChangeExtend"] = onNickChangeAutoban
    tinychat.SETTINGS["onBanlistExtend"]    = onBanlistAutoforgives
    tinychat.SETTINGS["onBroadcastExtend"]  = onBroadcastDefense
    tinychat.SETTINGS["disconnectExtend"]   = disconnectExtended
    
    # Update all online texts, by interval.
    CONTROLS["listUpdater"] = threading.Thread(target=updateOnlineTexts, args=())
    CONTROLS["listUpdater"].daemon = True  # Exits when main thread quits.
    CONTROLS["listUpdater"].start()
    
    # Run!
    tinychat.main()
