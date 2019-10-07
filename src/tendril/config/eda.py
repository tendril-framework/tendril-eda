

from tendril.utils.config import ConfigOption
from tendril.utils import log
logger = log.get_logger(__name__, log.DEFAULT)

depends = ['tendril.config.core']


config_elements_eda = [
    ConfigOption(
        'EDA_LIBRARY_FUSION',
        "True",
        "Whether to attempt fusion of multiple EDA symbol libraries. "
        "If True, will return symbols from the first library in the priority "
        "order within which a suitable candidate is found. If False, will "
        "only return symbols from the first library in the priority order."
    ),
    ConfigOption(
        'EDA_LIBRARY_PRIORITY',
        "['geda']",
        "Priority order for the EDA symbol libraries."
    )
]


def load(manager):
    logger.debug("Loading {0}".format(__name__))
    manager.load_elements(config_elements_eda,
                          doc="EDA Subsystem Configuration")
