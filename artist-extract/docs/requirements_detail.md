# requirements_detail.md

참조: [artist-extract/docs/requirements.md](artist-extract/docs/requirements.md)

## 목적
특정 아티스트의 팬덤 사용자를 추출하는 Streamlit 기반 웹 애플리케이션의 상세 요구사항과 수용기준 정의.

## 개발 환경 개요
- **기술 스택**: Python, Streamlit, AWS Redshift, Pandas
- **배포 방식**: 서버 구성 없이 Streamlit 단독 실행 (로컬 또는 Streamlit Cloud)
- **데이터 소스**: AWS Redshift
- **개발 원칙**: TDD, SOLID, Clean Architecture

## 웹 페이지 컨셉
- **제목**: Artist Character 데이터 조회
- **기본 컨셉**
  - Streamlit의 기본 UI 컴포넌트를 활용한 단순하고 직관적인 인터페이스
  - 사용자 화면에 다크/라이트 모드 전환 기능 제공 (Streamlit 테마 활용)
  - **화면 구성**
    - **좌측 사이드바**: 아티스트 검색 및 필터 조건 입력 (st.sidebar 활용)
    - **메인 영역 상단**: 조회 결과 데이터 테이블 (st.dataframe)
    - **메인 영역 하단**: 요약 통계 및 시각화 보드 (st.columns, st.metric, st.plotly_chart 등)
  - docs/assets/pagetemp2.png 파일 참조 (Streamlit 레이아웃으로 구현)

## 사용자 스토리 및 수용기준

### 사용자 스토리 1 — 아티스트 검색/선택
- **요약**: 사용자는 가수명으로 검색하여 유사한 아티스트 목록을 보고 복수 선택할 수 있다.
- **Streamlit 구현**:
  - `st.sidebar.text_input()` 으로 가수명 입력받기
  - 입력값 변경 시 Redshift에서 LIKE 쿼리 실행
  - `st.sidebar.multiselect()` 또는 `st.sidebar.checkbox()` 로 다중 선택 구현
- **수용기준**:
  - 입력값에 대해 LIKE 쿼리(`ILIKE '%{input}%'`)로 최대 5개 결과 반환
  - 쿼리 결과는 사이드바 내에 실시간으로 표시
  - 결과에서 다중 선택(중복 허용) 가능
  - 선택된 아티스트 목록을 세션 상태(`st.session_state`)에 저장
  - `st.sidebar.button("조회")` 클릭 시 데이터 조회 실행

### 사용자 스토리 2 — 데이터 조회
- **요약**: 선택된 아티스트들의 artist_id로 사용자-아티스트별 청취건수 데이터를 조회한다.
- **Streamlit 구현**:
  - `st.sidebar.slider()` 또는 `st.sidebar.number_input()` 으로 청취건수 범위 필터 설정
  - Redshift에서 데이터 조회 후 Pandas DataFrame으로 변환
  - `st.dataframe()` 또는 `st.table()` 로 상위 20건 표시
  - `st.download_button()` 으로 CSV 다운로드 기능 제공
- **수용기준**:
  - 필터(청취건수 범위)를 적용할 수 있음
  - 화면에 상위 20건(청취건수 내림차순)만 표시
  - 전체 데이터를 CSV로 다운로드 가능 (사용자 로컬 PC에 저장)
  - 데이터 없을 경우 `st.info()` 또는 `st.warning()` 으로 안내 메시지 표시

### 사용자 스토리 3 — 요약 및 시각화
- **요약**: 조회 결과의 summary(건수, max, min, avg, median)를 표시하고 시각화 보드를 제공한다.
- **Streamlit 구현**:
  - `st.columns()` 로 요약 통계 영역 분할
  - `st.metric()` 으로 각 통계값 표시 (전체 건수, 최대, 최소, 평균, 중앙값)
  - `st.plotly_chart()` 또는 `st.altair_chart()` 로 시각화
    - 청취건수 분포 히스토그램
    - 상위 사용자별 청취건수 바차트
