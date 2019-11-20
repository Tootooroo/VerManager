from django.apps import AppConfig

initialized = False

class ManagerConfig(AppConfig):
    name = 'manager'

    def ready(self):
        global initialized
        if initialized == False:
            initialized = True
        else:
            return None

        from .misc.verControl import RevSync

        RevSync.revDBInit()
