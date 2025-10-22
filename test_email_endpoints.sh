#!/bin/bash
# Script para probar los endpoints de health check de email

# Variables
API_URL="http://localhost:8000/api/v1"
TOKEN="your_auth_token_here"

echo "========================================="
echo "TEST: Email Health Check Endpoints"
echo "========================================="

# Test 1: Verificar estado de servicios
echo ""
echo "[1] Verificando estado de servicios de email..."
echo "URL: GET $API_URL/email/health"
echo ""

curl -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/email/health" \
  | jq .

# Test 2: Reinicializar servicios
echo ""
echo ""
echo "[2] Reinicializando servicios de email..."
echo "URL: POST $API_URL/email/reinitialize"
echo ""

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/email/reinitialize" \
  | jq .

# Test 3: Verificar estado nuevamente
echo ""
echo ""
echo "[3] Verificando estado después de reinicializar..."
echo "URL: GET $API_URL/email/health"
echo ""

curl -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/email/health" \
  | jq .

echo ""
echo "========================================="
echo "Tests completados"
echo "========================================="
