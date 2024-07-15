import argparse
import configparser
import os
import sys
from collections import Counter
import datetime as dt
import emoji as emojilib
import requests
import math

import logger as lg
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
    "cutiekey",
    "magnetar",
    "villkey"
]

default_reaction = "\u2764" # heart

# Globals yay!
reactList = []
emojiList = []
emojisTotal = 0
ignored_emojis = []
text = ""
deafEarsText = ""
reactText = ""
getReactions = True
getReaction_Received = False
withReplies = True
getUTF8_emojis = False


cwtext = "#miceco"
user_agent = "MiCECo (github.com/vel_schmusis/MiCECo)"
s = requests.Session()
s.headers.update({"User-Agent": user_agent})

# TODO: Put signature at the start of the note's content, and check agains't the 3 first bytes
def note_is_miceco(note) -> bool:
    return note["text"].find(chr(8203) + chr(8203) + chr(8203)) > 0

def load_ignored_emojis() -> None:
    ignored_path = args.ignored or os.path.join(os.path.dirname(__file__), "ignoredemojis.txt")

    if not os.path.exists(ignored_path):
        lg.err("Config is set to ignore emojis but no file for ignored emojis was found!")
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


def get_yesterday_reactions(bis:int, lastTimestamp:int, formerTimestamp:int) -> tuple:
    reactionsList = []
    while True:
        if (bis != lastTimestamp) and (formerTimestamp == lastTimestamp):
            break

        reactions = client.get_reactions(user_info, seit, lastTimestamp)

        for jsonObj in reactions:
            # Ignore duplicate posts, I don't know why this happens, I guess Sharkey is woozy sometimes
            if reactionsList and reactionsList[-1] == jsonObj: continue
            reactionsList.append(jsonObj)

        formerTimestamp = lastTimestamp
        if len(reactionsList) <= 0:
            break

        lastTime = reactionsList[-1]["createdAt"]
        lastTimestamp = int(
            dt.datetime.timestamp(dt.datetime.strptime(lastTime, "%Y-%m-%dT%H:%M:%S.%f%z")) * 1000
        )
    return (reactionsList, lastTimestamp, formerTimestamp)


