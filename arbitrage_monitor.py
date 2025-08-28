import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    exchange: str
    symbol: str
    price: float
    timestamp: datetime
    volume_24h: Optional[float] = None


@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    timestamp: datetime


class ArbitrageMonitor:
    def __init__(self):
        self.session = None
        self.price_data: Dict[str, List[PriceData]] = {}
        self.opportunities: List[ArbitrageOpportunity] = []
        self.min_spread_pct = 0.5
        self.symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD']

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_coinbase_prices(self) -> List[PriceData]:
        """
        Fetch prices from Coinbase Pro API
        """
        url = "https://api.exchange.coinbase.com/products"
        prices = []

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    products = await response.json()

                    for symbol in self.symbols:
                        # Get 24hr stats for each symbol
                        stats_url = f"https://api.exchange.coinbase.com/products/{symbol}/stats"
                        async with self.session.get(stats_url) as stats_response:
                            if stats_response.status == 200:
                                stats = await stats_response.json()
                                prices.append(PriceData(
                                    exchange='coinbase',
                                    symbol=symbol.replace('-', ''),  # Normalize symbol
                                    price=float(stats['last']),
                                    volume_24h=float(stats['volume']),
                                    timestamp=datetime.now()
                                ))
        except Exception as e:
            logger.error(f"Error fetching Coinbase prices: {e}")

        return prices

    async def fetch_coingecko_prices(self) -> List[PriceData]:
        """
        Fetch prices from CoinGecko API
        """
        symbol_map = {
            'BTCUSD': 'bitcoin',
            'ETHUSD': 'ethereum',
            'SOLUSD': 'solana',
            'AVAXUSD': 'avalanche-2'
        }

        ids = ','.join(symbol_map.values())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_vol=true"
        prices = []

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    for symbol, coin_id in symbol_map.items():
                        if coin_id in data:
                            coin_data = data[coin_id]
                            prices.append(PriceData(
                                exchange='coingecko',
                                symbol=symbol,
                                price=float(coin_data['usd']),
                                volume_24h=coin_data.get('usd_24h_vol'),
                                timestamp=datetime.now()
                            ))
        except Exception as e:
            logger.error(f"Error fetching CoinGecko prices: {e}")

        print(f"Fetched CoinGecko prices: {len(prices)}")

        return prices

    async def fetch_binance_prices(self) -> List[PriceData]:
        """
        Fetch prices from Binance API
        API: https://api.binance.com/api/v3/ticker/24hr
        """
        # TODO: Implement Binance API integration
        pass

    async def fetch_all_prices(self) -> Dict[str, List[PriceData]]:
        """
        Fetch prices from all exchanges concurrently
        """
        tasks = [
            self.fetch_coinbase_prices(),
            self.fetch_coingecko_prices()
            #self.fetch_binance_prices()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_prices = []

        for result in results:
            if isinstance(result, list):
                all_prices.extend(result)
            else:
                logger.error(f"Error in price fetch: {result}")

        # Group by symbol
        grouped_prices = {}
        for price in all_prices:
            if price.symbol not in grouped_prices:
                grouped_prices[price.symbol] = []
            grouped_prices[price.symbol].append(price)

        print(grouped_prices)

        return grouped_prices

    def find_arbitrage_opportunities(self, price_groups: Dict[str, List[PriceData]]) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities from grouped price data
        Logic: For each symbol, find min/max price across exchanges
        Calculate spread percentage: (max_price - min_price) / min_price * 100
        """
        # TODO: Implement arbitrage detection logic
        pass

    def log_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Log found opportunities to console"""
        # TODO: Format and log opportunities
        pass

    def save_to_csv(self, opportunities: List[ArbitrageOpportunity], filename: str = "opportunities.csv"):
        """Save opportunities to CSV using pandas"""
        # TODO: Convert opportunities to DataFrame
        # TODO: Append to existing CSV or create new one
        pass

    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        # TODO: Fetch all prices
        # TODO: Find opportunities
        # TODO: Log and save results
        pass

    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous monitoring loop"""
        # TODO: Implement continuous monitoring with error handling
        pass


async def main():
    """Main entry point - run a few demo cycles"""
    async with ArbitrageMonitor() as monitor:
        await monitor.fetch_all_prices()
    pass


if __name__ == "__main__":
    asyncio.run(main())