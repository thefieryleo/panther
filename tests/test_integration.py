from unittest.mock import MagicMock

import pytest

from panther.enums import SellType
from panther.persistence import Trade
from panther.rpc.rpc import RPC
from panther.strategy.interface import SellCheckTuple
from tests.conftest import get_patched_pantherbot, patch_get_signal


def test_may_execute_exit_stoploss_on_exchange_multi(default_conf, ticker, fee,
                                                     limit_buy_order, mocker) -> None:
    """
    Tests workflow of selling stoploss_on_exchange.
    Sells
    * first trade as stoploss
    * 2nd trade is kept
    * 3rd trade is sold via sell-signal
    """
    default_conf['max_open_trades'] = 3
    default_conf['exchange']['name'] = 'binance'

    stoploss = {
        'id': 123,
        'info': {}
    }
    stoploss_order_open = {
        "id": "123",
        "timestamp": 1542707426845,
        "datetime": "2018-11-20T09:50:26.845Z",
        "lastTradeTimestamp": None,
        "symbol": "BTC/USDT",
        "type": "stop_loss_limit",
        "side": "sell",
        "price": 1.08801,
        "amount": 90.99181074,
        "cost": 0.0,
        "average": 0.0,
        "filled": 0.0,
        "remaining": 0.0,
        "status": "open",
        "fee": None,
        "trades": None
    }
    stoploss_order_closed = stoploss_order_open.copy()
    stoploss_order_closed['status'] = 'closed'
    stoploss_order_closed['filled'] = stoploss_order_closed['amount']

    # Sell first trade based on stoploss, keep 2nd and 3rd trade open
    stoploss_order_mock = MagicMock(
        side_effect=[stoploss_order_closed, stoploss_order_open, stoploss_order_open])
    # Sell 3rd trade (not called for the first trade)
    should_sell_mock = MagicMock(side_effect=[
        SellCheckTuple(sell_type=SellType.NONE),
        SellCheckTuple(sell_type=SellType.SELL_SIGNAL)]
    )
    cancel_order_mock = MagicMock()
    mocker.patch('panther.exchange.Binance.stoploss', stoploss)
    mocker.patch.multiple(
        'panther.exchange.Exchange',
        fetch_ticker=ticker,
        get_fee=fee,
        amount_to_precision=lambda s, x, y: y,
        price_to_precision=lambda s, x, y: y,
        fetch_stoploss_order=stoploss_order_mock,
        cancel_stoploss_order_with_result=cancel_order_mock,
    )

    mocker.patch.multiple(
        'panther.pantherbot.PantherBot',
        create_stoploss_order=MagicMock(return_value=True),
        _notify_exit=MagicMock(),
    )
    mocker.patch("panther.strategy.interface.IStrategy.should_sell", should_sell_mock)
    wallets_mock = mocker.patch("panther.wallets.Wallets.update", MagicMock())
    mocker.patch("panther.wallets.Wallets.get_free", MagicMock(return_value=1000))

    panther = get_patched_pantherbot(mocker, default_conf)
    panther.strategy.order_types['stoploss_on_exchange'] = True
    # Switch ordertype to market to close trade immediately
    panther.strategy.order_types['sell'] = 'market'
    panther.strategy.confirm_trade_entry = MagicMock(return_value=True)
    panther.strategy.confirm_trade_exit = MagicMock(return_value=True)
    patch_get_signal(panther)

    # Create some test data
    panther.enter_positions()
    assert panther.strategy.confirm_trade_entry.call_count == 3
    panther.strategy.confirm_trade_entry.reset_mock()
    assert panther.strategy.confirm_trade_exit.call_count == 0
    wallets_mock.reset_mock()

    trades = Trade.query.all()
    # Make sure stoploss-order is open and trade is bought (since we mock update_trade_state)
    for trade in trades:
        trade.stoploss_order_id = 3
        trade.open_order_id = None

    n = panther.exit_positions(trades)
    assert n == 2
    assert should_sell_mock.call_count == 2
    assert panther.strategy.confirm_trade_entry.call_count == 0
    assert panther.strategy.confirm_trade_exit.call_count == 1
    panther.strategy.confirm_trade_exit.reset_mock()

    # Only order for 3rd trade needs to be cancelled
    assert cancel_order_mock.call_count == 1
    # Wallets must be updated between stoploss cancellation and selling, and will be updated again
    # during update_trade_state
    assert wallets_mock.call_count == 4

    trade = trades[0]
    assert trade.sell_reason == SellType.STOPLOSS_ON_EXCHANGE.value
    assert not trade.is_open

    trade = trades[1]
    assert not trade.sell_reason
    assert trade.is_open

    trade = trades[2]
    assert trade.sell_reason == SellType.SELL_SIGNAL.value
    assert not trade.is_open


