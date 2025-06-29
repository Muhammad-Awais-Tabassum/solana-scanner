import asyncio
import logging
from datetime import datetime
from utils.api_clients import HeliusClient, BirdeyeClient, TelegramClient
from utils.filters import NewMintFilter, GraduatedTokenFilter, TrendingTokenFilter
from utils.alerts import AlertManager
from config import load_config

class TokenMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.processed_tokens = set()
        
        # Initialize clients
        self.helius = HeliusClient(config['helius_api_key'])
        self.birdeye = BirdeyeClient(config['birdeye_api_key'])
        self.telegram = TelegramClient(
            config['telegram_bot_token'],
            config['telegram_chat_id']
        )
        
        # Initialize filters
        self.filters = {
            'new': NewMintFilter(config['blacklisted_deployers']),
            'graduated': GraduatedTokenFilter(config['blacklisted_deployers']),
            'trending': TrendingTokenFilter()
        }
        
        # Initialize alert manager
        self.alert_manager = AlertManager(self.telegram)

    async def cleanup(self):
        await self.helius.close()
        await self.birdeye.close()
        await self.telegram.close()

    async def get_new_mints(self) -> list:
        """Fetch new token mints from Helius"""
        data = await self.helius.get_recent_mints(limit=100)
        return data.get('result', [])

    async def get_trending_tokens(self) -> list:
        """Fetch trending tokens from Birdeye"""
        data = await self.birdeye.get_trending_tokens()
        return data.get('data', {}).get('tokens', [])

    async def batch_process_tokens(self, tokens: list, token_type: str) -> list:
        """Batch process tokens with parallel API calls"""
        if not tokens:
            return []

        mint_addresses = [t['mint'] if 'mint' in t else t['address'] for t in tokens]
        
        # Batch fetch all required data
        metadata_tasks = [self.helius.get_token_metadata(mint) for mint in mint_addresses]
        price_tasks = [self.birdeye.get_token_price(mint) for mint in mint_addresses]
        
        if token_type in ['new', 'graduated']:
            holders_tasks = [self.helius.get_token_holders(mint) for mint in mint_addresses]
            holders_results = await asyncio.gather(*holders_tasks)
        else:
            holders_results = [None] * len(mint_addresses)
            
        metadata_results, price_results = await asyncio.gather(
            asyncio.gather(*metadata_tasks),
            asyncio.gather(*price_tasks)
        )

        filtered = []
        for token, metadata, holders, price in zip(tokens, metadata_results, holders_results, price_results):
            if not all([metadata, price]):
                continue
                
            if token_type == 'new' and self.filters['new'].filter(token, metadata, holders, price):
                token['metrics'] = self._calculate_new_mint_metrics(holders, price)
                filtered.append(token)
            elif token_type == 'graduated' and holders and self.filters['graduated'].filter(token, metadata, holders, price):
                token['metrics'] = self._calculate_graduated_metrics(holders, price)
                filtered.append(token)
            elif token_type == 'trending' and self.filters['trending'].filter(token, price):
                token['metrics'] = self._calculate_trending_metrics(price)
                filtered.append(token)
                
            self.processed_tokens.add(token['mint'] if 'mint' in token else token['address'])
        
        return filtered

    async def monitor(self):
        """Main monitoring loop with optimized processing"""
        while True:
            start_time = datetime.now()
            
            try:
                # Parallel fetch all token types
                new_mints, trending = await asyncio.gather(
                    self.get_new_mints(),
                    self.get_trending_tokens()
                )
                
                # Parallel process all token types
                filtered_new, filtered_trend = await asyncio.gather(
                    self.batch_process_tokens(new_mints, 'new'),
                    self.batch_process_tokens(trending, 'trending')
                )
                
                # Send alerts in parallel
                alert_tasks = []
                for token in filtered_new:
                    alert_tasks.append(self.alert_manager.send_token_alert(token, "New Mint"))
                for token in filtered_trend:
                    alert_tasks.append(self.alert_manager.send_token_alert(token, "Trending"))
                
                await asyncio.gather(*alert_tasks)
                
                # Dynamic sleep based on processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                sleep_time = max(30, 60 - processing_time)
                logging.info(f"Cycle completed in {processing_time:.2f}s. Next run in {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"Monitoring error: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying

async def main():
    config = load_config()
    monitor = TokenMonitor(config)
    try:
        await monitor.monitor()
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())