import argparse
import configparser
import os
import sys
from collections import Counter
import datetime as dt
import emoji as emojilib
import requests
from requests.exceptions import HTTPError

from misskey_api import NoteVisibility, Misskey

# Edit that list to add new software
known_working_software = [
    "sharkey",
    "misskey",
    "firefish",
    "akkoma",
    "pleroma",
    "foundkey",
    "iceshrimp",
]

# Globals yay!
reactionList = []
reactList = []
emojiList = []
emojisTotal = 0
doubleList = []
ignored_emojis = []
text = ""
deafEarsText = ""
getReactions = True
getReaction_Received = False
withReplies = True
getUTF8_emojis = False


cwtext = "#miceco"

def note_is_miceco(note) -> bool:
    return note["text"].find(chr(8203) + chr(8203) + chr(8203)) > 0

def load_ignored_emojis() -> None:
    ignored_path = args.ignored or os.path.join(os.path.dirname(__file__), "ignoredemojis.txt")

    if not os.path.exists(ignored_path):
        print("Config is set to ignore emojis but no file for ignored emojis was found!")
        sys.exit(1)

    ignored_emojis = []
    with open(ignored_path, "r", encoding="utf8") as ignored_file:
        for element in ignored_file.readlines():
            i = element.strip()
            ignored_emojis.append(emojilib.demojize(i))

def get_yesterday_notes(bis:int, lastTimestamp:int, formerTimestamp:int) -> tuple[list, int,int]:
    noteList = []
    while True:
        if (bis != lastTimestamp) and (formerTimestamp == lastTimestamp):
            break


        notes = client.get_notes(user_info, seit, lastTimestamp, withReplies)

        noteList += notes

        formerTimestamp = lastTimestamp

        if len(noteList) <= 0:  # If there is zero notes, then break the while loop
           break

        lastTime = noteList[len(noteList) - 1]["createdAt"]
        lastTimestamp = int(
            dt.datetime.timestamp(dt.datetime.strptime(lastTime, "%Y-%m-%dT%H:%M:%S.%f%z")) * 1000
        )

    return (noteList, lastTimestamp, formerTimestamp)

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help="location of the configuration file")
parser.add_argument(
    "-i",
    "--ignored",
    help="location of the file which emojis are ignored while counting",
)


