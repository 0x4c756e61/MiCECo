import configparser
import os
import sys
import argparse
from datetime import *
import requests
import emoji as emojilib
from collections import Counter
import json

def check_str_to_bool(input_text) -> bool:
    if input_text == "True" or input_text == "true" or input_text == "TRUE":
        return True
    elif input_text == "False" or input_text == "false" or input_text == "FALSE":
        return False
    else:
        return True


noteList = []
reactionList = []
reactList = []
emojiList = []
emojisTotal = 0
doubleList = []
text = ""
deafEarsText = ""
getReactions = True
getReaction_Received = False
withReplies = True
getUTF8_emojis = False

cwtext = "#miceco"

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help="location of the configuration file")
parser.add_argument("-i", "--ignored", help="location of the file which emojis are ignored while counting")
args = parser.parse_args()

if args.config is None:
    configfilePath = os.path.join(os.path.dirname(__file__), 'miceco.cfg')
else:
    configfilePath = args.config

if not os.path.exists(configfilePath):
    print("No config File found!")
    print("Exit program!")
    sys.exit(1)

# Load configuration
config = configparser.ConfigParser()
config.read(configfilePath)

url = "https://" + config.get("misskey", "instance") + "/api"
token = config.get("misskey", "token")
user = config.get("misskey", "user")

try:
    getReactions = check_str_to_bool(config.get("misskey", "getReaction"))
except (TypeError, ValueError, configparser.NoOptionError) as err:
    getReactions = True

try:
    ignoreEmojis = check_str_to_bool(config.get("misskey", "ignoreEmojis"))
except (TypeError, ValueError, configparser.NoOptionError) as err:
    ignoreEmojis = False

try:
    getReaction_Received = check_str_to_bool(config.get("misskey", "getReaction_Received"))
except (TypeError, ValueError, configparser.NoOptionError) as err:
    getReaction_Received = False

try:
    withReplies = check_str_to_bool(config.get("misskey", "withReplies"))
except (TypeError, ValueError, configparser.NoOptionError) as err:
    withReplies = True

try:
    getUTF8_emojis = check_str_to_bool(config.get("misskey", "getUTF8_emojis"))
except (TypeError, ValueError, configparser.NoOptionError) as err:
    getUTF8_emojis = False

if ignoreEmojis:
    if args.ignored is None:
        ignored_path = os.path.join(os.path.dirname(__file__), "ignoredemojis.txt")
    else:
        ignored_path = args.ignored

    if not os.path.exists(ignored_path):
        print("No file for ignored emojis found!")
        print("Setting skipped!")

    if os.path.exists(ignored_path):
        with open(ignored_path, "r", encoding="utf8") as ignored_file:
            ignored_emojis = []
            for element in ignored_file.readlines():
                i = element.strip()
                ignored_emojis.append(emojilib.demojize(i))

try:
    noteVisibility = config.get("misskey", "noteVisibility")  # How should the note be printed?
    if noteVisibility != "public" and noteVisibility != "home" and noteVisibility != "followers" and noteVisibility != \
            "specified":
        noteVisibility = "followers"
except configparser.NoOptionError as err:
    noteVisibility = "followers"

try:
    req = requests.post(url + "/users/show", json={"username": user, "host": None})
    req.raise_for_status()
except requests.exceptions.HTTPError as err:
    print("Couldn't get Username!\n" + str(err))
    sys.exit(1)

userid = req.json()["id"]
if req.json()["name"] is not None:  # If no nickname is set, just user the username instead
    nickname = req.json()["name"]
else:
    nickname = req.json()["username"]

# Get max note length
try:
    req = requests.post(url + "/meta", json={"detail": True})
    req.raise_for_status()
except requests.exceptions.HTTPError as err:
    print("Couldn't get maximal note length!\n" + str(err))
    print("Setting max note length to 3.000 characters")
    max_note_length = 3000

max_note_length = int(req.json()["maxNoteTextLength"])

today = date.today()
formerDate = today - timedelta(days=1)
formerDateMidnight = datetime.combine(formerDate, time(0, 0, 0))
todayMidnight = datetime.combine(today, time(0, 0, 0))

seit = int(formerDateMidnight.timestamp()) * 1000  # Javascript uses millisecond timestamp and Python uses float
bis = int(todayMidnight.timestamp()) * 1000

lastTimestamp = bis
formerTimestamp = 0

while True:

    if (bis != lastTimestamp) and (formerTimestamp == lastTimestamp):
        break

    try:
        req = requests.post(url + "/users/notes", json={
            "userId": userid,
            "sinceDate": seit,
            "untilDate": lastTimestamp,
            "withReplies": withReplies,
            "limit": 100,
            "withRenotes": False,
            "withFiles": False
        })
        req.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print("Couldn't get Posts! " + str(err))
        sys.exit(1)

    for jsonObj in req.json():
        noteList.append(jsonObj)

    formerTimestamp = lastTimestamp

    if not len(noteList) <= 0:  # If there is zero notes, then break the while loop
        lastTime = noteList[len(noteList) - 1]["createdAt"]
        lastTimestamp = int(datetime.timestamp(datetime.strptime(lastTime, '%Y-%m-%dT%H:%M:%S.%f%z')) * 1000)
    else:
        break
