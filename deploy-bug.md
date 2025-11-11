# Railway Deployment Troubleshooting Log

**Fecha:** 11 de Noviembre 2025
**Proyecto:** ZEUES Backend MVP
**Plataforma:** Railway
**Tech Stack:** Python 3.9 + FastAPI + nixpacks

---

## Problema Inicial

**Síntoma:**
```
ModuleNotFoundError: No module named 'backend'
File "/app/main.py", line 31, in <module>
    from backend.config import config
```

**Contexto:**
- La aplicación funcionaba correctamente en local
- Al deployar en Railway, el backend crasheaba inmediatamente
- El error indicaba que Python no podía encontrar el módulo `backend`

---

## Estructura del Proyecto

```
/Users/sescanella/Proyectos/ZEUES-by-KM/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   ├── routers/
│   ├── services/
│   ├── repositories/
│   └── requirements.txt
├── Procfile
├── railway.json
└── nixpacks.toml (se creó durante debugging)
```

---

## Intentos de Solución

### ❌ Intento 1: Cambiar a Imports Relativos
**Commit:** `669172e` → `496952d`

**Acción:**
Cambié los imports en `backend/main.py` de absolutos a relativos:
```python
# Antes (absolutos)
from backend.config import config
from backend.exceptions import ZEUSException

# Después (relativos)
from .config import config
from .exceptions import ZEUSException
```

**Resultado:**
```
ImportError: attempted relative import with no known parent package
```

**Lección Aprendida:**
Los imports relativos NO funcionan cuando el archivo es ejecutado como un script directamente. Railway estaba tratando de ejecutar el archivo como script, no como parte de un paquete.

---

### ❌ Intento 2: Revertir a Absolutos + nixpacks.toml con PYTHONPATH
**Commit:** `496952d` → `80f553a`

**Acción:**
1. Revertí los imports a absolutos
2. Creé `nixpacks.toml` con configuración:
```toml
[phases.setup]
nixPkgs = ["python39", "pip"]

[phases.install]
cmds = ["pip install -r backend/requirements.txt"]

[start]
cmd = "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"

[variables]
PYTHONPATH = "/app"
```

**Resultado:**
```
ModuleNotFoundError: No module named 'backend'
```

**Problema Identificado:**
El comando seguía siendo `uvicorn backend.main:app` directo, sin usar el módulo de Python.

---

### ❌ Intento 3: Usar python -m uvicorn
**Commit:** `80f553a`

**Acción:**
Cambié el comando de inicio en todos los archivos de configuración:
```toml
# nixpacks.toml
cmd = "python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT"

# railway.json
"startCommand": "python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT"

# Procfile
web: python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Resultado:**
Mismo error - Railway seguía viendo `/app/main.py` en lugar de `/app/backend/main.py`

**Problema Identificado:**
Railway tenía configurado **Root Directory: /backend** en Settings, lo que hacía que buscara todo dentro de ese directorio, pero los archivos de configuración estaban en la raíz.

---

### ❌ Intento 4: setup.py + pip install -e .
**Commit:** `c2c63bd`

**Acción:**
Creé `setup.py` para hacer `backend` un paquete instalable:
```python
from setuptools import setup, find_packages

setup(
    name="zeues-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open('backend/requirements.txt')
        if line.strip() and not line.startswith('#')
    ],
    python_requires=">=3.9",
)
```

Actualicé `nixpacks.toml`:
```toml
[phases.install]
cmds = [
  "pip install --upgrade pip setuptools wheel",
  "pip install -e ."
]
```

**Resultado:**
```
/bin/bash: line 1: pip: command not found
```

**Lección Aprendida:**
En el ambiente de nixpacks, `pip` no está directamente en el PATH.

---

### ❌ Intento 5: python -m pip
**Commit:** `51877aa`

**Acción:**
```toml
[phases.install]
cmds = [
  "python -m pip install --upgrade pip setuptools wheel",
  "python -m pip install -e ."
]
```

**Resultado:**
Railway usó cache del build anterior, seguía mostrando el error de `pip: command not found`

**Acción Correctiva:**
Commit vacío para forzar rebuild: `28a255c`

**Nuevo Resultado:**
```
/root/.nix-profile/bin/python: No module named pip
```

**Lección Aprendida:**
Python 3.9 en nixpacks NO incluye el módulo `pip` por defecto. `python -m pip` no funciona sin configuración adicional.

---

### ❌ Intento 6: Agregar pip a nixPkgs + PYTHONPATH
**Commit:** `e8eb586`

**Acción:**
Simplificado el enfoque completamente:

```toml
[phases.setup]
nixPkgs = ["python39", "python39Packages.pip"]  # ← Agregar pip explícitamente

