from typing import Dict

# Very simple in-memory market data for demo purposes - US stocks only
MOCK_PRICES: Dict[str, float] = {
    "AAPL.US": 190.0,
    "TSLA.US": 250.0,
    "MSFT.US": 420.0,
    "GOOGL.US": 140.0,
    "AMZN.US": 155.0,
    "NVDA.US": 875.0,
    "META.US": 485.0,
}


def get_last_price(symbol: str, market: str) -> float:
    key = f"{symbol}.{market}"
    return MOCK_PRICES.get(key, 100.0)
