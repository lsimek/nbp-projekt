"""
logger, can be modified to output
either to a file or stdout
"""
import logging
import sys

colors = {
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'white': '\033[37m',
    'reset': '\033[0m',
}

formats = {
    'DEBUG': f'{colors.get("reset")}{{}}',
    'INFO': f'{colors.get("green")}{{}}',
    'WARNING': f'{colors.get("yellow")}{{}}',
    'ERROR': f'{colors.get("red")}{{}}',
    'CRITICAL': f'{colors.get("red")}{{}}'
}

for k, v in formats.items():
    v += colors.get('reset')

counts = {k: 0 for k, _ in formats.items()}


class CountingHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def emit(self, record):
        counts[record.levelname] += 1


class ColoringFormatter(logging.Formatter):
    def format(self, record):
        buffer = ''
        delim = ' - '

        buffer += self.formatTime(record, '%H:%M:%S') + delim
        buffer += (levelname := record.levelname) + delim
        buffer += record.module + delim
        buffer += str(record.lineno) + delim
        buffer += record.funcName + delim
        buffer += record.getMessage() + delim

        return formats.get(levelname).format(buffer)[:-len(delim)]


logger = logging.getLogger('default-logger')

file_handler = logging.FileHandler('pygdb.log', mode='w')
stdout_handler = logging.StreamHandler(sys.stdout)
counting_handler = CountingHandler()

standard_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(funcName)s - %(message)s', '%H:%M:%S')
file_handler.setFormatter(standard_formatter)

coloring_formatter = ColoringFormatter()
stdout_handler.setFormatter(coloring_formatter)

logger.addHandler(stdout_handler)
logger.addHandler(counting_handler)


def get_stats():
    logger.info('Logging stats: ' + ' - '.join({formats.get(levelname).format(f'{count} {levelname}s') for levelname, count in counts.items()}))


logger.get_stats = get_stats

logger.setLevel(logging.DEBUG)