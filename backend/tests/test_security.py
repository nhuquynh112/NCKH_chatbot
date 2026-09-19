import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app
from app.middleware.rate_limit import RateLimitMiddleware


class SecurityConfigurationTests(unittest.TestCase):
    def test_insecure_defaults_are_rejected_in_production(self):
        with self.assertRaises(ValidationError):
            Settings(ENVIRONMENT="production", _env_file=None)

    def test_explicit_secure_production_configuration_is_allowed(self):
        production = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-unique-production-secret-key-with-32-characters",
            ADMIN_PASSWORD="a-long-admin-password",
            AUTO_SEED=False,
            CORS_ORIGINS="https://shop.example.com",
            _env_file=None,
        )
        self.assertEqual(production.ENVIRONMENT, "production")

    def test_admin_login_rejects_wrong_or_extra_credentials(self):
        client = TestClient(app)
        wrong = client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrong"}
        )
        extra = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123", "unexpected": True},
        )
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(extra.status_code, 422)


class RateLimitTests(unittest.TestCase):
    def test_login_rate_limit_returns_retry_after(self):
        limited_app = FastAPI()
        limited_app.add_middleware(RateLimitMiddleware, chat_limit=2, login_limit=2)

        @limited_app.post("/api/auth/login")
        def fake_login():
            return {"ok": True}

        client = TestClient(limited_app)
        self.assertEqual(client.post("/api/auth/login").status_code, 200)
        self.assertEqual(client.post("/api/auth/login").status_code, 200)
        blocked = client.post("/api/auth/login")
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)


if __name__ == "__main__":
    unittest.main()
