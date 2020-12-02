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

import typing as T
import client.client as Client
from client.messages import Message
from manager.master.exceptions import BASIC_CONFIG_IS_COVERED

config_value = str
config_handle = T.Callable[[Message, T.List[str], str], None]
config_item = T.Tuple[config_handle, T.List[str]]


def config_is_broadcast(msg: Message, who: T.List[str], cfg_v: str) -> None:
    if cfg_v == "ON":
        for ident in Client.clients:
            # Already exist.
            if ident in who:
                continue
            who.append(ident)


class ProxyConfigs:
    """
    A Place to defined configs that Proxy support.

    Assumptions to make sure ProxConfigs works well:
    (1) A config is not depend on another configs.
    (2) A set of configs must able to be apply in any orders.
    (3) There is a set of basic configs used to control how Message
        to transfer, such as send to which client or send to several clients.
    """

    BASIC_CONFIGS = {
        #                | handle             | value domain
        "is_broadcast": (config_is_broadcast, ["ON", "OFF"]),
    }  # type: T.Dict[str, config_item]

    # You should not to add config to this dict
    # manually.
    CONFIGS = {}  # type: T.Dict[str, config_item]

    @classmethod
    def add_config(self, cfg_name: str, handle: config_handle,
                   values: T.List[str]) -> None:

        # To ensure that the BASIC_CONFIGS is not been covered.
        if cfg_name in self.BASIC_CONFIGS:
            raise BASIC_CONFIG_IS_COVERED(cfg_name)

        self.CONFIGS[cfg_name] = (handle, values)

    @classmethod
    def rm_config(self, cfg_name: str) -> None:
        # To ensure basic config is not been removed.
        if cfg_name in self.BASIC_CONFIGS:
            raise BASIC_CONFIG_IS_COVERED(cfg_name)
        del self.CONFIGS[cfg_name]

        return None

    def get_config(self, cfg_name: str) -> T.Optional[config_item]:
        if cfg_name in self.BASIC_CONFIGS:
            return self.BASIC_CONFIGS[cfg_name]
        elif cfg_name in self.CONFIGS:
            return self.CONFIGS[cfg_name]

        return None

    @classmethod
    def is_exists(self, cfg_name: str) -> bool:
        return cfg_name in self.BASIC_CONFIGS or cfg_name in self.CONFIGS

    @classmethod
    def apply(self, cfgs: T.Dict[str, str], msg: Message) \
        -> T.Tuple[
            Message,       # Message to be sended
            T.List[str]]:  # Who should receive the message
        """
        Apply configs to a message.
        """
        who = []  # type: T.List[str]

        # Apply configs
        for key in cfgs:

            if key in self.BASIC_CONFIGS:
                handle, domain = self.BASIC_CONFIGS[key]
            elif key in self.CONFIGS:
                handle, domain = self.CONFIGS[key]

            value = cfgs[key]
            if domain != [] and value not in domain:
                # Value error try next config
                continue

            handle(msg, who, cfgs[key])

        return (msg, who)
