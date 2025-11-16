from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session

from app.auth import get_current_user
from app.database import get_session
from app.models import User
from app.services.pokeapi_service import PokeAPIService
from app.rate_limiter import limiter 


router = APIRouter(
    prefix="/api/v1",
    tags=["pokemon"],
)

pokeapi_service = PokeAPIService()


# --- Grupo 1: Búsqueda de Pokémon (Proxy a PokeAPI) ---

@router.get("/search")
@limiter.limit("30/minute")
async def search_pokemon_endpoint(
    request: Request,           # añadido para SlowAPI
    name: str = Query(..., min_length=1, description="Nombre del Pokémon a buscar"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
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
@limiter.limit("60/minute")
async def get_pokemon_detail_endpoint(
    request: Request,           
    id_or_name: str,
    current_user: User = Depends(get_current_user),  
):
    """
    GET /api/v1/pokemon/{id_or_name}

    - Obtiene detalles completos de un Pokémon
    - Incluye stats, abilities, types, sprite, etc.
    """
    pokemon = await pokeapi_service.get_pokemon(id_or_name)
    return pokemon
