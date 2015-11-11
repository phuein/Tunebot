#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# The friendly Tunebot! [ by James Koss phuein@gmail.com ] October 30th, 2015.
# -------------------------------------------------------------------
# Started as Qbot in PHP, which was extensively modified and fixed,
# And then translated into Python, using the core code from Pinychat.

# This is a tinychat.py extension module,
# Expecting a patched version of tinychat.py to try/except its functions,
# Which are patched into it as globals.

# Unicode support is troublesome, and therefore not official.

import tinychat                     # https://github.com/notnola/pinychat

import requests                     # http://www.python-requests.org/
requests.packages.urllib3.disable_warnings() # For python < 2.7.9

import random
import traceback                    # https://docs.python.org/2/library/traceback.html
import re                           # https://docs.python.org/2/library/re.html
import threading
import time
import os
import json
import sys
from urllib import quote, quote_plus    # Handles URLs.

# Return an unscaped string from an HTML string.
import HTMLParser
unescape = HTMLParser.HTMLParser().unescape

# Operationals.
NICKNAME = "Tunebot"
CMD = "!"                           # The prefix for commands.
BOT_ACTIVE = True                   # Respond to room commands.
READY_MESSAGE = False               # Say in the room, when connected and available.
SETTINGS_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings", "")
START_TIME = int(time.time())
HELP_LINK = "http://is.gd/Qc2bjE"   # Link to an online help file How To use Tunebot.

CONTROLS = {
    # Basics.
    "greet":            False,      # Smartly respond to people saying greetings.
    # Defenses.
    "camclose":         False,
    "camban":           False,
    "autoban":          False,
    "autoforgive":      False,
    "banSnapshots":     True,
    "banNewusers":      False,
    "banGuests":        True,       # Catches fakers who change nick to guest-#.
    "banPhones":        {
        "android":          False,
        "iphone":           False
    },
    # Extras.
    "listUpdater":      None        # Thread object for automatic list updater.
}

# Get extra arguments from command-line:
# nick=NICK, bot=0/1, greet=0/1, snap=0/1.
try:
    for item in sys.argv:
        match = item.lower()
        
        if match.find("nick=") == 0 or match.find("nickname=") == 0:
            val = item.split("=")[1]
            NICKNAME = val
            continue
        
        if match.find("bot=") == 0:
            val = item.split("=")[1]
            try:
                BOT_ACTIVE = bool(int(val))
            except:
                print("Argument BOT must be 0 or 1, only.")
            continue
        
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
except:
    pass

# A timed thread checks for items in this list.
# If any exist, it will check if anything is still playing,
# And if not, it will play the next item from this list.
PARTY = {
    "thread": None,
    "list": [],
    "mode": False
}

# Return an online or local file converted to a list or dictionary:
# Parts = 3: [cmd: [method, msg], ...] 2: [cmd: msg] 1: [item].
# Ignores empty lines and // comments. online=True for online files.
# One per line. Indexes 0 and 1 are forced lower-case.
# word Takes only one word per line. youtubes Allows many command words, lowercased.
# strict Forces all parts of index over 0 to exist, otherwise only index 0 is forced.
# strict Also forced indexes 0 and 1 to be lower-case.
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
            raw = open(link)
            if not unicode:
                lines = raw.read().encode("ascii", "ignore").splitlines()
            else:
                lines = raw.read().splitlines()
                try:
                    lines = lines.decode("utf-8", "replace")
                except:
                    pass
            raw.close()
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
                    if skip > 10000:
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
BOTTERS = []
filename = "botters.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, word=True)
if result is None:
    print("Failed to load the Botters list from " + filename + ".")
else:
    BOTTERS = result

# Load more botters from online list.
filename = "bottersextra.txt"
BottersText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Extra Botters list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    BottersText = result[0]
    
    result = listLoader(BottersText, online=True, word=True)
    if result is None:
        print("Failed to load the Extra Botters list from " + BottersText + ".")
    else:
        for item in result:
            if item not in BOTTERS:
                BOTTERS.append(item)

# Users denied from using room commands.
IGNORED = []

# Load Youtube commands from file.
YTS = {}
filename = "youtubes.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, parts=3, youtubes=True)
if result is None:
    print("Failed to load the Youtubes list from " + filename + ".")
else:
    YTS = result

# Load more Youtube commands from online file.
ExtraYTS = {}
ExtraYTsText = None
filename = "extrayts.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Extra Youtubes list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    ExtraYTsText = result[0]
    
    result = listLoader(ExtraYTsText, online=True, parts=3, youtubes=True)
    if result is None:
        print("Failed to load the Extra Youtubes list from " + ExtraYTsText + ".")
    else:
        ExtraYTS = result

# Load the Playlists from online.
PLAYLISTS = {}
PlaylistsText = None
filename = "playlists.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Playlists list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    PlaylistsText = result[0]
    # TODO: Put listLoader() instead of call below.

def getPlaylists(PlaylistsText):
    if not PlaylistsText:
        return
    
    try:
        raw = requests.get(PlaylistsText, timeout=15)
        lines = raw.text.encode("ascii", "ignore").splitlines()
    except:
        return
    
    # Reset content, keeping reference.
    PLAYLISTS.clear()
    
    curPL = False
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
            PLAYLISTS[curPL] = []
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
        PLAYLISTS[curPL].append([vid, title, skip])
getPlaylists(PlaylistsText)

# Autobans from file.
AUTOBANS = []
filename = "autoban.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the AUTOBANS list from " + filename + ".")
else:
    AUTOBANS = result

# Load more autobans from online list.
filename = "autobansextra.txt"
AutobansText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Extra Autobans list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    AutobansText = result[0]
    
    result = listLoader(AutobansText, online=True, word=True)
    if result is None:
        print("Failed to load the Extra Autobans list from " + AutobansText + ".")
    else:
        for item in result:
            if item not in AUTOBANS:
                AUTOBANS.append(item)

# Autoforgives from file.
AUTOFORGIVES = []
filename = "autoforgive.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the AUTOFORGIVES list from " + filename + ".")
else:
    AUTOFORGIVES = result

# Load more autoforgives from online list.
filename = "autoforgiveextra.txt"
AutoforgivesText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Extra Autoforgives list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    AutoforgivesText = result[0]
    
    result = listLoader(AutoforgivesText, online=True, word=True)
    if result is None:
        print("Failed to load the Extra Autoforgives list from " + AutoforgivesText + ".")
    else:
        for item in result:
            if item not in AUTOFORGIVES:
                AUTOFORGIVES.append(item)

# Banned accounts.
BANNED_ACCOUNTS = []
filename = "bannedaccounts.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the BANNED ACCOUNTS list from " + filename + ".")
else:
    BANNED_ACCOUNTS = result

# Load more banned accounts from online list.
filename = "bannedaccountsextra.txt"
acctbanText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Extra Banned Accounts list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    acctbanText = result[0]
    
    result = listLoader(acctbanText, online=True, word=True)
    if result is None:
        print("Failed to load the Extra Banned Accounts list from " + acctbanText + ".")
    else:
        for item in result:
            if item not in BANNED_ACCOUNTS:
                BANNED_ACCOUNTS.append(item)

# Banwords from file.
BANWORDS = []
filename = "banwords.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the BANWORDS list from " + filename + ".")
else:
    BANWORDS = result

# Load more banwords from online list.
filename = "banwordsextra.txt"
banwordsText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the Extra Banwords list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    banwordsText = result[0]
    
    result = listLoader(banwordsText, online=True)
    if result is None:
        print("Failed to load the Extra Banwords list from " + banwordsText + ".")
    else:
        for item in result:
            if item not in BANWORDS:
                BANWORDS.append(item)

# Room message commands from file.
ROOM_MESSAGES = {}
filename = "messages.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, parts=2)
if result is None:
    print("Failed to load the ROOM MESSAGES list from " + filename + ".")
else:
    ROOM_MESSAGES = result

# More messages from online page.
filename = "extramessages.txt"
moreMessagesText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the EXTRA ROOM MESSAGES list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    moreMessagesText = result[0]
    
    result = listLoader(moreMessagesText, online=True, parts=2)
    if result is None:
        print("Failed to load the EXTRA ROOM MESSAGES list from " + moreMessagesText + ".")
    else:
        ROOM_MESSAGES.update(result)

# Funny ascii-art room user commands.
ASCII_MESSAGES = {}
filename = "ascii.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, parts=2, unicode=True)
if result is None:
    print("Failed to load the ASCII MESSAGES list from " + filename + ".")
