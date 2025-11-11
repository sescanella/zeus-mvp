# Guía Rápida: Entornos Virtuales Python (macOS)

## Crear entorno virtual

```bash
python3 -m venv venv
```

## Activar entorno

```bash
source venv/bin/activate
```

## Instalar paquetes

```bash
pip install pandas openpyxl
```

## Guardar dependencias

```bash
pip freeze > requirements.txt
```

## Instalar desde requirements.txt

```bash
pip install -r requirements.txt
```

## Desactivar entorno

```bash
deactivate
```

## Agregar a .gitignore

```
venv/
*.pyc
__pycache__/
```

## Verificar entorno activo

```bash
which python  # Debe mostrar la ruta dentro de venv/
```
