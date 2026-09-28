import pytest
from httpx import AsyncClient

from tests.conftest import PASSWORD, auth, register

pytestmark = pytest.mark.usefixtures("plans")


async def test_register_creates_user_company_and_owner_membership(client: AsyncClient) -> None:
    tokens = await register(client)
    assert tokens["token_type"] == "bearer"

    me = await client.get("/api/v1/users/me", headers=auth(tokens["access_token"]))
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "ana@acme.com"
    assert body["memberships"][0]["role"] == "owner"
    assert body["memberships"][0]["company"]["slug"] == "acme-ltda"
    assert "hashed_password" not in body


async def test_register_duplicate_email_is_case_insensitive(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Outra",
            "email": "ANA@acme.com",
            "password": PASSWORD,
            "company_name": "Outra",
        },
    )
    assert response.status_code == 409


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ana", "email": "a@b.com", "password": "12345678", "company_name": "X"},
    )
    assert response.status_code == 422


async def test_login_with_oauth2_form(client: AsyncClient) -> None:
    await register(client)
    ok = await client.post(
        "/api/v1/auth/login", data={"username": "ana@acme.com", "password": PASSWORD}
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/api/v1/auth/login", data={"username": "ana@acme.com", "password": "errada123"}
    )
    assert bad.status_code == 401
    assert bad.headers["www-authenticate"] == "Bearer"

    unknown = await client.post(
        "/api/v1/auth/login", data={"username": "ninguem@acme.com", "password": PASSWORD}
    )
    assert unknown.status_code == 401


async def test_protected_route_requires_valid_access_token(client: AsyncClient) -> None:
    tokens = await register(client)
    assert (await client.get("/api/v1/users/me")).status_code == 401
    assert (await client.get("/api/v1/users/me", headers=auth("lixo"))).status_code == 401
    # Refresh token não pode ser usado como access token.
    refresh_as_access = await client.get("/api/v1/users/me", headers=auth(tokens["refresh_token"]))
    assert refresh_as_access.status_code == 401


async def test_refresh_rotation_and_reuse_detection(client: AsyncClient) -> None:
    tokens = await register(client)
    old_refresh = tokens["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Reapresentar o token antigo => detecção de reuso: tudo é revogado.
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    tokens = await register(client)
    out = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=auth(tokens["access_token"]),
    )
    assert out.status_code == 204
    again = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert again.status_code == 401


async def test_change_password(client: AsyncClient) -> None:
    tokens = await register(client)
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Nova-senha-9"},
        headers=auth(tokens["access_token"]),
    )
    assert response.status_code == 204
    login = await client.post(
        "/api/v1/auth/login", data={"username": "ana@acme.com", "password": "Nova-senha-9"}
    )
    assert login.status_code == 200
    stale = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert stale.status_code == 401
