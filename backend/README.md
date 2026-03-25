# VAPE DOG ERP Backend

증산점·양산점·범어점 3개 매장 운영을 위한 전자담배 매장 ERP 시스템.

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
pip install psycopg2-binary  # alembic용
```

## .env 설정

```bash
cp .env.example .env
# .env 파일을 열어 실제 값 입력
```

필수 항목:
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `SECRET_KEY`: JWT 서명 키 (32자 이상, `openssl rand -hex 32`)
- `REFRESH_SECRET_KEY`: Refresh 토큰 서명 키 (별도 생성)

## 서버 실행

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

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

### 상품 마스터 (XLSX)
```bash
# products_master.xlsx를 backend/scripts/ 에 배치 후:
cd backend
python3 scripts/seed_products.py
```

## API 목록

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| POST | /auth/login | 로그인 | - |
| POST | /auth/register | 가입 신청 | - |
| POST | /auth/refresh | 토큰 갱신 | - |
| POST | /auth/logout | 로그아웃 | 인증 |
| GET | /auth/me | 내 정보 | 인증 |
| GET | /products/ | 상품 목록 | 인증 |
| GET | /products/{id} | 상품 상세 | 인증 |
| GET | /customers/ | 고객 목록 | 인증 |
| GET | /customers/{id} | 고객 상세 | 인증 |
| POST | /customers/ | 고객 등록 | 인증 |
| PATCH | /customers/{id}/mileage | 적립금 조정 | 총괄+ |
| GET | /transactions/ | 거래 목록 | 인증 |
| GET | /transactions/{id} | 거래 상세 | 인증 |
| POST | /transactions/ | 거래 생성 | 인증 |
| GET | /staff/ | 직원 목록 | 매니저+ |
| GET | /dayclose/ | 일마감 목록 | 매니저+ |
| POST | /dayclose/ | 일마감 제출 | 매니저+ |
| PATCH | /dayclose/{id}/approve | 일마감 승인 | 총괄+ |

## 가격 엔진 (price_engine)

- 3병 묶음 할인: 50,000원 (이벤트) + 5,000원/일반
- 폐이벤트 2병: 45,000원
- 기기 연동 할인: device_discount_price 적용
- 적립: 이체/현금 결제 시 1% (10원 단위 절사)

## 서비스 엔진 (service_engine)

- 액상 1병 → 서비스 1개
- 액상 3병 → SET3 묶음 1개
- 기기 구매 → 기기 증정
- 카드/마일리지전액 → 서비스 불가
