from typing import Dict
import logging
from collections import deque
import time

class AlertManager:
    def __init__(self, telegram_client, max_alerts: int = 15, timeframe: int = 60):
        self.telegram = telegram_client
        self.alert_times = deque(maxlen=max_alerts)
        self.timeframe = timeframe
        self.sent_alerts = set()  # Track alert IDs to prevent duplicates

    async def send_token_alert(self, token: Dict, token_type: str):
        alert_id = f"{token['mint']}-{token_type}"
        if alert_id in self.sent_alerts:
            return False

        if not self._check_alert_limits():
            logging.warning("Alert rate limit reached")
            return False

        message = self._format_message(token, token_type)
        try:
            await self.telegram.send_alert(message)
            self.sent_alerts.add(alert_id)
            self.alert_times.append(time.time())
            return True
        except Exception as e:
            logging.error(f"Failed to send alert: {str(e)}")
            return False

    def _check_alert_limits(self) -> bool:
        now = time.time()
        # Remove old alerts from the queue
        while self.alert_times and now - self.alert_times[0] > self.timeframe:
            self.alert_times.popleft()
        return len(self.alert_times) < self.alert_times.maxlen

    def _format_message(self, token: Dict, token_type: str) -> str:
        metrics = token.get('metrics', {})
        return (
            f"🚨 <b>{token_type} Alert</b> 🚨\n\n"
            f"🔹 <b>Token:</b> {token.get('name', 'Unknown')}\n"
            f"🔹 <b>Mint:</b> <code>{token.get('mint')}</code>\n"
            f"🔹 <b>Market Cap:</b> ${metrics.get('market_cap', 0):,.2f}\n"
            f"🔹 <b>Volume:</b> ${metrics.get('volume', 0):,.2f}\n"
            f"⚠️ <i>DYOR before trading</i> ⚠️"
        )