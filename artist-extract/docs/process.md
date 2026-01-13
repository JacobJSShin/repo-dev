# process.md

Artist Character 데이터 조회 애플리케이션 개발 실행 계획

참조: [design.md](design.md), [requirements_detail.md](requirements_detail.md)

## 개발 원칙

- **TDD (Test-Driven Development)**: 테스트 먼저 작성 → 구현 → 리팩토링
- **SOLID 원칙**: 단일 책임, 개방-폐쇄, 리스코프 치환, 인터페이스 분리, 의존성 역전
- **Clean Architecture**: 레이어 분리 및 의존성 방향 준수
- **점진적 개발**: 각 단계는 독립적으로 실행 및 테스트 가능

## 사전 준비사항

### 1. 개발 환경 확인
- [ ] Python 3.9 이상 설치 확인
- [ ] Git 설치 확인
- [ ] AWS Redshift 접근 권한 확인
- [ ] IDE/Editor 설정 (VSCode 권장)

### 2. Redshift 스키마 확인
- [ ] `flo_deh.d_artist` 테이블 구조 확인
- [ ] `flo_deh.user_artist_listens` 테이블 구조 확인
- [ ] 샘플 데이터 확인 (최소 100건 이상)
- [ ] 필요 시 테스트용 뷰 또는 테이블 생성

### 3. 프로젝트 초기화
```bash
cd /Users/shen/Dev/music-flo/floda-workflow/artist-extract
```

---

## Phase 1: 프로젝트 기반 구축

### Step 1.1: 프로젝트 구조 생성

**목표**: Clean Architecture 기반 디렉토리 구조 생성

**체크리스트**:
- [ ] 기본 디렉토리 구조 생성
- [ ] `__init__.py` 파일 생성
- [ ] `.gitignore` 설정

**실행 명령**:
```bash
# 디렉토리 생성
mkdir -p src/{domain/{services,models},infrastructure/{database,config,logging},ui/{components,utils}}
mkdir -p tests/{unit,integration}
mkdir -p logs
mkdir -p .streamlit

# __init__.py 생성
touch src/__init__.py
touch src/domain/__init__.py
touch src/domain/services/__init__.py
touch src/domain/models/__init__.py
touch src/infrastructure/__init__.py
touch src/infrastructure/database/__init__.py
touch src/infrastructure/config/__init__.py
touch src/infrastructure/logging/__init__.py
touch src/ui/__init__.py
touch src/ui/components/__init__.py
touch src/ui/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

**생성 파일**:
- `.gitignore`
- `README.md` (프로젝트 개요)

**검증**:
```bash
tree -L 3 src/
tree -L 2 tests/
```

**완료 조건**: 디렉토리 구조가 design.md의 구조와 일치

---

### Step 1.2: 의존성 관리 설정

**목표**: Python 패키지 의존성 정의

**체크리스트**:
- [ ] `requirements.txt` 생성
- [ ] 가상환경 생성 및 활성화
- [ ] 패키지 설치 확인

**실행 명령**:
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 설치 확인
pip list
```

**생성 파일**:
- `requirements.txt`
- `requirements-dev.txt` (개발 전용 패키지)

**파일 내용**:
```txt
# requirements.txt
streamlit>=1.28.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
redshift-connector>=2.0.0
sqlalchemy>=2.0.0
plotly>=5.17.0
altair>=5.1.0
pyyaml>=6.0

# requirements-dev.txt
-r requirements.txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
black>=23.0.0
flake8>=6.1.0
mypy>=1.7.0
```

**검증**:
```bash
python -c "import streamlit; print(streamlit.__version__)"
python -c "import pandas; print(pandas.__version__)"
```

**완료 조건**: 모든 패키지가 정상적으로 설치됨

---

### Step 1.3: 설정 파일 구조 생성

**목표**: 환경별 설정 파일 및 시크릿 관리 구조 생성

**체크리스트**:
- [ ] Redshift 연결 정보 템플릿 생성
- [ ] Streamlit 설정 파일 생성
- [ ] Git에서 민감 정보 제외

**실행 명령**:
```bash
# 설정 파일 템플릿 생성
touch res/config.artist-extract.dev.yml
touch .streamlit/config.toml
touch .streamlit/secrets.toml.example

# .gitignore에 추가
echo ".streamlit/secrets.toml" >> .gitignore
echo "venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "logs/*.log" >> .gitignore
```

**생성 파일**:
- `res/config.artist-extract.dev.yml`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`
- `.gitignore`

**파일 내용 예시**:

`res/config.artist-extract.dev.yml`:
```yaml
app:
  name: "Artist Character 데이터 조회"
  version: "1.0.0"
  log_level: "DEBUG"

database:
  type: "redshift"
  # 실제 연결 정보는 .streamlit/secrets.toml에서 관리

cache:
  artist_search_ttl: 300  # 5분
```

`.streamlit/config.toml`:
```toml
[theme]
primaryColor="#FF4B4B"
backgroundColor="#0E1117"
secondaryBackgroundColor="#262730"
textColor="#FAFAFA"
font="sans serif"

