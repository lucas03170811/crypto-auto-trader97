from __future__ import annotations
from typing import Optional
from config import DESIRED_TRADE_USD_DEFAULT, DEBUG_MODE

def plan_final_qty(
    client,
    symbol: str,
    price: float,
    desired_usd: float | None = None,
) -> Optional[float]:
    """
    回傳「最終可下單數量」；若資金不足或規則取不到則回傳 None
    規則：
      1) 先用 desired_usd（預設 6U）換算 qty
      2) 再強制拉到 minNotional（向上對齊 stepSize）
      3) 若可用 USDT 不足以覆蓋 minNotional，則跳過
    """
    try:
        f = client.get_symbol_filters(symbol)
        step = f["step_size"]
        min_notional = f["min_notional"]
    except Exception as e:
        if DEBUG_MODE:
            print(f"[WARN] 取不到 {symbol} 規則：{e}")
        return None

    if price <= 0:
        return None

    target_usd = float(desired_usd or DESIRED_TRADE_USD_DEFAULT)
    qty = target_usd / price

    # 拉到滿足最小名目 + 向上對齊
    qty = client.ensure_min_notional(qty, price, min_notional, step)

    # 檢查資金是否能 cover「至少」min_notional
    need_usd = max(target_usd, min_notional)
    free = client.get_available_usdt()
    if free < need_usd:
        if DEBUG_MODE:
            print(f"[SKIP] {symbol} 可用USDT不足：free={free:.4f} < need={need_usd:.4f}")
        return None

    return qty