# Fetch custom emojis from instance
try:
    req = requests.get(url + "/emojis")
    req.raise_for_status()
except requests.exceptions.HTTPError as err:
    print("Couldn't get custom emojis!\n" + str(err))
    sys.exit(1)
emoji_list = req.json()


if len(noteList) == 0:
    print("Nothing to count, exiting script.")
    sys.exit(1)

if len(noteList) == 1:
    if noteList[0]["text"].find(chr(8203) + chr(8203) + chr(8203)) > 0:
        print("Only note is MiCECo note.")
        print("Nothing to count, exiting script")
        sys.exit(1)

for element in noteList:
    if element["text"] is None:  # Skip Notes without text
        print("Skip Note " + element["id"] + " without Text\nTime noted: " + element["createdAt"])
        continue

    if element["text"].find(chr(8203) + chr(8203) + chr(8203)) > 0:  # Skip notes with three Zero-Width-Space in a
        # row (Marker to skip older MiCECo notes)
        print("Skip Note " + element["id"] + " with Zero-Width-Space\nTime noted: " + element["createdAt"])
        continue

    # Process and count custom Emojis
    emojis = emoji_list["emojis"]

    if emojis is not None:
        for emoji in emojis:
            if emoji["name"].find("@") == -1:  # Only emojis from the own instance, because reactions will be in
                # "emojis" too
                emojiname = ":" + emoji["name"] + ":"
                if emojiname not in doubleList:
                    doubleList.append(emojiname)  # Easy way to prevent a double emoji in the list.
                    emojiDict = {"emoji": emojiname, "count": 0}
                    emojiList.append(emojiDict)
            else:
                continue

            index = doubleList.index(":" + emoji["name"] + ":")

            emojiList[index]["count"] += element["text"].count(emojiList[index]["emoji"])

            if element["cw"] is not None:
                emojiList[index]["count"] += element["cw"].count(emojiList[index]["emoji"])  # Count those Emojis, that
                # are in this note CW text

            if "poll" in element:
                for pollchoice in element["poll"]["choices"]:
                    emojiList[index]["count"] += pollchoice["text"].count(emojiList[index]["emoji"])  # CCount custom emojis that are used in poll texts

    # Process UTF8 Emojis
    if element["cw"] is not None:
        UTF8text = element["text"] + " " + element["cw"]
    else:
        UTF8text = element["text"]

    if "poll" in element:
        for pollchoice in element["poll"]["choices"]:
            UTF8text += " " + pollchoice["text"]
    if getUTF8_emojis:
        UTF8ListRaw = emojilib.distinct_emoji_list(UTF8text)  # Find all UTF8 Emojis in Text and CW text
        UTF8text = emojilib.demojize(UTF8text)
        if len(UTF8ListRaw) > 0:
            UTF8List = list(set(UTF8ListRaw))
            for emoji in UTF8List:
                emoji = emojilib.demojize(emoji)
                if emoji not in doubleList:
                    doubleList.append(emoji)  # Easy way to prevent a double emoji in the list without checking the whole
                    # dictionary
                    emojiDict = {"emoji": emoji, "count": 0}
                    emojiList.append(emojiDict)

                index = doubleList.index(emoji)
                emojiList[index]["count"] += UTF8text.count(emoji)

if ignoreEmojis:
    for ignoredEmoji in ignored_emojis:
        if ignoredEmoji in doubleList:
            indx = doubleList.index(ignoredEmoji)
            del doubleList[indx]
            del emojiList[indx]

doubleList = []
hostList = []
emojiList = sorted(emojiList, reverse=True, key=lambda d: d["count"])  # Sort it by the most used Emojis!

reactionCount = 0