[server]
headless = true
port = 8501
```

`.streamlit/secrets.toml.example`:
```toml
[redshift]
host = "your-cluster.xxxxxx.region.redshift.amazonaws.com"
port = 5439
database = "your_database"
user = "your_username"
password = "your_password"
schema = "flo_deh"
sslmode = "require"
```

**검증**:
```bash
cat .gitignore | grep secrets.toml
cat res/config.artist-extract.dev.yml
```

**완료 조건**: 설정 파일 구조가 완성되고 민감 정보가 Git에서 제외됨

---

### Step 1.4: 로깅 설정 구현

**목표**: 애플리케이션 로깅 기반 구축

**테스트 파일**: `tests/unit/test_logger.py`

**테스트 코드 작성**:
```python
# tests/unit/test_logger.py
import pytest
import logging
from pathlib import Path
from src.infrastructure.logging.logger import get_logger, setup_logging

def test_setup_logging_creates_log_file():
    """로그 파일이 정상적으로 생성되는지 확인"""
    setup_logging()
    log_file = Path("logs/process.log")
    assert log_file.exists()

def test_get_logger_returns_configured_logger():
    """로거가 정상적으로 설정되는지 확인"""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG

def test_logger_writes_to_file(tmp_path):
    """로거가 파일에 정상적으로 기록하는지 확인"""
    log_file = tmp_path / "test.log"
    logger = get_logger(__name__)
    
    # 테스트 로그 핸들러 추가
    handler = logging.FileHandler(log_file)
    logger.addHandler(handler)
    
    logger.info("Test log message")
    
    assert log_file.exists()
    assert "Test log message" in log_file.read_text()
```

**구현 파일**: `src/infrastructure/logging/logger.py`

**구현 코드**:
```python
# src/infrastructure/logging/logger.py
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_level: str = "INFO", log_file: str = "logs/process.log"):
    """로깅 설정 초기화"""
    # 로그 디렉토리 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 로그 포맷 설정
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 루트 로거 설정
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 콘솔 핸들러
            logging.StreamHandler(sys.stdout),
            # 파일 핸들러 (10MB, 5개 백업)
            RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,
                backupCount=5,
                encoding='utf-8'
            )
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)
```

**실행 및 검증**:
```bash
# 테스트 실행
pytest tests/unit/test_logger.py -v

# 커버리지 확인
pytest tests/unit/test_logger.py --cov=src/infrastructure/logging --cov-report=term-missing
```

**완료 조건**: 
- 모든 테스트 통과
- 로그 파일이 `logs/process.log`에 생성됨
- 커버리지 80% 이상

---

## Phase 2: Infrastructure Layer 구현

### Step 2.1: Config Loader 구현

**목표**: YAML 설정 파일 로더 구현

**테스트 파일**: `tests/unit/test_config_loader.py`

**테스트 코드**:
```python
# tests/unit/test_config_loader.py
import pytest
from pathlib import Path
from src.infrastructure.config.config_loader import ConfigLoader, ConfigurationError

@pytest.fixture
def config_loader():
    return ConfigLoader()

def test_load_config_success(config_loader):
    """설정 파일 로드 성공"""
    config = config_loader.load_config("dev")
    assert config is not None
    assert "app" in config
    assert "database" in config

def test_load_config_file_not_found(config_loader):
    """존재하지 않는 설정 파일"""
    with pytest.raises(ConfigurationError):
        config_loader.load_config("nonexistent")

def test_get_db_config(config_loader):
    """DB 설정 조회"""
    config_loader.load_config("dev")
    db_config = config_loader.get_db_config()
    assert "type" in db_config

def test_get_app_config(config_loader):
    """앱 설정 조회"""
    config_loader.load_config("dev")
    app_config = config_loader.get_app_config()
    assert "name" in app_config
    assert "version" in app_config
```

**구현 파일**: `src/infrastructure/config/config_loader.py`

**구현 코드**:
```python
# src/infrastructure/config/config_loader.py
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigurationError(Exception):
    """설정 관련 예외"""
    pass

