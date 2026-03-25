# Initial seed

This project includes `seed_initial_data.py` to create the default stores and an initial owner account.

## What it creates
- Stores: 홍대점, 강남점, 신촌점
- Owner account login id: `owner_admin`
- Owner display name: `사장`

## Run
```bash
cd ~/Projects/erp/backend
python3 seed_initial_data.py
```

## Optional overrides
```bash
SEED_OWNER_LOGIN_ID=myowner SEED_OWNER_NAME='대표' SEED_OWNER_PASSWORD='strong-password' python3 seed_initial_data.py
```

## Notes
- If the owner already exists, the script will not overwrite it.
- If the password is auto-generated, it is shown only once in terminal output.
- Seed password is truncated to a bcrypt-safe length before hashing.
- Change the initial password after first successful login.
