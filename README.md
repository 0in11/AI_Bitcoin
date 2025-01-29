# 📈"AI BITCOIN AUTOTRADING"📈

GPT-4 기반 비트코인 자동매매 시스템으로, AWS EC2에서 실시간으로 구동되며 Streamlit 대시보드를 통해 모니터링할 수 있습니다.


## 🏗️ ARCHITECTURE
![Image](https://github.com/user-attachments/assets/e55b0dd7-57d5-4640-ad01-00442d5f6623)

## ✨ 주요 기능

- **실시간 시장 분석**
  - Upbit 차트를 통한 실시간 시장 데이터 수집
  - 볼린저 밴드, RSI, MACD 등 기술적 지표 분석

- **뉴스 및 시장 심리 분석**
  - 실시간 비트코인 관련 뉴스 크롤링
  - Fear & Greed Index 모니터링

- **AI 기반 매매 결정**
  - GPT-4o를 활용한 데이터 분석
  - '워뇨띠'의 매매 전략 적용
  - Upbit API를 통한 자동 매수/매도 실행

- **거래 기록 및 성과 분석**
  - SQLite 데이터베이스에 거래 내역 저장
  - 투자 성과 자동 계산
  - 거래 분석 및 개선점 도출
  - streamlit 기반 실시간 거래 내역 및 성과 분석 대시보드



## 🛠 Technical Stack

- Backend: AWS EC2 (Ubuntu 20.04)
- Database: SQLite
- APIs: Upbit API, Alternative.me API, OpenAI GPT-4o
- Libraries:
  - Selenium (웹 크롤링)
  - PyUpbit (거래소 API)
  - Pandas (데이터 처리)
  - TA-Lib (기술적 분석)
  - Streamlit (대시보드)
  - Schedule (작업 스케줄링)
<br/>
Inspiration of JOCOING's Youtube

