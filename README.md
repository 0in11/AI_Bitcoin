# 📈"AI_BITCOIN_AUTOTRADING"📈
<br />
<div align="center">
  <img src="https://github.com/user-attachments/assets/84a7fe61-bf7c-4f54-9989-0c08584bf093" width="300px">
  <img src="https://github.com/user-attachments/assets/29331362-ff0e-404a-aae2-7b0c7597d67e" width="500px"/>
</div>
<br/>
<br/>

## 1. Project Overview
- 프로젝트 이름: **"긴급재난 대피 알림 서비스"**
- 프로젝트 주제: 긴급한 재난 상황에서 신속한 대응을 위한 구체적인 정보를 맞춤 제공해주는 서비스
- 프로젝트 기간: 2024.03~2024.04 (1개월)
<br/>

## 2. Key Points
<img src="https://github.com/user-attachments/assets/7cc0749d-5833-4a4e-826d-3b69e2441459" width="800px"/>

- **앱 PUSH알림 발송**:
  - 재난 문자를 수신하였을 때, 수신된 재난문자의 재난 종류의 따른 행동요령 제시
  - 동시에 앱 PUSH알림을 즉시 발송하고, 클릭시 앱으로 이동

- **기본 행동요령 안내**:
  - 발생된 재난 종류에 따른 기본적인 행동요령 출력

- **대피소 위치 안내**:
  - 사용자의 GPS정보를 취득 
  - 발생된 재난 종류에 따라 근처 대피소들을 표시한 지도 생성
  - 지도 클릭 시 별도의 지도앱으로 이동

- **대피소 경로 안내**:
  - 현재 위치에서 인접한 대피소들의 혼잡도를 실시간으로 예측
  - 현재 위치에서 인접한 대피소들 중 예측한 혼잡도를 기반으로 혼잡도가 높지 않은 대피소를 안내

- **ChatBot 기능 탑재**:
  - 사용자가 입력창을 통해 본인의 추가적인 상황 제시
  - 생성형AI를 이용해 주어진 상황에 대한 행동요령을 즉시 피드백

<br/>

## 4. Technology
### 4.1 Congestion Analysis Model
- **실시간 대피소 이동자 수집**:
  - 앱 이용자의 GPS를 분석해 실시간으로 이동중인 대피소 파악
    
- **이동 예측 모델**:
  - 수집된 실시간 대피소 이동자 데이터로 재난 대피소의 혼잡상황을 파악할 수 있는 인공지능(AI) 기반 데이터 분석모델 이용
    
- **대피소 선택**:
  - 모델을 통해 예측한 대피소 혼잡도에 따라, 혼잡도와 이동 시간을 파악해 최적의 대피소 안내
  - 카카오맵 API를 활용하여 지도로 경로 제공

### 4.2 Emergency Response with RAG
- **재난종류 파악**:
  - 전송받은 재난문자의 재난 종류 파악
    
- **재난에 맞는 행동요령 출력**:
  - Rule-Based System으로 재난 상황에 맞는 기본적인 행동요령을 사용자에게 알려줌
    
- **챗봇**:
  - 챗봇에 재난과 관련된 특정 상황에 대해서 query로 입력
  - 재난 행동요령 데이터베이스에서 문장유사도를 분석해 참조데이터로 인용
  - queary와 함께 참조데이터를 LLM에 입력하면 각 query에 맞는 정확한 응답 제공
<img src="https://github.com/user-attachments/assets/3a254bc2-124c-4e07-b207-fdaae89c191f" width="500px"/>
<br/>
<br/>

## 5. Presentation PDF
- 프로젝트 자세히 알아보기<br />[📄 Disaster_Guidance_System_PDF](https://github.com/maeng99/disaster_guidance_system/blob/main/disaster_guidance_system_PDF.pdf)
