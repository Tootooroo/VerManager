import os
import sys

from django.apps import AppConfig

initialized = False

predicates = [
    lambda cfgs: "Address" in cfgs,
    lambda cfgs: "Port" in cfgs,
    lambda cfgs: "LogDir" in cfgs,
    lambda cfgs: "ResultDir" in cfgs,
    lambda cfgs: "GitlabUrl" in cfgs,
    lambda cfgs: "PrivateToken" in cfgs,
    lambda cfgs: "TimeZone" in cfgs
]

class ManagerConfig(AppConfig):
    name = 'manager'

    def ready(self):
        from manager.basic.info import Info
        import manager.master.master as S

        if os.environ.get('RUN_MAIN') == 'true':
            info = Info("./config.yaml")
            sInst = S.ServerInst(info.getConfig("Address"),
                                    info.getConfig("Port"),
                                    "./config_test.yaml")
            sInst.start()

        S.ServerInstance = sInst