@pytest.mark.parametrize("balance_ratio,result1", [
                        (1, 200),
                        (0.99, 198),
])
def test_forcebuy_last_unlimited(default_conf, ticker, fee, mocker, balance_ratio, result1) -> None:
    """
    Tests workflow unlimited stake-amount
    Buy 4 trades, forcebuy a 5th trade
    Sell one trade, calculated stake amount should now be lower than before since
    one trade was sold at a loss.
    """
    default_conf['max_open_trades'] = 5
    default_conf['forcebuy_enable'] = True
    default_conf['stake_amount'] = 'unlimited'
    default_conf['tradable_balance_ratio'] = balance_ratio
    default_conf['dry_run_wallet'] = 1000
    default_conf['exchange']['name'] = 'binance'
    default_conf['telegram']['enabled'] = True
    mocker.patch('panther.rpc.telegram.Telegram', MagicMock())
    mocker.patch.multiple(
        'panther.exchange.Exchange',
        fetch_ticker=ticker,
        get_fee=fee,
        amount_to_precision=lambda s, x, y: y,
        price_to_precision=lambda s, x, y: y,
    )

    mocker.patch.multiple(
        'panther.pantherbot.PantherBot',
        create_stoploss_order=MagicMock(return_value=True),
        _notify_exit=MagicMock(),
    )
    should_sell_mock = MagicMock(side_effect=[
        SellCheckTuple(sell_type=SellType.NONE),
        SellCheckTuple(sell_type=SellType.SELL_SIGNAL),
        SellCheckTuple(sell_type=SellType.NONE),
        SellCheckTuple(sell_type=SellType.NONE),
        SellCheckTuple(sell_type=SellType.NONE)]
    )
    mocker.patch("panther.strategy.interface.IStrategy.should_sell", should_sell_mock)

    panther = get_patched_pantherbot(mocker, default_conf)
    rpc = RPC(panther)
    panther.strategy.order_types['stoploss_on_exchange'] = True
    # Switch ordertype to market to close trade immediately
    panther.strategy.order_types['sell'] = 'market'
    patch_get_signal(panther)

    # Create 4 trades
    n = panther.enter_positions()
    assert n == 4

    trades = Trade.query.all()
    assert len(trades) == 4
    assert panther.wallets.get_trade_stake_amount('XRP/BTC') == result1

    rpc._rpc_forcebuy('TKN/BTC', None)

    trades = Trade.query.all()
    assert len(trades) == 5

    for trade in trades:
        assert trade.stake_amount == result1
        # Reset trade open order id's
        trade.open_order_id = None
    trades = Trade.get_open_trades()
    assert len(trades) == 5
    bals = panther.wallets.get_all_balances()

    n = panther.exit_positions(trades)
    assert n == 1
    trades = Trade.get_open_trades()
    # One trade sold
    assert len(trades) == 4
    # stake-amount should now be reduced, since one trade was sold at a loss.
    assert panther.wallets.get_trade_stake_amount('XRP/BTC') < result1
    # Validate that balance of sold trade is not in dry-run balances anymore.
    bals2 = panther.wallets.get_all_balances()
    assert bals != bals2
    assert len(bals) == 6
    assert len(bals2) == 5
    assert 'LTC' in bals
    assert 'LTC' not in bals2


def test_dca_buying(default_conf_usdt, ticker_usdt, fee, mocker) -> None:
    default_conf_usdt['position_adjustment_enable'] = True

    panther = get_patched_pantherbot(mocker, default_conf_usdt)
    mocker.patch.multiple(
        'panther.exchange.Exchange',
        fetch_ticker=ticker_usdt,
        get_fee=fee,
        amount_to_precision=lambda s, x, y: y,
        price_to_precision=lambda s, x, y: y,
    )

    patch_get_signal(panther)
    panther.enter_positions()

    assert len(Trade.get_trades().all()) == 1
    trade = Trade.get_trades().first()
    assert len(trade.orders) == 1
    assert trade.stake_amount == 60
    assert trade.open_rate == 2.0
    # No adjustment
    panther.process()
    trade = Trade.get_trades().first()
    assert len(trade.orders) == 1
    assert trade.stake_amount == 60

    # Reduce bid amount
    ticker_usdt_modif = ticker_usdt.return_value
    ticker_usdt_modif['bid'] = ticker_usdt_modif['bid'] * 0.995
    mocker.patch('panther.exchange.Exchange.fetch_ticker', return_value=ticker_usdt_modif)

    # additional buy order
    panther.process()
    trade = Trade.get_trades().first()
    assert len(trade.orders) == 2
    for o in trade.orders:
        assert o.status == "closed"
    assert trade.stake_amount == 120

    # Open-rate averaged between 2.0 and 2.0 * 0.995
    assert trade.open_rate < 2.0
    assert trade.open_rate > 2.0 * 0.995

    # No action - profit raised above 1% (the bar set in the strategy).
    panther.process()
    trade = Trade.get_trades().first()
    assert len(trade.orders) == 2
    assert trade.stake_amount == 120
    assert trade.orders[0].amount == 30
    assert trade.orders[1].amount == 60 / ticker_usdt_modif['bid']

    assert trade.amount == trade.orders[0].amount + trade.orders[1].amount
    assert trade.nr_of_successful_buys == 2

    # Sell
    patch_get_signal(panther, value=(False, True, None, None))
    panther.process()
    trade = Trade.get_trades().first()
    assert trade.is_open is False
    assert trade.orders[0].amount == 30
    assert trade.orders[0].side == 'buy'
    assert trade.orders[1].amount == 60 / ticker_usdt_modif['bid']
    # Sold everything
    assert trade.orders[-1].side == 'sell'
    assert trade.orders[2].amount == trade.amount

    assert trade.nr_of_successful_buys == 2
