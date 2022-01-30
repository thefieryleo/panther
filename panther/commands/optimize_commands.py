import logging
from typing import Any, Dict

from panther import constants
from panther.configuration import setup_utils_configuration
from panther.enums import RunMode
from panther.exceptions import OperationalException
from panther.misc import round_coin_value


logger = logging.getLogger(__name__)


def setup_optimize_configuration(args: Dict[str, Any], method: RunMode) -> Dict[str, Any]:
    """
    Prepare the configuration for the Hyperopt module
    :param args: Cli args from Arguments()
    :param method: Bot running mode
    :return: Configuration
    """
    config = setup_utils_configuration(args, method)

    no_unlimited_runmodes = {
        RunMode.BACKTEST: 'backtesting',
        RunMode.HYPEROPT: 'hyperoptimization',
    }
    if method in no_unlimited_runmodes.keys():
        if (config['stake_amount'] != constants.UNLIMITED_STAKE_AMOUNT
                and config['stake_amount'] > config['dry_run_wallet']):
            wallet = round_coin_value(config['dry_run_wallet'], config['stake_currency'])
            stake = round_coin_value(config['stake_amount'], config['stake_currency'])
            raise OperationalException(f"Starting balance ({wallet}) "
                                       f"is smaller than stake_amount {stake}.")

    return config


def start_backtesting(args: Dict[str, Any]) -> None:
    """
    Start Backtesting script
    :param args: Cli args from Arguments()
    :return: None
    """
    # Import here to avoid loading backtesting module when it's not used
    from panther.optimize.backtesting import Backtesting

    # Initialize configuration
    config = setup_optimize_configuration(args, RunMode.BACKTEST)

    logger.info('Starting panther in Backtesting mode')

    # Initialize backtesting object
    backtesting = Backtesting(config)
    backtesting.start()


def start_backtesting_show(args: Dict[str, Any]) -> None:
    """
    Show previous backtest result
    """

    config = setup_utils_configuration(args, RunMode.UTIL_NO_EXCHANGE)

    from panther.data.btanalysis import load_backtest_stats
    from panther.optimize.optimize_reports import show_backtest_results, show_sorted_pairlist

    results = load_backtest_stats(config['exportfilename'])

    show_backtest_results(config, results)
    show_sorted_pairlist(config, results)


def start_hyperopt(args: Dict[str, Any]) -> None:
    """
    Start hyperopt script
    :param args: Cli args from Arguments()
    :return: None
    """
    # Import here to avoid loading hyperopt module when it's not used
    try:
        from filelock import FileLock, Timeout

        from panther.optimize.hyperopt import Hyperopt
    except ImportError as e:
        raise OperationalException(
            f"{e}. Please ensure that the hyperopt dependencies are installed.") from e
    # Initialize configuration
    config = setup_optimize_configuration(args, RunMode.HYPEROPT)

    logger.info('Starting panther in Hyperopt mode')

    lock = FileLock(Hyperopt.get_lock_filename(config))

    try:
        with lock.acquire(timeout=1):

            # Remove noisy log messages
            logging.getLogger('hyperopt.tpe').setLevel(logging.WARNING)
            logging.getLogger('filelock').setLevel(logging.WARNING)

            # Initialize backtesting object
            hyperopt = Hyperopt(config)
            hyperopt.start()

    except Timeout:
        logger.info("Another running instance of panther Hyperopt detected.")
        logger.info("Simultaneous execution of multiple Hyperopt commands is not supported. "
                    "Hyperopt module is resource hungry. Please run your Hyperopt sequentially "
                    "or on separate machines.")
        logger.info("Quitting now.")
        # TODO: return False here in order to help panther to exit
        # with non-zero exit code...
        # Same in Edge and Backtesting start() functions.


def start_edge(args: Dict[str, Any]) -> None:
    """
    Start Edge script
    :param args: Cli args from Arguments()
    :return: None
    """
    from panther.optimize.edge_cli import EdgeCli

    # Initialize configuration
    config = setup_optimize_configuration(args, RunMode.EDGE)
    logger.info('Starting panther in Edge mode')

    # Initialize Edge object
    edge_cli = EdgeCli(config)
    edge_cli.start()