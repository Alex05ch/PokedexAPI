# app/teams.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
import io

from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from app.services.pokeapi_service import PokeAPIService
from app.rate_limiter import limiter


from app.auth import get_current_user
from app.database import get_session
from app.models import (
    User,
    Team,
    TeamMember,
    PokedexEntry,
    TeamCreate,
    TeamUpdate,
    TeamRead,
    PokedexEntryRead,
)

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
)



#  LISTAR EQUIPOS


@router.get(
    "",
    response_model=List[TeamRead],
)
@limiter.limit("60/minute")
def list_teams(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v1/teams

    Lista los equipos del usuario autenticado.
    """
    stmt = (
        select(Team)
        .where(Team.trainer_id == current_user.id)
        .order_by(Team.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    teams = session.exec(stmt).all()
    return teams



#  CREAR EQUIPO


@router.post(
    "",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
def create_team(
    request: Request,
    payload: TeamCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    POST /api/v1/teams

    Crea un nuevo equipo para el usuario actual.

    - payload.pokemon_ids: ids de PokedexEntry del propio usuario
    - Máximo 6 miembros
    """

    pokemon_ids = payload.pokemon_ids or []

    if not pokemon_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El equipo debe tener al menos 1 Pokémon.",
        )

    if len(pokemon_ids) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El equipo no puede tener más de 6 Pokémon.",
        )

    # Verificar que todas las entradas pertenecen al usuario
    stmt = select(PokedexEntry).where(
        PokedexEntry.id.in_(pokemon_ids),
        PokedexEntry.owner_id == current_user.id,
    )
    entries = session.exec(stmt).all()

    if len(entries) != len(pokemon_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alguna de las PokedexEntry no existe o no pertenece al usuario.",
        )

    # Crear equipo
    team = Team(
        trainer_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    session.add(team)
    session.commit()
    session.refresh(team)

    # Crear miembros del equipo (posición 1..n)
    for position, entry_id in enumerate(pokemon_ids, start=1):
        member = TeamMember(
            team_id=team.id,
            pokedex_entry_id=entry_id,
            position=position,
        )
        session.add(member)

    session.commit()

    return team



#  DETALLE DE EQUIPO


@router.get(
    "/{team_id}",
    response_model=TeamRead,
)
@limiter.limit("60/minute")
def get_team(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v1/teams/{team_id}

    Devuelve la info básica del equipo (sin miembros).
    """
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return team


#  MIEMBROS DE UN EQUIPO


@router.get(
    "/{team_id}/members",
    response_model=List[PokedexEntryRead],
)
@limiter.limit("60/minute")
def get_team_members(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v1/teams/{team_id}/members

    Devuelve las entradas de Pokédex que forman el equipo, en orden de posición.
    """
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Obtener los TeamMember del equipo
    stmt_members = (
        select(TeamMember)
        .where(TeamMember.team_id == team.id)
        .order_by(TeamMember.position.asc())
    )
    members = session.exec(stmt_members).all()

    if not members:
        return []

    pokedex_ids = [m.pokedex_entry_id for m in members]

    stmt_entries = select(PokedexEntry).where(
        PokedexEntry.id.in_(pokedex_ids),
        PokedexEntry.owner_id == current_user.id,
    )
    entries = session.exec(stmt_entries).all()

    # Ordenar entries según la posición en el equipo
    entry_map = {e.id: e for e in entries}
    ordered_entries = [entry_map[eid] for eid in pokedex_ids if eid in entry_map]

    return ordered_entries



#  ACTUALIZAR EQUIPO


@router.put(
    "/{team_id}",
    response_model=TeamRead,
)
@limiter.limit("20/minute")
def update_team(
    request: Request,
    team_id: int,
    payload: TeamUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    PUT /api/v1/teams/{team_id}

    Actualiza nombre/descripcion y opcionalmente los miembros del equipo.
    """
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Actualizar campos básicos
    team.name = payload.name
    team.description = payload.description

    # Si vienen nuevos pokemon_ids, actualizamos miembros
    if payload.pokemon_ids is not None:
        pokemon_ids = payload.pokemon_ids

        if not pokemon_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El equipo debe tener al menos 1 Pokémon.",
            )

        if len(pokemon_ids) > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El equipo no puede tener más de 6 Pokémon.",
            )

        stmt = select(PokedexEntry).where(
            PokedexEntry.id.in_(pokemon_ids),
            PokedexEntry.owner_id == current_user.id,
        )
        entries = session.exec(stmt).all()
        if len(entries) != len(pokemon_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alguna de las PokedexEntry no existe o no pertenece al usuario.",
            )

        # Borrar miembros antiguos
        stmt_del = select(TeamMember).where(TeamMember.team_id == team.id)
        old_members = session.exec(stmt_del).all()
        for m in old_members:
            session.delete(m)

        # Crear nuevos miembros
        for position, entry_id in enumerate(pokemon_ids, start=1):
            member = TeamMember(
                team_id=team.id,
                pokedex_entry_id=entry_id,
                position=position,
            )
            session.add(member)

    session.add(team)
    session.commit()
    session.refresh(team)

    return team



#  BORRAR EQUIPO

@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("20/minute")
def delete_team(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    DELETE /api/v1/teams/{team_id}

    Elimina el equipo y sus miembros.
    """
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Borrar miembros
    stmt_members = select(TeamMember).where(TeamMember.team_id == team.id)
    members = session.exec(stmt_members).all()
    for m in members:
        session.delete(m)

    # Borrar equipo
    session.delete(team)
    session.commit()

    return None

@router.get(
    "/{team_id}/export",
    response_class=StreamingResponse,
    summary="Exportar equipo en PDF",
)
@limiter.limit("60/minute")
async def export_team(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /api/v1/teams/{team_id}/export

    Exporta un equipo en formato PDF con:
    - Nombre y descripción del equipo
    - Fichas de los Pokémon del equipo
    - Estadísticas combinadas del equipo
    """

    # 1) Comprobar que el equipo existe y es del usuario
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # 2) Obtener miembros del equipo (TeamMember) en orden de posición
    stmt_members = (
        select(TeamMember)
        .where(TeamMember.team_id == team.id)
        .order_by(TeamMember.position.asc())
    )
    members = session.exec(stmt_members).all()

    if not members:
        raise HTTPException(
            status_code=400,
            detail="El equipo no tiene Pokémon para exportar.",
        )

    pokedex_ids = [m.pokedex_entry_id for m in members]

    # 3) Cargar las PokedexEntry correspondientes
    stmt_entries = select(PokedexEntry).where(
        PokedexEntry.id.in_(pokedex_ids),
        PokedexEntry.owner_id == current_user.id,
    )
    entries = session.exec(stmt_entries).all()

    # Mapear por id para mantener el orden según posición
    entry_map = {e.id: e for e in entries}
    ordered_entries = [entry_map[eid] for eid in pokedex_ids if eid in entry_map]

    if not ordered_entries:
        raise HTTPException(
            status_code=400,
            detail="No se pudieron cargar las entradas de Pokédex del equipo.",
        )

    # 4) Obtener stats desde PokeAPI para calcular estadísticas combinadas
    pokeapi = PokeAPIService()

    combined_stats: dict[str, float] = {}
    detailed_pokemon: list[dict] = []

    for entry in ordered_entries:
        # Llamada a PokeAPI por id de Pokémon
        pokemon = await pokeapi.get_pokemon(entry.pokemon_id)

        # Guardamos información para la ficha
        detailed_pokemon.append(
            {
                "id": pokemon["id"],
                "name": pokemon["name"],
                "types": pokemon["types"],
                "stats": pokemon["stats"],
            }
        )

        # Sumamos stats para luego hacer la media
        for s in pokemon["stats"]:
            stat_name = s["name"]
            base = s["base_stat"]
            combined_stats[stat_name] = combined_stats.get(stat_name, 0) + base

    num_members = len(ordered_entries)
    avg_stats = {
        name: round(total / num_members, 1) for name, total in combined_stats.items()
    }

    # 5) Generar PDF en memoria
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    # Título del equipo
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, f"Equipo: {team.name}")
    y -= 25

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Descripción: {team.description or 'Sin descripción'}")
    y -= 40

    # Fichas de Pokémon
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Miembros del equipo")
    y -= 20
    pdf.setFont("Helvetica", 11)

    for idx, p in enumerate(detailed_pokemon, start=1):
        if y < 80:  # salto de página si nos quedamos sin espacio
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 11)

        types_str = ", ".join(p["types"])
        pdf.drawString(
            50,
            y,
            f"{idx}. #{p['id']} {p['name'].capitalize()} (Tipos: {types_str})",
        )
        y -= 15

    # Espacio antes de stats combinadas
    y -= 20
    if y < 120:
        pdf.showPage()
        y = height - 50
        pdf.setFont("Helvetica", 11)

    # Estadísticas combinadas
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Estadísticas combinadas (media)")
    y -= 20
    pdf.setFont("Helvetica", 11)

    for stat_name, value in avg_stats.items():
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 11)
        pdf.drawString(50, y, f"{stat_name}: {value}")
        y -= 15

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    filename = f"team_{team_id}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
