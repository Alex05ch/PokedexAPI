import pytest

from app.services.pokeapi_service import PokeAPIService
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_pokeapi_service_get_pokemon():
    """Servicio obtiene Pokémon correctamente."""
    service = PokeAPIService()
    pokemon = await service.get_pokemon("pikachu")

    assert pokemon["name"] == "pikachu"
    assert "types" in pokemon
    assert isinstance(pokemon["types"], list)


@pytest.mark.asyncio
async def test_pokeapi_service_handles_404():
    """Servicio maneja Pokémon no encontrado."""
    service = PokeAPIService()

    with pytest.raises(HTTPException) as excinfo:
        await service.get_pokemon("esto_no_existe_123")

    assert excinfo.value.status_code == 404