else:
    ASCII_MESSAGES = result

# More ascii-art from online page.
filename = "extraascii.txt"
asciiText = None
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the EXTRA ASCII MESSAGES list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    asciiText = result[0]
    
    result = listLoader(asciiText, online=True, parts=2, unicode=True)
    if result is None:
        print("Failed to load the EXTRA ASCII MESSAGES list from " + asciiText + ".")
    else:
        ASCII_MESSAGES.update(result)

# Password for bot's mod access on PM.
MODPASS = ""
filename = "modpass.txt"
result = listLoader(SETTINGS_DIRECTORY + filename, word=True)
if result is None:
    print("Failed to load the MODPASS from " + filename + ".")
elif len(result) == 0:
    pass
else:
    MODPASS = result[0]

# Load the random response commands from online file.
RANDOM_CMDS = {}
randomsText = None
filename = "randoms.txt"
result = listLoader(SETTINGS_DIRECTORY + filename)
if result is None:
    print("Failed to load the RANDOM COMMANDS list from " + filename + ".")
elif len(result) == 0:
    pass
else:
    randomsText = result[0]
    # TODO: Put listLoader() instead of call below.

def getRandoms(randomsText):
    if not randomsText:
        return
    
    try:
        raw = requests.get(randomsText, timeout=15)
        lines = raw.text.encode("ascii", "ignore").splitlines()
    except:
        return
    
    # Reset content, keeping reference.
    RANDOM_CMDS.clear()
    
    curCmd = False
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
                    RANDOM_CMDS[curCmd] = []
                else:
                    RANDOM_CMDS[word.lower()] = RANDOM_CMDS[curCmd]
            continue
        
        # Add to command.
        RANDOM_CMDS[curCmd].append(line)
getRandoms(randomsText)



# Handle disconnect from spam attack.
def disconnectDefenses(room):
    pass

# All actions to do, after bot in room.
def onJoinsdoneExtended(room):
    # Start the timed automatic user playlist player, on first connection.
    if not PARTY["thread"]:
        PARTY["thread"] = threading.Thread(target=partyModeChecker, args=())
        PARTY["thread"].daemon = True     # Exits when main thread quits.
        PARTY["thread"].start()
    
    # Initialize room's quitlist.
    if not hasattr(room, "quitList"):
        room.quitList = []

# Notice bans, for autoforgive.
def onNoticeBans(room, notice):
    if notice.find(" was banned by ") >= 0:
        target = notice.split(" was banned by ")[0]
        
        # Forgive all mode.
        if CONTROLS["autoforgive"]:
            try:
                room.forgive(room.users[target].id)
            except:
                pass
            return
        
        # Check for user account as well.
        try:
            usr = room._getUser(target)
            acct = usr.accountName
        except:
            acct = None
        
        # Exact nicks or accounts start with *.
        # Wildcard is ?.
        for string in AUTOFORGIVES:
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
            
            if match:
                if acct:
                    room.forgive(usr.id)
                    room._chatlog(usr.nick+" ("+usr.id+
                        ") has been forgiven from AUTOFORGIVES: "+string, True)
                else:
                    try:
                        room.forgive(room.users[target].id)
                        room._chatlog(room.users[target].nick+" ("+room.users[target].id+
                            ") has been forgiven from AUTOFORGIVES: "+string, True)
                    except:
                        pass
                return

# Room spam defenses and greets, and commands.
def onMessageExtended(room, user, msg):
    # Spam defenses for unrecognized users.
    if not user.oper and user.nick not in BOTTERS:
        msgL = msg.lower()
        
        # Auto ban screenshotters and TC link spammers.
        if CONTROLS["banSnapshots"]:
            s = "I just took a video snapshot of this chatroom."
            if s in msg:
                room.ban(user)
                return
        
        # Autoban TC room links.
        find = re.match(r'.*tinychat.com\/\w+($| |\/+ |\/+$).*', msg, re.I)
        if find:
            room.ban(user)
            return
        
        # Unicode banwords.
        try:
            if u"\u25b2\u25b2" in msg or u"\x85\x85" in msg:
                room.ban(user)
                return
        except:
            traceback.print_exc()
        
        # Banwords, by substring.
        for words in BANWORDS:
            # PM only banwords start with @.
            if words[0] == "@":
                continue
            
            words = words.lower()
            
            if words in msgL:
                room.ban(user)
                # Currently, crashes chrome if click on link.
                if words == "%30%30":
                    room.notice("*DO NOT* click on links with %30%30 in them, as it crashes chrome!")
                return
        
        # Auto greet back.
        if CONTROLS["greet"] and hasattr(user, "greet") and not user.greet["greeted"]:
            t = time.time()
            if t - user.greet["lastEvent"] < 60:
                user.greet["greeted"] = 1
                user.greet["lastEvent"] = t
                
                # First greeting.
                opts = {"hi", "hey", "hello", "sup", "howdy"}
                words = msgL.split()
                if any(x in words[0] for x in opts) and len(words) <= 3:
                    # Get random greeting.
                    greetOpts = ["Welcome", "Hi", "Hello", "Hey", "Howdy"]
                    r = random.randint(0, len(greetOpts)-1)
                    # Greet.
                    room.say(greetOpts[r] + " " + user.nick)
    
    # Room commands.
    handleUserCommand(room, user, msg)

# PM defenses and commands.
def onPMExtended(room, user, msg):
    # Spam defenses for unrecognized users.
    if not user.oper and user.nick not in BOTTERS:
        msgL = msg.lower()
        
        # Banwords, by substring.
        for words in BANWORDS:
            # PM only banwords start with @.
            if words[0] != "@":
                continue
            
            # Remove the @.
            words = words[1:]
            
            # Case insensitive.
            words = words.lower()
            
            if words in msgL:
                room.ban(user)
                return
    
    pmCommands(room, user, msg)

# Handle user commands to bot in PM.
def pmCommands(room, user, msg):
    if msg == "help" or msg == CMD+"help":
        room.pm(user.nick, "*Tunebot's Instructions:* "+HELP_LINK)
        return
        sendHelp(room, user)
        return
    
    # Only for commands, from here on.
    if msg[0] != CMD:
        return
    
    msg = msg[1:]   # Remove mark.
    
    # If available, get the string without the command.
    hasArgs = msg.find(" ")
    userArgsStr = ""
    if (hasArgs >= 0):
        userArgsStr = msg[hasArgs+1:]
    
    userArgs = msg.split()          # Split to words.
    
    userCmd = userArgs[0].lower()   # Get the cmd word as lowercase.
    del userArgs[0]                 # Remove the cmd word from args list.
    
    # For ease of use.
    try:
        target = userArgs[0]
    except:
        target = False
    
    # Public commands.
    if userCmd == "mod":
        if not MODPASS:
            return
        
        if target == MODPASS:
            user.oper = True
            room.pm(user, "You are now recognized as a *moderator*!")
            return
    
    # Botter commands.
    if not user.oper and user.nick not in BOTTERS:
        return
    
    # Mod commands.
    if not user.oper:
        return
    
    if userCmd == "bot":
        if tinychat.SETTINGS["BotActive"]:
            tinychat.SETTINGS["BotActive"] = False
            room.pm(user, "Bot is now deactivated!")
        else:
            tinychat.SETTINGS["BotActive"] = True
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
            room.pm(user, "User "+target+" not found...")
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
            if curUser.oper:
                curUser.oper = False
                room.pm(user, target.title() + " is *not* recognized as a moderator, anymore.")
            else:
                curUser.oper = True
                room.pm(user, target.title() + " is now recognized as a *moderator*!")
        return
    
    # Shut bot down.
    if userCmd in {"close", "restart", "reconnect", "reset"}:
        room.disconnect()
        tinychat.SETTINGS["Run"] = False
        return
    
    # Ban a user. Mods included.
    if userCmd == "ban":
        if not target:
            room.pm(user, "Give me a nickname to ban...")
            return
        room.ban(target, True)
        return
    
    # Forgive a user.
    if userCmd == "forgive":
        if not target:
            room.pm(user, "Give me a nickname to forgive...")
            return
        room.forgiveNick(target)
    
    # Ignore room commands from a user, any user.
    if userCmd == "ignore":
        if not target:
            room.pm(user, "Give me a nickname to ignore...")
            return
        
        string = target.lower()
        
        # Toggle ignoring.
        try:
            IGNORED.remove(string)
            room.pm(user, string+" has been removed from the ignore list.")
        except:
            IGNORED.append(string)
            room.pm(user, string+" has been added to the ignore list!")
    
    if userCmd == "who":
        if not target:
            room.pm(user, "Give me a nickname to inspect...")
            return
        
        who = room._getUser(target)
        if not who:
            room.pm(user, "Failed to find user "+target+"...")
            return
        
        if who.accountName:
            room.pm(user, "User "+target+" is logged in as "+who.accountName+".")
        else:
            room.pm(user, "User "+target+" is not logged in.")

