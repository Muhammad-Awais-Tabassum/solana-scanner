from typing import Dict, Optional
import logging

class BaseFilter:
    def __init__(self, blacklisted_deployers: set):
        self.blacklisted_deployers = blacklisted_deployers

    def _calculate_dev_holding(self, holders: Dict, deployer: str) -> float:
        if not holders or not deployer:
            return 0.0
        total_supply = float(holders.get('totalSupply', 1))
        deployer_holding = next(
            (float(h['amount']) for h in holders.get('holders', [])
            if h['address'] == deployer
        )
        return (deployer_holding / total_supply) * 100 if total_supply > 0 else 0.0

class NewMintFilter(BaseFilter):
    def filter(self, token: Dict, metadata: Dict, holders: Dict, price_data: Dict) -> bool:
        if token.get('deployer') in self.blacklisted_deployers:
            return False

        dev_holding = self._calculate_dev_holding(holders, token.get('deployer'))
        holder_count = len(holders.get('holders', []))
        volume = float(price_data.get('volume', {}).get('value', 0))
        market_cap = float(price_data.get('marketCap', 0))

        return all([
            dev_holding <= 15,
            holder_count >= 5,
            volume >= 3000,
            market_cap >= 7000,
            self._has_twitter_mention(metadata)
        ])

    def _has_twitter_mention(self, metadata: Dict) -> bool:
        return metadata.get('socials', {}).get('twitter') is not None

class GraduatedTokenFilter(BaseFilter):
    def filter(self, token: Dict, metadata: Dict, holders: Dict, price_data: Dict) -> bool:
        dev_holding = self._calculate_dev_holding(holders, token.get('deployer'))
        insider_holding = self._calculate_insider_holding(holders)
        
        return all([
            dev_holding <= 5,
            insider_holding <= 5,
            float(price_data.get('marketCap', 0)) >= 50000,
            float(price_data.get('volume', {}).get('value', 0)) >= 500000,
            self._has_social_mention(metadata),
            self._check_recent_volume(price_data),
            self._check_price_dump(token, price_data)
        ])

    def _calculate_insider_holding(self, holders: Dict) -> float:
        top_holders = sorted(
            holders.get('holders', []),
            key=lambda x: float(x['amount']),
            reverse=True
        )[:10]
        total = sum(float(h['amount']) for h in top_holders)
        return (total / float(holders.get('totalSupply', 1))) * 100

class TrendingTokenFilter:
    def filter(self, token: Dict, price_data: Dict) -> bool:
        volume = float(price_data.get('volume', {}).get('value', 0))
        market_cap = float(price_data.get('marketCap', 0))
        liquidity = float(price_data.get('liquidity', 0))
        
        return all([
            volume >= 5000,
            6000 <= market_cap <= 1000000,
            liquidity >= 8250
        ])