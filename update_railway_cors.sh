#!/bin/bash
#
# Script para actualizar ALLOWED_ORIGINS en Railway
#
# NOTA: Este script requiere configurar manualmente la variable en Railway UI
# porque railway CLI no está autenticado actualmente.
#
# PASOS MANUALES:
# 1. Ir a https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]/variables
# 2. Buscar o crear variable ALLOWED_ORIGINS
# 3. Configurar valor:
#    http://localhost:3000,https://zeues-frontend.vercel.app
# 4. Guardar y Railway redesplegará automáticamente

echo "============================================================"
echo "  ACTUALIZAR CORS EN RAILWAY - INSTRUCCIONES"
echo "============================================================"
echo ""
echo "🎯 PROBLEMA: CORS bloqueando requests desde Vercel"
echo ""
echo "📝 SOLUCIÓN: Configurar variable ALLOWED_ORIGINS en Railway"
echo ""
echo "🔧 PASOS:"
echo "   1. Abrir Railway: https://railway.app"
echo "   2. Ir a: Proyecto 'zeues-backend-mvp' → Variables"
echo "   3. Buscar variable: ALLOWED_ORIGINS"
echo "   4. Configurar valor:"
echo ""
echo "      http://localhost:3000,https://zeues-frontend.vercel.app"
echo ""
echo "   5. Guardar cambios (Railway redesplegará automáticamente)"
echo ""
echo "✅ VERIFICACIÓN:"
echo "   Después del redeploy, ejecutar:"
echo "   python3 test_production_e2e.py"
echo ""
echo "============================================================"
