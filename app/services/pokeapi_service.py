import httpx
from typing import Optional, List, Dict
from fastapi import HTTPException
import logging
from datetime import datetime 

logger = logging.getLogger("pokedex_api")


class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    async def get_pokemon(self, identifier: str | int) -> Dict:
        """
        Obtiene información completa de un Pokémon.

        Args:
            identifier: Nombre o ID del Pokémon

        Returns:
            Dict con datos del Pokémon

        Raises:
            HTTPException: Si el Pokémon no existe o hay error de red
        """
        url = f"{self.BASE_URL}/pokemon/{identifier}"

        try:
            start = datetime.utcnow()
            logger.info("PokeAPI GET %s", url)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
            duration = (datetime.utcnow() - start).total_seconds()
            logger.info(
                "PokeAPI response %s status=%s duration=%.3fs",
                url, response.status_code, duration,
            )

        except httpx.TimeoutException:
            logger.error("Timeout llamando a %s", url)
            raise HTTPException(status_code=504, detail="Timeout llamando a PokeAPI")
        except httpx.RequestError as exc:
            logger.error("Error de red llamando a PokeAPI: %s", exc)
            raise HTTPException(
                status_code=502, detail="Error de conexión con PokeAPI"
            )

        if response.status_code == 404:
            logger.warning("Pokémon no encontrado: %s", identifier)
            raise HTTPException(status_code=404, detail="Pokémon no encontrado")

        if response.status_code >= 500:
            logger.error(
                "Error interno de PokeAPI (%s): %s",
                response.status_code,
                response.text,
            )
            raise HTTPException(status_code=502, detail="Error en PokeAPI")

        data = response.json()

        # --- Transformación de datos: solo campos relevantes ---
        types = [t["type"]["name"] for t in data.get("types", [])]
        abilities = [a["ability"]["name"] for a in data.get("abilities", [])]
        stats = [
            {"name": s["stat"]["name"], "base_stat": s["base_stat"]}
            for s in data.get("stats", [])
        ]

        pokemon = {
            "id": data.get("id"),
            "name": data.get("name"),
            "height": data.get("height"),
            "weight": data.get("weight"),
            "base_experience": data.get("base_experience"),
            "types": types,
            "abilities": abilities,
            "stats": stats,
            "sprite": data.get("sprites", {}).get("front_default"),
        }

        return pokemon

    async def search_pokemon(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """
        Lista Pokémon con paginación.

        Args:
            limit: número de resultados (1-100)
            offset: desplazamiento (>= 0)
        """
        # --- Validación de parámetros de entrada ---
        if limit <= 0 or limit > 100:
            raise HTTPException(
                status_code=400, detail="limit debe estar entre 1 y 100"
            )
        if offset < 0:
            raise HTTPException(
                status_code=400, detail="offset no puede ser negativo"
            )

        url = f"{self.BASE_URL}/pokemon"
        params = {"limit": limit, "offset": offset}

        try:
            start = datetime.utcnow()
            logger.info("PokeAPI GET %s params=%s", url, params)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)

            duration = (datetime.utcnow() - start).total_seconds()
            logger.info(
                "PokeAPI response %s status=%s duration=%.3fs",
                url, response.status_code, duration,
            )
        except httpx.TimeoutException:
            logger.error("Timeout llamando a %s", url)
            raise HTTPException(status_code=504, detail="Timeout llamando a PokeAPI")
        except httpx.RequestError as exc:
            logger.error("Error de red llamando a PokeAPI: %s", exc)
            raise HTTPException(
                status_code=502, detail="Error de conexión con PokeAPI"
            )

        if response.status_code >= 500:
            logger.error(
                "Error interno de PokeAPI (%s): %s",
                response.status_code,
                response.text,
            )
            raise HTTPException(status_code=502, detail="Error en PokeAPI")

        data = response.json()

        # --- Transformación de datos ---
        results = [
            {
                "name": item["name"],
                "url": item["url"],
            }
            for item in data.get("results", [])
        ]

        return {
            "count": data.get("count"),
            "next": data.get("next"),
            "previous": data.get("previous"),
            "results": results,
        }

    async def get_pokemon_by_type(self, type_name: str) -> List[Dict]:
        """
        Obtiene todos los Pokémon de un tipo específico (fire, water, etc.).
        """
        if not type_name:
            raise HTTPException(status_code=400, detail="type_name es obligatorio")

        url = f"{self.BASE_URL}/type/{type_name}"

        try:
            start = datetime.utcnow()
            logger.info("PokeAPI GET %s", url)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
            
            duration = (datetime.utcnow() - start).total_seconds()
            logger.info(
                "PokeAPI response %s status=%s duration=%.3fs",
                url, response.status_code, duration,
            )


        except httpx.TimeoutException:
            logger.error("Timeout llamando a %s", url)
            raise HTTPException(status_code=504, detail="Timeout llamando a PokeAPI")
        except httpx.RequestError as exc:
            logger.error("Error de red llamando a PokeAPI: %s", exc)
            raise HTTPException(
                status_code=502, detail="Error de conexión con PokeAPI"
            )

        if response.status_code == 404:
            logger.warning("Tipo de Pokémon no encontrado: %s", type_name)
            raise HTTPException(status_code=404, detail="Tipo de Pokémon no encontrado")

        if response.status_code >= 500:
            logger.error(
                "Error interno de PokeAPI (%s): %s",
                response.status_code,
                response.text,
            )
            raise HTTPException(status_code=502, detail="Error en PokeAPI")

        data = response.json()

        # --- Transformación de datos ---
        pokemon_list = [
            {
                "name": entry["pokemon"]["name"],
                "url": entry["pokemon"]["url"],
            }
            for entry in data.get("pokemon", [])
        ]

        return pokemon_list
    
    async def search_pokemon_simplified(
        self,
        name: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Búsqueda para el endpoint de la práctica:
        - Filtra por 'name' (subcadena)
        - Devuelve lista simplificada: {id, name, sprite, types}
        """

        # Reutilizamos la paginación básica de PokeAPI
        data = await self.search_pokemon(limit=limit, offset=offset)

        # Filtramos por nombre (contains)
        filtered = [
            item for item in data["results"]
            if name.lower() in item["name"].lower()
        ]

        result: list[dict] = []

        # Para cada Pokémon filtrado, pedimos el detalle y simplificamos
        for item in filtered:
            details = await self.get_pokemon(item["name"])
            result.append(
                {
                    "id": details["id"],
                    "name": details["name"],
                    "sprite": details["sprite"],
                    "types": details["types"],
                }
            )

        return result








    