# Find and execute the first matching user command, from public to oper.
def handleUserCommand(room, user, msg):
    # Ignore surrounding spaces.
    msg = msg.strip()
    
    # Nothing to do, on empty message.
    if not msg:
        return
    
    # Ignore all commands, other than reset cmd, if deactivated!
    if not tinychat.SETTINGS["BotActive"] and msg[:4] != CMD+"bot":
        return
    
    # Ignore nick from list.
    if user.nick.lower() in IGNORED:
        return
    
    # All commands start with an exclamation mark.
    if msg[0] != CMD:
        return
    
    userArgs = msg.split()              # Split to words.
    
    userCmd = userArgs.pop(0).lower()   # Get the cmd word as lowercase, and remove from args.
    userCmd = userCmd[1:]               # Remove mark.
    
    # Empty command.
    if not userCmd:
        return
    
    # Get args as string. Empty string if none.
    userArgsStr = " ".join(userArgs)
    
    # For ease of use.
    try:
        target = userArgs[0]
    except:
        target = None
    
    # Public commands.
    publicCommands(room, userCmd, userArgsStr, userArgs, target, user)
    
    # Botters and Opers.
    if not user.oper and user.nick not in BOTTERS:
        return
    
    botterCommands(room, userCmd, userArgsStr, userArgs, target, user)
    
    # Opers only.
    if not user.oper:
        return
    
    operCommands(room, userCmd, userArgsStr, userArgs, target, user)

# Add a YT/SC track to PARTY[] queue at position,
# Or default to LAST, and activate party mode.
# Sends a notice() to room about queuing.
def queueTrack(room, track, position=None, title="", skip=0):
    if position is None:
        PARTY["list"].append([track, skip])
        position = len(PARTY["list"])
    else:
        # Verify given position. Default to LAST.
        try:
            position = int(position)
            if position < 0:
                position = len(PARTY["list"])
        except:
            position = len(PARTY["list"])
        
        PARTY["list"].insert(position, [track, skip])
        # Change back from index to track number.
        position += 1
    
    # Optional title.
    if not title: title = "Track"
    else: title = "*"+title+"*"
    
    room.notice(title+" added to autoplaylist at position #"+str(position)+".")
    # Activate, if first item added.
    if len(PARTY["list"]) == 1:
        PARTY["mode"] = True

# Room commands available to everyone.
def publicCommands(room, userCmd, userArgsStr, userArgs, target, user):
    # Get bot to PM you with noob tip.
    if userCmd == "help":
        room.notice("*Tunebot's Instructions:* "+HELP_LINK)
        return
        
        if not target:
            sendHelp(room, user)
            return
        
        # Only moderators can send help to others.
        if not user.oper and user.nick not in BOTTERS: 
            room.notice("Only *botters* can send *!help* to other users...")
            return
        
        # PM the target nick.
        targetUser = room._getUser(target)
        
        if not targetUser:
            room.notice("User "+target+" was not found...")
            return
        
        sendHelp(room, targetUser)
        return
    
    # Sends a response message, from file.
    for key, val in ROOM_MESSAGES.items():
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
                room._chatlog("Failed to execute from ROOM_MESSAGES!")
                return
    
    # UTF-16 Unicode! Sends an ASCII response message, from file.
    try:
        for key, val in ASCII_MESSAGES.items():
            if u""+userCmd == u""+key:
                msg = u""+val
                
                room.notice(msg)
                return
    except:
        room._chatlog(u"Failed to execute from ASCII_MESSAGES!")
        traceback.print_exc()
        return
    
    # Random response from list commands.
    for key, val in RANDOM_CMDS.items():
        if userCmd == key:
            r = random.randint(0, len(val))
            msg = val[r]
            
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
        if not user.oper and user.nick not in BOTTERS:
            room.notice("You ain't a botter, " + user.nick + "... Suck my dick.")
            return
        
        if not target:
            if user.oper:
                room.notice("You are my glorious master, " + user.nick + "!")
            else:
                room.notice("I obey your commands, " + user.nick + ".")
        else:
            if target in BOTTERS:
                BOTTERS.remove(target)
                room.notice(target + " has been remove from the botters list. Fuck them.")
            else:
                BOTTERS.append(target)
                room.notice(target + " has been added to the botters list. I obey.")
        return
    
    if userCmd == "random":
        r = random.randint(1, 100)
        room.notice(str(r))
        return