def format_delta_time(start, end) -> str:
    process_time = (end-start).total_seconds();
    time_unit = "s"
    if process_time < 0.5:
        process_time *= 1000
        time_unit = "ms"

    process_time = round(process_time, 2)

    return f"{process_time} {time_unit}"


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
        lg.err("No config File found!")
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
    start = dt.datetime.now()
    custom_emojis = client.get_custom_emojis()
    end = dt.datetime.now()
    lg.debug(f"Fetching custom emojis took : {format_delta_time(start, end)}")


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

    lg.debug(f"Fetching all notes took : {format_delta_time(start,end)}")

    if len(noteList) == 0:
        lg.info("Nothing to count, exiting script.")
        sys.exit(1)

    if len(noteList) == 1 and note_is_miceco(noteList[0]):
        lg.info("Only note is MiCECo note.")
        lg.info("Nothing to count, exiting script")
        sys.exit(1)

    # processing
    emoji_count = {}

    start = dt.datetime.now()

    for note in noteList:
        if note["text"] is None:
            lg.info(f"Skipped Note {note['id'] } without Text (Noted at: {note['createdAt']})")
            continue

        if (note_is_miceco(note)):
            # Skip notes with three Zero-Width-Space in a
            # row (Marker to skip older MiCECo notes)
            lg.info(f"Skipped MiCECo Note '{note['id'] }' (Noted at: {note['createdAt']})")
            continue

        # Concat all note fields into one for easier parsing
        note_content = note["text"]
        if note["cw"] is not None:
            note_content = note["text"] + " " + note["cw"]

        if "poll" in note:
            for pollchoice in note["poll"]["choices"]: note_content += " " + pollchoice["text"]

        # Process and count custom Emojis
        if custom_emojis is not None:
            for emoji in custom_emojis:
                # Ignore remote emojis
                if "@" in emoji["name"]: continue
                stringified_emoji = f":{emoji['name']}:"

                if ignoreEmojis and stringified_emoji in ignored_emojis:continue

                emoji_occurences_in_note = note_content.count(stringified_emoji)
                if emoji_occurences_in_note <=0:
                    continue

                if stringified_emoji not in emoji_count:
                    emoji_count[stringified_emoji] = emoji_occurences_in_note
                    continue

                emoji_count[stringified_emoji] += emoji_occurences_in_note


        # Process UTF8 Emojis
        # Find all UTF8 Emojis in Text and CW text
        if getUTF8_emojis:

            emojis_in_note = emojilib.distinct_emoji_list(note_content)
            note_content = emojilib.demojize(note_content)

            if len(emojis_in_note) > 0:
                for emoji in emojis_in_note:
                    if ignoreEmojis and emoji in ignored_emojis:continue

                    stringified_emoji = emojilib.demojize(emoji)

                    emoji_occurences_in_note = note_content.count(stringified_emoji)
                    if emoji_occurences_in_note <=0:
                        continue

                    if stringified_emoji not in emoji_count:
                        emoji_count[stringified_emoji] = emoji_occurences_in_note
                        continue


                    emoji_count[stringified_emoji] += emoji_occurences_in_note

    end = dt.datetime.now()

    lg.debug(f"Counting emojis took : {format_delta_time(start,end)}")

    for key in emoji_count:
        emojisTotal += emoji_count[key]



    # Sort it by the most used Emojis!
    start = dt.datetime.now()
    emoji_count = {k: v for k, v in sorted(emoji_count.items(),reverse=True, key=lambda item: item[1])}
    end   = dt.datetime.now()

    lg.debug(f"Sorting emojis took : {format_delta_time(start,end)}")

    reactionCount = 0
    reaction_count = {}
    hosts = []
    if getReactions:
        lastTimestamp = bis

        start = dt.datetime.now()
        reactions, _, _ = get_yesterday_reactions(bis, lastTimestamp, formerTimestamp)
        end = dt.datetime.now()

        lg.debug(f"Fetching yesterday's reactions took : {format_delta_time(start,end)}")

        start = dt.datetime.now()
        for react in reactions:
            stringified_reaction_emoji = react["type"].replace("@.", "")
            host = react["note"]["user"]["host"]

            if stringified_reaction_emoji != default_reaction and host is not None:
                hosts.append(host)

            if stringified_reaction_emoji not in reaction_count:
                reaction_count[stringified_reaction_emoji] = 0

            reaction_count[stringified_reaction_emoji] += 1

        end   = dt.datetime.now()
        lg.debug(f"Counting reactions took : {format_delta_time(start,end)}")


        start = dt.datetime.now()
        reaction_count = {k: v for k, v in sorted(reaction_count.items(),reverse=True, key=lambda item: item[1])}
        end   = dt.datetime.now()
        lg.debug(f"Sorting reactions took : {format_delta_time(start,end)}")

        reactText = "\n\nAnd didn't use any reactions."
        if len(reaction_count) > 0:
            # Summarize the number of Reactions used
            for stringified_reaction_emoji in reaction_count:
                reactionCount += reaction_count[stringified_reaction_emoji]

            reactText = (f"\n\n\nAnd used {reactionCount} reactions:\n\n{chr(9553)} ")

            for stringified_reaction_emoji in reaction_count:
                reactText += f"{reaction_count[stringified_reaction_emoji]}x {stringified_reaction_emoji} {chr(9553)} "

    host_counter = Counter(hosts)
    deaf_ears = 0
    if getReaction_Received:
        start = dt.datetime.now()
        for host, count in host_counter.items():
            try:
                # print("Next query:")
                # print(element)
                # Get the URL from nodeinfo
                nodeinfo_response = s.get(f"https://{host}/.well-known/nodeinfo")

                nodeinfo_data = nodeinfo_response.json()
                last_href = nodeinfo_data["links"][-1]["href"]

                # Execute GET request using the URL from nodeinfo
                result_response = s.get(last_href)
                result_data = result_response.json()

                # Check if 'reactions' is supported
                if "reactions" not in result_data:
                    # Get software name
                    software_name = result_data["software"]["name"]
                    # print(f"Software name: {software_name}")

                    # Check supported software
                    if software_name not in known_working_software:
                        # Check reaction support for Others

                        mastodon_instance_info_response = s.get(
                            f"https://{host}/api/v2/instance")

                        mastodon_instance_info_data = mastodon_instance_info_response.json()
                        if "reactions" not in mastodon_instance_info_data:
                            deaf_ears += count

            except Exception as e:
                if type(e) is requests.exceptions.ConnectionError:
                    lg.warn(f"Unable count deaf ears for '{host}' as host is down")
                    continue

                lg.warn(f"An error occurred: {e}")
                lg.warn("If you see this error, please report it on github")
                lg.warn("This happens when a host is not providing an easy way to know if they support emoji reactions")
                lg.warn("Host which couldn't be queried:" + host)
                lg.warn("miceco will assume that this instance supports emoji reactions since it's probably not mastodon")
                continue

        end = dt.datetime.now()
        lg.debug(f"Counting deaf ears took : {format_delta_time(start,end)}")

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

        for emoji in emoji_count:
            emoji_text += f"{emoji_count[emoji]}x {emoji} " + chr(9553) + " "

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
        for emoji in list(emoji_count.keys())[0:5]:
            emoji_text += f"{emoji_count}x {emoji} " + chr(9553) + " "
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