- **수용기준**:
  - 전체 사용자 수(레코드 수) 표시
  - 청취건수 최대/최소/평균/중앙값(50백분위) 계산이 정확해야 함
  - Pandas를 활용한 통계 계산 (`df.describe()`, `df.median()`)
  - 시각화는 인터랙티브하게 동작 (확대/축소, 툴팁 등)

## 기술 스택 상세

### Streamlit 컴포넌트 매핑
| 기능 | Streamlit 컴포넌트 |
|------|-------------------|
| 가수명 입력 | `st.sidebar.text_input()` |
| 아티스트 선택 | `st.sidebar.multiselect()` |
| 청취건수 필터 | `st.sidebar.slider()` 또는 `number_input()` |
| 조회 버튼 | `st.sidebar.button()` |
| 결과 테이블 | `st.dataframe()` |
| CSV 다운로드 | `st.download_button()` |
| 요약 통계 | `st.metric()` |
| 시각화 | `st.plotly_chart()` 또는 `st.altair_chart()` |
| 다크/라이트 모드 | Streamlit 테마 설정 (`.streamlit/config.toml`) |

### 데이터베이스 연결
- **라이브러리**: `psycopg2` 또는 `sqlalchemy` + `redshift_connector`
- **연결 정보 관리**: 
  - `artist-extract/res/config.artist-extract.dev.yml` 에서 읽기
  - `st.secrets` 를 활용한 민감 정보 관리 (`.streamlit/secrets.toml`)
- **연결 풀링**: `@st.cache_resource` 데코레이터로 DB 커넥션 재사용

### 성능 최적화
- **캐싱**: `@st.cache_data` 데코레이터로 쿼리 결과 캐싱
- **세션 상태**: `st.session_state` 로 사용자 선택 정보 유지
- **지연 로딩**: 조회 버튼 클릭 시에만 데이터 조회

## 데이터/쿼리 인터페이스

### 1. 아티스트 검색 쿼리
```sql
SELECT artist_id, artist_nm 
FROM flo_deh.d_artist 
WHERE artist_nm ILIKE '%{input}%' 
LIMIT 5;
```

### 2. 사용자별 아티스트별 청취건수 조회 쿼리
```sql
SELECT user_id, artist_id, listen_count 
FROM user_artist_listens 
WHERE artist_id IN ({artist_ids}) 
  AND listen_count BETWEEN {min_count} AND {max_count}
ORDER BY listen_count DESC;
```
- 화면 표시: 상위 20건
- CSV 다운로드: 전체 결과

### 3. 요약 통계 계산 (Pandas 활용)
```python
summary = {
    'total_users': len(df),
    'max_listen_count': df['listen_count'].max(),
    'min_listen_count': df['listen_count'].min(),
    'avg_listen_count': df['listen_count'].mean(),
    'median_listen_count': df['listen_count'].median()
}
```

## 프로젝트 구조

```
artist-extract/
├── src/
│   └── streamlit_app.py           # 메인 Streamlit 애플리케이션
│   ├── db/
│   │   └── redshift_connector.py  # Redshift 연결 및 쿼리 모듈
│   ├── services/
│   │   ├── artist_service.py      # 아티스트 검색 비즈니스 로직
│   │   └── listens_service.py     # 청취 데이터 조회 비즈니스 로직
│   ├── models/
│   │   └── data_models.py         # 데이터 모델 정의
│   └── utils/
│       ├── config_loader.py       # 설정 파일 로더
│       └── visualization.py       # 시각화 헬퍼 함수
├── tests/
│   ├── test_artist_service.py
│   ├── test_listens_service.py
│   └── test_redshift_connector.py
├── res/
│   └── config.artist-extract.dev.yml  # 환경 설정 파일
├── .streamlit/
│   ├── config.toml                # Streamlit 테마 설정
│   └── secrets.toml               # DB 연결 정보 (Git 제외)
├── logs/
│   └── process.log                # 애플리케이션 로그
└── requirements.txt               # Python 패키지 의존성
```