# Room commands available only to botters and opers.
def botterCommands(room, userCmd, userArgsStr, userArgs, target, user):
    # Optional queuing or skip for YTs.
    q = False
    skip = 0
    try:
        if userArgs[0] == "!":
            q = True
        else:
            skip = int(userArgs[0])
    except:
        pass
    
    # From file.
    try:
        if not skip:
            skip = YTS[userCmd][1]
        if q:
            queueTrack(room, YTS[userCmd][0], skip=skip)
        else:
            room.startYT(YTS[userCmd][0], skip)
        return
    except:
        pass
    
    # From online.
    try:
        if not skip:
            skip = ExtraYTS[userCmd][1]
        if q:
            queueTrack(room, ExtraYTS[userCmd][0], skip=skip)
        else:
            room.startYT(ExtraYTS[userCmd][0], skip)
        return
    except:
        pass
    
    # Close cam by nickname.
    if userCmd == "uncam":
        if not target:
            room.say("Give me a nickname to close...")
            return
        
        room.uncam(target)
        return
    
    # YT controls.
    if userCmd in {"yt", "youtube"}:
        if not target:
            room.notice("Give me a Youtube link, like: "+
                CMD+"yt www.youtube.com/watch?v=ZRCtkvlGjzo")
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
                    room.notice("I have only played "+str(l)+" videos...")
                    return
                # Play counting from the end (most recent).
                target = tinychat.YTqueue["history"][-v]
            except:
                pass
        
        # Try to play.
        res = room.startYT(target, skip)
        
        # On failure.
        if res is not True:
            if not res:
                room.notice("Give me a Youtube link, like: "+
                    CMD+"yt www.youtube.com/watch?v=ZRCtkvlGjzo")
            else:
                room.notice(res)
            return
        # Success.
        user.playedOnce = True
        return
    
    if userCmd == "close":
        if target:
            room.notice("Did you mean to use the !uncam command?")
            return
        room.closeYT()
        return
    
    if userCmd in {"pause", "stop"}:
        room.pauseYT()
        return
    
    if userCmd in {"resume"}:
        if target:
            room.notice("Did you mean to use the "+CMD+"yt command to play a video?")
            return
        room.resumeYT()
        return
    
    if userCmd == "skip":
        if not target:
            room.notice("Give me a time to skip in *seconds*, or like: *"+CMD+"skip 1h2m3s*...")
            return
        res = room.skipYT(target)
        if res is False:
            room.notice("Give me a time to skip in *seconds*, or like: *"+CMD+"skip 1h2m3s*...")
        return
    
    # SC controls.
    if userCmd in {"sc", "soundcloud"}:
        if not target:
            room.notice("Give me a SoundCloud link, like: "+
                CMD+"sc https://soundcloud.com/dumbdog-studios/senor-chang-gay-saying-ha-gay")
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
                        room.notice("I have only played "+str(l)+" tracks...")
                        return
                    # Play counting from the end (most recent).
                    target = tinychat.SCqueue["history"][-v]
            except:
                pass
        
        # Try to play.
        res = room.startSC(target, skip)
        
        if res is not True:
            if not res:
                room.notice("Give me a SoundCloud link, like: "+
                    CMD+"sc https://soundcloud.com/dumbdog-studios/senor-chang-gay-saying-ha-gay")
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
            room.notice("Did you mean to use the "+CMD+"sc command to play a song?")
            return
        room.resumeSC()
        return
    
    if userCmd == "sskip":
        if not target:
            room.notice("Give me a time to skip in *seconds*, or like: *"+CMD+"skip 1h2m3s*...")
            return
        res = room.skipSC(target)
        if res is False:
            room.notice("Give me a time to skip in *seconds*, or like: *"+CMD+"skip 1h2m3s*...")
        return
    
    # Either display all playlists, or list tracks in a single playlist.
    if userCmd == "pls" or userCmd == "playlists":
        if not target:
            pls = ""
            for pl in PLAYLISTS.keys():
                pls += "*" + pl.title() + "*, "
            room.notice("These playlists are available: " + pls)
        else:
            try:
                pl = PLAYLISTS[target.lower()]
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
            room.notice("Give me a playlist name to play... Use *"+CMD+"pls* to see a full listing...")
            return
        
        target = target.lower()
        
        # Validate playlist exists.
        try:
            pl = PLAYLISTS[target]
        except:
            room.notice("The *"+target.title()+"* playlist does not exist...")
            return
        
        # Play selected song immediately.
        if len(userArgs) == 3 and userArgs[2] == "!":
            track = userArgs[1]
            # Validate as number.
            try:
                track = int(track)-1
            except:
                room.notice("Give me a track number to play, like: "+CMD+"pl # !")
                return
            
            # Try to play the track.
            try:
                vid = pl[track][0]
                skip = pl[track][2]
                room.startYT(vid, skip)
            except:
                room.say("Track #" + str(track) + " does not exist..." + 
                        " Playlist " + target.title() + " has " + str(len(pl)) + " tracks...")
            return
        
        # Play random song immediately.
        if len(userArgs) == 1:
            track = random.randint(0, len(pl)-1)
            vid = pl[track][0]
            # Avoid selecting recently played videos.
            maxCheck = 10
            # Don't go into infinite loop.
            if maxCheck >= len(pl): maxCheck = len(pl)-1
            
            YTid = tinychat.getYTid(vid)
            SCid = tinychat.getSCid(vid)
            
            while YTid in tinychat.YTqueue["history"][-maxCheck:] or \
                    SCid in tinychat.SCqueue["history"][-maxCheck:]:
                track = random.randint(0, len(pl)-1)
                vid = pl[track][0]
                YTid = tinychat.getYTid(vid)
                SCid = tinychat.getSCid(vid)
            
            room.notice("Track #"+str(track+1)+" has been selected...")
            skip = pl[track][2]
            room.startYT(vid, skip)
            return
        
        # Queue by track number, or queue entire playlist.
        if len(userArgs) == 2:
            # Queue entire playlist.
            if userArgs[1] in {"*"}:
                # Override autoplaylist.
                del PARTY["list"][:]
                # Add all tracks to automatic player.
                for item in pl:
                    vid = item[0]
                    skip = item[2]
                    PARTY["list"].append([vid, skip])
                PARTY["mode"] = True
                room.notice("*"+target.title()+"* playlist is now set to autoplay at "+str(len(pl))+" tracks...")
                return
            
            # Play by track number.
            track = userArgs[1]
            # Validate as number.
            try:
                track = int(track)-1
            except:
                room.say("Give me a track number to play, or let me choose randomly...")
                return
            
            # Add to queue.
            try:
                vid = pl[track][0]
                skip = pl[track][2]
                queueTrack(room, vid, skip=skip)
            except:
                room.say("Track #" + str(track) + " does not exist..." + 
                        " Playlist " + target.title() + " has " + str(len(pl)) + " tracks...")
            return
    
    # Handle the autoplaylist - play YT/SC automatically.
    if userCmd in {"party", "py", "yp", "queue", "que", "q", "play"}:
        # Display state and instructions.
        if not target or target == "?":
            # State.
            if not PARTY["list"]:
                room.notice("The autoplaylist is *empty*.")
            else:
                if PARTY["mode"]: mode = "ON"
                else: mode = "OFF"
                
                if len(PARTY["list"]) == 1:
                    room.notice("There is 1 track in the autoplaylist, and party mode is *"+mode+".*")
                else:
                    room.notice("There are "+str(len(PARTY["list"]))+
                        " tracks in the autoplaylist, and party mode is *"+mode+".*")
            
            # Instructions.
            # if not target:
            #     room.notice("To play a song, do like: !q https://youtu.be/NAj26rVWK14")
            return
        
        # Toggle mode.
        if target == "!":
            if PARTY["mode"]:
                PARTY["mode"] = False
                room.notice("Party mode is now *OFF.*")
            else:
                if not PARTY["list"]:
                    room.notice("The autoplaylist is *empty*.")
                else:
                    room.notice("Party mode is now *ON,* and has "+str(len(PARTY["list"]))+" tracks queued.")
                    PARTY["mode"] = True
            return
        
        # Clear out.
        if target == "!*":
            if not PARTY["list"]:
                room.notice("The autoplaylist is already *empty*.")
            else:
                count = str(len(PARTY["list"]))
                
                if count > 1: s = "s"
                else: s = ""
                
                del PARTY["list"][:]
                PARTY["mode"] = False
                room.notice(count+" track"+s+" removed. The autoplaylist is now *empty*.")
            return
        
        # Remove a track from queue by index.
        if target[0] == "!":
            # Nothing to remove with empty playlist.
            l = len(PARTY["list"])
            if l == 0:
                room.notice("No tracks to remove. The autoplaylist is already *empty*.")
                return
            
            try:
                num = int(target[1:])-1     # To index.
            except:
                # Can accept some words.
                if target[1:] in {"last", "end"}:
                    num = l-1   # To index.
                elif target[1:] in {"next", "first"}:
                    num = 0
                else:
                    room.notice("To remove a track from the autoplaylist, "+
                        "do like: "+CMD+"q !1 or "+CMD+"q !last")
                    return
            
            # Verify.
            if num < 0:
                room.notice("The track number to remove must be 1 or greater.")
                return
            
            # Track number larger than playlist size.
            if num >= l:
                if l == 1:
                    s = ""
                else:
                    s = "s"
                room.notice("The autoplaylist only has "+str(l)+" track"+s+" in it.")
                return
            
            # Remove it.
            del PARTY["list"][num]
            room.notice("Removed track #"+str(num+1)+" from the autoplaylist.")
            return
        
        # Make a list from a SoundCloud collection page.
        # https://developers.soundcloud.com/docs/api/reference#users
        if "soundcloud.com/" in target:
            # Grab relative path.
            try:
                rel = target.split("soundcloud.com/")[1]
            except:
                room.notice("Give me a SoundCloud link to track or collection, "+
                "like "+CMD+"party https://soundcloud.com/axiommy/tracks")
                return
            
            parts = rel.split("/")
            # Only got username in link. Default to tracks.
            if len(parts) == 1:
                parts.append("tracks")
            # Empty part.
            if parts[1] == "":
                parts[1] = "tracks"
            # A specific playlist/set.
            if len(parts) == 3:
                pl = parts[2]
            else:
                pl = ""
            # Username and page type.
            username = parts[0]
            collection = parts[1]   # {"tracks", "sets", "likes", "reposts"}
            
            # Must be a collection type. Otherwise, add as single track.
            if collection in {"tracks", "sets", "reposts", "likes"}:
                # q word anywhere.
                # skip and then limit, in this order.
                skip    = None
                limit   = None
                q       = None
                for arg in userArgs[1:]:
                    try:
                        j = int(arg)
                        if skip is None:
                            skip = j
                        else:
                            limit = j
                    except:
                        q = arg
                
                tracks = getCollectionSC(username, collection, pl, limit, skip)
                
                # Failure, or empty list.
                if type(tracks) is str:
                    room.notice(tracks)
                    return
                
                # Position in queue.
                if q in {"next", "first", "start"}:
                    pos = "next"
                elif q in {"last", "end"}:
                    pos = "last"
                else:
                    pos = None
                
                # Optional queue in position.
                if pos == "next":
                    PARTY["list"] = tracks + PARTY["list"]
                    infomsg = "Added "+str(len(tracks))+" tracks to autoplaylist at start of queue."
                elif pos == "last":
                    if not PARTY["list"]:
                        count = "1"
                    else:
                        count = str(len(PARTY["list"]))
                    PARTY["list"] += tracks
                    infomsg = "Added "+str(len(tracks))+" tracks to autoplaylist at end of queue position #"+count+"."
                else:
                    PARTY["list"] = tracks
                    infomsg = "SoundCloud collection is now set to autoplay at "+str(len(tracks))+" tracks."
                
                # And finish.
                PARTY["mode"] = True
                room.notice(infomsg)
                return
        
        #Make a list from a Youtube user channel videos.
        if "youtube.com/" in target and not tinychat.getYTid(target):
            # Test link validity.
            try:
                rel = target.split("youtube.com/")[1]
                # Either playlist, or user's channel.
                if "playlist?" in rel:
                    collection = rel.split("list=")[1]
                    colType = "playlist"
                else:
                    collection = rel.split("/")[1]
                    colType = "channel"
            except:
                room.notice("Give me a Youtube link to a user's channel or playlist, "+
                    "like "+CMD+"party https://www.youtube.com/user/RHCPtv/")
                return
            
            # q word anywhere.
            # skip and then limit, in this order.
            skip    = None
            limit   = None
            q       = None
            for arg in userArgs[1:]:
                try:
                    j = int(arg)
                    if skip is None:
                        skip = j
                    else:
                        limit = j
                except:
                    q = arg
            
            videos = getCollectionYT(collection, colType, limit, skip)
            
            # Failure, or empty list.
            if type(videos) is str:
                room.notice(videos)
                return
            
            # Position in queue.
            if q in {"next", "first", "start"}:
                pos = "next"
            elif q in {"last", "end"}:
                pos = "last"
            else:
                pos = None
            
            # Optional queue in position.
            if pos == "next":
                PARTY["list"] = videos + PARTY["list"]
                infomsg = "Added "+str(len(videos))+" videos to autoplaylist at start of queue."
            elif pos == "last":
                if not PARTY["list"]:
                    count = "1"
                else:
                    count = str(len(PARTY["list"]))
                PARTY["list"] += videos
                infomsg = "Added "+str(len(videos))+" videos to autoplaylist at end of queue position #"+count+"."
            else:
                PARTY["list"] = videos
                infomsg = "Youtube "+colType+" is now set to autoplay at "+str(len(videos))+" videos."
            
            # And finish.
            PARTY["mode"] = True
            room.notice(infomsg)
            return
        
        # Add one track to autoplaylist.
        try:
            # Position in queue by word.
            if userArgs[1].lower() in {"next", "first"}:
                pos = 0
            else:
                if userArgs[2].lower() in {"next", "first"}:
                    pos = 0
                else:
                    raise Exception()
        except:
            pos = len(PARTY["list"])
        
        # Skip in seconds.
        try:
            try:
                skip = int(userArgs[1])
            except:
                skip = int(userArgs[2])
        except:
            skip = 0
        
        queueTrack(room, target, pos, skip=skip)
        return
    
    # Toggle greeting back of expected messages.
    if userCmd == "greetback":
        if CONTROLS["greet"]:
            CONTROLS["greet"] = False
            room.notice("Auto greeting back is now *OFF.*")
        else:
            CONTROLS["greet"] = True
            room.notice("Auto greeting back is now *ON.*")
        return
    
    # Plays first YT result from search.
    if userCmd == "lucky":
        # Requires an API key.
        if not tinychat.YTkey:
            return
        
        if not target:
            room.notice("Give me a query to search for in Youtube...")
            return
        
        m = 10  # Max results.
        
        # Queue by default.
        if userArgs[-1] == "!":
            userArgsStr = " ".join(userArgs[:-1])
            q = False
            # Don't overplay within a time limit.
            if isOverplaying(5):
                return
        elif userArgs[-1] in {"next", "first", "start"}:
            q = True
            pos = 0
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
            # https://developers.google.com/youtube/v3/docs/search/list
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': 1
            }
            
            raw = requests.get("https://www.googleapis.com/youtube/v3/search?"+
                "maxResults="+str(m)+"&part=snippet,id&key="+tinychat.YTkey+
                "&type=video&safeSearch=none&q="+
                quote_plus(userArgsStr.encode("utf-8"), safe=''),
                headers=header,
                timeout=15)
            obj = raw.json()
            
            # Optional title.
            try:
                title = obj["items"][n]["snippet"]["title"]
            except:
                title = ""
            
            try:
                vid = str(obj["items"][n]["id"]["videoId"])
            except:
                room.notice("Failed to get any videos from Youtube...")
                return
        except:
            traceback.print_exc()
            return
        
        if q:
            # Add to queue.
            queueTrack(room, vid, title=title, position=pos)
        else:
            # Play.
            room.startYT(vid)
        return
    
    # Plays first SC result from search.
    if userCmd == "slucky":
        # Requires an API key.
        if not tinychat.SCkey:
            return
        
        if not target:
            room.notice("Give me a query to search for in SoundCloud...")
            return
        
        m = 10  # Max results.
        
        # Queue by default. Removes it from string.
        if userArgs[-1] == "!":
            userArgsStr = " ".join(userArgs[:-1])
            q = False
            # Don't overplay within a time limit.
            if isOverplaying(5):
                return
        elif userArgs[-1] in {"next", "first", "start"}:
            q = True
            pos = 0
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
            raw = requests.get("https://api.soundcloud.com/tracks?client_id="+
                tinychat.SCkey+"&limit="+str(m)+"&q="+
                quote_plus(userArgsStr.encode("utf-8"), safe=''),
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
            queueTrack(room, trackID, title=title, position=pos)
        else:
            # Play.
            room.startSC(trackID)
        return
    
    if userCmd == "cam":
        # Self.
        if not target:
            res = approveCam(room, user)
            if type(res) is str: room.notice(res)
            return
        
        # Another.
        res = approveCam(room, target)
        if type(res) is str: room.notice(res)
    
    if userCmd == "uptime":
        string = formatUptime()
        room.notice("I have been alive for *"+string+".*")
        return
    
    # Closes currently playing YT and SC,
    # And plays the next queued item.
    if userCmd == "next":
        # Only for active filled autoplaylist.
        if not PARTY["list"] or not PARTY["mode"]:
            return
        
        # Close current, if any playing.
        if tinychat.getTimeYT():
            room.closeYT()
        if tinychat.getTimeSC():
            room.closeSC()
        
        # TODO: Play next one immediately.
        # ...
        return
    
# Room commands available only to opers.
def operCommands(room, userCmd, userArgsStr, userArgs, target, user):
    if userCmd == "ban":
        if not target:
            room.say("Give me a nickname to ban...")
            return
        
        if target in BOTTERS:
            room.notice("I do not ban botters...")
            return
        
        res = room.ban(target)
        
        if res is False:
            room.notice(target + " was not found in the userlist...")
        elif res is not True:
            room.notice(res)
        return
    
    # Ban all users by substring.
    if userCmd in {"banall", "banthese"}:
        if not target:
            room.say("Give me a part of a nickname, to ban all matching users...")
            return
        
        for nick, user in room.users.items():
            # Don't ban Botters.
            if nick in BOTTERS: continue
            
            if target in nick:
                room.ban(user)
        return
    
    # Bans and forgives.
    if userCmd == "kick":
        if not target:
            room.say("Give me a nickname to kick...")
            return
        
        who = room._getUser(target)
        
        if not who:
            room.notice(target + " was not found in the userlist...")
            return
        
        if who.nick in BOTTERS:
            room.notice("I do not ban botters...")
            return
        
        userID = who.id # Remember the ID for the forgive.
        
        res = room.ban(who)
        
        if res is not True:
            if not res:
                room.notice(target + " was not found in the userlist...")
            else:
                room.notice(res)
        else:
            room.forgive(userID)
            room.notice(target + " has been banned and forgiven.")
        return
    
    if userCmd in {"kickall", "kickthese"}:
        if not target:
            room.say("Give me a part of a nickname, to kick all matching users...")
            return
        
        for nick, user in room.users.items():
            # Don't ban Botters.
            if nick in BOTTERS: continue
            
            if target in nick:
                userID = user.id
                room.ban(user)
                room.forgive(userID)
        return
    
    if userCmd == "forgive":
        if not target:
            room.say("Give me an exact nickname to forgive...")
            return
        
        room.forgiveNick(target)        # Case-sensitive.
        room.getBanlist()               # Update banlist.
        room.notice("*" + target + "* will be forgiven, momentarily...")
        return
    
    # Forgives all users in room.banlist, or by substring.
    if userCmd == "forgiveall":
        if not target:
            room.say("Give me a partial string to forgive all matching nicknames, " +
                        "or ! to forgive all users...")
        elif target == "!":
            room.forgiveNick(True)
            room.getBanlist()               # Update banlist.
            room.notice("*All users* in the banlist will be forgiven, momentarily...")
        else:
            room.forgiveNick(target, True)  # Case-sensitive.
            room.getBanlist()               # Update banlist.
            room.notice("All users with *"+target+"* in their nicks will be forgiven, momentarily...")
        return
    
    # Toggle substring in AUTOFORGIVES.
    # Exact nicks start with *, otherwise partial string match.
    # Wildcards are ?.
    if userCmd == "autoforgive":
        if not target:
            # room.pm(user, "Autoforgives: *" + "*, *".join(AUTOFORGIVES) + "*.")
            return
        
        # Clear list.
        if target == "!!":
            del AUTOFORGIVES[:]
            room.notice("The autoforgives list is now *empty*.")
            return
        
        # WARNING: Forgives all bans! For extreme measures only.
        if target == "!":
            if CONTROLS['autoforgive']:
                CONTROLS['autoforgive'] = False
                room.notice("*Autoforgive mode is now OFF.* All users may be banned.")
            else:
                CONTROLS['autoforgive'] = True
                room.notice("*Autoforgive mode is now ON!* All users who get banned will be forgiven!")
            return
        
        # Prevent excessive autoforgives, if not exact nick.
        if target[0] != "*":
            if len(target) <= 3:
                room.notice("Give me a partial nick longer than 3 characters...")
                return
        
        # Don't allow certain strings.
        l = "newuser"
        for word in l:
            if target in word:
                return
        
        # Toggle from list.
        if target not in AUTOFORGIVES:
            AUTOFORGIVES.append(target)
            room.notice(target + " has been added to the autoforgives.")
        else:
            AUTOFORGIVES.remove(target)
            room.notice(target + " has been removed from the autoforgives.")
        return
    
    # Toggle substring in AUTOBANS.
    # Exact nicks start with *, otherwise partial string match.
    # Wildcards are ?.
    if userCmd == "autoban":
        if not target:
            # room.pm(user, "Autobans: *" + "*, *".join(AUTOBANS) + "*.")
            return
        
        # Clear list.
        if target == "!!":
            del AUTOBANS[:]
            room.notice("The autobans list is now *empty*.")
            return
        
        # WARNING: Bans all joins! For extreme measures only.
        if target == "!":
            if CONTROLS['autoban']:
                CONTROLS['autoban'] = False
                room.notice("*Autoban mode is now OFF.* All users may join the room.")
            else:
                CONTROLS['autoban'] = True
                room.notice("*Autoban mode is now ON!* All users who join the room will be banned!")
            return
        
        # Prevent excessive autobans, if not exact nick.
        if target[0] != "*":
            if len(target) <= 3:
                room.notice("Give me a partial nick longer than 3 characters...")
                return
        
        # Don't allow certain strings.
        l = "newuser"
        for word in l:
            if target in word:
                return
        
        # Toggle from list.
        if target not in AUTOBANS:
            AUTOBANS.append(target)
            room.notice(target + " has been added to the autobans.")
        else:
            AUTOBANS.remove(target)
            room.notice(target + " has been removed from the autobans.")
        return
    
    if userCmd == "botters":
        room.notice(user, "Botters: *" + "*, *".join(BOTTERS) + "*.")
    
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
        if string == "!":
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
        if string == "!":
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
        if not target:
            room.notice("Banwords: *" + "*, *".join(BANWORDS) + "*.")
            return
        
        string = userArgsStr.lower()
        
        # Clear list.
        if string == "!":
            del BANWORDS[:]
            room.notice("The banwords list is now *empty*.")
            return
        
        # Prevent excessive banwords.
        if len(string) <= 3:
            room.notice("Give me a word longer than 3 characters...")
            return
        
        if string in BANWORDS:
            BANWORDS.remove(string)
            room.notice("*"+string+"* has been removed from the banwords list.")
        else:
            BANWORDS.append(string)
            room.notice("*"+string + "* has been added to the banwords list.")
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
        
        if curUser.oper:
            curUser.oper = False
            room.notice(target + " is *not* recognized as a moderator, anymore.")
        else:
            curUser.oper = True
            room.notice(target + " is now recognized as a *moderator*!")
    
    # Toggle an account name to be automatically banned.
    if userCmd == "banaccount":
        if not target:
            room.notice("Banned Accounts: *" + "*, *".join(BANNED_ACCOUNTS) + "*.")
            return
        
        if target in BANNED_ACCOUNTS:
            BANNED_ACCOUNTS.remove(target)
            room.notice(target + " account has been removed from the autobans.")
        else:
            BANNED_ACCOUNTS.append(target)
            room.notice(target + " account has been added to the autobans.")
        return
    
    # Rename the bot.
    if userCmd in {"rename", "nick"}:
        if not target:
            return
        res = room.setNick(target)
        
        if type(res) in {str, unicode}:
            room.notice(res)
        return
    
    # Close all cams.
    if userCmd == "uncamall":
        for nick, user in room.users.items():
            if user.broadcasting:
                uncam(nick)
        return
    
    # Toggle bot's listening to room commands.
    if userCmd == "bot":
        if tinychat.SETTINGS["BotActive"]:
            tinychat.SETTINGS["BotActive"] = False
            room.notice("Bot is now deactivated!")
        else:
            tinychat.SETTINGS["BotActive"] = True
            room.notice("Bot is now active.")
        return
    
    # Kill the bot.
    if userCmd == "killbot":
        room.disconnect()
        tinychat.SETTINGS["Run"] = False
        return
    
    # Reconnect.
    if userCmd == "reconnect":
        # room.reconnect()
        return
    
    # Print empty lines to clear the chatbox.
    if userCmd in {"empty", "clean", "clear"}:
        try:
            if room.user.oper:
                room.notice("\n\n\n\n\n\n\n\n\n\n -- Chat Cleared Aye Sir! ^_^ -- ")
            else:
                text = "133,133,133,133,133,133,133,133,133,133"+ \
                    room._encodeMessage("  -- Chat Cleared Aye Sir! ^_^ -- ")
                room._sendCommand("privmsg", [text, room.color+",en"])
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
            CONTROLS["banPhones"]["android"]    = True
            CONTROLS["banPhones"]["iphone"]     = True
            room.notice("All *phone* users will now be *banned on broadcast*!")
        else:
            CONTROLS["banPhones"]["android"]    = False
            CONTROLS["banPhones"]["iphone"]     = False
            room.notice("All *phone* users can now broadcast.")
        return
    
    # Display or set room topic.
    if userCmd == "topic":
        if not target:
            room.notice("*Topic is:* " + room.topic)
            return
        
        room.setTopic(userArgsStr)
        room.notice("*Topic is now:* " + userArgsStr)

# Extended join handling.
def onJoinHandle(room, user):
    # Ban all mode.
    if CONTROLS['autoban']:
        if not user.oper and user.nick not in BOTTERS:
            room.ban(user)
    
    # Autogreetings.
    user.greet = {}
    user.greet["lastEvent"] = time.time()
    user.greet["greeted"] = 0

# Remember who left.
def onQuitList(room, nick):
    pass

# Autobans, by substring, or nickchange spammers.
def onNickChangeAutoban(room, user, new, old):
    # Don't overban.
    try:
        if user.banned == 2:
            return
    except:
        user.banned = 0;
    
    # Except mods and botters.
    if user.oper or user.nick in BOTTERS:
        return
    
    # Ban newusers.
    if CONTROLS["banNewusers"] and new.find("newuser") == 0:
        room.ban(user)
        user.banned += 1
    
    # Ban fake guests.
    if CONTROLS["banGuests"] and new.find("guest") == 0:
        room.ban(user)
        user.banned += 1
    
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
            room._chatlog(user.nick+" ("+user.id+") has been banned for nick spamming.", True)
            user.banned += 1
        user.nickSpam[0] = 1
        user.nickSpam[1] = t
    
    # Exact nickbans start with *.
    # Wildcard is ?.
    for string in AUTOBANS:
        exact = False
        # Exact matching.
        if string[0] == "*":
            string  = string[1:]
            exact   = True
        
        match = isMatch(string, new, exact=exact)
        
        if match:
            room.ban(user)
            room._chatlog(user.nick+" ("+user.id+") has been banned from AUTOBANS: "+string, True)
            user.banned += 1
            return

# Autobanned accounts.
def onUserinfoReceivedExtended(room, user, account):
    if account in BANNED_ACCOUNTS:
        room.ban(user)

# Forgive from autoforgives.
def onBanlistAutoforgives(room):
    if AUTOFORGIVES:
        for user in room.banlist:
            userID = user[0]
            userNick = user[1]
            
            for nick in AUTOFORGIVES:
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
    if user.oper or user.nick in BOTTERS:
        return
    
    # Auto ban phone users.
    if user.device:
        # Android.
        if CONTROLS["banPhones"]["android"] and user.device == "android":
            room.ban(user)
            user.banned += 1
            return
        # iPhone.
        if CONTROLS["banPhones"]["iphone"] and user.device == "ios":
            room.ban(user)
            user.banned += 1
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
        return
    
    # Auto cam ban by nick.
    if type(CONTROLS["camban"]) is list:
        for name in CONTROLS["camban"]:
            if name.lower() in user.nick.lower():
                room.ban(user)
                user.banned += 1
                room._chatlog(user.nick+" ("+user.id+") has been banned from CAMBANS.", True)
                return
    
    # Cam counter and intelligent camspam blocker.
    t = int(time.time())
    
    try:
        user.camSpam[0] += 1
    except:
        # Initialize counter.
        user.camSpam = [1, t]
    
    # Ban & mark spammer and reset counts.
    if user.camSpam[0] == 2:
        if t - user.camSpam[1] < 9:
            room.ban(user)
            room._chatlog(user.nick+" ("+user.id+") has been banned for (2) cam spamming.", True)
            user.banned += 1
    
    if user.camSpam[0] == 3:
        if t - user.camSpam[1] < 40:
            room.ban(user)
            room._chatlog(user.nick+" ("+user.id+") has been banned for (3) cam spamming.", True)
            user.banned += 1
        # Reset count, in either case.
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
            start = string.find(tag, start+1)
            continue
        # Remove from string.
        string = string[0:start] + string[end+1:]
        # Find next.
        start = string.find(tag)
    
    return string

# Return an HTML escaped string. Doesn't do whitespaces!
# Not for URLs, only for HTML code.
def escape(string):
    """Returns the given HTML with ampersands, quotes and carets encoded."""
    return (string.replace('&', '&amp;').replace('<', '&lt;')
        .replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;'))

# After a delay, plays the next item in the PARTY["list"].
def partyModeChecker():
    while True:
        time.sleep(5)
        
        if not PARTY["mode"]: continue
        
        try:    room = tinychat.ROOMS[0]
        except: continue
        
        if not room.connected: continue
        
        # If nothing is currently playing.
        if not tinychat.getTimeYT() and not tinychat.getTimeSC():
            if not PARTY["list"]:
                PARTY["mode"] = False
                continue
            
            # Each item in list can be an ID,
            # or an array with more options.
            item = PARTY["list"].pop(0)
            
            if type(item) is list:
                vid = item[0]
                
                # Optional skip.
                try:
                    skip = int(item[1])
                except:
                    skip = 0
            else:
                vid = item
                skip = 0
            
            # Play next. Skips invalids.
            room.startYT(vid, skip)
            time.sleep(10)      # Extra time to catch up.

# Return tracks list from a reposts page,
# Or error message.
def getRepostsSC(username, limit):
    url = "https://api.soundcloud.com/users/"+username+"?client_id="+tinychat.SCkey
    
    try:
        raw = requests.get(url, timeout=15)
        obj = raw.json()
    except:
        return "Failed to get a response from SoundCloud.com..."
    
    try:
        userID = str(obj["id"])
    except:
        traceback.print_exc()
        return "Failed to get user ID from SoundCloud API..."
    
    url = "https://api-v2.soundcloud.com/profile/soundcloud:users:"+userID+ \
        "?limit="+str(limit)
    
    try:
        raw = requests.get(url, timeout=15)
        obj = raw.json()
    except:
        return "Failed to get a response from SoundCloud.com..."
    
    tracks = []
    
    try:
        # Get all tracks and add to list.
        for item in obj["collection"]:
            # Only get tracks.
            if item["type"] != "track-repost" or item["track"]["kind"] != "track":
                continue
            
            track = str(item["track"]["id"])
            # No duplicates in list.
            if track not in tracks:
                tracks.append(track)
                
                limit -= 1
                if limit == 0: break
            if limit == 0: break
        
        if not tracks:
            return "Got no tracks from user's reposts..."
    except:
        traceback.print_exc()
        return "Failed to get tracks from user's reposts..."
    
    # Success.
    return tracks

# Return tracks list from a set page,
# Or error message.
def getPlaylistSC(username, collection, pl, limit):
    try:
        raw = requests.get("https://api.soundcloud.com/resolve?client_id="+
            tinychat.SCkey+"&limit="+str(limit)+"&url=https://soundcloud.com/"+username+
            "/"+collection+"/"+pl, timeout=15)
        obj = raw.json()
    except:
        return "Failed to get details from SoundCloud link..."
        
    tracks = []
    
    try:
        # Get all tracks and add to list.
        for item in obj["tracks"]:
            # Only get tracks.
            if item["kind"] != "track": continue
            
            track = str(item["id"])
            # No duplicates in list.
            if track not in tracks:
                tracks.append(track)
                
                limit -= 1
                if limit == 0: break
        
        if not tracks:
            return "Got no tracks from playlist..."
    except:
        traceback.print_exc()
        return "Failed to get tracks from playlist..."
    
    # Success.
    return tracks

# Return tracks list from a sets page,
# Or error message.
def getPlaylistsSC(username, collection, limit):
    # Change to API standards.
    collection = collection.replace("sets", "playlists")
    
    try:
        raw = requests.get("https://api.soundcloud.com/users/"+username+"/"+collection+"?client_id="+
            tinychat.SCkey+"&limit="+str(limit), timeout=15)
        obj = raw.json()
    except:
        return "Failed to get details from SoundCloud link..."
    
    tracks = []
    
    try:
        # Get all tracks and add to list.
        for pl in obj:
            tracklist = pl["tracks"]
            
            for item in tracklist:
                # Only get tracks.
                if item["kind"] != "track": continue
                
                track = str(item["id"])
                # No duplicates in list.
                if track not in tracks:
                    tracks.append(track)
                    
                    limit -= 1
                    if limit == 0: break
            if limit == 0: break
        
        if not tracks:
            return "Got no tracks from user's page..."
    except:
        traceback.print_exc()
        return "Failed to get tracks from user's page..."
    
    # Succes.
    return tracks

# Return tracks list from a tracks or likes page,
# Or error message.
def getTracksSC(username, collection, limit):
    # Change to API standards.
    collection = collection.replace("likes", "favorites")
    
    try:
        raw = requests.get("https://api.soundcloud.com/users/"+username+"/"+collection+"?client_id="+
            tinychat.SCkey+"&limit="+str(limit), timeout=15)
        obj = raw.json()
    except:
        traceback.print_exc()
        return "Failed to get details from SoundCloud link..."
    
    tracks = []
    
    try:
        # Get all tracks and add to list.
        for item in obj:
            # Only get tracks.
            if item["kind"] != "track": continue
            
            track = str(item["id"])
            # No duplicates in list.
            if track not in tracks:
                tracks.append(track)
                
                limit -= 1
                if limit == 0: break
        
        if not tracks:
            return "Got no tracks from user's page..."
    except:
        traceback.print_exc()
        return "Failed to get tracks from user's page..."
    
    # Success.
    return tracks

# Return a list of tracks from a collection page (limited amount),
# Or an empty list if no tracks found.
# Return False on failure.
def getCollectionSC(username, collection, pl=None, limit=100, skip=0):
    if not tinychat.SCkey:
        return "A SoundCloud Client ID is required to fetch tracks from a link..."
    
    # Max tracks to return.
    # Make sure limit is a usable value.
    try:
        limit = int(limit)
        if not limit: limit = 100
    except:
        limit = 100
    
    # Verify skip.
    try:
        skip = int(skip)
    except:
        skip = 0
    
    # Shift limit to acknowledge skipped tracks.
    limit = limit + skip
    
    # Different special (unsuppurted) mechanism for /reposts.
    if collection == "reposts":
        tracks = getRepostsSC(username, limit)
    
    # Playlists are structured differently.
    if collection == "sets":
        # A single playlist.
        if pl:
            tracks = getPlaylistSC(username, collection, pl, limit)
        else:
            tracks = getPlaylistsSC(username, collection, limit)
    
    # The rest are the same.
    if collection in {"tracks", "likes"}:
        tracks = getTracksSC(username, collection, limit)
    
    # Skip tracks, if not an error.
    if type(tracks) is list and skip:
        tracks = tracks[skip:]
    
    # Return tracks list, or an error message str().
    return tracks

# Return videos list from a user's channel,
# Or error message.
def getChannelYT(collection, limit):
    # Get ChannelID by username.
    url = "https://www.googleapis.com/youtube/v3/channels?key="+tinychat.YTkey+ \
        "&forUsername="+collection+"&part=id"
    
    try:
        raw = requests.get(url, timeout=15)
        obj = raw.json()
    except:
        return "Failed to get a response from Youtube.com..."
    
    try:
        chanID = obj["items"][0]["id"]
    except:
        traceback.print_exc()
        return "Failed to get channel ID from Youtube API..."
    
    # Get videos from user's videos page.
    url = "https://www.googleapis.com/youtube/v3/search?key="+tinychat.YTkey+ \
        "&channelId="+chanID+"&part=snippet,id&order=date&maxResults="+str(limit)
    
    try:
        raw = requests.get(url, timeout=15)
        obj = raw.json()
    except:
        return "Failed to get a response from Youtube.com..."
    
    try:
        videos = []
        
        # Get all videos and add to list.
        for item in obj["items"]:
            # Only get videos.
            if item["id"]["kind"] != "youtube#video": continue
            
            vid = str(item["id"]["videoId"])
            
            # No duplicates in list.
            if vid not in videos:
                videos.append(vid)
                
                limit -= 1
                if limit == 0: break
        
        if not videos:
            return "Got no videos from user channel..."
    except:
        traceback.print_exc()
        return "Failed to get videos from user channel..."
    
    # Success.
    return videos

# Return videos list from a playlist page,
# Or error message.
def getPlaylistYT(collection, limit):
    # Get videos from a playlist page.
    url = "https://www.googleapis.com/youtube/v3/playlistItems?key="+tinychat.YTkey+ \
        "&playlistId="+collection+"&part=snippet,id&order=date&maxResults="+str(limit)
    
    try:
        raw = requests.get(url, timeout=15)
        obj = raw.json()
    except:
        return "Failed to get a response from Youtube.com..."
    
    try:
        videos = []
        
        # Get all videos and add to list.
        for item in obj["items"]:
            # Only get videos.
            if item["kind"] != "youtube#playlistItem" or \
               item["snippet"]["resourceId"]["kind"] != "youtube#video":
                continue
            
            vid = str(item["snippet"]["resourceId"]["videoId"])
            
            # No duplicates in list.
            if vid not in videos:
                videos.append(vid)
                
                limit -= 1
                if limit == 0: break
            
        if not videos:
            return "Got no videos from playlist..."
    except:
        traceback.print_exc()
        return "Failed to get videos from playlist..."
    
    # Success.
    return videos

# Return a list of videos from a user's channel (limited amount),
# Or an empty list if no videos found.
# Return False on failure.
def getCollectionYT(collection, colType, limit=50, skip=0):
    # Max videos to return.
    # Make sure limit is a usable value.
    try:
        limit = int(limit)
        if not limit or limit > 50:
            limit = 50
    except:
        limit = 50
    
    # Verify skip.
    try:
        skip = int(skip)
    except:
        skip = 0
    
    # Shift limit to acknowledge skipped videos.
    limit = limit + skip
    if limit > 50:
        limit = 50
    
    if colType == "channel":
        videos = getChannelYT(collection, limit)
    elif colType == "playlist":
        videos = getPlaylistYT(collection, limit)
    
    # Skip videos, if not an error.
    if type(videos) is list and skip:
        videos = videos[skip:]
    
    # Videos list, or error message.
    return videos

# Updates all the commands and defenses from online texts, by interval.
def updateOnlineTexts():
    while True:
        # Every interval in minutes.
        time.sleep(60*5)
        
        # NOTE: To remove from append() lists, remove both from online,
        # And from the running bot, with a command.
        
        # Botters and commands.
        result = listLoader(BottersText, online=True, parts=1, word=True)
        if result:
            for item in result:
                if item not in BOTTERS:
                    BOTTERS.append(item)    # Only add new ones.
        
        result = listLoader(ExtraYTsText, online=True, parts=3, youtubes=True)
        if result:
            ExtraYTS.clear()                # Empty.
            ExtraYTS.update(result)         # Add results, without changing reference.
        
        getPlaylists(PlaylistsText)
        
        result = listLoader(moreMessagesText, online=True, parts=2)
        if result:
            ROOM_MESSAGES.update(result)    # Add results, without changing reference.
        
        result = listLoader(asciiText, online=True, parts=2, unicode=True)
        if result:
            ASCII_MESSAGES.clear()          # Empty.
            ASCII_MESSAGES.update(result)   # Add results, without changing reference.
        
        getRandoms(randomsText)
        
        # Defenses.
        result = listLoader(AutobansText, online=True, word=True)
        if result:
            for item in result:
                if item not in AUTOBANS:
                    AUTOBANS.append(item)   # Only add new ones.
        
        result = listLoader(AutoforgivesText, online=True, word=True)
        if result:
            for item in result:
                if item not in AUTOFORGIVES:
                    AUTOFORGIVES.append(item)   # Only add new ones.
        
        result = listLoader(acctbanText, online=True, word=True)
        if result:
            for item in result:
                if item not in BANNED_ACCOUNTS:
                    BANNED_ACCOUNTS.append(item)    # Only add new ones.
        
        result = listLoader(banwordsText, online=True)
        if result:
            for item in result:
                if item not in BANWORDS:
                    BANWORDS.append(item)   # Only add new ones.
  
# Approve a cam waiting in the Greenroom,
# By user obj or nickname.
# Returns str() on failure.
def approveCam(room, user):
    if type(user) is str or type(user) is unicode:
        nick = user
        user = room._getUser(user)
        if not user:
            return "User "+nick+" was not found..."
    
    if not room.bpass:
        return
    
    room._sendCommand("privmsg", [room._encodeMessage("/allowbroadcast "+room.bpass),
        "#0,en"+"n"+ user.id+"-"+user.nick])

# Returns a nicely formatted string for uptime cmd.
def formatUptime():
    t = int(time.time())
    d = t - START_TIME
    
    days = int(d / 60 / 60 / 24)
    hours = int((d / 60 / 60) - (days * 24))
    minutes = int((d / 60) - (hours * 60) - (days * 24 * 60))
    seconds = int(d - (minutes * 60) - (hours * 60 * 60) - (days * 24 * 60 * 60))
    
    string = ""
    
    if days:
        end = " "
        if days > 1: end = "s "
        string += str(days) + " days"+end
    if hours:
        end = " "
        if hours > 1: end = "s "
        string += str(hours) + " hour"+end
    if minutes:
        end = " "
        if minutes > 1: end = "s "
        string += str(minutes) + " minute"+end
    
    string += str(seconds) + " seconds"
    
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
    # Case-sensitivity.
    if not case:
        name    = name.lower()
        string  = string.lower()
    
    # Exact match, handling wildcards and case.
    if exact:
        # Replace with wildcards in name.
        for i in range(len(string)):
            if string[i] == wildcard:
                # Replace char at index.
                name = name[:i]+wildcard+name[i+1:]
        
        if name == string:
            return True
        
        return
    
    # Escape characters for RE, and replace wildcard with RE wildcard.
    stringFixed = ".".join(map(re.escape, string.split("?")))
    
    r = re.compile(stringFixed)
    
    if r.search(name):
        return True

if __name__ == "__main__":
    # Apply tinychat global settings.
    tinychat.CONN_ARGS["nickname"]      = NICKNAME
    tinychat.SETTINGS["BotActive"]      = BOT_ACTIVE
    tinychat.SETTINGS["ReadyMessage"]   = READY_MESSAGE
    
    # Apply extension functions.
    tinychat.SETTINGS["onJoinExtend"]               = onJoinHandle
    tinychat.SETTINGS["onJoinsdoneExtend"]          = onJoinsdoneExtended
    tinychat.SETTINGS["onQuitExtend"]               = onQuitList
    tinychat.SETTINGS["onNoticeExtend"]             = onNoticeBans
    tinychat.SETTINGS["onMessageExtend"]            = onMessageExtended
    tinychat.SETTINGS["onPMExtend"]                 = onPMExtended
    tinychat.SETTINGS["onNickChangeExtend"]         = onNickChangeAutoban
    tinychat.SETTINGS["onUserinfoReceivedExtend"]   = onUserinfoReceivedExtended
    tinychat.SETTINGS["onBanlistExtend"]            = onBanlistAutoforgives
    tinychat.SETTINGS["onBroadcastExtend"]          = onBroadcastDefense
    tinychat.SETTINGS["disconnectExtend"]           = disconnectDefenses
    
    # Update all online texts, by interval.
    CONTROLS["listUpdater"] = threading.Thread(target=updateOnlineTexts, args=())
    CONTROLS["listUpdater"].daemon = True     # Exits when main thread quits.
    CONTROLS["listUpdater"].start()
    
    # Run!
    tinychat.main()
    