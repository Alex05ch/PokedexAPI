# Consideraciones de Seguridad

## Autenticación

- La API usa JWT (JSON Web Tokens) para autenticar peticiones.
- El login se realiza en `POST /api/v1/auth/login`.  
  - Si las credenciales son correctas se genera un `access_token` firmado con `SECRET_KEY` y el algoritmo HS256.
  - El payload incluye, como mínimo: `sub` (username) y `user_id`.
- La verificación del token se hace en la dependencia `get_current_user`, que:
  - Valida la firma del token.
  - Revisa la expiración (`exp`).
  - Carga el usuario desde la base de datos.
- Los endpoints protegidos requieren la cabecera:
  ```http
  Authorization: Bearer <access_token>

2. Política de expiración de tokens

- La duración del token está controlada por la variable de entorno:
  - `ACCESS_TOKEN_EXPIRE_MINUTES` (por ejemplo, 60 minutos).
- Tokens cortos reducen el impacto si se filtra un token.
- Se recomienda usar HTTPS en producción para proteger tokens en tránsito.

## Contraseñas

1. Algoritmo de hashing

- Las contraseñas no se guardan en texto plano.
- Se usan funciones de hashing basadas en bcrypt (a través de `passlib`).
- Para verificar una contraseña:
  - Se compara la contraseña en claro con el hash mediante `verify_password`.
  - Nunca se deshace el hash.

2. Política de contraseñas

- Se recomienda:
  - Longitud mínima de 8 caracteres.
  - Combinar letras, números y símbolos.
- La API permite políticas más estrictas en el futuro (validación en el registro).


## Rate Limiting
1. Limites por endpoint 

Se usa slowapi para limitar peticiones por cliente:

- `POST /api/v1/auth/login`  
  - Límite: `10/minute`  
  - Objetivo: mitigar ataques de fuerza bruta al login.

- Endpoints de Pokédex:
  - `GET /api/v1/pokedex` → `100/minute`
  - `POST /api/v1/pokedex` → `30/minute`
  - `GET /api/v1/pokedex/{entry_id}` → `60/minute`
  - `PATCH /api/v1/pokedex/{entry_id}` → `30/minute`
  - `DELETE /api/v1/pokedex/{entry_id}` → `30/minute`

- Endpoints de Teams y Pokémon usan límites similares para evitar abusos de scraping.

2. Justificación

- Protege la API frente a:
  - Intentos masivos de login.
  - Scraping agresivo de datos de PokeAPI y de la propia API.
- Mejora la estabilidad del servicio ante usuarios maliciosos o scripts mal configurados.


## CORS

1. Orígenes permitidos

- En desarrollo se suele permitir:
  - `http://localhost`
  - `http://localhost:3000` (u otros puertos de frontends locales).

2. Por qué es necesario

- CORS controla qué frontends pueden realizar peticiones AJAX al backend.
- Ayuda a evitar que páginas no autorizadas utilicen el token del usuario desde su navegador.


## Variables de Entorno

1. Información sensible almacenada

- `SECRET_KEY` – clave usada para firmar JWT.
- `DATABASE_URL` – credenciales de la base de datos (si no es SQLite local).
- `ACCESS_TOKEN_EXPIRE_MINUTES` – configuración de expiración.
- Cualquier otra clave relacionada con servicios externos.

2. Cómo protegerla

- No se sube ningún `.env` real al repositorio.
- Sólo se versiona `.env.example` con nombres de variables, nunca con valores reales.
- En producción:
  - Usar gestores de secretos (por ejemplo, variables del sistema, vaults, etc.).
  - Rotar claves periódicamente, especialmente si se sospecha de una filtración.



## Vulnerabilidades Conocidas

1. OWASP API Security Top 10 consideradas

- API1:2019 – Broken Object Level Authorization  
  - Mitigación:  
    - Todas las operaciones de Pokédex y Teams comprueban `owner_id`.  
    - Un usuario no puede leer/modificar/borrar recursos de otro usuario.

- API2:2019 – Broken Authentication
  - Mitigación:  
    - Uso de JWT con expiración.  
    - Contraseñas hasheadas con bcrypt.  
    - Rate limiting en `/login`.

- API3:2019 – Excessive Data Exposure
  - Mitigación:  
    - Se usan modelos de respuesta (`response_model`) para controlar los campos devueltos.  
    - Nunca se exponen hashes de contraseñas u otros datos sensibles.

- API4:2019 – Lack of Resources & Rate Limiting
  - Mitigación:  
    - Límites por endpoint con slowapi (ver sección de Rate Limiting).

- API5:2019 – Broken Function Level Authorization
  - Mitigación:  
    - Endpoints de administración de recursos siempre requieren JWT.  
    - No hay rutas de administración públicas.

### Mitigaciones adicionales

- Validación de datos de entrada con Pydantic/SQLModel.
- Manejo controlado de errores para no exponer trazas internas.
- Recomendación de desplegar siempre sobre HTTPS.
