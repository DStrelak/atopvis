import atop_resource
from atopsar_parser import AtopsarParser
import logging
import sys

LOGGER = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class AtopReport:
    def __init__(self, file):
        self.file = file
        self.resources = []
        self.resources.append(AtopsarParser.parse_cpu(file))
        self.resources.append(AtopsarParser.parse_memory(file))
        self.resources.extend(AtopsarParser.parse_drives(file))
        self.resources.extend(AtopsarParser.parse_gpus(file))
        self.processes = AtopsarParser.parse_processes(file)
        self.timeline = None
