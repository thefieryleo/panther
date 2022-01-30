import logging
from typing import Dict

from panther.exchange import Exchange


logger = logging.getLogger(__name__)


class Okex(Exchange):
    """Okex exchange class.

    Contains adjustments needed for Panther to work with this exchange.
    """

    _ft_has: Dict = {
        "ohlcv_candle_limit": 300,
    }
