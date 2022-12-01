from pybit.usdt_perpetual import HTTP
import pandas as pd
import time
from datetime import datetime
import calendar
import smtplib 
from email.mime.text import MIMEText
##### bybit key #####
session = HTTP(
    endpoint="https://api.bybit.com", 
    api_key="iX7k37KXnQjwBzGZhd", 
    api_secret="srUkMMdV6LowHORthjqdNM2pkH8fI5VCjEVF"
)
##### RSI #####
def rsi_bybit(itv, symbol='BTCUSDT'):
    now = datetime.utcnow()
    unixtime = calendar.timegm(now.utctimetuple())
    since = unixtime-itv*60*200;
    response=session.query_kline(symbol='BTCUSDT',interval=str(itv),**{'from':since})['result']
    df = pd.DataFrame(response)
    rsi=rsi_calc(df,14).iloc[-1]
    rsi=round(rsi,2)
    return rsi
def rsi_calc(ohlc: pd.DataFrame, period: int = 14):
    ohlc = ohlc['close'].astype(float)
    delta = ohlc.diff()
    gains, declines = delta.copy(), delta.copy()
    gains[gains < 0] = 0
    declines[declines > 0] = 0
    _gain = gains.ewm(com=(period-1), min_periods=period).mean()
    _loss = declines.abs().ewm(com=(period-1), min_periods=period).mean()
    RS = _gain / _loss
    return pd.Series(100-(100/(1+RS)), name="RSI") 
##### States #####
USDT = session.get_wallet_balance(coin="USDT")['result']['USDT']['available_balance'] # USDT 보유량
position_average_short = session.my_position(symbol='BTCUSDT')['result'][1]['entry_price'] # BTCUSDT short average position price
position_average_long = session.my_position(symbol='BTCUSDT')['result'][0]['entry_price'] # BTCUSDT long average position price
position_leverage_short = session.my_position(symbol='BTCUSDT')['result'][1]['leverage'] # BTCUSDT short 레버리지
position_leverage_long = session.my_position(symbol='BTCUSDT')['result'][0]['leverage'] # BTCUSDT long 레버리지
def price():
    price_now = float(session.latest_information_for_symbol(symbol='BTCUSDT')['result'][0]['last_price']) # BTCUSDT 현재 가격
    return price_now
def size(x): # x=0 ; long, x=1 ; short
    position_size = session.my_position(symbol='BTCUSDT')['result'][x]['size']
    return position_size
def sendMail(content, subject):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login('inhosuh2@gmail.com', 'gzkhsszlvisozhya')
    msg = MIMEText('현재가 : ' + str(price()) + content + str( datetime.now()))
    msg['Subject'] = subject
    s.sendmail("inhosuh2@gmail.com", "inhosuh2@gmail.com", msg.as_string())
    s.quit()
def entry_price(x) : # x=0 ; long, x=1 ; short
    entry_price = session.my_position(symbol='BTCUSDT')['result'][x]['entry_price'] # BTCUSDT average position price
    return entry_price
def unrealized(x) : # x=0 ; long, x=1 ; short
    unrealized = session.my_position(symbol='BTCUSDT')['result'][x]['unrealised_pnl'] # BTCUSDT short unrelaized_pnl
    return unrealized
short_open_ready = 0; long_open_ready =0; eventnotice = 0
pre_price_1 = [ price(),price(),price(),price(),price() ]
pre_price_5 = [ price(),price(),price(),price(),price() ]; delta_price_5 = [0,0,0,0,0]
pre_price_15 = [ price(),price(),price(),price(),price() ]; delta_price_15 = [0,0,0,0,0]
while True:
    now = datetime.now(); period_5 = now.minute % 5; period_15 = now.minute % 15
    if now.second <1 :
        for i in range(0,4):
            pre_price_1[4-i] = pre_price_1[3-i]
        pre_price_1[0] = price()
        print(pre_price_1, pre_price_5, pre_price_15)
    if period_5 == 0 and now.second < 1 :
        for i in range(0,4):
            pre_price_5[4-i] = pre_price_5[3-i]
        pre_price_5[0] = price()
        for i in range(0,4):
            delta_price_5[4-i] = pre_price_5[3-i] -pre_price_5[4-i]
        delta_price_5[0] = price() - pre_price_5[0]       
    if period_15 == 0 and now.second < 1 :
        for i in range(0,4):
            pre_price_15[4-i] = pre_price_15[3-i]
        pre_price_15[0] = price()
        for i in range(0,4):
            delta_price_15[4-i] = pre_price_15[3-i] -pre_price_15[4-i]
        delta_price_15[0] = price() - pre_price_15[0]
    if size(1) == 0:
        if size(0) == 0:
            trade_state = 0 # no position
        else:
            trade_state = 1 # long posiont only
    else:
        if size(0) == 0:
            trade_state = 2 # short position only
        else:
            trade_state = 3 # both position
    if trade_state == 0 and eventnotice ==0 : # no position
        if abs(price()-pre_price_1[0]) > 50 :
            sendMail('\n1분봉에서 50point 이상 변화가 감지되었습니다. ','제목 : 1분봉에서 급격한 변동 신호가 잡혔습니다.')
            eventnotice =1
        if long_open_ready == 0 : # long open signal
            if rsi_bybit(5) < 30 :
                if rsi_bybit(15) <30 :
                    sendMail('\n과매도 구간에 진입했으니 long를 고려하세요.','제목 : 과매도 신호가 잡혔습니다.')
                    short_open_ready = 0 ; long_open_ready = 1             
        if short_open_ready == 0 : 
            if rsi_bybit(5) > 70 : # short open signal
                if rsi_bybit(15) > 70 :
                    sendMail('\n과매수 구간에 진입했으니 short를 고려하세요.','제목 : 과매수 신호가 잡혔습니다.')
                    short_open_ready = 1; long_open_ready = 0    
        if long_open_ready == 0 and short_open_ready == 0 and period_15 == 0 and now.second < 1 :
            sendMail('\n아직 position을 잡지 못했습니다.','제목 : no position notice')
            eventnotice =0
        if long_open_ready == 1 and delta_price_15[1] > 0 :
            sendMail(' \n적극적으로 long position을 잡을 것을 고려하세요.', '제목 : long position notice')
            eventnotice =1
        if short_open_ready ==1 and delta_price_15[1] < 0 :
           sendMail(' \n적극적으로 short position을 잡을 것을 고려하세요.', '제목 : short position notice')
           eventnotice =1
    if trade_state == 1 : # long position
        if abs(price()-pre_price_1[0]) > 50 :
            sendMail('\n1분봉에서 50point 이상 변화가 감지되었습니다. ','제목 : 1분봉에서 급격한 변동 신호가 잡혔습니다.')
            eventnotice =1
        else :
            if period_15 == 0 and now.second < 1 :
                sendMail('\nUnrealized P/L :' + str(unrealized(0))+'\n1분봉에서 50point 이상 변화가 감지되었습니다. ','제목 : long position notice.')
                eventnotice =0
    if trade_state == 2 : # short position  
        if abs(price()-pre_price_1[0]) > 50 :
            sendMail('\n1분봉에서 50point 이상 변화가 감지되었습니다. ','제목 : 1분봉에서 급격한 변동 신호가 잡혔습니다.')
            eventnotice =1
        else :
            if period_15 == 0 and now.second < 1 :
                sendMail('\nUnrealized P/L :' + str(unrealized(0))+'\n1분봉에서 50point 이상 변화가 감지되었습니다. ','제목 : short position notice.')
                eventnotice =0

    time.sleep(1)