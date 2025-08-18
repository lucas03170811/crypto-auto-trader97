    async def adjust_qty_for_min_notional(self, symbol: str, desired_qty: float) -> float:
        """
        Ensure qty is aligned to step and that notional >= min_notional.
        Includes DEBUG prints for troubleshooting.
        """
        price = await self.get_price(symbol)
        if price <= 0:
            print(f"[DEBUG][{symbol}] price invalid: {price}")
            return 0.0

        price_d = Decimal(str(price))
        step = await self.get_step_size(symbol)
        min_notional = await self.get_min_notional(symbol)

        qty_d = Decimal(str(desired_qty))
        notional = (qty_d * price_d).quantize(Decimal("0.00000001"))

        print(f"[DEBUG][{symbol}] desired_qty={qty_d}, desired_notional={notional}, step={step}, min_notional={min_notional}")

        min_step_qty = step if step > 0 else Decimal("0.00000001")

        if notional >= min_notional:
            aligned = self.round_down_to_step(qty_d, step)
            if aligned <= 0:
                aligned = self.round_up_to_step(min_step_qty, step)
            if (aligned * price_d) >= min_notional:
                print(f"[DEBUG][{symbol}] aligned_qty={aligned}, aligned_notional={(aligned*price_d)} ✅ ok")
                return float(aligned)

        # Need to increase qty to meet min_notional
        required_qty = (min_notional / price_d)
        if required_qty < min_step_qty:
            required_qty = min_step_qty

        required_aligned = self.round_up_to_step(required_qty, step)

        if (required_aligned * price_d) < min_notional:
            required_aligned = required_aligned + step

        print(f"[DEBUG][{symbol}] required_qty={required_qty}, required_aligned={required_aligned}, final_notional={(required_aligned*price_d)} ✅ ok")

        if required_aligned <= 0:
            print(f"[DEBUG][{symbol}] after adjustment still <=0 ❌")
            return 0.0
        return float(required_aligned)
