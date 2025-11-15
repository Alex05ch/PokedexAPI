from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.models import User
from app.services.pokeapi_service import PokeAPIService

router = APIRouter(
    prefix="/api/v1",
    tags=["pokemon"],
)

pokeapi_service = PokeAPIService()


# --- Grupo 1: Búsqueda de Pokémon (Proxy a PokeAPI) ---

@router.get("/pokemon/search")
async def search_pokemon_endpoint(
    name: str,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),  # requiere autenticación
):
    """
    GET /api/v1/pokemon/search?name={name}&limit=20&offset=0

    - Busca Pokémon en PokeAPI
    - Devuelve lista simplificada: {id, name, sprite, types}
    """
    results = await pokeapi_service.search_pokemon_simplified(
        name=name,
        limit=limit,
        offset=offset,
    )
    return results


@router.get("/pokemon/{id_or_name}")
async def get_pokemon_detail_endpoint(
    id_or_name: str,
    current_user: User = Depends(get_current_user),  # requiere autenticación
):
    """
    GET /api/v1/pokemon/{id_or_name}

    - Obtiene detalles completos de un Pokémon
    - Incluye stats, abilities, types, sprite, etc.
    """
    pokemon = await pokeapi_service.get_pokemon(id_or_name)
    return pokemon