if __name__ == "__main__":
    args           = parser.parse_args()
    configfilePath = args.config or os.path.join(os.path.dirname(__file__), "miceco.cfg")

    if not os.path.exists(configfilePath):
        print("No config File found!")
        sys.exit(1)

    # Load configuration
    config = configparser.ConfigParser()
    config.read(configfilePath)

    instance = config.get("misskey", "instance")
    token    = config.get("misskey", "token")
    user     = config.get("misskey", "user")

    getReactions         = config.getboolean("misskey", "getReaction", fallback=True)
    ignoreEmojis         = config.getboolean("misskey", "ignoreEmojis", fallback=False)
    getReaction_Received = config.getboolean("misskey", "getReaction_Received", fallback=False)
    withReplies          = config.getboolean("misskey", "withReplies", fallback=True)
    getUTF8_emojis       = config.getboolean("misskey", "getUTF8_emojis", fallback=False)
    noteVisibility       = config.get("misskey", "noteVisibility", fallback=NoteVisibility.ME)

    if (
        noteVisibility     != NoteVisibility.PUBLIC
        and noteVisibility != NoteVisibility.HOME
        and noteVisibility != NoteVisibility.FOLLOWERS
        and noteVisibility != NoteVisibility.ME
    ):
        noteVisibility = NoteVisibility.ME

    # load ignored emojis
    if ignoreEmojis: load_ignored_emojis()

    # Create API client
    client          = Misskey(token, instance, user)
    user_info       = client.get_user_info()
    max_note_length = client.get_max_note_length()

    # fetch custom emojis
    emoji_list = client.get_custom_emojis()

    today              = dt.date.today()
    formerDate         = today - dt.timedelta(days=1)
    formerDateMidnight = dt.datetime.combine(formerDate, dt.time(0, 0, 0))
    todayMidnight      = dt.datetime.combine(today, dt.time(0, 0, 0))

    # Am not touching that code cuz idk what it does and am too lazy to try to understand it lmao - Lunya of the wind
    # Javascript uses millisecond timestamp and Python uses float
    seit = (int(formerDateMidnight.timestamp()) * 1000)
    bis  = int(todayMidnight.timestamp()) * 1000

    # Used to move the window of post as in [0..100] -> [100..200]
    lastTimestamp = bis
    formerTimestamp = 0

    start = dt.datetime.now()
    noteList, lastTimestamp, formerTimestamp = get_yesterday_notes(bis, lastTimestamp, formerTimestamp)
    end   = dt.datetime.now()

    print(f"Fetching all notes took : {end-start}")


    if len(noteList) == 0:
        print("Nothing to count, exiting script.")
        sys.exit(1)

    if len(noteList) == 1 and note_is_miceco(noteList[0]):
        print("Only note is MiCECo note.")
        print("Nothing to count, exiting script")
        sys.exit(1)

    # processing
    seen_emoji = [False for _ in range(len(emoji_list))]
    for note in noteList:
        if note["text"] is None:
            print(f"Skipped Note {note['id'] } without Text\nTime noted: element['createdAt']")
            continue

        if (note_is_miceco(note)):
            # Skip notes with three Zero-Width-Space in a
            # row (Marker to skip older MiCECo notes)
            print(f"Skipped MiCECo Note {note['id'] }\nTime noted: element['createdAt']")
            continue

        # Process and count custom Emojis
        if emoji_list is not None:
            for i,emoji in enumerate(emoji_list):
                # Only emojis from the own instance, because reactions will be in "emojis" too
                if "@" in emoji["name"]:continue

                emojiname = f":{emoji['name']}:"
                if not seen_emoji[i]:
                    seen_emoji[i] = True
                    emojiDict = {"emoji": emojiname, "count": 0}
                    emojiList.append(emojiDict)


                # count the emojis in that note
                emojiList[i]["count"] += note["text"].count(emojiList[i]["emoji"])

                if note["cw"] is not None:
                    # Also count emojis inside the CW
                    emojiList[i]["count"] += note["cw"].count(emojiList[i]["emoji"])

                # Count custom emojis that are used in poll texts
                if "poll" in note:
                    for pollchoice in note["poll"]["choices"]:
                        emojiList[i]["count"] += pollchoice["text"].count(emojiList[i]["emoji"])


        # Process UTF8 Emojis
        # Find all UTF8 Emojis in Text and CW text
        if getUTF8_emojis:
            # Concat all note fields into one for easier parsing
            note_content = note["text"]
            if note["cw"] is not None:
                note_content = note["text"] + " " + note["cw"]

            if "poll" in note:
                for pollchoice in note["poll"]["choices"]: note_content += " " + pollchoice["text"]

            emojis_in_note = emojilib.distinct_emoji_list(note_content)
            note_content = emojilib.demojize(note_content)
            emojis_in_note = list(set(emojis_in_note)) # Cool way to remove duplicates

            if len(emojis_in_note) > 0:
                for i, emoji in enumerate(emojis_in_note):
                    emoji = emojilib.demojize(emoji)
                    # Again, really slow procedure, but here we do not really know all the emojis in advance
                    # unless if we load all utf8 emojis which may be too heavy
                    if emoji not in doubleList:
                        # Easy way to prevent a double emoji in the list without checking the whole dictionary
                        doubleList.append(emoji)
                        emojiDict = {"emoji": emoji, "count": 0}
                        emojiList.append(emojiDict)


                    emojiList[i]["count"] += note_content.count(emoji)

    if ignoreEmojis:
        for ignoredEmoji in ignored_emojis:
            # TODO: Redo this, here we check the list 2 times, once with 'in' and another time with 'index'
            if ignoredEmoji in doubleList:
                indx = doubleList.index(ignoredEmoji)
                del doubleList[indx]
                del emojiList[indx]

    doubleList = []
    hostList = []

    # Sort it by the most used Emojis!
    emojiList = sorted(emojiList, reverse=True, key=lambda d: d["count"])

    reactionCount = 0

    if getReactions:
        lastTimestamp = bis

        while True:
            if (bis != lastTimestamp) and (formerTimestamp == lastTimestamp):
                break


            reactions = client.get_reactions(user_info, seit, lastTimestamp)

            for jsonObj in reactions:
                # Ignore duplicate posts, I don't know why this happens, I guess Sharkey is woozy sometimes
                if reactionList and reactionList[-1] == jsonObj: continue
                reactionList.append(jsonObj)

            formerTimestamp = lastTimestamp
            if len(reactionList) <= 0:
                break

            lastTime = reactionList[len(reactionList) - 1]["createdAt"]
            lastTimestamp = int(
                dt.datetime.timestamp(dt.datetime.strptime(lastTime, "%Y-%m-%dT%H:%M:%S.%f%z")) * 1000
            )


        react = ""
        host = ""
        index = None
        reactionElement: dict

        for reactionElement in reactionList:
            # print(json.dumps(reactionElement))
            # get note.user.host
            # \u2764 is default (heart)
            react = reactionElement["type"]
            react = react.replace("@.", "")
            host = reactionElement["note"]["user"]["host"]

            if react != "\u2764" and host is not None:
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

            initial_react_text = (
                "\n\n\nAnd used " + str(reactionCount) + " reactions:\n\n" + chr(9553) + " "
            )
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
        for note, count in host_counter.items():
            try:
                # print("Next query:")
                # print(element)
                # Get the URL from nodeinfo
                nodeinfo_response = requests.get(f"https://{note}/.well-known/nodeinfo")
                nodeinfo_data = nodeinfo_response.json()
                last_href = nodeinfo_data["links"][-1]["href"]

                # Execute GET request using the URL from nodeinfo
                result_response = requests.get(last_href)
                result_data = result_response.json()

                # Check if 'reactions' is supported
                if "reactions" not in result_data:
                    # Get software name
                    software_name = result_data["software"]["name"]
                    # print(f"Software name: {software_name}")

                    # Check supported software
                    if software_name not in known_working_software:
                        # Check reaction support for Others
                        mastodon_instance_info_response = requests.get(
                            f"https://{note}/api/v2/instance"
                        )
                        mastodon_instance_info_data = mastodon_instance_info_response.json()
                        if "reactions" not in mastodon_instance_info_data:
                            deaf_ears += count

            except Exception as e:
                print(f"An error occurred: {e}")
                print("If you see this error, please report it on github")
                print(
                    "This happens when a host is not providing an easy way to know if they support emoji reactions"
                )
                print("Host which couldn't be queried:" + note)
                print(
                    "miceco will assume that this instance supports emoji reactions since it's probably not mastodon"
                )
                continue


    initial_text = ""
    initial_react_text = ""

    if emojisTotal > 0:
        initial_text = (
            user_info.display_name
            + " has written "
            + str(len(noteList))
            + " Notes yesterday, "
            + formerDate.strftime("%a %d-%m-%Y")
            + "\nand used a total of "
            + str(emojisTotal)
            + " Emojis."
            + chr(8203)
            + chr(8203)
            + chr(8203)
            + "\n\n"
            + chr(9553)
            + " "
        )
        initial_text = f"{user_info.display_name} has written {len(noteList)} Notes yesterday ({formerDate.strftime("%a %d-%m-%Y")}) and used a total of {emojisTotal} Emojis."
        # signature to identify miceco posts
        initial_text += chr(8203) + chr(8203) + chr(8203) + "\n\n"+ chr(9553)+ " "

        text = initial_text
        emoji_text = ""

        for note in emojiList:
            count = note["count"]
            emoji = note["emoji"]
            # Don't include emojis that were never used
            if count > 0:
                emoji_text += f"{count}x {emoji} " + chr(9553) + " "

    else:

        emoji_text = f"{user_info.display_name} has written {len(noteList)} Notes yesterday ({formerDate.strftime("%a %d-%m-%Y")})\nand didn't use any emojis."
        emoji_text += chr(8203) + chr(8203) + chr(8203)

    if getReaction_Received:
        if deaf_ears > 0:
            deafEarsText = f"\n\nOf the {reactionCount} reactions {user_info.display_name} sent, at least {deaf_ears} went into the void (to Mastodon users) :("

        else:
            deafEarsText = "\n\nLooks like all reactions actually got received!"

    text += emoji_text + reactText + deafEarsText
    text = emojilib.emojize(text)
    # print(text)

    max_note_length = max_note_length - len(cwtext)

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

    client.post_note(text, cwtext, noteVisibility) #pyright:ignore