## 환경 설정

### requirements.txt
```
streamlit>=1.28.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
redshift-connector>=2.0.0
sqlalchemy>=2.0.0
plotly>=5.17.0
altair>=5.1.0
pyyaml>=6.0
pytest>=7.4.0
```

### .streamlit/config.toml (다크/라이트 모드 설정)
```toml
[theme]
primaryColor="#FF4B4B"
backgroundColor="#0E1117"
secondaryBackgroundColor="#262730"
textColor="#FAFAFA"
font="sans serif"
```

### .streamlit/secrets.toml (예시)
```toml
[redshift]
host = "my-cluster.xxxxxx.us-east-1.redshift.amazonaws.com"
port = 5439
database = "analytics"
user = "admin"
password = "your-password"
schema = "flo_deh"
```

## 비기능 요구사항

### 성능
- 아티스트 자동완성: 300ms 이내 응답 (캐싱 활용)
- 데이터 조회: 5초 이내 응답 (결과 건수에 따라 가변)
- Streamlit 캐싱으로 반복 쿼리 최적화

### 사용성
- 로딩 중 `st.spinner()` 로 진행 상태 표시
- 에러 발생 시 `st.error()` 로 사용자 친화적 메시지 표시
- 빈 결과 시 `st.info()` 로 안내

### 보안
- DB 연결 정보는 `secrets.toml` 에 저장 (Git 제외)
- SSL 연결 사용 권장 (`sslmode='require'`)

### 로깅
- 검색어, 선택된 아티스트, 쿼리 실행 시간 로그 기록
- `logs/process.log` 에 기록
- 개인정보는 로그에 포함하지 않음 (user_id 해싱 또는 제외)

## 테스트 수용기준

### 단위 테스트 (pytest)
- `artist_service.py`: 검색 쿼리 파라미터 변형 케이스
- `listens_service.py`: 청취건수 필터 로직 검증
- `redshift_connector.py`: DB 연결 및 쿼리 실행 모킹

### 통합 테스트
- Redshift 연결 테스트 (테스트 DB 사용)
- 전체 데이터 플로우 테스트 (검색 → 조회 → 통계 계산)

### UI 테스트
- Streamlit UI 테스트는 수동 테스트로 진행
  - 다크/라이트 모드 전환 확인
  - 다중 선택 동작 확인
  - CSV 다운로드 동작 확인
  - 시각화 렌더링 확인

## 개발 워크플로우

1. **환경 설정**
   - `.streamlit/secrets.toml` 생성 및 DB 연결 정보 입력
   - `res/config.artist-extract.dev.yml` 설정 확인
   - `pip install -r requirements.txt` 실행

2. **TDD 기반 개발**
   - 각 모듈별 테스트 먼저 작성 (`tests/`)
   - 테스트 통과하도록 구현 (`src/`)
   - 리팩토링 및 코드 품질 개선

3. **Streamlit 앱 실행**
   ```bash
   streamlit run src/streamlit_app.py
   ```

4. **로그 확인**
   - `logs/process.log` 에서 실행 로그 확인
   - 에러 발생 시 로그 분석 및 디버깅

## 데모 미적용 대상 요구사항 (추후 고려사항)
- 동시성: 동시 50명 사용자 지원 (Streamlit Cloud 또는 서버 배포 시 고려)
- 보안: API 인증 (사내 SSO 또는 토큰) - 현재는 로컬 실행으로 불필요
- 대용량 데이터: 수백만 건 이상의 데이터 처리 (페이징, 파티셔닝 고려)
- 멀티유저 세션 관리: 현재는 단일 사용자 로컬 실행 가정

## 다음 단계
1. **데이터베이스 스키마 확인**: Redshift의 실제 테이블 구조 파악
2. **프로토타입 개발**: 기본 UI 및 DB 연결 구현
3. **테스트 작성 및 실행**: TDD 기반 개발 진행
4. **사용자 피드백 수렴**: 초기 버전 데모 후 개선


