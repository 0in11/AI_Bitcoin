import os
from dotenv import load_dotenv
import pyupbit
import pandas as pd
import json
from openai import OpenAI
import ta
from ta.utils import dropna
import time
import requests
import base64
from PIL import Image
import io

# selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.keys import Keys


import warnings
import time
from selenium.webdriver.common.keys import Keys
import logging
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi
from pydantic import BaseModel
from openai import OpenAI
import sqlite3

class TradingDecision(BaseModel):
    decision: str
    percentage: int
    reason: str

# DB 정의의
def init_db():
    conn = sqlite3.connect('bitcoin_trades.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  decision TEXT,
                  percentage INTEGER,
                  reason TEXT,
                  btc_balance REAL,
                  krw_balance REAL,
                  btc_avg_buy_price REAL,
                  btc_krw_price REAL,
                  reflection TEXT)''')
    conn.commit()
    return conn

def log_trade(conn, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection=''):
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("""INSERT INTO trades 
                 (timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection))
    conn.commit()

def get_recent_trades(conn, days=7):
    c = conn.cursor()
    seven_days_ago = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute("SELECT * FROM trades WHERE timestamp > ? ORDER BY timestamp DESC", (seven_days_ago,))
    columns = [column[0] for column in c.description]
    return pd.DataFrame.from_records(data=c.fetchall(), columns=columns)

def calculate_performance(trades_df):
    if trades_df.empty:
        return 0
    
    initial_balance = trades_df.iloc[-1]['krw_balance'] + trades_df.iloc[-1]['btc_balance'] * trades_df.iloc[-1]['btc_krw_price']
    final_balance = trades_df.iloc[0]['krw_balance'] + trades_df.iloc[0]['btc_balance'] * trades_df.iloc[0]['btc_krw_price']
    
    return (final_balance - initial_balance) / initial_balance * 100

def generate_reflection(trades_df, current_market_data):
    performance = calculate_performance(trades_df)
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI trading assistant tasked with analyzing recent trading performance and current market conditions to generate insights and improvements for future trading decisions."
            },
            {
                "role": "user",
                "content": f"""
                Recent trading data:
                {trades_df.to_json(orient='records')}
                
                Current market data:
                {current_market_data}
                
                Overall performance in the last 7 days: {performance:.2f}%
                
                Please analyze this data and provide:
                1. A brief reflection on the recent trading decisions
                2. Insights on what worked well and what didn't
                3. Suggestions for improvement in future trading decisions
                4. Any patterns or trends you notice in the market data
                
                Limit your response to 250 words or less.
                """
            }
        ]
    )
    
    return response.choices[0].message.content

def get_db_connection():
    return sqlite3.connect('bitcoin_trades.db')

# 데이터베이스 초기화
init_db()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def add_indicators(df):
    # 볼린저 밴드
    indicator_bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_bbm'] = indicator_bb.bollinger_mavg()
    df['bb_bbh'] = indicator_bb.bollinger_hband()
    df['bb_bbl'] = indicator_bb.bollinger_lband()
    
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    # MACD
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    
    # 이동평균선
    df['sma_20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
    df['ema_12'] = ta.trend.EMAIndicator(close=df['close'], window=12).ema_indicator()
    
    return df

def get_fear_and_greed_index():
    url = "https://api.alternative.me/fng/"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['data'][0]
    else:
        logger.error(f"Failed to fetch Fear and Greed Index. Status code: {response.status_code}")
        return None

# 구글 뉴스 크롤링
class NewsCrawler:
    def __init__(self):
        warnings.filterwarnings(action='ignore')
        self.driver = self._initialize_driver()
    
    # Local
    # def _initialize_driver(self):
    #     """웹드라이버 초기화"""
    #     options = webdriver.ChromeOptions()
    #     options.add_argument("--ignore-local-proxy")
    #     options.add_argument("--headless")  # 디버깅을 위해 헤드리스 모드 비활성화
        
    #     try:
    #         driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), 
    #                                 options=options)
    #     except:
    #         driver = webdriver.Chrome()
            
    #     return driver
    
    # EC2 Server
    def _initialize_driver(self):
        """웹드라이버 초기화 - EC2 환경에 맞게 설정"""
        options = webdriver.ChromeOptions()
        
        # EC2 서버 환경을 위한 필수 옵션들
        options.add_argument("--headless")  # 헤드리스 모드 필수
        options.add_argument("--no-sandbox")  # 리눅스 환경 필수
        options.add_argument("--disable-dev-shm-usage")  # 메모리 관련 옵션
        options.add_argument("--disable-gpu")  # GPU 가속 비활성화
        options.add_argument("--ignore-local-proxy")  # 프록시 설정 무시
        
        try:
            # EC2의 크롬드라이버 경로 지정
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"ChromeDriver 초기화 오류: {e}")
            raise
            
        return driver
    
    def _find_and_click(self, xpath):
        """요소 찾아서 클릭"""
        elem = self.driver.find_element("xpath", xpath)
        elem.click()
        
    def _find_and_get_text(self, xpath):
        """요소 찾아서 텍스트 반환"""
        elem = self.driver.find_element("xpath", xpath)
        return elem.text
    
    def search_keyword(self, keyword):
        """검색어로 뉴스 검색"""
        self.driver.get("https://www.google.com/search?q=%EB%89%B4%EC%8A%A4&sca_esv=07fe2ed8acd931f7&hl=ko&biw=1365&bih=911&tbm=nws&sxsrf=ADLYWILjupBNc67GtS37bqy0ovtxpmkhIg%3A1736322515218&ei=0y1-Z_GFDfGVvr0P292ggQE&ved=0ahUKEwixu_C10eWKAxXxiq8BHdsuKBAQ4dUDCA4&uact=5&oq=%EB%89%B4%EC%8A%A4&gs_lp=Egxnd3Mtd2l6LW5ld3MiBuuJtOyKpDIIEAAYgAQYsQMyCxAAGIAEGLEDGIMBMgsQABiABBixAxiDATILEAAYgAQYsQMYgwEyCBAAGIAEGLEDMgsQABiABBixAxiDATILEAAYgAQYsQMYgwEyCxAAGIAEGLEDGIMBMgQQABgDMgsQABiABBixAxiDAUjKElC8BFjvEHADeACQAQKYAaUBoAHkCaoBAzAuOLgBA8gBAPgBAZgCBqACxwaoAgCYAwGIBgGSBwMxLjWgB4Yo&sclient=gws-wiz-news")
        time.sleep(3)
        
        # 검색창에 키워드 입력
        search_box = self.driver.find_element("xpath", 
            "/html/body/div[2]/div[2]/form/div[1]/div[1]/div[2]/div/div[2]/textarea")
        search_box.clear() # 검색창 키워드 삭제
        search_box.send_keys(keyword, Keys.ENTER)
        time.sleep(1)
        
    def crawl_news(self):
        """상위 5개 뉴스의 제목과 날짜만 크롤링"""
        news_data = []
        
        for idx in range(1, 6):  # 상위 5개만 크롤링
            try:
                news_item = {
                    'title': self._find_and_get_text(f"/html/body/div[3]/div/div[11]/div/div/div[2]/div[2]/div/div/div/div/div[{idx}]/div/div/a/div/div[2]/div[2]"),
                    'date': self._find_and_get_text(f"/html/body/div[3]/div/div[11]/div/div/div[2]/div[2]/div/div/div/div/div[{idx}]/div/div/a/div/div[2]/div[4]/span")
                }
                news_data.append(news_item)
                
                # 수집된 데이터 출력
                print(f"제목: {news_item['title']}")
                print(f"날짜: {news_item['date']}")
                print()
                
            except Exception as e:
                print(f"Error crawling news item {idx}: {str(e)}")
                continue
                
        return news_data
    
    def close(self):
        """브라우저 종료"""
        self.driver.quit()

def get_bitcoin_news():
    """비트코인 뉴스 크롤링 함수"""
    try:
        crawler = NewsCrawler()
        crawler.search_keyword("btc")
        news_data = crawler.crawl_news()
        return news_data
    except Exception as e:
        print(f"Error in get_bitcoin_news: {e}")
        return []
    finally:
        if 'crawler' in locals():
            crawler.close()

# 로컬용용
# def setup_chrome_options():
#     chrome_options = Options()
#     chrome_options.add_argument("--start-maximized")
#     chrome_options.add_argument("--headless")  # 디버깅을 위해 헤드리스 모드 비활성화
#     chrome_options.add_argument("--disable-gpu")
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--disable-dev-shm-usage")
#     chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
#     return chrome_options

# def create_driver():
#     logger.info("ChromeDriver 설정 중...")
#     service = Service(ChromeDriverManager().install())
#     driver = webdriver.Chrome(service=service, options=setup_chrome_options())
#     return driver

# EC2 서버용
def create_driver():
    logger.info("ChromeDriver 설정 중...")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 헤드리스 모드 사용
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        service = Service('/usr/bin/chromedriver')  # Specify the path to the ChromeDriver executable

        # Initialize the WebDriver with the specified options
        driver = webdriver.Chrome(service=service, options=chrome_options)

        return driver
    except Exception as e:
        logger.error(f"ChromeDriver 생성 중 오류 발생: {e}")
        raise


def click_element_by_xpath(driver, xpath, element_name, wait_time=10):
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        # 요소가 뷰포트에 보일 때까지 스크롤
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        # 요소가 클릭 가능할 때까지 대기
        element = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        element.click()
        logger.info(f"{element_name} 클릭 완료")
        time.sleep(2)  # 클릭 후 잠시 대기
    except TimeoutException:
        logger.error(f"{element_name} 요소를 찾는 데 시간이 초과되었습니다.")
    except ElementClickInterceptedException:
        logger.error(f"{element_name} 요소를 클릭할 수 없습니다. 다른 요소에 가려져 있을 수 있습니다.")
    except NoSuchElementException:
        logger.error(f"{element_name} 요소를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"{element_name} 클릭 중 오류 발생: {e}")

def perform_chart_actions(driver, timeframe, is_first_capture=False):
    # 시간 메뉴 클릭
    click_element_by_xpath(
        driver,
        "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]",
        "시간 메뉴"
    )
    
    # timeframe에 따른 xpath 선택
    timeframe_xpath = {
        "1h": "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]/cq-menu-dropdown/cq-item[8]",
        "5m": "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]/cq-menu-dropdown/cq-item[4]"
    }
    
    # 해당 시간봉 옵션 선택
    click_element_by_xpath(
        driver,
        timeframe_xpath[timeframe],
        f"{timeframe} 옵션"
    )
    
    # 첫 번째 캡처에서만 지표 추가
    if is_first_capture:
        # 지표 메뉴 클릭
        click_element_by_xpath(
            driver,
            "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]",
            "지표 메뉴"
        )
        
        # 볼린저 밴드 선택
        click_element_by_xpath(
            driver,
            "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[15]",
            "볼린저 밴드"
        )
        
    # 지표 메뉴 클릭
        click_element_by_xpath(
            driver,
            "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]",
            "지표 메뉴"
        )

        # RSI 선택
        rsi_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[81]"
        try:
            rsi_element = driver.find_element("xpath", rsi_xpath)
            driver.execute_script("arguments[0].scrollIntoView(true);", rsi_element)
            time.sleep(1)
            rsi_element.click()
            logger.info("RSI 지표 클릭 완료")
        except Exception as e:
            logger.error(f"RSI 지표 클릭 중 오류: {e}")
        
        time.sleep(2)  # 지표 적용 대기

def capture_and_encode_screenshot(driver, timeframe):
    try:
        # 스크린샷 캡처
        png = driver.get_screenshot_as_png()
        
        # PIL Image로 변환
        img = Image.open(io.BytesIO(png))
        
        # 이미지 리사이즈
        img.thumbnail((2000, 2000))
        
        # 현재 시간을 파일명에 포함
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upbit_chart_{timeframe}_{current_time}.png"
        
        # 현재 스크립트의 경로를 가져옴
        script_dir = os.path.dirname(os.path.abspath(__file__))
        #chart_img_path = os.path.join(script_dir, 'chart_img')
        #file_path = os.path.join(chart_img_path, filename)

        # 파일 저장 경로 설정
        file_path = os.path.join(script_dir, filename)
        
        # 이미지 파일로 저장
        img.save(file_path)
        logger.info(f"{timeframe} 스크린샷이 저장되었습니다: {file_path}")
        
        # 이미지를 바이트로 변환
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        
        # base64로 인코딩
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return base64_image, file_path
    except Exception as e:
        logger.error(f"{timeframe} 스크린샷 캡처 및 인코딩 중 오류 발생: {e}")
        return None, None

def get_combined_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        combined_text = ' '.join(entry['text'] for entry in transcript)
        return combined_text
    except Exception as e:
        logger.error(f"Error fetching YouTube transcript: {e}")
        return ""

def ai_trading():
    # Upbit 객체 생성
    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")
    upbit = pyupbit.Upbit(access, secret)

    # 1. 현재 투자 상태 조회
    all_balances = upbit.get_balances()
    filtered_balances = [balance for balance in all_balances if balance['currency'] in ['BTC', 'KRW']]
    print(filtered_balances)
    
    # 2. 오더북(호가 데이터) 조회
    orderbook = pyupbit.get_orderbook("KRW-BTC")
    print(orderbook)

    # 3. 차트 데이터 조회 및 보조지표 추가
    df_daily = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=30)
    df_daily = dropna(df_daily)
    df_daily = add_indicators(df_daily)
    print(df_daily)
    
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)
    df_hourly = dropna(df_hourly)
    df_hourly = add_indicators(df_hourly)

    # 4. 공포 탐욕 지수 가져오기
    fear_greed_index = get_fear_and_greed_index()
    print(f"fear_greedy: \n{fear_greed_index}")

    # 5. 뉴스 헤드라인 가져오기
    news_headlines = get_bitcoin_news()
    print(f"news: \n{news_headlines}")

    # 6. YouTube 자막 데이터 가져오기
    #youtube_transcript = get_combined_transcript("3XbtEX3jUv4")  # 여기에 실제 비트코인 관련 YouTube 영상 ID를 넣으세요
    #print(f"yotube: \n{youtube_transcript}")

    # Selenium으로 차트 캡처
    driver = None
    chart_images = {}
    try:
        driver = create_driver()
        driver.get("https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC")
        logger.info("페이지 로드 완료")
        time.sleep(10)  # 페이지 로딩 대기 시간 증가

        # logger.info("차트 작업 시작")
        # perform_chart_actions(driver)
        # logger.info("차트 작업 완료")
        # chart_image, saved_file_path = capture_and_encode_screenshot(driver)
        # logger.info(f"스크린샷 캡처 완료. 저장된 파일 경로: {saved_file_path}")

        # 1시간봉 차트 캡처
        logger.info("1시간봉 차트 작업 시작")
        perform_chart_actions(driver, "1h", is_first_capture=True)
        time.sleep(5)  # 차트 로딩 대기
        chart_images["1h"], _ = capture_and_encode_screenshot(driver, "1h")
        logger.info("1시간봉 차트 캡처 완료")

        # 5분봉 차트 캡처
        logger.info("5분봉 차트 작업 시작")
        perform_chart_actions(driver, "5m", is_first_capture=False)
        time.sleep(5)  # 차트 로딩 대기
        chart_images["5m"], _ = capture_and_encode_screenshot(driver, "5m")
        logger.info("5분봉 차트 캡처 완료")

    except WebDriverException as e:
        logger.error(f"WebDriver 오류 발생: {e}")
    except Exception as e:
        logger.error(f"차트 캡처 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()

    # AI에게 데이터 제공하고 판단 받기
    client = OpenAI()

    # 데이터베이스 연결
    conn = get_db_connection()

    # 최근 거래 내역 가져오기
    recent_trades = get_recent_trades(conn)

     # 현재 시장 데이터 수집 (기존 코드에서 가져온 데이터 사용)
    current_market_data = {
        "fear_greed_index": fear_greed_index,
        "news_headlines": news_headlines,
        "orderbook": orderbook,
        "daily_ohlcv": df_daily.to_dict(),
        "hourly_ohlcv": df_hourly.to_dict()
    }

    # 반성 및 개선 내용 생성
    reflection = generate_reflection(recent_trades, current_market_data)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"""You are an expert in Bitcoin investing. Analyze the provided data and determine whether to buy, sell, or hold at the current moment. Consider the following in your analysis:

                - Technical indicators across multiple timeframes (1h and 5m charts)
                - The 1-hour chart looks at long-term trends, while the 5-minute chart looks at short-term trends.
                - Recent news headlines and their potential impact on Bitcoin price
                - The Fear and Greed Index and its implications
                - Overall market sentiment
                - Patterns and trends visible in the chart image
                - Recent trading performance and reflection

                Recent trading reflection:
                {reflection}

                Particularly important is to always refer to the trading method of 'Wonyyotti', a legendary Korean investor, to assess the current situation and make trading decisions. Wonyyotti's trading method is as follows:

                - Emphasize focusing on winning and paying attention to the charts you see rather than investing in high risk
                - Reading the market by looking at charts, being sensitive to market shifts and changing your position lines accordingly (e.g., aggressive buying in rising markets and conservative selling in falling markets)
                - Emphasizes the importance of not being overly influenced by market news or sharp movements
                - Volume and candlesticks matter most
                - Take a wait-and-see approach when the market is sideways or ambiguous
                - How analyzing historical charts to determine entry, exit, and stop losses is key to trading strategy 


                Based on this trading method, analyze the current market situation and make a judgment by synthesizing it with the provided data.

                Response format:
                1. Decision (buy, sell, or hold)
                2. If the decision is 'buy', provide a percentage (1-100) of available KRW to use for buying.
                If the decision is 'sell', provide a percentage (1-100) of held BTC to sell.
                If the decision is 'hold', set the percentage to 0.
                3. Reason for your decision

                Ensure that the percentage is an integer between 1 and 100 for buy/sell decisions, and exactly 0 for hold decisions.
                Your percentage should reflect the strength of your conviction in the decision based on the analyzed data."""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Current investment status: {json.dumps(filtered_balances)}
        Orderbook: {json.dumps(orderbook)}
        Daily OHLCV with indicators (30 days): {df_daily.to_json()}
        Hourly OHLCV with indicators (24 hours): {df_hourly.to_json()}
        Recent news headlines: {json.dumps(news_headlines)}
        Fear and Greed Index: {json.dumps(fear_greed_index)}"""
                    },
{
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{chart_images['1h']}"
                    }
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{chart_images['5m']}"
                    }
                }
                ]
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "trading_decision",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string", "enum": ["buy", "sell", "hold"]},
                        "percentage": {"type": "integer"},
                        "reason": {"type": "string"}
                    },
                    "required": ["decision", "percentage", "reason"],
                    "additionalProperties": False
                }
            }
        },
        max_tokens=4095
    )

    # 최신 pydantic 메서드 사용
    result = TradingDecision.model_validate_json(response.choices[0].message.content)

    print(f"### AI Decision: {result.decision.upper()} ###")
    print(f"### Reason: {result.reason} ###")

    order_executed = False

    if result.decision == "buy":
        my_krw = upbit.get_balance("KRW")
        buy_amount = my_krw * (result.percentage / 100) * 0.9995  # 수수료 고려
        if buy_amount > 5000:
            print(f"### Buy Order Executed: {result.percentage}% of available KRW ###")
            order = upbit.buy_market_order("KRW-BTC", buy_amount)
            if order:
                order_executed = True
            print(order)
        else:
            print("### Buy Order Failed: Insufficient KRW (less than 5000 KRW) ###")
    elif result.decision == "sell":
        my_btc = upbit.get_balance("KRW-BTC")
        sell_amount = my_btc * (result.percentage / 100)
        current_price = pyupbit.get_current_price("KRW-BTC")
        if sell_amount * current_price > 5000:
            print(f"### Sell Order Executed: {result.percentage}% of held BTC ###")
            order = upbit.sell_market_order("KRW-BTC", sell_amount)
            if order:
                order_executed = True
            print(order)
        else:
            print("### Sell Order Failed: Insufficient BTC (less than 5000 KRW worth) ###")

    # 거래 실행 여부와 관계없이 현재 잔고 조회
    time.sleep(1)  # API 호출 제한을 고려하여 잠시 대기
    balances = upbit.get_balances()
    btc_balance = next((float(balance['balance']) for balance in balances if balance['currency'] == 'BTC'), 0)
    krw_balance = next((float(balance['balance']) for balance in balances if balance['currency'] == 'KRW'), 0)
    btc_avg_buy_price = next((float(balance['avg_buy_price']) for balance in balances if balance['currency'] == 'BTC'), 0)
    current_btc_price = pyupbit.get_current_price("KRW-BTC")

    # 거래 정보 로깅
    log_trade(conn, result.decision, result.percentage if order_executed else 0, result.reason, 
              btc_balance, krw_balance, btc_avg_buy_price, current_btc_price)

    # 데이터베이스 연결 종료
    conn.close()

# Main loop
while True:
    try:
        ai_trading()
        time.sleep(3600 * 4)  # 4시간마다 실행
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        time.sleep(300)  # 오류 발생 시 5분 후 재시도
