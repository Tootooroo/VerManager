# oemRegister.py
#
# Handle of register of oem file
import typing
import os

def oemRegister(oemIdent: str, oemFile: typing.TextIO) -> bool:
    oemPath = "/tmp/registeredOem/" + oemIdent
    # Is the oem already registered
    if os.access(oemPath, os.F_OK):
        return False

    # Register oem file
    with open(oemPath, "w+") as dest:
        for chunk in oemFile:
            dest.write(chunk)
    return True
