from django.apps import AppConfig
from client.eventHandlers import init as event_handler_init


class ClientConfig(AppConfig):
    name = 'client'

    def ready(self) -> None:
        event_handler_init()
