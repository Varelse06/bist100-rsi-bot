import os
import asyncio
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from telegram import Bot

"""BIST‑100 RSI Telegram Bot (async ‑ PTB v20+)
=================================================
• Gönderim eşiği: RSI < 35 veya > 70
• Veri kaynağı : Yahoo Finance (60‑dakikalık mumlar) – ^XU100
• Kontrol aralığı: 15 dakika (değiştirilebilir)

Nasıl kullanılır
----------------
1. python bist100_rsi_bot.py  🚀
"""

############################################################
# 1️⃣  AYARLAR
############################################################
TELEGRAM_TOKEN = "7881664727:AAEuR2uBTNoOlYg7B32b8JPOtwOO2f9Ryxw"
CHAT_ID        = "-1002727685944"  # ← BURAYA kendi chat ID'ni yaz

LOWER_THRESHOLD = 35
UPPER_THRESHOLD = 70
POLL_INTERVAL   = 15 * 60    # saniye (15 dk)
RSI_PERIOD      = 14         # standart RSI periyodu
YF_INTERVAL     = "60m"      # 15m XU100 için yok → 60m kullandık
TICKER          = "^XU100"   # BIST 100 endeksi
############################################################


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Basit RSI hesaplama (wilders ema yerine SMA kullanır)."""
    delta = series.diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = up.rolling(window=period).mean()
    avg_loss = down.rolling(window=period).mean().replace(0, 1e-9)
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


class BistRsiBot:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token)
        self.chat_id = chat_id
        self.last_state: str | None = None  # "low" | "high" | None

    async def send(self, text: str):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as exc:
            print(f"[TELEGRAM ERROR] {exc}")

    async def fetch_rsi(self) -> float:
        """En son RSI değerini getir."""
        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=30)  # yeterli geçmiş

        df = yf.download(
            TICKER,
            start=start,
            end=end,
            interval=YF_INTERVAL,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            raise RuntimeError("Yahoo Finance veri döndüremedi (muhtemelen endeks 60m desteklemiyor).")
        last_rsi = rsi(df["Close"], RSI_PERIOD).iloc[-1]
        return float(last_rsi)

    async def run(self):
        await self.send("BIST 100 RSI botu başlatıldı ✅")
        while True:
            try:
                value = await self.fetch_rsi()
                now   = datetime.now().strftime("%Y‑%m‑d %H:%M")

                if value < LOWER_THRESHOLD and self.last_state != "low":
                    await self.send(f"⚠️ {now}: RSI {value:.2f} (<{LOWER_THRESHOLD}) – Aşırı SATIŞ")
                    self.last_state = "low"
                elif value > UPPER_THRESHOLD and self.last_state != "high":
                    await self.send(f"🚀 {now}: RSI {value:.2f} (>{UPPER_THRESHOLD}) – Aşırı ALIM")
                    self.last_state = "high"
                elif LOWER_THRESHOLD <= value <= UPPER_THRESHOLD:
                    self.last_state = None
            except Exception as exc:
                print(f"[ERROR] {exc}")
            await asyncio.sleep(POLL_INTERVAL)


def main():
    if "PASTE_YOUR_BOT_TOKEN_HERE" in TELEGRAM_TOKEN or "PASTE_CHAT_ID_HERE" in CHAT_ID:
        raise SystemExit("TELEGRAM_TOKEN ve CHAT_ID girilmemiş!")
    bot = BistRsiBot(TELEGRAM_TOKEN, CHAT_ID)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