[phases.install]
cmds = [
  "pip install -r backend/requirements.txt"  # ← Simple, directo
]

[start]
cmd = "cd /app && PYTHONPATH=/app python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
# ← PYTHONPATH=/app permite encontrar el módulo backend
```

**Configuración de Railway:**
- ✅ Root Directory: (vacío / raíz del proyecto)
- ✅ Custom Start Command: (vacío - usa railway.json)
- ✅ RAILWAY_START_COMMAND: (eliminada)

**Resultado:**
```
This environment is externally managed
This command has been disabled as it tries to modify the immutable /nix/store filesystem.

To use Python with Nix and nixpkgs, have a look at the online documentation
<https://nixos.org/manual/nixpkgs/stable/#python>.

"pip install -r backend/requirements.txt" did not complete successfully: exit code 1
```

**Lección Aprendida:**
El sistema de archivos en nixpacks es **inmutable**. No puedes usar `pip install` para modificar el ambiente porque intenta escribir en `/nix/store`, que es de solo lectura. Este es un diseño fundamental de Nix que no se puede evitar.

---

### ✅ Intento 7: Dockerfile
**Commit:** `fa34604`

**Acción:**
Abandoné nixpacks completamente y creé un **Dockerfile estándar**:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt
COPY . /app
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Pruebas Locales:**
✅ Build completado sin errores
✅ Container starts y API responde correctamente

**Resultado:**
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

**Problema Identificado:**
Railway ejecutaba el `startCommand` de `railway.json` que tenía `$PORT` como string literal. La variable no se expandía porque estaba en contexto JSON.

---

### ✅ Intento 8: Corregir $PORT Variable (SOLUCIÓN FINAL)
**Commit:** `f5f8050`

**Acción:**
Dos cambios clave para permitir expansión de variable `$PORT`:

**1. Dockerfile - Cambiar a shell form:**
```dockerfile
# Antes (exec form - no expande variables)
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Después (shell form - expande variables)
CMD python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**2. railway.json - Eliminar startCommand:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**¿Por qué funciona?**
- **Shell form** (`CMD command`) ejecuta en shell, permitiendo expansión de variables
- **Exec form** (`CMD ["command"]`) ejecuta directo, no expande variables
- **`${PORT:-8000}`** usa `$PORT` si existe, sino usa `8000` como default
- Sin `startCommand` en railway.json, Railway usa el CMD del Dockerfile

**Pruebas Locales:**
```bash
docker build -t zeues-backend-port-fix .
docker run -d -p 9000:9000 -e PORT=9000 zeues-backend-port-fix
curl http://localhost:9000/
# ✅ {"message":"ZEUES API - Manufacturing Traceability System",...}
```

**Estado:** ✅ Deployado a Railway - esperando confirmación de producción

---

## Errores Comunes Encontrados

### 1. Root Directory Incorrecto
**Problema:** Railway configurado con Root Directory `/backend`
**Síntoma:** No encuentra `setup.py`, `nixpacks.toml`, `railway.json`
**Solución:** Dejar Root Directory vacío o en `/`

### 2. Comando de Inicio Incorrecto
**Problema:** Variables de entorno con comandos viejos
**Variables Conflictivas:**
- `RAILWAY_START_COMMAND` con comando viejo
- Custom Start Command en Settings con comando viejo
**Solución:** Eliminar estas variables y dejar que nixpacks.toml maneje todo

