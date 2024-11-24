import logging
from modules.client import client, scheduler
import modules.commands

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S %Z'
)

if __name__ == '__main__':
    scheduler.start()
    client.run_until_disconnected()
