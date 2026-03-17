import os
import telebot
from flask import Flask, request
import FinanceDataReader as fdr
from datetime import datetime, timedelta

# Vercel 환경 변수에서 토큰을 불러옵니다.
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BOT_USERNAME = '@tujadoumi_bot' # 본인 봇 아이디로 변경

tickers_dict = {
    "VIX (공포지수)": "^VIX",
    "SOX (반도체지수)": "^SOX",
    "SOXX (반도체ETF)": "SOXX",
    "USD/KRW (환율)": "USD/KRW",
    "Brent (브렌트유)": "BZ=F",
    "WTI (서부텍사스유)": "CL=F"
}

def get_market_data():
    result_text = "📊 **[현재 글로벌 주요 지표]**\n\n"
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    for name, ticker in tickers_dict.items():
        try:
            df = fdr.DataReader(ticker, start=start_date)
            df = df.dropna(subset=['Close']) # 결측치 제거
            
            if len(df) >= 2:
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2]
                
                change = current_price - prev_price
                pct_change = (change / prev_price) * 100 if prev_price != 0 else 0.0
                
                if change > 0: emoji = "🔺"
                elif change < 0: emoji = "🔻"
                else: emoji = "➖"
                
                result_text += f"▪️ **{name}**\n   {current_price:,.2f} {emoji} {abs(change):.2f} ({pct_change:+.2f}%)\n\n"
            elif len(df) == 1: 
                current_price = df['Close'].iloc[-1]
                result_text += f"▪️ **{name}**\n   {current_price:,.2f} (어제 데이터 없음)\n\n"
            else:
                result_text += f"▪️ {name}: 유효한 데이터 없음\n\n"
        except Exception as e:
            result_text += f"▪️ {name}: 데이터 로드 에러\n\n"
            
    return result_text

@bot.message_handler(func=lambda message: message.text and BOT_USERNAME in message.text)
def reply_market_data(message):
    msg = bot.reply_to(message, "데이터를 분석 중입니다... 잠시만요 ⏳")
    data_text = get_market_data()
    bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=data_text, parse_mode='Markdown')

# --- Vercel 서버리스 웹훅 라우팅 부분 ---

# 정상 작동 확인용 기본 주소
@app.route('/')
def home():
    return "텔레그램 봇 서버가 Vercel에서 정상 작동 중입니다!"

# 텔레그램 서버가 메시지를 보내줄(웹훅) 주소
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    # 텔레그램에서 보낸 JSON 데이터를 봇이 처리하도록 넘겨줍니다.
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200