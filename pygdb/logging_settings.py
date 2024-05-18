import logging
import sys

logger = logging.getLogger('default-logger')

file_handler = logging.FileHandler('pygdb.log', mode='w')
stdout_handler = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%H:%M:%S')
file_handler.setFormatter(formatter); stdout_handler.setFormatter(formatter)

logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

