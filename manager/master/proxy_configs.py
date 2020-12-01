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
from client.messages import Message
from manager.master.exceptions import BASIC_CONFIG_IS_COVERED


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
        "is_broadcast": None
    }

    # You should not to add config to this dict
    # manually.
    CONFIGS = {}

    def add_config(self, cfg_name: str, handle: T.Callable) -> None:
        # To ensure that the BASIC_CONFIGS is not been covered.
        if cfg_name in self.BASIC_CONFIGS:
            raise BASIC_CONFIG_IS_COVERED(cfg_name)

        self.CONFIGS[cfg_name] = handle

    def get_config(self, cfg_name: str) -> T.Optional[str]:
        if cfg_name not in self.CONFIGS:
            return None
        return self.CONFIGS[cfg_name]

    def rm_config(self, cfg_name: str) -> None:
        pass

    def eval(self, cfgs: T.Dict[str, str], msg: Message) \
        -> T.Tuple[
            Callable,      # How to send
            Message,       # Message to be sended
            T.List[str]]:  # Who should receive the message

        # First, to deal with the problem that How to send
        # and who should receive the message
