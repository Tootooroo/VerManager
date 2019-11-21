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

        # Signal registering via decorator
        from .misc.verControl import RevSync

        # Start Syncner
        rSyncner = RevSync()
        rSyncner.start()
