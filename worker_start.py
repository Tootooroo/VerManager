import sys

from manager.basic.info import Info
from manager.worker.client import Client

if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    address = info.getConfig('MASTER_ADDRESS', 'host')
    port = info.getConfig('MASTER_ADDRESS', 'port')

    client = Client(address, port, configPath)
    client.start()
