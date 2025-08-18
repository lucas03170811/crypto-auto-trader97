import math

# 最小名目要求
MIN_NOTIONAL = {
    "BTCUSDT": 100,
    "ETHUSDT": 20,
    "LINKUSDT": 20,
    # 其他通通用 5
    "DEFAULT": 5
}

def adjust_qty(symbol: str, qty: float, price: float, step_size: float) -> float:
    """
    保證 qty 不為 0，且達到最小名目限制
    """
    # 取得最小名目
    min_notional = MIN_NOTIONAL.get(symbol, MIN_NOTIONAL["DEFAULT"])

    # 如果金額不夠，強制拉到最小
    notional = qty * price
    if notional < min_notional:
        qty = min_notional / price

    # 對齊交易所 step_size
    if step_size > 0:
        qty = math.floor(qty / step_size) * step_size

    # 防止 qty=0，強制設為 step_size
    if qty <= 0:
        qty = step_size

    return round(qty, 8)
