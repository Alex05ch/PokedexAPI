import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import create_db_and_tables
from app.rate_limiter import limiter  

# Routers de la API
from app.auth import router as auth_router
from app.pokemon import router as pokemon_router
from app.pokedex import router as pokedex_router
from app.teams import router as teams_router


# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pokedex_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Código de arranque / parada de la app."""
    # Startup: crear tablas
    create_db_and_tables()
    logger.info("Base de datos inicializada")
    yield
    # Aquí iría lógica de shutdown si la necesitas


app = FastAPI(
    title="Tu Pokédex API",
    version="1.0.0",
    lifespan=lifespan,
)

# SlowAPI necesita esto
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -------------------------------------------------
# CORS 
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000", # React dev
    "http://localhost:5173", # Vite dev
    "https://tu-dominio.com" # Producción
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
# -------------------------------------------------
# Routers
# -------------------------------------------------
app.include_router(auth_router)
app.include_router(pokemon_router)
app.include_router(pokedex_router)
app.include_router(teams_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
