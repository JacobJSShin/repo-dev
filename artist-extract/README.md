# artist-extract

특정 아티스트의 팬덤 사용자를 추출하는 화면 기능을 Vibe Coding으로 개발  
DAS-1615-artist-extract

## 프로젝트 구조

```
artist-extract/
├── src/
│   ├── backend/         # FastAPI 백엔드 서버
│   │   ├── api/         # API 엔드포인트
│   │   ├── db/          # Redshift 커넥터
│   │   └── tests/       # 백엔드 테스트
│   └── frontend/        # React + TypeScript 프론트엔드
│       ├── src/
│       │   ├── components/  # UI 컴포넌트
│       │   ├── services/    # API 서비스
│       │   └── types/       # TypeScript 타입
├── res/                 # 환경 설정 파일
├── logs/                # 애플리케이션 로그
└── docs/                # 문서

## 기술 스택

### 백엔드
- **Python 3.11+** with FastAPI
- **asyncpg** for Redshift connection
- **pytest** for testing
- **Docker** for containerization

### 프론트엔드
- **React 19** with TypeScript
- **Vite** for build tooling
- **Axios** for API communication
- **Recharts** for data visualization
- Dark/Light theme support

## 빠른 시작

### 전체 스택 실행 (Docker Compose)

```bash
# 전체 스택 빌드 및 실행
docker-compose up --build

# 백엔드: http://localhost:8000
# 프론트엔드: http://localhost:5173
```

### 개별 실행

#### 백엔드

```bash
cd src/backend

# Docker로 실행
docker build -t artist-extract-backend .
docker run -p 8000:8000 artist-extract-backend

# 또는 로컬에서 실행 (Python 3.11+)
pip install -r requirements.txt
uvicorn app:app --reload
```

#### 프론트엔드

```bash
cd src/frontend

# 의존성 설치 및 실행
npm install
npm run dev
```

## 테스트

### 백엔드 테스트

```bash
# Docker 컨테이너 내에서
docker-compose exec backend pytest -v tests/

# 로컬에서
cd src/backend
PYTHONPATH=/app pytest -v tests/
```

### API 엔드포인트 테스트

```bash
# Health check
curl http://localhost:8000/

# Artists autocomplete
curl "http://localhost:8000/api/artists?q=BTS&limit=5"

# Listens data
curl -X POST http://localhost:8000/api/listens \
  -H "Content-Type: application/json" \
  -d '{"artist_ids": [1], "limit": 20}'

# CSV download
curl -X POST http://localhost:8000/api/listens/csv \
  -H "Content-Type: application/json" \
  -d '{"artist_ids": [1], "limit": 20}' \
  --output listens.csv
```

## 환경 설정

### 개발 환경

`res/.env.example` 파일을 복사하여 `.env` 파일 생성:

```bash
cp res/.env.example res/.env
# .env 파일에서 Redshift 연결 정보 수정
```

### 운영 환경

`res/.env.prod.example`을 참고하여 운영 환경 설정:
- Redshift 연결 정보
- CORS 설정
- 로그 레벨

## 주요 기능

1. **아티스트 자동완성**: Debounce 검색, 다중 선택
2. **필터링**: 청취 횟수 범위 필터
3. **데이터 시각화**: 
   - 통계 요약 (count, max, min, avg, median)
   - 상위 10개 바 차트
   - 상위 20개 데이터 테이블
4. **CSV 다운로드**: 필터된 데이터 + 통계 footer
5. **다크/라이트 테마**: 사용자 선호도 저장

## 로그

애플리케이션 로그는 `logs/` 디렉터리에 저장:
- `process.log` - 작업 진행 현황
- Backend logs는 Docker logs로도 확인 가능: `docker-compose logs -f backend`

## 개발 가이드

자세한 개발 원칙 및 가이드는 다음 문서 참고:
- [requirements.md](docs/requirements.md) - 요구사항 정의
- [design.md](docs/design.md) - 설계 문서
- [development_guide.md](docs/development_guide.md) - 개발 가이드
- [tasks/](docs/tasks/) - 단계별 작업 문서
