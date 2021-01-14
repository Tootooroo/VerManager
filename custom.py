import typing as T
import gitlab
import re
from bs4 import BeautifuSoup
from tabulate import tabulate


async def doc_gen(contents: T.List[T.List[str]], path: str) -> T.Optional[str]:

    changelogfile = open(path, "w")

    for content in contents:

        if len(content) == 0:
            continue
        table = []
        table.append(["WTD_NO", "ISSUE", "DESCRIPTION"])

        for line in content:
            table.append(["N/A", "NULL", line])

        changelogfile.write(tabulate(table)+"\n")

    return path
