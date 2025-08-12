# main.py (debug 起始版 — 覆蓋用，部署後把錯誤貼給我)
import os, traceback, sys
print("=== STARTUP DEBUG ===")
print("CWD:", os.getcwd())
print("LIST /app:")
for root, dirs, files in os.walk("/app"):
    # limit depth to avoid huge logs
    depth = root.count(os.sep) - 1
    indent = "  " * depth
    print(f"{indent}{os.path.basename(root)}/")
    for f in files:
        print(f"{indent}  - {f}")
print("=== END FILE TREE ===\n")

# try to import main components and print errors
try:
    # show python path
    print("sys.path:", sys.path)
    # Try to import the modules we expect
    import config
    print("[OK] imported config")
    from exchange.binance_client import BinanceClient
    print("[OK] imported exchange.binance_client")
    # strategies package
    try:
        import strategies
        print("[OK] strategies package found")
        import strategies.trend as trend_m
        print("[OK] strategies.trend loaded:", getattr(trend_m, '__file__', 'no-file'))
    except Exception as e:
        print("[ERR] loading strategies modules:", e)
        traceback.print_exc()
    # risk
    from risk.risk_mgr import RiskManager
    print("[OK] imported risk.risk_mgr")
except Exception as e:
    print("[IMPORT ERROR] Something failed during imports:")
    traceback.print_exc()

print("\n>>> Now attempting to run a minimal main loop to exercise startup (no orders).")
try:
    # if everything imported try a tiny run
    from exchange.binance_client import BinanceClient
    from strategies.signal_generator import SignalGenerator
    from risk.risk_mgr import RiskManager
    from config import BINANCE_API_KEY, BINANCE_API_SECRET, SYMBOL_POOL, MIN_NOTIONAL, EQUITY_RATIO_PER_TRADE

    client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET)
    print("[DEBUG] BinanceClient created")
    sg = SignalGenerator(client)
    print("[DEBUG] SignalGenerator created")
    rm = RiskManager(client, EQUITY_RATIO_PER_TRADE)
    print("[DEBUG] RiskManager created")
    print("Startup smoke test done. Now exiting (no live loop).")
except Exception as e:
    print("[RUNTIME ERROR] during minimal run:")
    traceback.print_exc()

# keep the process alive if you want to inspect logs further
# Commented out: infinite loop not desired on Railway; simply exit.
print("=== DEBUG MAIN END ===")