### 3. Cache de Railway
**Problema:** Railway usa builds cacheados de configuraciones antiguas
**Síntoma:** Los cambios en nixpacks.toml no se reflejan
**Solución:**
- Hacer commit vacío para forzar rebuild
- O usar "Clear Build Cache" en Railway Settings

### 4. Pip No Disponible en Nixpacks
**Problema:** `pip` no está en PATH ni como módulo de Python
**Síntoma:**
```bash
pip: command not found
python: No module named pip
```
**Solución:** Agregar `python39Packages.pip` a nixPkgs

### 5. Nixpacks Filesystem Inmutable
**Problema:** Nixpacks usa un sistema de archivos de solo lectura (`/nix/store`)
**Síntoma:**
```
This environment is externally managed
This command has been disabled as it tries to modify the immutable /nix/store filesystem
```
**Solución:** Usar Dockerfile en lugar de nixpacks. El filesystem inmutable es un diseño fundamental de Nix y no se puede evitar.

### 6. Variable $PORT No Se Expande
**Problema:** La variable de entorno `$PORT` no se expande en Docker exec form o en JSON
**Síntoma:**
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```
**Causas:**
1. Usar exec form en Dockerfile: `CMD ["command", "$PORT"]` - no expande variables
2. Tener `startCommand` en railway.json con `$PORT` - JSON no expande variables

**Solución:**
1. Usar shell form en Dockerfile: `CMD command --port ${PORT:-8000}`
2. Eliminar `startCommand` de railway.json y dejar que Dockerfile maneje el comando
3. Usar sintaxis `${PORT:-default}` para tener fallback en local

---

## Lecciones Aprendidas

### 1. Imports en Python
- **Imports absolutos** (`from backend.config`) requieren que el directorio padre esté en `sys.path` o `PYTHONPATH`
- **Imports relativos** (`from .config`) solo funcionan cuando el archivo se importa como módulo, no cuando se ejecuta como script
- **`python -m uvicorn backend.main:app`** ejecuta uvicorn como módulo, lo que configura correctamente `sys.path`

### 2. Nixpacks en Railway
- Nixpacks construye un ambiente mínimo, no incluye todo por defecto
- Necesitas declarar explícitamente las dependencias del sistema en `nixPkgs`
- `pip` NO está incluido por defecto, debes agregar `python39Packages.pip`
- Los comandos en `[phases.install]` se ejecutan en el contexto de nixpacks

### 3. PYTHONPATH
- `PYTHONPATH` le dice a Python dónde buscar módulos adicionales
- En Railway/Docker, `/app` es el directorio de trabajo
- Configurar `PYTHONPATH=/app` permite que Python encuentre `backend/` dentro de `/app/`

### 4. Docker CMD: Shell Form vs Exec Form
**Exec form** (`CMD ["executable", "param"]`):
- No usa shell para ejecutar
- NO expande variables de entorno
- Ejemplo: `CMD ["python", "--port", "$PORT"]` → `$PORT` es literal
- Más seguro para evitar shell injection
- Mejor manejo de señales (SIGTERM)

**Shell form** (`CMD executable param`):
- Ejecuta comando en shell (`/bin/sh -c`)
- SÍ expande variables de entorno
- Ejemplo: `CMD python --port ${PORT}` → `${PORT}` se expande
- Necesario cuando usas variables de entorno
- Usa `${VAR:-default}` para valores por defecto

**Cuándo usar cada uno:**
- Shell form: Cuando necesitas expansión de variables (`$PORT`, `$ENV_VAR`)
- Exec form: Para comandos fijos sin variables

### 5. Railway Configuration Priority
**Orden de prioridad (mayor a menor):**
1. Custom Start Command en Settings UI
2. Variable de entorno `RAILWAY_START_COMMAND`
3. `railway.json` → `deploy.startCommand`
4. `nixpacks.toml` → `[start].cmd`
5. `Procfile`

**Recomendación:** Usar solo `nixpacks.toml` o `railway.json`, eliminar las demás para evitar conflictos.

---

## Comandos de Verificación Local

```bash
# 1. Verificar que los imports funcionan
source venv/bin/activate
python -c "from backend.main import app; print('✅ Import OK')"

