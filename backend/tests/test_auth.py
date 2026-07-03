"""
Sprint 1 — JWT authentication endpoint tests.
"""

VALID_USER = {
    "email": "test@wealthflow.io",
    "password": "SuperSecret123",
    "full_name": "Test User",
}


def _register(client, **overrides):
    payload = {**VALID_USER, **overrides}
    return client.post("/api/v1/auth/register", json=payload)


def _login(client, email=VALID_USER["email"], password=VALID_USER["password"]):
    return client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


class TestRegister:
    def test_register_success(self, client):
        response = _register(client)
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == VALID_USER["email"]
        assert body["full_name"] == VALID_USER["full_name"]
        assert body["role"] == "user"
        assert body["is_active"] is True
        assert "hashed_password" not in body  # never leak the hash

    def test_register_duplicate_email_rejected(self, client):
        _register(client)
        response = _register(client, full_name="Someone Else")
        assert response.status_code == 409

    def test_register_short_password_rejected(self, client):
        response = _register(client, password="short")
        assert response.status_code == 422

    def test_register_invalid_email_rejected(self, client):
        response = _register(client, email="not-an-email")
        assert response.status_code == 422


class TestLogin:
    def test_login_success_returns_token_pair(self, client):
        _register(client)
        response = _login(client)
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["refresh_token"]

    def test_login_wrong_password_rejected(self, client):
        _register(client)
        response = _login(client, password="WrongPassword1")
        assert response.status_code == 401

    def test_login_unknown_email_rejected(self, client):
        response = _login(client, email="ghost@wealthflow.io")
        assert response.status_code == 401


class TestMe:
    def test_me_requires_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_returns_authenticated_user(self, client):
        _register(client)
        tokens = _login(client).json()
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == VALID_USER["email"]

    def test_me_rejects_garbage_token(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_rotates_token_pair(self, client):
        _register(client)
        tokens = _login(client).json()

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200
        new_tokens = response.json()
        assert new_tokens["refresh_token"] != tokens["refresh_token"]
        assert new_tokens["access_token"] != tokens["access_token"]

    def test_refresh_rejects_reused_old_token(self, client):
        """Old refresh token must be invalidated once rotated (replay protection)."""
        _register(client)
        tokens = _login(client).json()

        client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        replay = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert replay.status_code == 401

    def test_refresh_rejects_access_token(self, client):
        """An access token must not work where a refresh token is expected."""
        _register(client)
        tokens = _login(client).json()

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )
        assert response.status_code == 401

    def test_refresh_rejects_garbage_token(self, client):
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_revokes_refresh_token(self, client):
        _register(client)
        tokens = _login(client).json()

        logout_response = client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        )
        assert logout_response.status_code == 204

        reuse_response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert reuse_response.status_code == 401

    def test_logout_is_idempotent(self, client):
        """Logging out twice (or with an unknown token) should not error."""
        _register(client)
        tokens = _login(client).json()

        first = client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        )
        second = client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        )
        assert first.status_code == 204
        assert second.status_code == 204
