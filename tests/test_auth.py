def test_register_user_success(client):
    """Registro exitoso de usuario."""
    payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword",
    }
    resp = client.post("/api/v1/auth/register", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == payload["username"]
    assert "id" in data


def test_register_duplicate_username(client, test_user_payload):
    """Error al registrar username duplicado."""
    # Registramos una vez
    resp1 = client.post("/api/v1/auth/register", json=test_user_payload)
    assert resp1.status_code in (201, 400)

    # Registramos de nuevo con el mismo username
    resp2 = client.post("/api/v1/auth/register", json=test_user_payload)
    assert resp2.status_code == 400
    assert "ya registrados" in resp2.json()["detail"].lower()


def test_login_success(client, test_user):
    """Login exitoso retorna JWT válido."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": test_user["username"], "password": test_user["password"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Login con credenciales incorrectas retorna 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "noexiste", "password": "mala"},
    )

    assert resp.status_code == 401


def test_access_protected_endpoint_without_token(client):
    """Acceso sin token retorna 401 en un endpoint protegido."""
    # Usamos /api/v1/pokedex (lista) como endpoint protegido
    resp = client.get("/api/v1/pokedex")
    assert resp.status_code in (401, 403)

def test_rate_limit_exceeded(client, test_user):
    """Rate limit funciona correctamente: 11 logins rápidos => 429."""
    key = "rate-limit-test"  # bucket específico para este test

    last_resp = None
    for i in range(11):
        last_resp = client.post(
            "/api/v1/auth/login",
            headers={"X-RateLimit-Key": key},  
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )

    assert last_resp.status_code == 429