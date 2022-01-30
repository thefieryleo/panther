""" Bybit exchange subclass """
import logging
from typing import Dict

from panther.exchange import Exchange


logger = logging.getLogger(__name__)


class Bybit(Exchange):
    """
    Bybit exchange class. Contains adjustments needed for Panther to work
    with this exchange.

    Please note that this exchange is not included in the list of exchanges
    officially supported by the Panther development team. So some features
    may still not work as expected.
    """

    _ft_has: Dict = {
        "ohlcv_candle_limit": 200,
    }
