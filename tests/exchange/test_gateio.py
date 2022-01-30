import pytest

from panther.exceptions import OperationalException
from panther.exchange import Gateio
from panther.resolvers.exchange_resolver import ExchangeResolver


def test_validate_order_types_gateio(default_conf, mocker):
    default_conf['exchange']['name'] = 'gateio'
    mocker.patch('panther.exchange.Exchange._init_ccxt')
    mocker.patch('panther.exchange.Exchange._load_markets', return_value={})
    mocker.patch('panther.exchange.Exchange.validate_pairs')
    mocker.patch('panther.exchange.Exchange.validate_timeframes')
    mocker.patch('panther.exchange.Exchange.validate_stakecurrency')
    mocker.patch('panther.exchange.Exchange.name', 'Bittrex')
    exch = ExchangeResolver.load_exchange('gateio', default_conf, True)
    assert isinstance(exch, Gateio)

    default_conf['order_types'] = {
        'buy': 'market',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    with pytest.raises(OperationalException,
                       match=r'Exchange .* does not support market orders.'):
        ExchangeResolver.load_exchange('gateio', default_conf, True)
