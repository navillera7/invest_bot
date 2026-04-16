import os
import telebot
from flask import Flask, request
import FinanceDataReader as fdr
from datetime import datetime, timedelta

# Vercel 환경 변수에서 토큰을 불러옵니다.
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# threaded=False 를 추가해서 백그라운드 작업을 막고 동기식으로 꽉 잡아둡니다!
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

BOT_USERNAME = '@tujadoumi_bot' # 본인 봇 아이디로 변경

tickers_dict = {
    "VIX 😱 (공포지수)": "^VIX",
    "SOX 🧦 (반도체지수)": "^SOX",
    "SOXX 🧦🧦 (반도체ETF)": "SOXX",
    "USD/KRW 💹 (환율)": "USD/KRW",
    "Brent 🇳🇴🛢️(브렌트유)": "BZ=F",
    "WTI 🔫🛢️ (서부텍사스유)": "CL=F", 
    "Gold 🏆 (금)": "GC=F",
    "Silver 🪙 (은)": "SI=F",
    "Copper 🔑 (구리)": "HG=F",
    "Natural Gas 💨 (천연가스)": "NG=F",
    "코스피 🇰🇷 (KOSPI)": "KS11",
    "코스닥 🇰🇷 (KOSDAQ)": "KQ11",
    "EWY 🇰🇷 (한국ETF)": "EWY"
}

def get_market_data():
    result_text = "📊 **[현재 글로벌 주요 지표]**\n\n"
    # 충분한 데이터를 위해 기간을 7일로 잡습니다.
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    now = datetime.now()

    for name, ticker in tickers_dict.items():
        try:
            df = fdr.DataReader(ticker, start=start_date)
            df = df.dropna(subset=['Close'])
            
            if not df.empty:
                # 마지막 데이터의 날짜/시간 확인
                last_time = df.index[-1]
                current_price = df['Close'].iloc[-1]
                
                # [장중 판단 로직] 
                # 데이터의 마지막 업데이트가 현재 시간으로부터 20분 이내라면 장중(🟩)으로 표시
                # (참고: 무료 API 특성상 지연 시간이 있을 수 있어 20~30분 여유를 두는 것이 좋습니다)
                time_diff = now - last_time
                # 만약 인덱스에 시간 정보가 없고 날짜만 있다면(날짜형 데이터), 
                # 오늘 날짜와 같으면 장중으로 간주하거나 추가 처리가 필요합니다.
                is_active = time_diff < timedelta(minutes=20)
                status_emoji = "🟩" if is_active else "▪️"

                if len(df) >= 2:
                    prev_price = df['Close'].iloc[-2]
                    change = current_price - prev_price
                    pct_change = (change / prev_price) * 100 if prev_price != 0 else 0.0
                    
                    trend_emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
                    
                    result_text += f"{status_emoji} **{name}**\n   {current_price:,.2f} {trend_emoji} {abs(change):.2f} ({pct_change:+.2f}%)\n\n"
                else:
                    result_text += f"{status_emoji} **{name}**\n   {current_price:,.2f} (비교 데이터 부족)\n\n"
            else:
                result_text += f"▪️ {name}: 유효한 데이터 없음\n\n"
        except Exception as e:
            result_text += f"▪️ {name}: 데이터 로드 에러\n\n"
            
    return result_text

@bot.message_handler(func=lambda message: message.text and BOT_USERNAME in message.text)
def reply_market_data(message):
    try:
        # 1:1 채팅이나 단톡방에서 태그가 인식되면 실행됩니다.
        msg = bot.reply_to(message, "데이터를 분석 중입니다... 잠시만요 ⏳")
        data_text = get_market_data()
        
        # 가독성을 위해 마크다운 모드 다시 활성화 (에러 나면 다시 끄셔도 됩니다)
        bot.edit_message_text(chat_id=message.chat.id, 
                              message_id=msg.message_id, 
                              text=data_text, 
                              parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"에러 발생: {e}")
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