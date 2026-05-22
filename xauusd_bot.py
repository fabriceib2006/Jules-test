import numpy as np
import pandas as pd
import datetime
import os
import argparse
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

def simulate_xauusd(days=60, start_price=2000, volatility=0.015, mu=0.0002):
    """
    Simulates XAUUSD price data using Geometric Brownian Motion.
    volatility: daily volatility
    mu: daily drift
    """
    dt = 1
    prices = [start_price]
    for _ in range(1, days):
        change = np.exp((mu - 0.5 * volatility**2) * dt +
                        volatility * np.sqrt(dt) * np.random.normal())
        prices.append(prices[-1] * change)

    dates = [datetime.date.today() - datetime.timedelta(days=days-1-i) for i in range(days)]
    df = pd.DataFrame({'Date': dates, 'Price': prices})
    return df

def calculate_moving_averages(df):
    df['MA7'] = df['Price'].rolling(window=7).mean()
    df['MA30'] = df['Price'].rolling(window=30).mean()
    return df

def run_trading_strategy(df, initial_balance=10000):
    balance = initial_balance
    position = 0  # Amount of XAUUSD held
    ledger = []

    for i in range(len(df)):
        row = df.iloc[i]
        date = row['Date']
        price = row['Price']
        ma7 = row['MA7']
        ma30 = row['MA30']

        # Golden Cross Strategy needs at least 30 days of data
        if pd.isna(ma7) or pd.isna(ma30):
            ledger.append({'Date': date, 'Price': price, 'Action': 'Wait', 'Balance': balance, 'Holdings': position})
            continue

        prev_ma7 = df.iloc[i-1]['MA7']
        prev_ma30 = df.iloc[i-1]['MA30']

        action = 'Hold'
        # Buy Signal: MA7 crosses above MA30
        if prev_ma7 <= prev_ma30 and ma7 > ma30:
            if balance > 0:
                position = balance / price
                balance = 0
                action = 'Buy'

        # Sell Signal: MA7 crosses below MA30
        elif prev_ma7 >= prev_ma30 and ma7 < ma30:
            if position > 0:
                balance = position * price
                position = 0
                action = 'Sell'

        ledger.append({'Date': date, 'Price': price, 'Action': action, 'Balance': balance, 'Holdings': position})

    final_value = balance + (position * df.iloc[-1]['Price'])
    return pd.DataFrame(ledger), final_value

def format_ledger(ledger_df, final_value, initial_balance=10000):
    report = "--- XAUUSD Trading Ledger ---\n"
    for _, row in ledger_df.iterrows():
        action_str = f" {row['Action']}" if row['Action'] in ['Buy', 'Sell'] else ""
        report += f"{row['Date']}: ${row['Price']:.2f}{action_str}\n"

    report += f"\nInitial Balance: ${initial_balance:.2f}\n"
    report += f"Final Portfolio Value: ${final_value:.2f}\n"
    profit = final_value - initial_balance
    report += f"Total Profit/Loss: ${profit:.2f} ({ (profit/initial_balance)*100:.2f}%)\n"
    return report

async def simulate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = simulate_xauusd()
    df = calculate_moving_averages(df)
    ledger_df, final_value = run_trading_strategy(df)
    report = format_ledger(ledger_df, final_value)

    # Telegram message limit is 4096 characters. A 60-day ledger should fit easily.
    if len(report) > 4000:
        for i in range(0, len(report), 4000):
            await update.message.reply_text(report[i:i+4000])
    else:
        await update.message.reply_text(report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run a local test without Telegram')
    args = parser.parse_args()

    if args.test:
        print("Running local simulation test...")
        df = simulate_xauusd()
        df = calculate_moving_averages(df)
        ledger_df, final_value = run_trading_strategy(df)
        print(format_ledger(ledger_df, final_value))
    else:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
            return

        application = ApplicationBuilder().token(token).build()
        application.add_handler(CommandHandler('simulate', simulate_command))
        print("Bot started. Send /simulate in Telegram.")
        application.run_polling()

if __name__ == '__main__':
    main()
