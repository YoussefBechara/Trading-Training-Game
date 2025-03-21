import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import copy
import random
import mplfinance as mpf
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
from twelvedata import TDClient
import os
import json

class TradingTrainingGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Training Game")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e2e")
        
        # Default settings
        self.length_of_training = 100
        self.length_of_revealing = 20
        self.tickers_list = ['eurusd', 'gbpusd', 'usdchf', 'usdcad', 'audusd', 'nzdusd', 
                         'cadchf', 'audchf', 'gbpcad', 'eurchf', 'eurgbp', 'gbpnzd', 
                         'usdjpy', 'eurjpy', 'gbpjpy', 'nzdjpy']
        self.provider = 'twelve_data'
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#1e1e2e')
        self.style.configure('TButton', background='#3b4252', foreground='white', 
                         borderwidth=0, focuscolor='#4c566a', font=('Segoe UI', 10, 'bold'))
        self.style.map('TButton', background=[('active', '#4c566a')])
        self.style.configure('TLabel', background='#1e1e2e', foreground='#eceff4', font=('Segoe UI', 10))
        self.style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))
        self.style.configure('Stats.TLabel', font=('Segoe UI', 12))
        
        # Game state variables
        self.current_game = None
        self.training_df = None
        self.revealing_df = None
        self.ticker = None
        self.canvas = None
        self.correct_predictions = 0
        self.total_predictions = 0
        
        # Load session data if exists
        self.session_file = "trading_game_session.json"
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                    self.correct_predictions = session_data.get('correct', 0)
                    self.total_predictions = session_data.get('total', 0)
            except:
                pass
        
        # Create main layout
        self.create_layout()
        
    def create_layout(self):
        # Main frames
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)
        
        self.chart_frame = ttk.Frame(self.root)
        self.chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.stats_frame = ttk.Frame(self.root)
        self.stats_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        # Create a more compact horizontal layout for controls
        # Row 1: Title and main buttons
        row1 = ttk.Frame(self.control_frame)
        row1.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1, text="Trading Training Game", style='Header.TLabel').pack(side=tk.LEFT, padx=(0, 20))
        
        self.new_game_btn = ttk.Button(row1, text="New Game", command=self.start_new_game)
        self.new_game_btn.pack(side=tk.LEFT, padx=5)
        
        self.reveal_btn = ttk.Button(row1, text="Reveal", command=self.show_reveal, state=tk.DISABLED)
        self.reveal_btn.pack(side=tk.LEFT, padx=5)
        
        # Prediction buttons in same row
        self.prediction_label = ttk.Label(row1, text="Your Prediction:", style='Stats.TLabel')
        self.prediction_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.buy_btn = ttk.Button(row1, text="BUY", command=lambda: self.record_prediction("BUY"), state=tk.DISABLED)
        self.buy_btn.pack(side=tk.LEFT, padx=5)
        
        self.sell_btn = ttk.Button(row1, text="SELL", command=lambda: self.record_prediction("SELL"), state=tk.DISABLED)
        self.sell_btn.pack(side=tk.LEFT, padx=5)
        
        # Add accuracy to the right side of row1
        self.accuracy_var = tk.StringVar(value="Accuracy: 0.0% (0/0)")
        self.accuracy_label = ttk.Label(row1, textvariable=self.accuracy_var, style='Stats.TLabel')
        self.accuracy_label.pack(side=tk.RIGHT, padx=10)
        
        # Row 2: Settings and status
        row2 = ttk.Frame(self.control_frame)
        row2.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # Settings section
        settings_section = ttk.Frame(row2)
        settings_section.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(settings_section, text="Training Length:").pack(side=tk.LEFT, padx=(0, 5))
        self.training_var = tk.StringVar(value="100")
        training_entry = ttk.Entry(settings_section, textvariable=self.training_var, width=5)
        training_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(settings_section, text="Revealing Length:").pack(side=tk.LEFT, padx=(0, 5))
        self.revealing_var = tk.StringVar(value="20")
        revealing_entry = ttk.Entry(settings_section, textvariable=self.revealing_var, width=5)
        revealing_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status on the right side of row2
        self.status_var = tk.StringVar(value="Ready to start")
        self.status_label = ttk.Label(row2, textvariable=self.status_var, style='Stats.TLabel')
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Chart area placeholder
        self.placeholder_label = ttk.Label(self.chart_frame, text="Start a new game to view charts", anchor=tk.CENTER)
        self.placeholder_label.pack(expand=True)
    
    def start_new_game(self):
        try:
            self.length_of_training = int(self.training_var.get())
            self.length_of_revealing = int(self.revealing_var.get())
        except ValueError:
            self.status_var.set("Invalid input for training or revealing length")
            return
        
        # Disable buttons during loading
        self.new_game_btn.configure(state=tk.DISABLED)
        self.status_var.set("Loading data... Please wait")
        self.root.update()
        
        # Start data loading in a separate thread
        threading.Thread(target=self.load_game_data).start()
    
    def load_game_data(self):
        try:
            # Clear previous chart if exists
            if self.canvas is not None:
                for widget in self.chart_frame.winfo_children():
                    widget.destroy()
            
            # Choose random ticker
            self.ticker = random.choice(self.tickers_list)
            
            # Get data
            total_df = self.get_data(ticker=self.ticker, provider=self.provider)
            start_idx = random.randint(0, len(total_df) - (self.length_of_training + self.length_of_revealing))
            self.training_df = total_df.iloc[start_idx:start_idx + self.length_of_training]
            self.revealing_df = total_df.iloc[start_idx + self.length_of_training:start_idx + self.length_of_training + self.length_of_revealing]
            
            # Update UI in main thread
            self.root.after(0, self.display_training_chart)
        except Exception as e:
            # Update error in main thread
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
            self.root.after(0, lambda: self.new_game_btn.configure(state=tk.NORMAL))
    
    def display_training_chart(self):
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Plot training data
        fig, axes = mpf.plot(
            self.training_df,
            type='candle',
            style='yahoo',
            title=f"{self.ticker.upper()} - Training Data",
            volume=False if 'volume' not in self.training_df.columns.str.lower() else True,
            figsize=(10, 6),
            returnfig=True
        )
        
        # Embed chart in Tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        toolbar_frame = ttk.Frame(self.chart_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # Enable relevant buttons
        self.new_game_btn.configure(state=tk.NORMAL)
        self.reveal_btn.configure(state=tk.NORMAL)
        self.buy_btn.configure(state=tk.NORMAL)
        self.sell_btn.configure(state=tk.NORMAL)
        
        # Reset prediction for new game
        self.current_prediction = None
        
        # Update status
        self.status_var.set(f"Game started with {self.ticker.upper()}. Make your prediction!")
    
    def show_reveal(self):
        if self.training_df is None or self.revealing_df is None:
            return
        
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Combine data
        combined_df = pd.concat([self.training_df, self.revealing_df])
        training_end_idx = len(self.training_df)
        
        # Create custom style for the chart
        mc = mpf.make_marketcolors(
            up='g', down='r',
            edge={'up': 'g', 'down': 'r'},
            wick={'up': 'g', 'down': 'r'},
            volume='inherit',
            ohlc='i',
            alpha=0.7
        )
        
        s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='yahoo')
        
        # Plot complete data
        fig, axes = mpf.plot(
            combined_df,
            type='candle',
            style=s,
            title=f"{self.ticker.upper()} - Complete Data",
            volume=False if 'volume' not in combined_df.columns.str.lower() else True,
            figsize=(10, 6),
            returnfig=True,
            tight_layout=True,
            datetime_format='%Y-%m-%d',
            show_nontrading=True
        )
        
        # Highlight revealing area
        ax = axes[0]
        for idx in range(training_end_idx, len(combined_df)):
            date = combined_df.index[idx]
            o, h, l, c = combined_df.iloc[idx][['open', 'high', 'low', 'close']]
            color = 'blue' if c >= o else 'orange'
            x = mdates.date2num(date)
            ax.plot([x, x], [l, h], color=color, linewidth=1)
            ax.plot([x, x + 0.4], [o, o], color=color, linewidth=2)
            ax.plot([x, x + 0.4], [c, c], color=color, linewidth=2)
            width = 0.8
            rect = Rectangle((x - width / 2, min(o, c)), width, abs(c - o), color=color, alpha=0.3 if c >= o else 0.6)
            ax.add_patch(rect)
        
        # Add legend
        training_patch = plt.Rectangle((0, 0), 1, 1, color='g', alpha=0.6, label='Training (Up)')
        training_patch2 = plt.Rectangle((0, 0), 1, 1, color='r', alpha=0.6, label='Training (Down)')
        revealing_patch = plt.Rectangle((0, 0), 1, 1, color='blue', alpha=0.6, label='Revealing (Up)')
        revealing_patch2 = plt.Rectangle((0, 0), 1, 1, color='orange', alpha=0.6, label='Revealing (Down)')
        
        ax.legend(handles=[training_patch, training_patch2, revealing_patch, revealing_patch2], loc='upper left')
        
        # Embed chart in Tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        toolbar_frame = ttk.Frame(self.chart_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # Check prediction result if a prediction was made
        if hasattr(self, 'current_prediction') and self.current_prediction is not None:
            self.check_prediction()
    
    def record_prediction(self, prediction):
        self.current_prediction = prediction
        self.buy_btn.configure(state=tk.DISABLED if prediction == "BUY" else tk.NORMAL)
        self.sell_btn.configure(state=tk.DISABLED if prediction == "SELL" else tk.NORMAL)
        self.status_var.set(f"Prediction recorded: {prediction}. Click 'Reveal' to see the result.")
    
    def check_prediction(self):
        if not hasattr(self, 'current_prediction') or self.current_prediction is None:
            return
        
        # Get the first candle of revealing data to determine the start price
        start_price = self.revealing_df.iloc[0]['open']
        
        # Get the last candle of revealing data to determine the end price
        end_price = self.revealing_df.iloc[-1]['close']
        
        # Determine the actual market movement
        actual_movement = "BUY" if end_price > start_price else "SELL"
        
        # Check if prediction was correct
        is_correct = self.current_prediction == actual_movement
        
        # Update stats
        self.total_predictions += 1
        if is_correct:
            self.correct_predictions += 1
        
        # Calculate and display accuracy
        accuracy = (self.correct_predictions / self.total_predictions) * 100 if self.total_predictions > 0 else 0
        self.accuracy_var.set(f"Accuracy: {accuracy:.1f}% ({self.correct_predictions}/{self.total_predictions})")
        
        # Update status
        result_text = "CORRECT!" if is_correct else "INCORRECT!"
        self.status_var.set(f"Your prediction was {result_text} Market went {actual_movement}")
        
        # Save session data
        with open(self.session_file, 'w') as f:
            json.dump({
                'correct': self.correct_predictions,
                'total': self.total_predictions
            }, f)

    def get_data(self, ticker="TSLA", period="2y", interval="1day", provider='twelve_data', ticker_type='forex'):
        if provider.lower() == 'twelve_data':
            td_clients = [
                TDClient(apikey=''),
                TDClient(apikey=''),
                TDClient(apikey='')
            ]

            def fetch_data(td, symbol, interval, start_date, end_date):
                all_data = []
                interval_map = {
                    '1min': 1/1440, '5min': 5/1440, '15min': 15/1440,
                    '30min': 30/1440, '45min': 45/1440, '1h': 1/24,
                    '2h': 2/24, '4h': 4/24, '8h': 8/24,
                    '1day': 1, '1week': 7, '1month': 30
                }

                days_per_request = min(30, int(5000 * interval_map.get(interval, 1)))
                step = timedelta(days=days_per_request)

                current_end = end_date
                first_chunk = True

                while current_end > start_date:
                    current_start = max(current_end - step, start_date)
                    try:
                        ts = td.time_series(
                            symbol=symbol,
                            interval=interval,
                            start_date=current_start.strftime('%Y-%m-%d %H:%M:%S'),
                            end_date=current_end.strftime('%Y-%m-%d %H:%M:%S'),
                            outputsize=5000
                        )
                        data = ts.as_pandas().sort_index(ascending=True)
                        if not data.empty:
                            all_data.insert(0, data)
                            if first_chunk:
                                end_date = data.index[-1]
                                first_chunk = False
                    except:
                        pass
                    current_end = current_start

                if not all_data:
                    raise ValueError("No data available for the specified timeframe")

                result = pd.concat(all_data).sort_index(ascending=True)
                result = result[~result.index.duplicated(keep='last')]
                return result

            end_date = datetime.now()

            max_years_map = {
                '1min': 0.1, '5min': 0.2, '15min': 0.5,
                '30min': 1, '45min': 1, '1h': 2,
                '2h': 2, '4h': 3, '8h': 5,
                '1day': 10, '1week': 20, '1month': 20
            }
            max_years_allowed = max_years_map.get(interval, 2)

            if isinstance(period, str):
                if period[-1].lower() == 'y':
                    period_years = min(float(period[:-1]), max_years_allowed)
                else:
                    period_years = min(float(period[:-1])/12, max_years_allowed)
            else:
                period_years = min(float(period), max_years_allowed)

            start_date = end_date - timedelta(days=int(period_years*365))

            if ticker_type.lower() == 'forex':
                if '/' not in ticker:
                    ticker = f"{ticker[:3]}/{ticker[-3:]}"

            df = None
            for td_client in td_clients:
                try:
                    df = fetch_data(td_client, ticker, interval, start_date, end_date)
                    if not df.empty:
                        break
                except Exception as e:
                    continue

            if df is None or df.empty:
                raise ValueError(f"No data available for {ticker} between {start_date} and {end_date}")

        elif provider.lower() == 'yfinance':
            import yfinance as yf
            ticker = f"{ticker.upper()}=X" if ticker_type.lower() == 'forex' else ticker.upper()
            if interval =='1day':
                interval='1d'
            df = yf.Ticker(ticker).history(period="max", interval=interval)
            df.rename(columns={'Close': 'close', 'Open': 'open', 'Low':'low', 'High': 'high'}, inplace=True)
            df.drop(columns=['Volume', 'Dividends', 'Stock Splits'], axis='columns', inplace=True, errors='ignore')

        return df

# Main application function
def main():
    root = tk.Tk()
    app = TradingTrainingGameGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
