from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.rate_limiter import limiter  
from sqlmodel import Session, select
from datetime import datetime, timedelta
from collections import Counter

from app.auth import get_current_user
from app.database import get_session
from app.models import (
    User,
    PokedexEntry,
    PokedexEntryCreate,
    PokedexEntryRead,
    PokedexEntryUpdate,
)
from app.services.pokeapi_service import PokeAPIService
from app.rate_limiter import limiter

router = APIRouter(
    prefix="/api/v1/pokedex",
    tags=["pokedex"],
)

#Version 2 router
router_v2 = APIRouter(
    prefix="/api/v2/pokedex",
    tags=["pokedex-v2"],   # o "pokedex"
)

pokeapi_service = PokeAPIService()


#  LISTAR ENTRADAS POKÉDEX

@router.get(
    "",
    response_model=List[PokedexEntryRead],
)
@limiter.limit("100/minute")
async def list_pokedex_entries(
    request: Request, 
    captured: Optional[bool] = None,
    favorite: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v1/pokedex

    Lista las entradas de la Pokédex del usuario autenticado.

    Filtros opcionales:
      - captured: True/False (filtra por is_captured)
      - favorite: True/False
      - search: substring en pokemon_name o nickname

    Soporta paginación con limit/offset.
    """

    stmt = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)

    if captured is not None:
        stmt = stmt.where(PokedexEntry.is_captured == captured)

    if favorite is not None:
        stmt = stmt.where(PokedexEntry.favorite == favorite)

    if search:
        search_like = f"%{search.lower()}%"
        stmt = stmt.where(
            (PokedexEntry.pokemon_name.ilike(search_like))
            | (PokedexEntry.nickname.ilike(search_like))
        )

    stmt = stmt.order_by(PokedexEntry.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    entries = session.exec(stmt).all()
    return entries


#  CREAR ENTRADA POKÉDEX

@router.post(
    "",
    response_model=PokedexEntryRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_pokedex_entry(
    request: Request,
    payload: PokedexEntryCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    POST /api/v1/pokedex

    Crea una nueva entrada en la Pokédex del usuario.

    - El cliente envía: pokemon_id + campos de usuario (nickname, favorite, etc.)
    - La API consulta PokeAPI para rellenar pokemon_name y pokemon_sprite.
    """

    # Llamamos a PokeAPI para completar nombre y sprite
    pokemon_data = await pokeapi_service.get_pokemon(payload.pokemon_id)

    entry = PokedexEntry(
        owner_id=current_user.id,
        pokemon_id=payload.pokemon_id,
        pokemon_name=pokemon_data["name"],
        pokemon_sprite=pokemon_data["sprite"],
        is_captured=payload.is_captured,
        capture_date=payload.capture_date,
        nickname=payload.nickname,
        notes=payload.notes,
        favorite=payload.favorite,
    )

    session.add(entry)
    session.commit()
    session.refresh(entry)

    return entry


#  DETALLE DE UNA ENTRADA

@router.get(
    "/{entry_id}",
    response_model=PokedexEntryRead,
)
@limiter.limit("60/minute")
def get_pokedex_entry(
    request: Request,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v1/pokedex/{entry_id}

    Devuelve el detalle de una entrada de la Pokédex del usuario actual.
    """
    entry = session.get(PokedexEntry, entry_id)
    if not entry or entry.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    return entry


#  ACTUALIZAR ENTRADA (PATCH)

@router.patch(
    "/{entry_id}",
    response_model=PokedexEntryRead,
)
@limiter.limit("30/minute")
def update_pokedex_entry(
    request: Request,
    entry_id: int,
    payload: PokedexEntryUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    PATCH /api/v1/pokedex/{entry_id}

    Actualiza parcialmente una entrada de la Pokédex del usuario.
    Solo campos de usuario: is_captured, favorite, nickname, notes, capture_date.
    """
    entry = session.get(PokedexEntry, entry_id)
    if not entry or entry.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    session.add(entry)
    session.commit()
    session.refresh(entry)

    return entry



#  BORRAR ENTRADA


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_pokedex_entry(
    entry_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    DELETE /api/v1/pokedex/{entry_id}

    Elimina una entrada de la Pokédex del usuario.
    """
    entry = session.get(PokedexEntry, entry_id)
    if not entry or entry.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")

    session.delete(entry)
    session.commit()
    return None

@router.get("/stats")
async def get_pokedex_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """
    Devuelve estadísticas de la Pokédex del usuario autenticado.
    GET /api/v1/pokedex/stats
    """

    # Todas las entradas de la Pokédex del usuario
    statement = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    entries = session.exec(statement).all()

    total_pokemon = len(entries)
    captured = sum(1 for e in entries if e.is_captured)
    favorites = sum(1 for e in entries if e.favorite)

    if total_pokemon > 0:
        completion_percentage = captured / total_pokemon * 100
    else:
        completion_percentage = 0.0

    # --------- Tipo más común (most_common_type) ----------
    # Para simplificar: llamamos a PokeAPI por cada pokemon_id distinto
    pokeapi = PokeAPIService()

    type_counter: Counter[str] = Counter()

    unique_ids = {e.pokemon_id for e in entries}
    for pokemon_id in unique_ids:
        try:
            pokemon_data = await pokeapi.get_pokemon(pokemon_id)
            for t in pokemon_data.get("types", []):
                # en nuestro PokeAPIService cada Pokémon ya devuelve una lista "types"
                # así que si ya es una lista de strings, usamos directamente
                if isinstance(t, str):
                    type_counter[t] += 1
        except Exception:
            # Si falla PokeAPI para alguno, lo ignoramos en el cómputo de tipos
            continue

    most_common_type: str | None = None
    if type_counter:
        most_common_type = type_counter.most_common(1)[0][0]

    # --------- Racha de capturas (capture_streak_days) ----------
    # Racha actual de días consecutivos con al menos una captura
    captured_dates = {
        e.capture_date.date()
        for e in entries
        if e.is_captured and e.capture_date is not None
    }

    streak = 0
    today = datetime.utcnow().date()
    while today in captured_dates:
        streak += 1
        today = today - timedelta(days=1)

    return {
        "total_pokemon": total_pokemon,
        "captured": captured,
        "favorites": favorites,
        "completion_percentage": round(completion_percentage, 1),
        "most_common_type": most_common_type,
        "capture_streak_days": streak,
    }

@router_v2.get("/stats")
def get_pokedex_stats_v2(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v2/pokedex/stats

    Versión 2: mismas stats que v1 pero con mejoras (ej. metadatos extra).
    """

    stats = get_pokedex_stats(current_user=current_user, session=session)

    # Si stats es un modelo, conviértelo a dict: stats = stats.dict()
    return {
        "version": "v2",
        "generated_at": datetime.utcnow().isoformat(),
        "data": stats,
    }
