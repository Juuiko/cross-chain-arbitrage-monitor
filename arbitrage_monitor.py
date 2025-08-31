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
        self.min_spread_pct = 0.2
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

        return prices

    async def fetch_binance_prices(self) -> List[PriceData]:
        """
        Fetch prices from Binance API
        """
        # Map our symbols to Binance format
        binance_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
        symbol_map = {
            'BTCUSDT': 'BTCUSD',
            'ETHUSDT': 'ETHUSD',
            'SOLUSDT': 'SOLUSD',
            'AVAXUSDT': 'AVAXUSD'
        }

        url = "https://api.binance.com/api/v3/ticker/24hr"
        prices = []

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    tickers = await response.json()

                    for ticker in tickers:
                        if ticker['symbol'] in binance_symbols:
                            prices.append(PriceData(
                                exchange='binance',
                                symbol=symbol_map[ticker['symbol']],
                                price=float(ticker['lastPrice']),
                                volume_24h=float(ticker['volume']),
                                timestamp=datetime.now()
                            ))
        except Exception as e:
            logger.error(f"Error fetching Binance prices: {e}")

        return prices

    async def fetch_all_prices(self) -> Dict[str, List[PriceData]]:
        """
        Fetch prices from all exchanges concurrently
        """
        tasks = [
            self.fetch_coinbase_prices(),
            self.fetch_coingecko_prices(),
            self.fetch_binance_prices()
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

        return grouped_prices

    def find_arbitrage_opportunities(self, price_groups: Dict[str, List[PriceData]]) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities from grouped price data
        """
        opportunities = []

        for symbol, prices in price_groups.items():
            if len(prices) < 2:
                continue

            # Sort by price to find min and max
            sorted_prices = sorted(prices, key=lambda x: x.price)
            min_price = sorted_prices[0]
            max_price = sorted_prices[-1]

            # Calculate spread percentage
            spread_pct = ((max_price.price - min_price.price) / min_price.price) * 100

            if spread_pct >= self.min_spread_pct:
                opportunity = ArbitrageOpportunity(
                    symbol=symbol,
                    buy_exchange=min_price.exchange,
                    sell_exchange=max_price.exchange,
                    buy_price=min_price.price,
                    sell_price=max_price.price,
                    spread_pct=spread_pct,
                    timestamp=datetime.now()
                )
                opportunities.append(opportunity)

        return opportunities

    @staticmethod
    def log_opportunities(opportunities: List[ArbitrageOpportunity]):
        """Log found opportunities to console"""
        if not opportunities:
            logger.info("No arbitrage opportunities found")
            return

        logger.info(f"Found {len(opportunities)} arbitrage opportunities:")
        for opp in opportunities:
            logger.info(
                f"🚀 {opp.symbol}: Buy {opp.buy_exchange} @ ${opp.buy_price:.2f} | "
                f"Sell {opp.sell_exchange} @ ${opp.sell_price:.2f} | "
                f"Spread: {opp.spread_pct:.2f}%"
            )

    @staticmethod
    def save_to_csv(opportunities: List[ArbitrageOpportunity], filename: str = "./data/opportunities.csv"):
        """Save opportunities to CSV using pandas"""
        if not opportunities:
            return

        df = pd.DataFrame([
            {
                'timestamp': opp.timestamp,
                'symbol': opp.symbol,
                'buy_exchange': opp.buy_exchange,
                'sell_exchange': opp.sell_exchange,
                'buy_price': opp.buy_price,
                'sell_price': opp.sell_price,
                'spread_pct': opp.spread_pct
            }
            for opp in opportunities
        ])

        # Append to existing file or create new
        try:
            existing_df = pd.read_csv(filename)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        except FileNotFoundError:
            combined_df = df

        combined_df.to_csv(filename, index=False)
        logger.info(f"Saved {len(opportunities)} opportunities to {filename}")

    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("🔍 Starting arbitrage monitoring cycle...")

        # Fetch prices from all exchanges
        price_groups = await self.fetch_all_prices()

        # Find opportunities
        opportunities = self.find_arbitrage_opportunities(price_groups)

        # Log opportunities in console
        self.log_opportunities(opportunities)

        # Save opportunities to our csv
        self.save_to_csv(opportunities)

        return opportunities

    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous monitoring loop"""
        logger.info(f"🚀 Starting continuous arbitrage monitoring (interval: {interval_seconds}s)")

        while True:
            try:
                await self.run_monitoring_cycle()
                await asyncio.sleep(interval_seconds)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(interval_seconds)


async def main():
    """Main entry point - run a few demo cycles"""
    async with ArbitrageMonitor() as monitor:
        # For MVP: run a few cycles then exit
        for i in range(5):
            logger.info(f"Cycle {i + 1}/5")
            await monitor.run_monitoring_cycle()
            await asyncio.sleep(10)

        print("MVP demo complete!")


if __name__ == "__main__":
    asyncio.run(main())