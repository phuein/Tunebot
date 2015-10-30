# Tunebot
A friendly fork of several other bots (QBot, Pinychat), designed to assist Tinychat users and moderators.

**Like the bot? Donate in Bitcoins: 1LoyRpNMVB85WkTLWLkn7g8iPgyaVBFHKf**

Acknowledgements:
+ notnola
+ megaloler
+ qbot

\* _(Somebody else or a fix? Tell me.)_

<br>
## Files

**tunebot.py**

A patched-on module that runs the actual bot, that is responsive in the chat room.

**tinychat.py**

The core module responsible for interacting with Tinychat, handling the room object, users objects, and messages.

**rtmp**

Handles the RTMP connection and communication, using the AMF encoder/decoder module. This is a Python remake of the original C library.

<br>
**Requirements** [ _pip install NAME_ ]:
- PyAMF https://pypi.python.org/pypi/PyAMF
- PySocks https://github.com/Anorov/PySocks
- requests http://www.python-requests.org/en/latest/

<br>
## Command Line Arguments

The tinychat core module accepts these:

- room=ROOM [or tinychat*ROOM]

**Optional:**
- nick=NICK
- user=USER
- pass=PASS
- ready=0/1 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Say something, when ready in the room.)
- interactive=0/1 &nbsp;&nbsp;(Whether running from console or remotely.)
- ip=IP
- port=PORT

The tunebot module **adds** these **optional** arguments:

- nick=NICK&nbsp;&nbsp;&nbsp;&nbsp;(Override.)
- bot=0/1  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Whether bot starts active in listening to user commands.)
- greet=0/1 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(A smart greeting algorithm.)

<br>
## Settings

The top directory of the bot has a settings/ directory. In the code, you can see a lot of instructions come from simple .txt files in it.

The empty files in the settings/ directory expect **a link** to a TXT file format. For example, do "Export as TXT" in Google Docs, and copy the download URL from your browser downloads window.

<br>
