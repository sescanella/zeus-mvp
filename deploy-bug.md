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

### 🔄 Intento 6: Agregar pip a nixPkgs + PYTHONPATH (EN PROGRESO)
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

**Estado:** Esperando resultado del deployment...

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

### 4. Railway Configuration Priority
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

**Último Commit:** `e8eb586`
**Estrategia Actual:** pip explícito en nixPkgs + PYTHONPATH en start command
**Esperando:** Resultado del deployment en Railway

**Próximos Pasos si Falla:**
1. Verificar logs de Railway para el error específico
2. Considerar alternativas:
   - Dockerfile custom en lugar de nixpacks
   - requirements.txt en la raíz del proyecto
   - Mover todo el código a la raíz (sin carpeta `backend/`)

---

## Referencias

- [Railway Nixpacks Documentation](https://nixpacks.com/docs)
- [Python Import System](https://docs.python.org/3/reference/import.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Server](https://www.uvicorn.org/)

---

**Última Actualización:** 11 Nov 2025 - Esperando resultado del Intento 6
