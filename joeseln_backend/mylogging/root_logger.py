import logging, os
from logging import config

os.chdir(os.path.dirname(os.path.abspath(__file__)))

logging.config.fileConfig('logging.conf',
                          disable_existing_loggers=False)
# get root logger
logger = logging.getLogger(__name__)
