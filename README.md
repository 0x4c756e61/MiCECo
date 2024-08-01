# MiCECo
**M**isskey **C**ustom **E**moji **Co**unter

This fork builds on top of Vel's one, featuring a rewrite of the codebase, making the code easier to maintain, and much faster !

### Introduction
This little script counts custom emojis and used reactions from the previous day and automaticaly creates a note on your Sharkey account with an overview. There is also an option to include reaction emojis in the counts too.

All notes will be sent with a content warning, because some clients can't handle a big number of emojis!

### Installation
#### Docker
Clone the repository into a folder of your choice with `git clone https://github.com/0x4c756e61/MiCECo.git`
Edit the file `example-miceco.cfg` (see table below) and save it as `miceco.cfg`
Edit the file `docker-compose.yaml` and change `TZ=Europe/Berlin` to your local timezone

Start the container with `docker compose up --build`.

#### Source
Clone the repository into a folder of your choice with `git clone https://github.com/0x4c756e61/MiCECo.git`
Edit the file `example-miceco.cfg` (see table below) and save it as `miceco.cfg`

I advise you use virtual environments to avoid conflicting with your package manager or other project's dependencies, you can do as follows:
1) In the cloned folder, run `python -m venv .venv`
2) Activate the virtual environment `source .venv/bin/activate` (this command may change a little depending on the shell you use)

Make sure you repeat step 2 at the start of every session

Install the required dependencies via `pip install -r requirements.txt` in the cloned folder

You are now ready to run the script with any Python3 version.

I recommend using a cronjob to let it run on a daily basis.
In your console type `crontab -e`
Add `0 9 * * * python3 /path/to/file/miceco.py > /path/to/file/miceco_output.txt`
The script will now be run every day on 9:00am server time.

### Available flags
There are two flags that can be used to specify which external files the script gonna use

| Flag | Long name   | controlled behaviour                                                                     |
|------|-------------|------------------------------------------------------------------------------------------|
| `-c` | `--config`  | What configuration file should be used.<br/>Without this flag `miceco.cfg` will be used. |
| `-i` | `--ignored` | Which emojis should be ignored.<br/> Without this `ignoredemojis.txt` will be used       |

### Options for the config file
| Name           | Values     | Default    | Explanation                                                                                                                                                       |
|----------------|------------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| instance       | domain.tld | example.com  | The domain name for your Misskey instance that you want to read the notes from. Only supply the domain name and TLD, no `/`,`:` or `https`|
| user           | `username` | myuser  | The user you want to read the notes from|
| token          | `String`   | mytoken  | The token for your bot. Needs permission to write notes|
| getReaction    | `Boolean`  | `True`  | Should reactions emojis be counted as well?|
| ignoreEmojis   | `Boolean`  | `False`  | Should Emojis that are specified in `ignoredemojis.txt` be ignored?|
| noteVisibility | `String`   | `public`  | How should the note be shown in the Timeline?<br/>`public`: Visible for everyone<br/>`home`: Visible on Home timeline<br/>`folowers`: only visible for your followers<br/>`specified`: Only you can see it |
| getReaction_Received | `Boolean`   | `False`  | Set to True to (rudimentary) check wether your reactions got received (If the target server supports reactions).<br/>2-3 queries will be sent to each server that received at least 1 reaction. This happens once (not for each reaction). |
| withReplies | `Boolean`   | `True`  | Should replies be checked for custom emojis as well? (MiCECO will never search in DMs or Follower-Only posts) |
| getUTF8_emojis | `Boolean`   | `False`  | Should UTF8 Emojis be considered custom emojis and be counted as well? |


### Other notes
The script is written in a way that only the notes and reactions from yesterday(!!!) are caught and counted. There is no option currently to specify the date range for collection.

The exact timestamp to get yesterday is determined by the timezone of your server. At the moment there is no way to change the timezone.

If the note is longer than the maximum note length of the instance, then only the five most used emojis (and five most used reactions) will be shown.
