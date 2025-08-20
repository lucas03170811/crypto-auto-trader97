from decimal import Decimal
from typing import Tuple
from config import MIN_NOTIONAL, DEFAULT_MIN_NOTIONAL, ADD_SIZE_MULTIPLIER

def target_notional(symbol: str) -> float:
    return float(MIN_NOTIONAL.get(symbol, DEFAULT_MIN_NOTIONAL))

def compute_base_qty(symbol: str, price: float, step: Decimal) -> float:
    """
    依目標名目金額 -> 算出下單數量，並確保 >= step
    """
    notional = target_notional(symbol)
    raw = notional / max(price, 1e-12)
    # 將對齊交給 exchange 層再做一次，這裡只保證不為 0
    if raw < float(step):
        raw = float(step)
    return raw

def compute_add_qty(symbol: str, base_qty: float) -> float:
    """
    每次加碼量 = 基礎下單量 * ADD_SIZE_MULTIPLIER
    """
    return max(base_qty * ADD_SIZE_MULTIPLIER, 0.0)
