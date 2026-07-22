
def find_local_extrema(prices: list[float], window: int = 5):
    support    = []
    resistance = []

    for i in range(window, len(prices) - window):
        left= prices[i - window: i]
        right= prices[i + 1: i + window + 1]
        price= prices[i]

        if all(price <= p for p in left) and all(price <= p for p in right):
            support.append(price)

        if all(price >= p for p in left) and all(price >= p for p in right):
            resistance.append(price)

    return support, resistance


def cluster_levels(levels: list[float], tolerance: float = 0.015) -> list[dict]:
    if not levels:
        return []

    levels = sorted(levels)
    clusters = []
    current_cluster = [levels[0]]

    for level in levels[1:]:
        if (level - current_cluster[0]) / current_cluster[0] <= tolerance:
            current_cluster.append(level)
        else:
            clusters.append(current_cluster)
            current_cluster = [level]

    clusters.append(current_cluster)

    result = []
    for cluster in clusters:
        avg     = round(sum(cluster) / len(cluster), 2)
        touches = len(cluster)
        strength = "Strong" if touches >= 3 else "Moderate" if touches == 2 else "Weak"
        result.append({"level": avg, "touches": touches, "strength": strength})

    return sorted(result, key=lambda x: x["touches"], reverse=True)


def calculate_targets(price_history: dict, fundamentals: dict) -> dict:
    closes = price_history.get("close", [])
    highs  = price_history.get("high",  [])
    lows   = price_history.get("low",   [])

    if not closes or len(closes) < 20:
        return {"error": "Insufficient price history for target calculation."}

    current_price = closes[-1]

    raw_support,    _              = find_local_extrema(lows,   window=5)
    _,              raw_resistance = find_local_extrema(highs,  window=5)
    close_support,  close_resistance = find_local_extrema(closes, window=5)

    all_support    = cluster_levels(raw_support    + close_support)
    all_resistance = cluster_levels(raw_resistance + close_resistance)

    support_below = sorted(
        [s for s in all_support    if s["level"] < current_price * 0.99],
        key=lambda x: x["level"], reverse=True
    )
    resistance_above = sorted(
        [r for r in all_resistance if r["level"] > current_price * 1.01],
        key=lambda x: x["level"]
    )

    buy_target  = support_below[0]    if support_below    else None
    sell_target = resistance_above[0] if resistance_above else None
    stop_loss   = support_below[1]    if len(support_below) > 1 else None

    risk_reward = None
    if buy_target and sell_target and stop_loss:
        potential_gain = sell_target["level"] - buy_target["level"]
        potential_loss = buy_target["level"]  - stop_loss["level"]
        if potential_loss > 0:
            risk_reward = round(potential_gain / potential_loss, 2)

    parts = []
    if buy_target:
        parts.append(f"Buy zone: {buy_target['level']} ({buy_target['strength']} support, {buy_target['touches']} touches)")
    if sell_target:
        parts.append(f"Sell target: {sell_target['level']} ({sell_target['strength']} resistance, {sell_target['touches']} touches)")
    if stop_loss:
        parts.append(f"Stop loss: {stop_loss['level']} (below next support)")
    if risk_reward:
        rating = "Favourable" if risk_reward >= 2 else "Acceptable" if risk_reward >= 1 else "Poor"
        parts.append(f"Risk/Reward: {risk_reward}:1 ({rating})")
    parts.append("This is not financial advice. Consult a licensed financial advisor before trading.")

    return {
        "current_price":     current_price,
        "buy_target":        buy_target,
        "sell_target":       sell_target,
        "stop_loss":         stop_loss,
        "risk_reward":       risk_reward,
        "support_levels":    support_below[:5],
        "resistance_levels": resistance_above[:5],
        "summary":           " | ".join(parts),
    }