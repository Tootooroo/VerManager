# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


class EVENT_NOT_FOUND(Exception):

    def __init__(self, event_name: str) -> None:
        self.event_name = event_name

    def __str__(self) -> str:
        return "Event " + self.event_name + " not found"


class EVENT_PARSE_FAILED(Exception):

    def __str__(self) -> str:
        return "Can't parse string into a event"


class EVENT_IS_ALREADY_INSTALLED(Exception):

    def __init__(self, event_type: str) -> None:
        self.event_type = event_type

    def __str__(self) -> str:
        return "Event " + self.event_type + " is already installed"


class FAILED_TO_QUERY(Exception):
    pass
