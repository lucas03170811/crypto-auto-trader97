import logging
import time
from binance.error import ClientError

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, client, leverage, max_loss_pct, equity_ratio):
        self.client = client
        self.leverage = leverage
        self.max_loss_pct = max_loss_pct
        self.equity_ratio = equity_ratio

    def execute_trade(self, symbol, side, quantity, max_retries=3):
        """
        執行交易，如果資金不足會自動縮小數量重試
        """
        attempt = 0
        q = quantity

        while attempt < max_retries:
            try:
                logger.info(f"[RISK] Try order {symbol} side={side} qty={q}")
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=q
                )
                logger.info(f"[ORDER SUCCESS] {symbol} side={side} qty={q}")
                return order

            except ClientError as e:
                # Binance 錯誤代碼 -2019 => 保證金不足
                if e.error_code == -2019:
                    attempt += 1
                    q = round(q * 0.5, 3)  # 每次縮小一半
                    logger.warning(f"[RISK] Margin insufficient for {symbol}, retry with smaller qty={q}")

                    if q <= 0:
                        logger.error(f"[RISK] Order qty too small, aborting {symbol}")
                        return None

                    time.sleep(1)  # 稍等再試
                    continue
                else:
                    logger.error(f"[RISK] execute_trade error {symbol}: {e}")
                    return None

            except Exception as e:
                logger.error(f"[RISK] Unexpected error {symbol}: {e}")
                return None

        logger.error(f"[RISK] Failed to execute {symbol} after {max_retries} retries")
        return None
