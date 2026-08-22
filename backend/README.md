## Backend JWT Auth

The backend now uses JWT Bearer authentication for protected endpoints.

### Environment Variables

Add these values in `backend/.env`:

```env
JWT_SECRET_KEY=replace-with-a-long-random-string
JWT_EXPIRE_MINUTES=60
AUTH_USERNAME=admin
AUTH_PASSWORD=admin123
# Optional: set this instead of AUTH_PASSWORD
# AUTH_PASSWORD_HASH=$2b$12$...
```

Notes:
- `JWT_SECRET_KEY` should be unique and secret in production.
- If `AUTH_PASSWORD_HASH` is provided, the backend uses it directly.
- If `AUTH_PASSWORD_HASH` is omitted, the backend hashes `AUTH_PASSWORD` at startup.

### Auth Endpoints

- `POST /auth/token` (public): returns JWT access token
- `GET /auth/me` (protected): returns current authenticated user

### Protected Endpoints

- `POST /chat`
- `POST /upload`

Include this header when calling protected routes:

```http
Authorization: Bearer <access_token>
```

### Example: Get Token

```bash
curl -X POST http://localhost:8000/auth/token \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "username=admin&password=admin123"
```

### Example: Call Protected Route

```bash
curl -X POST http://localhost:8000/chat \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <token>" \
	-d '{"message":"hello"}'
```
