import os
import telebot
from flask import Flask, request
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pytz
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
    
    # 시간대 설정
    kst = pytz.timezone('Asia/Seoul')
    est = pytz.timezone('America/New_York')
    
    now_kst = datetime.now(kst)
    now_est = datetime.now(est)
    is_weekend = now_kst.weekday() >= 5
    # 한국 장중 확인 (월~금, 09:00 ~ 15:30)
    is_kr_open = now_kst.weekday() < 5 and 9 <= now_kst.hour < 16
    if now_kst.hour == 15 and now_kst.minute > 30: is_kr_open = False

    # 미국 장중 확인 (월~금, 09:30 ~ 16:00 / 썸머타임 미고려시 대략적 계산)
    is_us_open = now_est.weekday() < 5 and 9 <= now_est.hour < 16
    if now_est.hour == 9 and now_est.minute < 30: is_us_open = False

    start_date = (now_kst - timedelta(days=7)).strftime('%Y-%m-%d')

    for name, ticker in tickers_dict.items():
        try:
            df = fdr.DataReader(ticker, start=start_date)
            df = df.dropna(subset=['Close'])
            
            if not df.empty:
                current_price = df['Close'].iloc[-1]
                
                # [장중 판단 로직 개선]
                # 1. 한국 종목/ETF인 경우
                # 1. 한국 주식 (장 운영 시간 엄격 적용)
            if any(x in name for x in ["코스피", "코스닥"]):
                status_emoji = "🟩" if is_kr_open else "⬛️"
            
            # 2. 환율 및 원자재 (주말만 아니면 24시간 🟩)
            elif any(x in name for x in ["환율", "Brent", "WTI", "Gold", "Silver", "Copper", "Gas"]):
                status_emoji = "🟩" if not is_weekend else "⬛️"
            
            # 3. 미국 지수 및 ETF (미국 본장 시간 적용)
            else:
                status_emoji = "🟩" if is_us_open else "⬛️"
                
            if len(df) >= 2:
                prev_price = df['Close'].iloc[-2]
                change = current_price - prev_price
                pct_change = (change / prev_price) * 100 if prev_price != 0 else 0.0
                
                trend_emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
                result_text += f"{status_emoji} **{name}**\n   {current_price:,.2f} {trend_emoji} {abs(change):.2f} ({pct_change:+.2f}%)\n\n"
            else:
                result_text += f"{status_emoji} **{name}**\n   {current_price:,.2f} (데이터 부족)\n\n"
        except Exception as e:
            result_text += f"▪️ {name}: 에러\n\n"
        except Exception as e:
            result_text += f"▪️ {name}: 에러\n\n"
            
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