# 2. Verificar que uvicorn inicia correctamente
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. Test del endpoint
curl http://localhost:8000/
# Debería retornar: {"message":"ZEUES API - Manufacturing Traceability System",...}

# 4. Verificar PYTHONPATH funciona
PYTHONPATH=/Users/sescanella/Proyectos/ZEUES-by-KM python -c "from backend.main import app; print('✅')"
```

---

## Checklist de Deployment

Antes de hacer deploy a Railway, verificar:

- [ ] `backend/__init__.py` existe (puede estar vacío)
- [ ] `backend/requirements.txt` tiene todas las dependencias
- [ ] Imports en `backend/main.py` son absolutos (`from backend.*`)
- [ ] `nixpacks.toml` está en la raíz del proyecto (no dentro de `/backend`)
- [ ] `nixpacks.toml` incluye `python39Packages.pip` en nixPkgs
- [ ] Railway Settings → Root Directory está vacío o es `/`
- [ ] No hay Custom Start Command configurado en Railway UI
- [ ] Variables de entorno críticas están configuradas:
  - `GOOGLE_SHEET_ID`
  - `GOOGLE_CREDENTIALS_BASE64` (o archivo credentials.json)
  - `ENVIRONMENT=production`
  - `ALLOWED_ORIGINS` incluye el dominio de Railway
- [ ] El código funciona localmente con `python -m uvicorn backend.main:app`

---

## Estado Actual

**Último Commit:** `f5f8050`
**Estrategia Final:** ✅ **Dockerfile con shell form CMD** (abandonamos nixpacks)
**Estado:** Deployado a Railway - esperando confirmación de producción

### Resumen de la Solución

Después de **8 intentos** (6 con nixpacks, 2 con Dockerfile), la solución final fue:

✅ **Intento 7:** Dockerfile con Python 3.9 (solucionó nixpacks filesystem inmutable)
✅ **Intento 8:** Shell form CMD + eliminar startCommand (solucionó $PORT expansion)

**Cambios Clave:**
1. **Dockerfile con shell form:**
   ```dockerfile
   CMD python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```
2. **railway.json sin startCommand:**
   ```json
   {"build": {"builder": "DOCKERFILE"}, "deploy": {...}}
   ```

### ¿Por qué falló nixpacks?

Nixpacks tiene un **filesystem inmutable** (`/nix/store`) que impide el uso normal de `pip install`. Esto es un diseño fundamental de Nix, no un bug. Para proyectos Python con dependencias, Dockerfile es la opción más simple y confiable.

### ¿Por qué falló el primer Dockerfile?

El `CMD` usaba **exec form** (`CMD ["python", ...]`) que no expande variables de entorno. Railway intentaba pasar `$PORT` pero se interpretaba como string literal `"$PORT"`, no como el valor numérico.

**Solución:** Usar **shell form** (`CMD python ...`) que ejecuta en shell y expande variables correctamente.

### Archivos Clave del Deploy Final

1. **`Dockerfile`** - Define el container con shell form CMD
2. **`railway.json`** - Configura builder como DOCKERFILE (sin startCommand)
3. **`backend/requirements.txt`** - Dependencias de Python
4. **Variables de entorno en Railway** - Credenciales de Google Sheets + PORT

---

## Referencias

- [Railway Dockerfile Documentation](https://docs.railway.app/deploy/dockerfiles)
- [Railway Nixpacks Documentation](https://nixpacks.com/docs)
- [Python Import System](https://docs.python.org/3/reference/import.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Server](https://www.uvicorn.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Última Actualización:** 11 Nov 2025 - Solución PORT variable implementada (Intento 8 - FINAL)
