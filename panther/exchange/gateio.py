""" Gate.io exchange subclass """
import logging
from typing import Dict

from panther.exceptions import OperationalException
from panther.exchange import Exchange


logger = logging.getLogger(__name__)


class Gateio(Exchange):
    """
    Gate.io exchange class. Contains adjustments needed for Panther to work
    with this exchange.

    Please note that this exchange is not included in the list of exchanges
    officially supported by the Panther development team. So some features
    may still not work as expected.
    """

    _ft_has: Dict = {
        "ohlcv_candle_limit": 1000,
        "ohlcv_volume_currency": "quote",
    }

    _headers = {'X-Gate-Channel-Id': 'panther'}

    def validate_ordertypes(self, order_types: Dict) -> None:
        super().validate_ordertypes(order_types)

        if any(v == 'market' for k, v in order_types.items()):
            raise OperationalException(
                    f'Exchange {self.name} does not support market orders.')
