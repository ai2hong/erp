# Compatibility note

Current backend uses `passlib==1.7.4`.
`bcrypt==5.x` can break passlib bcrypt hashing in some environments.

Pinned workaround:
- `bcrypt<5`

If hashing errors mention `password cannot be longer than 72 bytes` during passlib backend detection,
this is usually a library compatibility issue rather than your actual password length.
