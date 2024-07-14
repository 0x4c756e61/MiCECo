import datetime

RED = "\x1b[38;2;246;96;96m";
YELLOW = "\x1b[38;2;255;237;129m";
GREEN = "\x1b[38;2;179;255;114m";
BLUE = "\x1b[38;2;86;164;255m";
GRAY = "\x1b[38;2;57;62;65m";
DEFAULT = "\x1b[0m";

def baseLogger(color:str, label:str, format:str) -> None:
    now = datetime.datetime.now()
    print(f"{GRAY}[{now.time().strftime("%H:%M:%S")}]{DEFAULT} {color}{label}{DEFAULT} \t-- {format}")

def info(text:str) -> None:
    baseLogger(BLUE, "INFO", text)

def warn(text:str) -> None:
    baseLogger(YELLOW, "WARN", text)

def err(text:str) -> None:
    baseLogger(RED, "ERROR", text)

def debug(text:str) -> None:
    baseLogger(GRAY, "DEBUG", text)
