# Pokédex API

## Descripción
La Pokédex API permite:

- Registrar usuarios y autenticarlos con JWT.
- Guardar Pokémon en la Pokédex de cada usuario (capturado, favorito, notas, etc.).
- Consultar, filtrar y borrar entradas de Pokédex.
- Calcular estadísticas simples (porcentaje capturado, tipo más común, racha de capturas).
- Integrarse con PokeAPI para obtener nombre y sprite de los Pokémon.

## Instalación
1. Clonar repositorio: 
git clone https://github.com/Alex05ch/PokedexAPI.git
cd PokedexAPI

2. Crear entorno virtual 
python -m venv venv
.\venv\Scripts\activate

3. Instalar requirements
pip install -r requirements.txt

## Configuración
Se entrega un .env.example 

## Ejecución
Con el entorno activado 
uvicorn app.main:app --reload

## Testing
pytest -q

## Endpoints
Auth(/api/v1/auth)
-POST /auth/register -> registro usuario
-POST /auth/login -> token autorizacion

Pokemon(/api/v1/pokemon)
-GET /api/v1/search -> busca por nombre y devuelve lista de pokeapi
-GET /api/v1/search/{id_or_name} -> devuelve la informacion de un pokemon en concreto 

Pokedex(/api/v1/pokedex)
-GET /pokedex -> lista de entradas 
-POST /pokedex ->crea entrada a partir de pokemon_id
-GET /pokedex/{entry_id} -> detalle de una entrada
-PATCH /pokedex/{entry_id} -> actualiza una entrada
-DELETE /pokedex/{entry_id} -> borra una entrada
-GET /pokedex/stats -> saca estadísticas(pdf)

Pokedex v2(/api/v2/pokedex)
-GET /pokedex/stats -> solo para versionado

Teams(api/v1/teams)
-GET /api/v1/teams –> lista los equipos del usuario.
-POST /api/v1/teams –> crea un nuevo equipo.
-GET /api/v1/teams/{team_id} –> detalle de un equipo.
-PUT /api/v1/teams/{team_id} –> modifica nombre/composición del equipo.
-DELETE /api/v1/teams/{team_id} -> elimina un equipo.
-GET /api/v1/teams/{team_id}/members –> devuelve los miembros (Pokémon) del equipo.
-GET /api/v1/teams/{team_id}/export –> genera un PDF con la información del equipo.

## Decisiones de Seguridad
1. JWT con expiración configurable
2. Contraseñas hasheadas con bcrypt
3. Rate limit con slowapi 
4. Comprobación de owner id en todas las operaciones de 

## Mejoras Futuras
1. Despliegue en cloud (PostgreSQL)
2. Más estadísticas
3. Roles más avanzados