if getReactions:
    lastTimestamp = bis

    while True:

        if (bis != lastTimestamp) and (formerTimestamp == lastTimestamp):
            break

        try:
            req = requests.post(url + "/users/reactions", json={
                "userId": userid,
                "sinceDate": seit,
                "untilDate": lastTimestamp
                }, headers={
                    "Authorization": f"Bearer {token}"
                })
            req.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print("Couldn't get Posts! " + str(err))
            sys.exit(1)

        for jsonObj in req.json():
            if reactionList and reactionList[-1] == jsonObj:
                continue  # Ignore duplicate posts, I don't know why this happens, I guess Sharkey is woozy sometimes
            reactionList.append(jsonObj)

        formerTimestamp = lastTimestamp
        if not len(reactionList) <= 0:
            lastTime = reactionList[len(reactionList) - 1]["createdAt"]
            lastTimestamp = int(datetime.timestamp(datetime.strptime(lastTime, '%Y-%m-%dT%H:%M:%S.%f%z')) * 1000)
        else:
            break

    react = ""
    host = ""
    index = None
    reactionElement: dict

    for reactionElement in reactionList:
        #print(json.dumps(reactionElement))
        # get note.user.host
        # \u2764 is default (heart)
        react = reactionElement["type"]
        react = react.replace("@.", "")
        host = reactionElement["note"]["user"]["host"]
        if react != "\u2764" and host != None:
            hostList.append(host)
        if react not in doubleList:
            doubleList.append(react)
            emojiDict = {"reaction": react, "count": 0}
            reactList.append(emojiDict)

        index = doubleList.index(react)
        reactList[index]["count"] += 1

    doubleList = []
    reactList = sorted(reactList, reverse=True, key=lambda d: d["count"])

    if len(reactList) > 0:
        for react in reactList:  # Summarize the number of Reactions used
            reactionCount += react["count"]

        initial_react_text = "\n\n\nAnd used " + str(reactionCount) + " reactions:\n\n" + chr(9553) + " "
        reactText = initial_react_text

        for reactionElement in reactList:
            count = reactionElement["count"]
            reaction = reactionElement["reaction"]
            reactText += f"{count}x {reaction} " + chr(9553) + " "
    else:
        reactText = "\n\nAnd didn't use any reactions."
else:
    reactText = ""

for count in emojiList:
    emojisTotal += count["count"]

host_counter = Counter(hostList)
deaf_ears = 0
if getReaction_Received:
    for element, count in host_counter.items():
        try:
            #print("Next query:")
            #print(element)
            # Get the URL from nodeinfo
            nodeinfo_response = requests.get(f"https://{element}/.well-known/nodeinfo")
            nodeinfo_data = nodeinfo_response.json()
            last_href = nodeinfo_data["links"][-1]["href"]

            # Execute GET request using the URL from nodeinfo
            result_response = requests.get(last_href)
            result_data = result_response.json()

            # Check if 'reactions' is supported
            if "reactions" not in result_data:
                # Get software name
                software_name = result_data["software"]["name"]
                #print(f"Software name: {software_name}")

                # Check supported software
                if software_name not in ["sharkey", "misskey", "firefish", "akkoma", "pleroma", "foundkey"]:
                    # Check reaction support for Others
                    mastodon_instance_info_response = requests.get(f"https://{element}/api/v2/instance")
                    mastodon_instance_info_data = mastodon_instance_info_response.json()
                    if "reactions" not in mastodon_instance_info_data:
                        deaf_ears += count
        except Exception as e:
            print(f"An error occurred: {e}")
            print("If you see this error, please report it on github")
            print("This happens when a host is not providing an easy way to know if they support emoji reactions")
            print("Host which couldn't be queried:" + element)
            print("miceco will assume that this instance supports emoji reactions since it's probably not mastodon")
            continue


initial_text = ""
initial_react_text = ""

if emojisTotal > 0:
    initial_text = nickname + " has written " + str(len(noteList)) + " Notes yesterday, " + formerDate.strftime(
        '%a %d-%m-%Y') + "\nand used a total of " + str(emojisTotal) + " Emojis." + chr(8203) + chr(8203) + chr(
        8203) + "\n\n" + chr(9553) + " "
    text = initial_text
    emoji_text = ""

    for element in emojiList:
        count = element["count"]
        emoji = element["emoji"]
        # Don't include emojis that were never used
        if count > 0:
            emoji_text += f"{count}x {emoji} " + chr(9553) + " "

else:
    emoji_text = nickname + " has written " + str(len(noteList)) + " Notes yesterday, " + formerDate.strftime(
        '%a %d-%m-%Y') + "\nand didn't use any emojis." + chr(8203) + chr(8203) + chr(8203)
if getReaction_Received:
    if deaf_ears > 0:
        deafEarsText = "\n\nOf the " + str(reactionCount) + " reactions " + nickname + " sent, at least " + str(deaf_ears) + " went into the void (to Mastodon users) :("
    else:
        deafEarsText = "\n\nLooks like all reactions actually got received!"

text += emoji_text + reactText + deafEarsText
text = emojilib.emojize(text)
# print(text)

max_note_length = max_note_length-len(cwtext)

if max_note_length < len(text):
    emoji_text = initial_text
    for item in range(0, 5):
        count = emojiList[item]["count"]
        emoji = emojiList[item]["emoji"]
        emoji_text += f"{count}x {emoji} " + chr(9553) + " "
    emoji_text += " and more..."

    if getReactions:
        reactText = initial_react_text
        for item in range(0, 5):
            count = reactList[item]["count"]
            reaction = reactList[item]["reaction"]
            reactText += f"{count}x {reaction} " + chr(9553) + " "
        reactText += " and more..."

    text = emoji_text + reactText
    text = emojilib.emojize(text)

try:
    req = requests.post(url + "/notes/create", json={
        "visibility": noteVisibility,
        "text": text,
        "cw": cwtext
    }, headers={
        "Authorization": f"Bearer {token}"
    })
    req.raise_for_status()
except requests.exceptions.HTTPError as err:
    print("Couldn't create Posts! " + str(err))
    sys.exit(1)

