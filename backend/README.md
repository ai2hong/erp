# VAPE DOG ERP Backend

증산점·양산점·범어점 3개 매장 운영을 위한 전자담배 매장 ERP 시스템.

## 계정 정보

- 관리자 아이디: `owner_admin`
- 비밀번호: 최초 시드 실행 시 콘솔에 출력됨 (README에 기록하지 않음)
- 역할: 사장 (전체 매장 접근 가능)

## 기술 스택

- **Framework**: FastAPI 0.115
- **DB**: PostgreSQL + SQLAlchemy 2.0 (async)
- **Auth**: JWT (Access 30분 / Refresh 7일) + bcrypt
- **Migration**: Alembic

## 설치

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## .env 설정

```bash
cp .env.example .env
# .env 파일을 열어 실제 값 입력
```

필수 항목:
- `DATABASE_URL`: PostgreSQL 연결 문자열 (예: `postgresql+asyncpg://user@localhost:5432/vapedb`)
- `SECRET_KEY`: JWT 서명 키 (32자 이상, `openssl rand -hex 32`)
- `REFRESH_SECRET_KEY`: Refresh 토큰 서명 키 (별도 생성)
- `ALGORITHM`: `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: `30`
- `REFRESH_TOKEN_EXPIRE_DAYS`: `7`
- `APP_NAME`: `VAPE DOG ERP`
- `DEBUG`: `true` (개발) / `false` (운영)

## 서버 실행

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health
- 목업 UI: http://localhost:8000/ui/

## DB 마이그레이션

```bash
cd backend
alembic upgrade head
```

## 시드 데이터

### 초기 데이터 (매장, 계정, 고객)
```bash
cd backend
python3 seed_initial_data.py
```
- 매장 3개 생성 (증산점, 양산점, 범어점)
- 사장 계정 생성 (임시 비밀번호 콘솔 출력)
- 샘플 고객 3명 생성

### 상품 마스터 (1,781개)
```bash
# products_master.xlsx를 backend/scripts/ 에 배치 후:
cd backend
python3 scripts/seed_products.py
```

## 동작 확인된 API 목록

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| POST | /auth/login | 로그인 | - |
| POST | /auth/register | 가입 신청 | - |
| POST | /auth/refresh | 토큰 갱신 | - |
| POST | /auth/logout | 로그아웃 | 인증 |
| GET | /auth/me | 내 정보 | 인증 |
| GET | /products/ | 상품 목록 (필터/검색/페이지네이션) | 인증 |
| GET | /products/{id} | 상품 상세 (원가는 총괄+만) | 인증 |
| GET | /customers/ | 고객 목록 (이름/전화 검색) | 인증 |
| GET | /customers/{id} | 고객 상세 | 인증 |
| POST | /customers/ | 고객 등록 | 인증 |
| PATCH | /customers/{id}/mileage | 적립금 수동 조정 | 총괄+ |
| GET | /transactions/ | 거래 목록 | 인증 |
| GET | /transactions/{id} | 거래 상세 (라인 포함) | 인증 |
| POST | /transactions/ | 거래 생성 (가격/서비스/재고 자동) | 인증 |
| GET | /staff/ | 직원 목록 | 매니저+ |
| GET | /dayclose/ | 일마감 목록 | 매니저+ |
| POST | /dayclose/ | 일마감 제출 | 매니저+ |
| PATCH | /dayclose/{id}/approve | 일마감 승인 | 총괄+ |

## 테스트 실행

```bash
cd backend
source .venv/bin/activate

# 단위 테스트 (61건)
python3 -m pytest tests/ -v

# 통합 시뮬레이션 (서버 실행 필요)
python3 scripts/simulate_full.py       # 8 시나리오
python3 scripts/simulate_edge_cases.py  # 19+3 시나리오
```

## 목업 UI 연동

서버 실행 후 http://localhost:8000/ui/ 접속:
- 로그인 모달 → `owner_admin` 로그인 → 토큰 localStorage 저장
- 상품 목록: GET /products/ (카테고리 필터, 검색, 페이지네이션)
- 고객 조회: GET /customers/?search= (이름/전화번호)
- 저장 확정: POST /transactions/ (할인, 메모, 성인인증 포함)
- 프론트 가격 계산 vs 백엔드 가격 계산 불일치 시 경고 모달 표시 → 사용자 확인 후 저장
- 할인금액 + 할인사유 입력 (사유 필수 검증)
- 성인인증 체크박스
- 직원 메모 입력
- 예상 적립금 실시간 표시 (결제수단 변경 시 자동 갱신)
- 저장 성공 시 적립금 토스트 표시

## 가격 엔진 (price_engine)

- 3병 묶음 할인: 50,000원 (이벤트) + 5,000원/일반
- 폐이벤트 2병: 45,000원
- 기기 연동 할인: device_discount_price 적용
- 할인제외 상품: 항상 정가
- 적립: 이체/현금 결제 시 1% (10원 단위 절사)

## 서비스 엔진 (service_engine)

- 액상 1병 → 서비스 1개
- 액상 3병 → SET3 묶음 1개
- 기기 구매 → 기기 증정
- 카드/마일리지전액 → 서비스 불가
- 단골 보너스: 방문 10회 + 누적 50만원 이상
