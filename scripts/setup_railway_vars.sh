#!/bin/bash

# ZEUES Backend - Railway Environment Variables Setup Script
# Este script configura todas las variables de entorno necesarias en Railway

set -e  # Exit on error

echo "=========================================="
echo "ZEUES Backend - Railway Setup"
echo "=========================================="
echo ""

# Verificar que Railway CLI está instalado
if ! command -v railway &> /dev/null; then
    echo "❌ ERROR: Railway CLI no está instalado"
    echo "   Ejecutar: npm install -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI encontrado"
echo ""

# Verificar que el usuario está autenticado
if ! railway whoami &> /dev/null; then
    echo "❌ ERROR: No estás autenticado en Railway"
    echo "   Ejecutar: railway login"
    exit 1
fi

echo "✅ Autenticado en Railway"
echo ""

# Verificar que el archivo de credenciales existe
CREDENTIALS_FILE="credenciales/zeus-mvp-81282fb07109.json"
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "❌ ERROR: Archivo de credenciales no encontrado: $CREDENTIALS_FILE"
    exit 1
fi

echo "✅ Archivo de credenciales encontrado"
echo ""

# Configurar variables de entorno
echo "📝 Configurando variables de entorno en Railway..."
echo ""

# Google Cloud
echo "1/6 - GOOGLE_CLOUD_PROJECT_ID"
railway variables set GOOGLE_CLOUD_PROJECT_ID=zeus-mvp

# Google Sheet ID (PRODUCCIÓN)
echo "2/6 - GOOGLE_SHEET_ID"
read -p "   Ingresa el ID del Google Sheet de PRODUCCIÓN: " SHEET_ID
railway variables set GOOGLE_SHEET_ID="$SHEET_ID"

# Environment
echo "3/6 - ENVIRONMENT"
railway variables set ENVIRONMENT=production

# CORS Origins
echo "4/6 - ALLOWED_ORIGINS"
read -p "   Ingresa las URLs permitidas para CORS (separadas por coma): " ORIGINS
railway variables set ALLOWED_ORIGINS="$ORIGINS"

# Cache TTL
echo "5/6 - CACHE_TTL_SECONDS"
railway variables set CACHE_TTL_SECONDS=300

# Google Service Account JSON
echo "6/6 - GOOGLE_APPLICATION_CREDENTIALS_JSON"
echo "   Leyendo archivo de credenciales..."
CREDENTIALS_JSON=$(cat "$CREDENTIALS_FILE")
railway variables set GOOGLE_APPLICATION_CREDENTIALS_JSON="$CREDENTIALS_JSON"

echo ""
echo "=========================================="
echo "✅ Variables de entorno configuradas exitosamente"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Verificar variables: railway variables"
echo "2. Deploy: railway up"
echo "3. Ver logs: railway logs"
echo "4. Obtener URL: railway domain"
echo ""
