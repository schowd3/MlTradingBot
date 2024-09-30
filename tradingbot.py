from lumibot.brokers import Alpaca#broker
from lumibot.backtesting import YahooDataBacktesting #framework for backtesting
from lumibot.strategies.strategy import Strategy # trading bot
from lumibot.traders import Trader # trader
from datetime import datetime
from alpaca_trade_api import REST
from pandas import Timedelta
from finbert_utils import estimate_sentiment

API_KEY = "PK5ZYENVJ1U9Z888QT07"
API_SECRET = "rCrbXfZGvy8mqk6ALxpWeVaSGy1VZQa4Xse1Rbdc"
BASE_URL = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {
    "API_KEY":API_KEY,
    "API_SECRET":API_SECRET,
    "PAPER": True
}
#Trading logic
class MLTrader(Strategy):
    def initialize(self, symbol ="SPY", cash_at_risk:float =.5):
        self.symbol = symbol
        # controls current sleep time for the strategy - set to high lvl now
        self.sleeptime = "24H"
        #capture our last trade, can undo sell/buys
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)
    
    #positiion and cash management
    def position_sizing(self):
        #cash management
        #how much cash is left
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        #how many units per amount we want to risk
        quantity = round(cash * self.cash_at_risk/last_price, 0)
        return cash, last_price, quantity
    
    def get_dates(self): 
        today = self.get_datetime()
        # THREE DAYS OF WORTH OF NEWS
        three_days_prior = today - Timedelta(days=5)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')
    
    #start of api
    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment     
        
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability > .999: 
                if self.last_trade == "sell": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="bracket", 
                    take_profit_price=last_price*1.20, 
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    type="bracket", 
                    take_profit_price=last_price*.8, 
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order) 
                self.last_trade = "sell"        

            '''
            # strategy for creating order - 10 units at random
            if self.last_trade == None  :
                news = self.get_news()
                print(news)
                order = self.create_order(
                    self.symbol,
                    1,
                    "buy",
                    # type = "market"
                    type="bracket",
                    # want to go up by 20 %
                    take_profit_price=last_price*1.20,
                    #stop loss price is set to 5%
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order)
                self.last_trade = "buy"
            '''
start_date = datetime(2022,1,1)
end_date = datetime(2024, 6, 26)
broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name='mlstrat', broker=broker,
                    parameters={"symbol":"SPY", 
                                "cash_at_risk":.5})
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol":"SPY", 
     "cash_at_risk":5}
)
