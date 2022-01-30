"""Kucoin exchange subclass."""
import logging
from typing import Dict

from panther.exchange import Exchange


logger = logging.getLogger(__name__)


class Kucoin(Exchange):
    """Kucoin exchange class.

    Contains adjustments needed for Panther to work with this exchange.

    Please note that this exchange is not included in the list of exchanges
    officially supported by the Panther development team. So some features
    may still not work as expected.
    """

    _ft_has: Dict = {
        "l2_limit_range": [20, 100],
        "l2_limit_range_required": False,
        "order_time_in_force": ['gtc', 'fok', 'ioc'],
        "time_in_force_parameter": "timeInForce",
    }
