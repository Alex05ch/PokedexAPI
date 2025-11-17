from typing import Dict

from sqlmodel import Session, select

from app.models import PokedexEntry, User


def _build_entry_payload(pokemon_id: int = 25) -> Dict:
    return {
        "pokemon_id": pokemon_id,
        "nickname": "Pika",
        "is_captured": True,
        "favorite": False,
        "notes": "Entrada de prueba",
    }


def test_add_pokemon_to_pokedex(client, auth_headers):
    """Añadir Pokémon a la Pokédex."""
    payload = _build_entry_payload(25)
    resp = client.post("/api/v1/pokedex", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["pokemon_id"] == 25
    assert data["nickname"] == "Pika"


def test_add_duplicate_pokemon(client, auth_headers):
    """No permitir duplicados (mismo pokemon_id para el mismo usuario)."""
    payload = _build_entry_payload(1)

    # Primera vez OK
    resp1 = client.post("/api/v1/pokedex", json=payload, headers=auth_headers)
    assert resp1.status_code in (201, 400)

    # Segunda vez debe fallar
    resp2 = client.post("/api/v1/pokedex", json=payload, headers=auth_headers)
    assert resp2.status_code == 400
    assert "duplicado" in resp2.json()["detail"].lower()


def test_get_pokedex_with_filters(client, auth_headers):
    """Filtros funcionan correctamente."""
    # Creamos dos entradas: una capturada, otra no
    client.post(
        "/api/v1/pokedex",
        json=_build_entry_payload(10) | {"is_captured": True},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/pokedex",
        json=_build_entry_payload(11) | {"is_captured": False},
        headers=auth_headers,
    )

    # Filtramos solo capturados
    resp = client.get("/api/v1/pokedex?captured=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(entry["is_captured"] for entry in data)


def test_update_pokedex_entry(client, auth_headers):
    """Actualizar entrada de Pokédex."""
    # Creamos
    resp_create = client.post(
        "/api/v1/pokedex",
        json=_build_entry_payload(50),
        headers=auth_headers,
    )
    assert resp_create.status_code in (201, 400)
    entry = resp_create.json()

    # Si ya existía, hacemos GET para recuperar un id válido
    if resp_create.status_code == 400:
        resp_list = client.get("/api/v1/pokedex", headers=auth_headers)
        entry = next(e for e in resp_list.json() if e["pokemon_id"] == 50)

    entry_id = entry["id"]

    # Actualizamos nickname y favorite
    update_payload = {
        "nickname": "Pika-Actualizado",
        "favorite": True,
    }
    resp_update = client.patch(
        f"/api/v1/pokedex/{entry_id}",
        json=update_payload,
        headers=auth_headers,
    )
    assert resp_update.status_code == 200
    updated = resp_update.json()
    assert updated["nickname"] == "Pika-Actualizado"
    assert updated["favorite"] is True


def test_delete_pokedex_entry(client, auth_headers):
    """Eliminar entrada de Pokédex."""
    resp_create = client.post(
        "/api/v1/pokedex",
        json=_build_entry_payload(99),
        headers=auth_headers,
    )
    assert resp_create.status_code in (201, 400)
    entry = resp_create.json()
    if resp_create.status_code == 400:
        resp_list = client.get("/api/v1/pokedex", headers=auth_headers)
        entry = next(e for e in resp_list.json() if e["pokemon_id"] == 99)

    entry_id = entry["id"]

    resp_delete = client.delete(
        f"/api/v1/pokedex/{entry_id}",
        headers=auth_headers,
    )
    assert resp_delete.status_code == 204

def test_cannot_modify_other_user_pokedex(client, auth_headers, test_user_payload):
    """No se puede modificar Pokédex de otro usuario."""
    # Creamos un segundo usuario
    other_payload = {
        "username": "otheruser",
        "email": "other@example.com",
        "password": "otherpassword",
    }
    resp_other = client.post("/api/v1/auth/register", json=other_payload)
    assert resp_other.status_code in (201, 400)

    # Login con el segundo usuario
    resp_login = client.post(
        "/api/v1/auth/login",
        json={"username": other_payload["username"], "password": other_payload["password"]},
    )
    assert resp_login.status_code == 200
    other_token = resp_login.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # El segundo usuario crea una entrada
    resp_create = client.post(
        "/api/v1/pokedex",
        json=_build_entry_payload(150),
        headers=other_headers,
    )
    assert resp_create.status_code in (201, 400)
    entry = resp_create.json()
    if resp_create.status_code == 400:
        resp_list = client.get("/api/v1/pokedex", headers=other_headers)
        entry = next(e for e in resp_list.json() if e["pokemon_id"] == 150)

    entry_id = entry["id"]

    # El usuario original intenta modificar la entrada del otro
    resp_update = client.patch(
        f"/api/v1/pokedex/{entry_id}",
        json={"nickname": "hack"},
        headers=auth_headers,
    )

    assert resp_update.status_code in (403, 404)