class ConfigLoader:
    """YAML 설정 파일 로더"""
    
    def __init__(self, config_dir: str = "res"):
        self.config_dir = Path(config_dir)
        self.config: Dict[str, Any] = {}
    
    def load_config(self, env: str = "dev") -> Dict[str, Any]:
        """환경별 설정 파일 로드"""
        config_file = self.config_dir / f"config.artist-extract.{env}.yml"
        
        if not config_file.exists():
            raise ConfigurationError(f"Config file not found: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            return self.config
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML: {e}")
    
    def get_db_config(self) -> Dict[str, Any]:
        """데이터베이스 설정 반환"""
        if "database" not in self.config:
            raise ConfigurationError("Database config not found")
        return self.config["database"]
    
    def get_app_config(self) -> Dict[str, Any]:
        """애플리케이션 설정 반환"""
        if "app" not in self.config:
            raise ConfigurationError("App config not found")
        return self.config["app"]
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        return self.config.get(key, default)
```

**실행 및 검증**:
```bash
pytest tests/unit/test_config_loader.py -v
pytest tests/unit/test_config_loader.py --cov=src/infrastructure/config
```

**완료 조건**: 모든 테스트 통과, 커버리지 80% 이상

---

### Step 2.2: Redshift Connector 구현

**목표**: Redshift 데이터베이스 연결 및 쿼리 실행 모듈 구현

**테스트 파일**: `tests/unit/test_redshift_connector.py`

**테스트 코드**:
```python
# tests/unit/test_redshift_connector.py
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from src.infrastructure.database.redshift_connector import (
    RedshiftConnector,
    DatabaseConnectionError,
    QueryExecutionError
)

@pytest.fixture
def mock_config():
    return {
        "host": "test-cluster.redshift.amazonaws.com",
        "port": 5439,
        "database": "test_db",
        "user": "test_user",
        "password": "test_pass",
        "schema": "test_schema"
    }

@pytest.fixture
def connector(mock_config):
    with patch('streamlit.secrets') as mock_secrets:
        mock_secrets.__getitem__.return_value = mock_config
        return RedshiftConnector()

def test_connector_initialization(connector):
    """커넥터 초기화 확인"""
    assert connector is not None
    assert connector.schema == "test_schema"

@patch('psycopg2.connect')
def test_get_connection_success(mock_connect, connector):
    """DB 연결 성공"""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    
    conn = connector.get_connection()
    assert conn is not None
    mock_connect.assert_called_once()

@patch('psycopg2.connect')
def test_get_connection_failure(mock_connect, connector):
    """DB 연결 실패"""
    mock_connect.side_effect = Exception("Connection failed")
    
    with pytest.raises(DatabaseConnectionError):
        connector.get_connection()

@patch('psycopg2.connect')
def test_execute_query_success(mock_connect, connector):
    """쿼리 실행 성공"""
    # Mock 커넥션 및 커서 설정
    mock_cursor = MagicMock()
    mock_cursor.description = [('col1',), ('col2',)]
    mock_cursor.fetchall.return_value = [('val1', 'val2')]
    
    mock_conn = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # 쿼리 실행
    query = "SELECT * FROM test_table WHERE id = %(id)s"
    params = {"id": 1}
    result = connector.execute_query(query, params)
    
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1

@patch('psycopg2.connect')
def test_execute_query_failure(mock_connect, connector):
    """쿼리 실행 실패"""
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("Query failed")
    
    mock_conn = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    with pytest.raises(QueryExecutionError):
        connector.execute_query("INVALID QUERY")

def test_close_connection(connector):
    """연결 종료"""
    connector._connection = Mock()
    connector.close_connection()
    connector._connection.close.assert_called_once()
```

**구현 파일**: `src/infrastructure/database/redshift_connector.py`

**구현 코드**:
```python
# src/infrastructure/database/redshift_connector.py
import psycopg2
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional
from contextlib import contextmanager
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class DatabaseConnectionError(Exception):
    """데이터베이스 연결 실패"""
    pass

class QueryExecutionError(Exception):
    """쿼리 실행 실패"""
    pass

class RedshiftConnector:
    """AWS Redshift 데이터베이스 커넥터"""
    
    def __init__(self):
        """Streamlit secrets에서 DB 설정 로드"""
        try:
            self.config = st.secrets["redshift"]
            self.schema = self.config.get("schema", "public")
            self._connection: Optional[Any] = None
            logger.info("RedshiftConnector initialized")
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing redshift config in secrets: {e}")
    
    def get_connection(self):
        """DB 커넥션 반환 (재사용)"""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(
                    host=self.config["host"],
                    port=self.config["port"],
                    database=self.config["database"],
                    user=self.config["user"],
                    password=self.config["password"],
                    sslmode=self.config.get("sslmode", "require")
                )
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise DatabaseConnectionError(f"Failed to connect to Redshift: {e}")
        
        return self._connection
    
    @contextmanager
    def get_cursor(self):
        """커서 컨텍스트 매니저"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """쿼리 실행 및 결과를 DataFrame으로 반환"""
        try:
            logger.debug(f"Executing query: {query[:100]}...")
            logger.debug(f"Query params: {params}")
            
            with self.get_cursor() as cursor:
                cursor.execute(query, params or {})
                
                # 결과가 있는 경우 (SELECT)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    df = pd.DataFrame(rows, columns=columns)
                    logger.info(f"Query executed successfully. Rows: {len(df)}")
                    return df
                else:
                    # 결과가 없는 경우 (INSERT, UPDATE, DELETE)
                    logger.info("Query executed successfully (no results)")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryExecutionError(f"Failed to execute query: {e}")
    
    def close_connection(self):
        """DB 커넥션 종료"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
```

**실행 및 검증**:
```bash
pytest tests/unit/test_redshift_connector.py -v
pytest tests/unit/test_redshift_connector.py --cov=src/infrastructure/database
```

**완료 조건**: 모든 테스트 통과, 커버리지 80% 이상

---

## Phase 3: Domain Layer 구현

### Step 3.1: Domain Models 구현

**목표**: 도메인 모델 (Artist, Listen, Statistics) 정의

**테스트 파일**: `tests/unit/test_models.py`

**테스트 코드**:
```python
# tests/unit/test_models.py
import pytest
from src.domain.models.artist import Artist
from src.domain.models.listen import Listen, ListenFilter, StatisticsSummary

def test_artist_creation():
    """Artist 모델 생성"""
    artist = Artist(artist_id=1, artist_nm="아이유")
    assert artist.artist_id == 1
    assert artist.artist_nm == "아이유"
    assert str(artist) == "아이유 (ID: 1)"

def test_listen_creation():
    """Listen 모델 생성"""
    listen = Listen(user_id=123, artist_id=1, listen_count=50)
    assert listen.user_id == 123
    assert listen.artist_id == 1
    assert listen.listen_count == 50

def test_listen_filter_to_query_params():
    """ListenFilter 쿼리 파라미터 변환"""
    filter = ListenFilter(
        artist_ids=[1, 2, 3],
        min_count=10,
        max_count=100
    )
    params = filter.to_query_params()
    
    assert params["artist_ids"] == (1, 2, 3)
    assert params["min_count"] == 10
    assert params["max_count"] == 100

def test_listen_filter_default_values():
    """ListenFilter 기본값"""
    filter = ListenFilter(artist_ids=[1])
    params = filter.to_query_params()
    
    assert params["min_count"] == 0
    assert params["max_count"] == 999999

def test_statistics_summary():
    """StatisticsSummary 생성 및 변환"""
    summary = StatisticsSummary(
        total_users=100,
        max_listen_count=150,
        min_listen_count=10,
        avg_listen_count=45.5,
        median_listen_count=40.0
    )
    
    assert summary.total_users == 100
    assert summary.max_listen_count == 150
    
    summary_dict = summary.to_dict()
    assert "total_users" in summary_dict
    assert summary_dict["avg_listen_count"] == 45.5
```

**구현 파일들**:

`src/domain/models/artist.py`:
```python
from dataclasses import dataclass

@dataclass
class Artist:
    """아티스트 도메인 모델"""
    artist_id: int
    artist_nm: str
    
    def __str__(self) -> str:
        return f"{self.artist_nm} (ID: {self.artist_id})"
```

`src/domain/models/listen.py`:
```python
from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class Listen:
    """청취 데이터 도메인 모델"""
    user_id: int
    artist_id: int
    listen_count: int

@dataclass
class ListenFilter:
    """청취 데이터 필터"""
    artist_ids: List[int]
    min_count: Optional[int] = None
    max_count: Optional[int] = None
    
    def to_query_params(self) -> dict:
        """쿼리 파라미터로 변환"""
        return {
            'artist_ids': tuple(self.artist_ids),
            'min_count': self.min_count if self.min_count is not None else 0,
            'max_count': self.max_count if self.max_count is not None else 999999
        }

@dataclass
class StatisticsSummary:
    """통계 요약 모델"""
    total_users: int
    max_listen_count: int
    min_listen_count: int
    avg_listen_count: float
    median_listen_count: float
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return asdict(self)
```

**실행 및 검증**:
```bash
pytest tests/unit/test_models.py -v
```

**완료 조건**: 모든 테스트 통과

---

### Step 3.2: Artist Service 구현

**목표**: 아티스트 검색 비즈니스 로직 구현

**테스트 파일**: `tests/unit/test_artist_service.py`

**테스트 코드**:
```python
# tests/unit/test_artist_service.py
import pytest
import pandas as pd
from unittest.mock import Mock
from src.domain.services.artist_service import ArtistService
from src.domain.models.artist import Artist

@pytest.fixture
def mock_db_connector():
    return Mock()

@pytest.fixture
def artist_service(mock_db_connector):
    return ArtistService(mock_db_connector)

def test_search_artists_success(artist_service, mock_db_connector):
    """아티스트 검색 성공"""
    # Mock 데이터
    mock_data = pd.DataFrame([
        {"artist_id": 1, "artist_nm": "아이유"},
        {"artist_id": 2, "artist_nm": "아이유(IU)"}
    ])
    mock_db_connector.execute_query.return_value = mock_data
    
    # 검색 실행
    results = artist_service.search_artists("아이유")
    
    assert len(results) == 2
    assert all(isinstance(r, Artist) for r in results)
    assert results[0].artist_nm == "아이유"

def test_search_artists_empty_term(artist_service):
    """빈 검색어"""
    results = artist_service.search_artists("")
    assert len(results) == 0

def test_search_artists_no_results(artist_service, mock_db_connector):
    """검색 결과 없음"""
    mock_db_connector.execute_query.return_value = pd.DataFrame()
    
    results = artist_service.search_artists("nonexistent")
    assert len(results) == 0

def test_search_artists_limit_5(artist_service, mock_db_connector):
    """최대 5개 결과 제한"""
    # 10개 결과 생성
    mock_data = pd.DataFrame([
        {"artist_id": i, "artist_nm": f"Artist{i}"}
        for i in range(10)
    ])
    mock_db_connector.execute_query.return_value = mock_data
    
    results = artist_service.search_artists("Artist")
    
    # 실제로는 쿼리에 LIMIT이 있지만, 서비스에서도 검증
    assert len(results) <= 5

def test_get_artist_by_id(artist_service, mock_db_connector):
    """ID로 아티스트 조회"""
    mock_data = pd.DataFrame([
        {"artist_id": 1, "artist_nm": "아이유"}
    ])
    mock_db_connector.execute_query.return_value = mock_data
    
    artist = artist_service.get_artist_by_id(1)
    
    assert artist is not None
    assert artist.artist_id == 1
    assert artist.artist_nm == "아이유"

def test_get_artist_by_id_not_found(artist_service, mock_db_connector):
    """존재하지 않는 아티스트"""
    mock_db_connector.execute_query.return_value = pd.DataFrame()
    
    artist = artist_service.get_artist_by_id(999)
    assert artist is None
```

**구현 파일**: `src/domain/services/artist_service.py`

**구현 코드**:
```python
# src/domain/services/artist_service.py
from typing import List, Optional
import pandas as pd
from src.domain.models.artist import Artist
from src.infrastructure.database.redshift_connector import RedshiftConnector
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class ArtistService:
    """아티스트 검색 비즈니스 로직"""
    
    def __init__(self, db_connector: RedshiftConnector):
        self.db = db_connector
    
    def search_artists(self, search_term: str) -> List[Artist]:
        """아티스트 검색 (최대 5개)"""
        if not search_term or not search_term.strip():
            logger.warning("Empty search term provided")
            return []
        
        query = """
            SELECT artist_id, artist_nm
            FROM flo_deh.d_artist
            WHERE artist_nm ILIKE %(search_term)s
            LIMIT 5
        """
        params = {"search_term": f"%{search_term}%"}
        
        try:
            logger.info(f"Searching artists with term: '{search_term}'")
            df = self.db.execute_query(query, params)
            
            if df.empty:
                logger.info("No artists found")
                return []
            
            artists = [
                Artist(artist_id=row["artist_id"], artist_nm=row["artist_nm"])
                for _, row in df.iterrows()
            ]
            
            logger.info(f"Found {len(artists)} artists")
            return artists
            
        except Exception as e:
            logger.error(f"Failed to search artists: {e}")
            raise
    
    def get_artist_by_id(self, artist_id: int) -> Optional[Artist]:
        """ID로 아티스트 조회"""
        query = """
            SELECT artist_id, artist_nm
            FROM flo_deh.d_artist
            WHERE artist_id = %(artist_id)s
        """
        params = {"artist_id": artist_id}
        
        try:
            df = self.db.execute_query(query, params)
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            return Artist(artist_id=row["artist_id"], artist_nm=row["artist_nm"])
            
        except Exception as e:
            logger.error(f"Failed to get artist by id {artist_id}: {e}")
            raise
```

**실행 및 검증**:
```bash
pytest tests/unit/test_artist_service.py -v
pytest tests/unit/test_artist_service.py --cov=src/domain/services/artist_service
```

**완료 조건**: 모든 테스트 통과, 커버리지 80% 이상

---

### Step 3.3: Listens Service 구현

**목표**: 청취 데이터 조회 비즈니스 로직 구현

**실행 절차**: Step 3.2와 유사하게 테스트 먼저 작성 → 구현 → 검증

**테스트 파일**: `tests/unit/test_listens_service.py`
**구현 파일**: `src/domain/services/listens_service.py`

**핵심 테스트 케이스**:
- 필터 없이 조회
- 청취건수 범위 필터 적용
- 여러 아티스트 동시 조회
- 빈 결과 처리
- 내림차순 정렬 검증

**완료 조건**: 모든 테스트 통과, 커버리지 80% 이상

---

### Step 3.4: Statistics Service 구현

**목표**: 통계 계산 비즈니스 로직 구현

**테스트 파일**: `tests/unit/test_statistics_service.py`
**구현 파일**: `src/domain/services/statistics_service.py`

**핵심 테스트 케이스**:
- 정확한 통계값 계산 (max, min, avg, median)
- 빈 데이터프레임 처리
- 단일 행 데이터 처리
- 중앙값 계산 (홀수/짝수 행)

**완료 조건**: 모든 테스트 통과, 커버리지 90% 이상

---

## Phase 4: UI Layer 구현

### Step 4.1: 세션 상태 관리 구현

**목표**: Streamlit 세션 상태 관리 유틸리티

**구현 파일**: `src/ui/utils/session_state.py`

**구현 코드**:
```python
# src/ui/utils/session_state.py
import streamlit as st
from typing import Any

class SessionStateManager:
    """Streamlit 세션 상태 관리"""
    
    @staticmethod
    def initialize():
        """세션 상태 초기화"""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.search_term = ""
            st.session_state.artist_options = []
            st.session_state.selected_artists = []
            st.session_state.listen_count_range = (0, 100)
            st.session_state.query_results = None
            st.session_state.statistics = None
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """세션 상태 조회"""
        return st.session_state.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any):
        """세션 상태 설정"""
        st.session_state[key] = value
    
    @staticmethod
    def clear():
        """세션 상태 초기화"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
```

**검증**: 수동 테스트 (Streamlit 앱 실행 시 확인)

---

### Step 4.2: 사이드바 컴포넌트 구현

**목표**: 아티스트 검색 및 필터 UI 구현

**구현 파일**: `src/ui/components/sidebar.py`

**구현 코드**:
```python
# src/ui/components/sidebar.py
import streamlit as st
from typing import List, Tuple
from src.domain.models.artist import Artist
from src.domain.services.artist_service import ArtistService

class Sidebar:
    """사이드바 UI 컴포넌트"""
    
    def __init__(self, artist_service: ArtistService):
        self.artist_service = artist_service
    
    def render(self) -> Tuple[List[int], Tuple[int, int], bool]:
        """
        사이드바 렌더링
        
        Returns:
            (selected_artist_ids, listen_count_range, query_button_clicked)
        """
        st.sidebar.title("🎵 아티스트 검색")
        
        # 검색어 입력
        search_term = st.sidebar.text_input(
            "가수명 입력",
            value=st.session_state.get('search_term', ''),
            placeholder="예: 아이유",
            help="검색할 가수명을 입력하세요"
        )
        
        # 검색어 변경 시 아티스트 검색
        artist_options = []
        if search_term:
            with st.spinner("검색 중..."):
                artists = self.artist_service.search_artists(search_term)
                artist_options = artists
                st.session_state.artist_options = artists
        
        # 아티스트 선택 (다중 선택)
        if artist_options:
            st.sidebar.markdown("### 아티스트 선택")
            selected_artists = st.sidebar.multiselect(
                "조회할 아티스트를 선택하세요 (다중 선택 가능)",
                options=artist_options,
                format_func=lambda x: x.artist_nm,
                default=st.session_state.get('selected_artists', [])
            )
            st.session_state.selected_artists = selected_artists
            selected_artist_ids = [a.artist_id for a in selected_artists]
        else:
            selected_artist_ids = []
        
        # 청취건수 필터
        st.sidebar.markdown("### 🎚️ 청취건수 필터")
        listen_count_range = st.sidebar.slider(
            "청취건수 범위",
            min_value=0,
            max_value=1000,
            value=st.session_state.get('listen_count_range', (0, 100)),
            help="조회할 청취건수 범위를 설정하세요"
        )
        st.session_state.listen_count_range = listen_count_range
        
        # 조회 버튼
        st.sidebar.markdown("---")
        query_button = st.sidebar.button(
            "🔍 데이터 조회",
            type="primary",
            use_container_width=True,
            disabled=len(selected_artist_ids) == 0
        )
        
        if len(selected_artist_ids) == 0:
            st.sidebar.info("아티스트를 선택한 후 조회하세요")
        
        return selected_artist_ids, listen_count_range, query_button
```

---

### Step 4.3: 데이터 테이블 컴포넌트 구현

**구현 파일**: `src/ui/components/data_table.py`

**구현 코드**:
```python
# src/ui/components/data_table.py
import streamlit as st
import pandas as pd

class DataTable:
    """데이터 테이블 UI 컴포넌트"""
    
    @staticmethod
    def render(df: pd.DataFrame, limit: int = 20):
        """
        데이터 테이블 렌더링
        
        Args:
            df: 표시할 데이터프레임
            limit: 화면에 표시할 최대 행 수
        """
        if df.empty:
            st.info("📭 조회 결과가 없습니다. 필터 조건을 변경해보세요.")
            return
        
        st.markdown(f"### 📊 조회 결과 (전체 {len(df):,}건 중 상위 {limit}건)")
        
        # 상위 N건만 표시
        display_df = df.head(limit)
        
        # 데이터 타입 포맷팅
        if 'listen_count' in display_df.columns:
            display_df = display_df.copy()
            display_df['listen_count'] = display_df['listen_count'].apply(lambda x: f"{x:,}")
        
        # 데이터프레임 표시
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # CSV 다운로드 버튼
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 전체 데이터 CSV 다운로드",
            data=csv_data,
            file_name="artist_listens_data.csv",
            mime="text/csv",
            help=f"전체 {len(df):,}건의 데이터를 다운로드합니다"
        )
```

---

### Step 4.4: 통계 컴포넌트 구현

**구현 파일**: `src/ui/components/statistics.py`

**구현 코드**:
```python
# src/ui/components/statistics.py
import streamlit as st
from src.domain.models.listen import StatisticsSummary

class StatisticsPanel:
    """통계 표시 UI 컴포넌트"""
    
    @staticmethod
    def render(summary: StatisticsSummary):
        """통계 요약 렌더링"""
        st.markdown("### 📈 요약 통계")
        
        # 5개 열로 분할
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="총 사용자 수",
                value=f"{summary.total_users:,}",
                help="전체 사용자(레코드) 수"
            )
        
        with col2:
            st.metric(
                label="최대 청취건수",
                value=f"{summary.max_listen_count:,}",
                help="가장 많이 청취한 사용자의 청취건수"
            )
        
        with col3:
            st.metric(
                label="최소 청취건수",
                value=f"{summary.min_listen_count:,}",
                help="가장 적게 청취한 사용자의 청취건수"
            )
        
        with col4:
            st.metric(
                label="평균 청취건수",
                value=f"{summary.avg_listen_count:.1f}",
                help="평균 청취건수"
            )
        
        with col5:
            st.metric(
                label="중앙값",
                value=f"{summary.median_listen_count:.1f}",
                help="50% 백분위수 (중앙값)"
            )
```

---

### Step 4.5: 시각화 컴포넌트 구현

**구현 파일**: `src/ui/components/visualization.py`

**구현 코드**:
```python
# src/ui/components/visualization.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

class VisualizationBoard:
    """시각화 UI 컴포넌트"""
    
    @staticmethod
    def render(df: pd.DataFrame):
        """시각화 보드 렌더링"""
        if df.empty:
            return
        
        st.markdown("### 📊 시각화")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 청취건수 분포 히스토그램
            st.markdown("#### 청취건수 분포")
            fig_hist = px.histogram(
                df,
                x='listen_count',
                nbins=30,
                title='청취건수 분포',
                labels={'listen_count': '청취건수', 'count': '사용자 수'}
            )
            fig_hist.update_layout(showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # 상위 사용자 바차트
            st.markdown("#### 상위 10명 사용자")
            top_users = df.nlargest(10, 'listen_count')
            fig_bar = px.bar(
                top_users,
                x='user_id',
                y='listen_count',
                title='상위 10명 사용자별 청취건수',
                labels={'user_id': '사용자 ID', 'listen_count': '청취건수'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
```

---

### Step 4.6: 메인 애플리케이션 구현

**목표**: 모든 컴포넌트를 통합한 Streamlit 앱 구현

**구현 파일**: `src/streamlit_app.py`

**구현 코드**:
```python
# src/streamlit_app.py
import streamlit as st
from src.infrastructure.logging.logger import setup_logging, get_logger
from src.infrastructure.config.config_loader import ConfigLoader
from src.infrastructure.database.redshift_connector import RedshiftConnector
from src.domain.services.artist_service import ArtistService
from src.domain.services.listens_service import ListensService
from src.domain.services.statistics_service import StatisticsService
from src.domain.models.listen import ListenFilter
from src.ui.utils.session_state import SessionStateManager
from src.ui.components.sidebar import Sidebar
from src.ui.components.data_table import DataTable
from src.ui.components.statistics import StatisticsPanel
from src.ui.components.visualization import VisualizationBoard

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="Artist Character 데이터 조회",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 캐싱된 리소스
@st.cache_resource
def get_db_connector():
    """DB 커넥터 초기화 (리소스 재사용)"""
    return RedshiftConnector()

@st.cache_resource
def get_services():
    """서비스 인스턴스 반환"""
    db = get_db_connector()
    return {
        'artist': ArtistService(db),
        'listens': ListensService(db),
        'statistics': StatisticsService()
    }

def main():
    """메인 애플리케이션"""
    logger.info("Application started")
    
    # 세션 상태 초기화
    SessionStateManager.initialize()
    
    # 서비스 로드
    services = get_services()
    
    # 타이틀
    st.title("🎵 Artist Character 데이터 조회")
    st.markdown("특정 아티스트의 팬덤 사용자 청취 데이터를 조회하고 분석합니다.")
    st.markdown("---")
    
    # 사이드바 렌더링
    sidebar = Sidebar(services['artist'])
    selected_artist_ids, listen_count_range, query_button = sidebar.render()
    
    # 조회 버튼 클릭 시
    if query_button:
        with st.spinner("데이터 조회 중..."):
            try:
                # 청취 데이터 조회
                filter = ListenFilter(
                    artist_ids=selected_artist_ids,
                    min_count=listen_count_range[0],
                    max_count=listen_count_range[1]
                )
                df = services['listens'].get_listens_by_artists(filter)
                
                if df.empty:
                    st.warning("조회 결과가 없습니다. 필터 조건을 변경해보세요.")
                else:
                    # 통계 계산
                    summary = services['statistics'].calculate_summary(df)
                    
                    # 세션 상태에 저장
                    st.session_state.query_results = df
                    st.session_state.statistics = summary
                    
                    logger.info(f"Query completed. Rows: {len(df)}")
                    
            except Exception as e:
                st.error(f"데이터 조회 중 오류가 발생했습니다: {str(e)}")
                logger.error(f"Query failed: {e}", exc_info=True)
    
    # 결과 표시
    if st.session_state.query_results is not None:
        df = st.session_state.query_results
        summary = st.session_state.statistics
        
        # 데이터 테이블
        DataTable.render(df, limit=20)
        
        st.markdown("---")
        
        # 통계
        StatisticsPanel.render(summary)
        
        st.markdown("---")
        
        # 시각화
        VisualizationBoard.render(df)

if __name__ == "__main__":
    main()
```

**실행 및 검증**:
```bash
# .streamlit/secrets.toml 파일 생성 (예시에서 복사)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
vim .streamlit/secrets.toml  # DB 정보 입력

# Streamlit 앱 실행
streamlit run src/streamlit_app.py
```

**검증 체크리스트**:
- [ ] 앱이 정상적으로 실행됨
- [ ] 사이드바에서 검색 가능
- [ ] 아티스트 다중 선택 가능
- [ ] 청취건수 필터 동작
- [ ] 조회 버튼 클릭 시 데이터 로드
- [ ] 데이터 테이블 표시
- [ ] CSV 다운로드 동작
- [ ] 통계 표시
- [ ] 시각화 차트 표시

**완료 조건**: 모든 UI 컴포넌트가 정상 동작

---

## Phase 5: 통합 테스트 및 안정화

### Step 5.1: 통합 테스트 작성

**목표**: End-to-End 통합 테스트

**테스트 파일**: `tests/integration/test_end_to_end.py`

**테스트 시나리오**:
1. DB 연결 → 아티스트 검색 → 청취 데이터 조회 → 통계 계산
2. 실제 Redshift 연결 (테스트 DB 또는 개발 DB)
3. 전체 플로우 검증

**실행**:
```bash
pytest tests/integration/ -v -s
```

---

### Step 5.2: 코드 품질 검사

**목표**: 코드 포맷팅 및 린팅

**실행 명령**:
```bash
# Black (코드 포맷팅)
black src/ tests/

# Flake8 (린팅)
flake8 src/ tests/ --max-line-length=100

# MyPy (타입 체킹)
mypy src/ --ignore-missing-imports
```

**완료 조건**: 모든 검사 통과 또는 경고만 존재

---

### Step 5.3: 문서화 완성

**목표**: 프로젝트 README 및 사용자 가이드 작성

**생성 파일**:
- `README.md` (루트)
- `docs/USER_GUIDE.md`

**README.md 구조**:
- 프로젝트 개요
- 기능 목록
- 설치 방법
- 실행 방법
- 설정 방법
- 개발 가이드
- 라이선스

---

### Step 5.4: 성능 최적화

**목표**: 쿼리 및 캐싱 최적화

**체크리스트**:
- [ ] 아티스트 검색 캐싱 (`@st.cache_data`)
- [ ] DB 커넥션 풀링 확인
- [ ] 쿼리 실행 시간 로깅
- [ ] 대용량 데이터 처리 테스트 (10만 건 이상)

**완료 조건**: 
- 아티스트 검색 300ms 이내
- 청취 데이터 조회 5초 이내 (10만 건 기준)

---

## Phase 6: 배포 준비

### Step 6.1: 로컬 실행 가이드 작성

**문서**: `docs/DEPLOYMENT.md`

**내용**:
- 환경 설정
- 의존성 설치
- DB 연결 설정
- 실행 명령어
- 트러블슈팅

---

### Step 6.2: Streamlit Cloud 배포 (선택사항)

**절차**:
1. GitHub 리포지토리에 푸시
2. Streamlit Cloud 계정 생성
3. 앱 연결 및 Secrets 설정
4. 배포 및 테스트

---

## 체크리스트 요약

### Phase 1: 프로젝트 기반 구축
- [ ] 1.1 프로젝트 구조 생성
- [ ] 1.2 의존성 관리 설정
- [ ] 1.3 설정 파일 구조 생성
- [ ] 1.4 로깅 설정 구현

### Phase 2: Infrastructure Layer
- [ ] 2.1 Config Loader 구현
- [ ] 2.2 Redshift Connector 구현

### Phase 3: Domain Layer
- [ ] 3.1 Domain Models 구현
- [ ] 3.2 Artist Service 구현
- [ ] 3.3 Listens Service 구현
- [ ] 3.4 Statistics Service 구현

### Phase 4: UI Layer
- [ ] 4.1 세션 상태 관리 구현
- [ ] 4.2 사이드바 컴포넌트 구현
- [ ] 4.3 데이터 테이블 컴포넌트 구현
- [ ] 4.4 통계 컴포넌트 구현
- [ ] 4.5 시각화 컴포넌트 구현
- [ ] 4.6 메인 애플리케이션 구현

### Phase 5: 통합 테스트 및 안정화
- [ ] 5.1 통합 테스트 작성
- [ ] 5.2 코드 품질 검사
- [ ] 5.3 문서화 완성
- [ ] 5.4 성능 최적화

### Phase 6: 배포 준비
- [ ] 6.1 로컬 실행 가이드 작성
- [ ] 6.2 Streamlit Cloud 배포 (선택)

---

## 다음 단계 시작하기

**현재 위치 확인**:
```bash
# 프로젝트 구조 확인
tree -L 2 src/

# 완료된 테스트 확인
pytest --collect-only

# Git 상태 확인
git status
```

**다음 단계 시작**:
위 체크리스트에서 체크되지 않은 가장 첫 번째 항목부터 시작하세요. 각 단계는 독립적으로 실행 가능하며, TDD 방식으로 진행합니다.

**진행 상황 기록**:
각 단계 완료 시 `logs/process.log`에 기록됩니다. 정기적으로 Git 커밋하여 진행 상황을 저장하세요.

```bash
# 각 단계 완료 후
git add .
git commit -m "Phase X.Y: [단계명] 완료"
```
