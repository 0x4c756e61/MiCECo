from enum import Enum
import requests
from requests.exceptions import HTTPError
import sys

class NoteVisibility(str, Enum):
    PUBLIC = "public"
    HOME = "home"
    FOLLOWERS = "followers"
    ME = "specified"

class UserInfo:
    user_id:str = None # pyright:ignore
    display_name:str = None #pyright:ignore

    def __init__(self, user_id:str, display_name:str) -> None:
        self.user_id = user_id
        self.display_name = display_name

class Misskey:
    token:str = None # pyright: ignore
    api_url:str = None # pyright: ignore
    username:str = None # pyright: ignore


    def __init__(self, token:str, instance:str, username:str) -> None:
        self.token = token
        self.api_url = f"https://{instance}/api"
        self.username = username

    def post_note(self, content:str,content_warning:str, visibility: NoteVisibility) -> None:
        try:
            req = requests.post(
                self.api_url + "/notes/create",
                json={"visibility": visibility, "text": content, "cw": content_warning},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            req.raise_for_status()
        except HTTPError as err:
            print(f"Couldn't create Posts! {err}")
            sys.exit(1)

    def get_user_info(self) -> UserInfo:
        try:
            req = requests.post(self.api_url + "/users/show", json={"username": self.username, "host": None})
            req.raise_for_status()
            return UserInfo(req.json()["id"], req.json()["name"] or req.json()["username"])

        except HTTPError as err:
            print(f"Couldn't get Username! {err} \n")
            sys.exit(1)

    def get_max_note_length(self) -> int:
        max_note_length = 3000 # default case
        try:
            req = requests.post(self.api_url + "/meta", json={"detail": True})
            req.raise_for_status()
            max_note_length = int(req.json()["maxNoteTextLength"])

        except HTTPError as err:
            print(f"Couldn't get maximal note length! {err}")
            print("Setting max note length to 3.000 characters")

        return max_note_length

    def get_custom_emojis(self): #pyright:ignore
        try:
            req = requests.get(self.api_url + "/emojis")
            req.raise_for_status()
            return req.json()["emojis"]

        except HTTPError as err:
            print(f"Couldn't get custom emojis! {err}")
            sys.exit(1)

    def get_reactions(self, user_info:UserInfo, since_date:int, until_date:int):
        try:
            req = requests.post(
                self.api_url + "/users/reactions",
                # seit lastTimestamp
                json={"userId": user_info.user_id, "sinceDate": since_date, "untilDate": until_date},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            req.raise_for_status()
            return req.json()

        except HTTPError as err:
            print("Couldn't get Posts! " + str(err))
            sys.exit(1)

    def get_notes(self, user: UserInfo, sinceDate:int, untilDate:int, include_replies:bool): #pyright:ignore
        try:
            req = requests.post(
                self.api_url + "/users/notes",
                json={
                    "userId": user.user_id,
                    "sinceDate": sinceDate, # seit
                    "untilDate": untilDate, # lastTimestamp
                    "withReplies": include_replies,
                    "limit": 100,
                    "withRenotes": False,
                    "withFiles": False,
                },
            )
            req.raise_for_status()
            return req.json()

        except HTTPError as err:
            print("Couldn't get Posts! " + str(err))
            sys.exit(1)
