# Phase 11: Manual Validation Checklist

## Prerequisites

- Backend running: `uvicorn main:app --reload --port 8000`
- Redis available: `redis-cli ping` returns PONG
- Test spools prepared (v3.0 and v4.0):
  - v3.0 spool: Total_Uniones = 0 (e.g., OLD-SPOOL)
  - v4.0 spool: Total_Uniones > 0 (e.g., TEST-02)
- Virtual environment activated: `source venv/bin/activate`

## Quick Setup

```bash
# Terminal 1: Start backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Run validation commands
source venv/bin/activate
# Execute curl commands below
```

## v4.0 Workflow Tests

### 1. INICIAR Success

**Command:**
```bash
curl -X POST http://localhost:8000/api/v4/occupation/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'
```

**Expected:**
- [ ] Returns 200 OK
- [ ] Response includes `{"message": "...", "tag_spool": "TEST-02", ...}`
- [ ] Message contains "ocupado exitosamente"

**Verify Backend State:**
```bash
# Check Redis lock
redis-cli GET "spool:TEST-02:lock"
# Expected: "MR(93)|<timestamp>"

# Check Operaciones sheet
# Ocupado_Por column should show: MR(93)
```

---

### 2. Query Disponibles ARM

**Command:**
```bash
curl http://localhost:8000/api/v4/uniones/TEST-02/disponibles?operacion=ARM
```

**Expected:**
- [ ] Returns 200 OK
- [ ] Response structure:
  ```json
  {
    "tag_spool": "TEST-02",
    "operacion": "ARM",
    "count": <number>,
    "unions": [
      {
        "id": "TEST-02+1",
        "n_union": 1,
        "dn_union": 3.5,
        "tipo_union": "BW"
      },
      ...
    ]
  }
  ```
- [ ] Only unions with `arm_fecha_fin = NULL` are returned
- [ ] Count matches array length

---

### 3. FINALIZAR Partial (PAUSAR)

**Setup:** First run INICIAR (Test #1)

**Command:**
```bash
curl -X POST http://localhost:8000/api/v4/occupation/finalizar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM",
    "selected_unions": ["TEST-02+1", "TEST-02+2"]
  }'
```

**Expected:**
- [ ] Returns 200 OK
- [ ] Response includes:
  ```json
  {
    "action_taken": "PAUSAR",
    "tag_spool": "TEST-02",
    "unions_processed": 2,
    "pulgadas": <calculated_value>,
    "message": "..."
  }
  ```
- [ ] Message contains "2 uniones" and "pausada"
- [ ] Pulgadas > 0 (sum of DN_UNION for selected unions)

**Verify Backend State:**
```bash
# Redis lock should be released
redis-cli GET "spool:TEST-02:lock"
# Expected: (nil)

# Operaciones sheet
# Ocupado_Por should be NULL
# Uniones_ARM_Completadas should increase by 2
```

**Verify Metadata Events:**
```bash
# Check Metadata sheet for events:
# - TOMAR_SPOOL (from INICIAR)
# - PAUSAR_SPOOL (from FINALIZAR)
# - UNION_ARM_REGISTRADA (2 events for each union)
```

---

### 4. FINALIZAR Complete (COMPLETAR)

**Setup:**
1. Run INICIAR
2. Select ALL remaining disponibles

**Command:**
```bash
# First, get all disponibles
curl http://localhost:8000/api/v4/uniones/TEST-02/disponibles?operacion=ARM

# Then finalize with all union IDs
curl -X POST http://localhost:8000/api/v4/occupation/finalizar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM",
    "selected_unions": ["TEST-02+3", "TEST-02+4", "TEST-02+5", ...]
  }'
```

**Expected:**
- [ ] Returns 200 OK
- [ ] Response includes:
  ```json
  {
    "action_taken": "COMPLETAR",
    "tag_spool": "TEST-02",
    "unions_processed": <count>,
    "pulgadas": <calculated_value>,
    "message": "..."
  }
  ```
- [ ] Message contains "completada"

**Verify Backend State:**
```bash
# Disponibles ARM should now be empty
curl http://localhost:8000/api/v4/uniones/TEST-02/disponibles?operacion=ARM
# Expected: {"count": 0, "unions": []}
```

---

### 5. Query Metrics

**Command:**
```bash
curl http://localhost:8000/api/v4/uniones/TEST-02/metricas
```

**Expected:**
- [ ] Returns 200 OK
- [ ] Response has exactly 6 fields:
  ```json
  {
    "tag_spool": "TEST-02",
    "total_uniones": 10,
    "arm_completadas": 5,
    "sold_completadas": 0,
    "pulgadas_arm": 18.50,
    "pulgadas_sold": 0.00
  }
  ```
- [ ] Pulgadas have exactly 2 decimal places (18.50, not 18.5)
- [ ] Counts match actual union states in Uniones sheet

---

## Version Detection Tests

### 6. v3.0 Spool Rejection

**Command:**
```bash
# Try v4.0 endpoint on v3.0 spool (Total_Uniones = 0)
curl -X POST http://localhost:8000/api/v4/occupation/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "OLD-SPOOL",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'
```

**Expected:**
- [ ] Returns 400 Bad Request
- [ ] Response structure:
  ```json
  {
    "detail": {
      "error": "WRONG_VERSION",
      "message": "Spool OLD-SPOOL is v3.0...",
      "correct_endpoint": "/api/v3/occupation/tomar",
      "spool_version": "v3.0"
    }
  }
  ```
- [ ] Error message helpful for frontend routing

---

### 7. v3.0 Endpoints Still Work

**Command:**
```bash
curl -X POST http://localhost:8000/api/v3/occupation/tomar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "OLD-SPOOL",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'
```

**Expected:**
- [ ] Returns 200 OK or 409 Conflict (if already occupied)
- [ ] v3.0 workflow functional at new `/api/v3/` prefix

**Verify Legacy Routes:**
```bash
# Legacy /api/occupation/* paths should also work
curl -X POST http://localhost:8000/api/occupation/tomar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "OLD-SPOOL",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
  }'
```

- [ ] Legacy routes functional (backward compatibility)

---

## ARM-Before-SOLD Validation

### 8. SOLD Requires ARM Complete

**Command:**
```bash
# Try SOLD on spool without ARM complete
curl -X POST http://localhost:8000/api/v4/occupation/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "FRESH-SPOOL",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "SOLD"
  }'
```

**Expected:**
- [ ] Returns 403 Forbidden
- [ ] Response structure:
  ```json
  {
    "detail": {
      "error": "ARM_PREREQUISITE",
      "message": "SOLD requires ARM complete. <N> uniones ARM pendientes",
      ...
    }
  }
  ```

**After ARM Complete:**
```bash
# 1. Complete all ARM unions first
# 2. Then retry SOLD
curl -X POST http://localhost:8000/api/v4/occupation/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "FRESH-SPOOL",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "SOLD"
  }'
```

- [ ] Now returns 200 OK (ARM prerequisite met)

---

## Performance Test

### 9. 10-Union Operation Under 1 Second

**Setup:**
1. Spool with at least 10 disponibles
2. INICIAR operation
3. Select 10 unions

**Command:**
```bash
# Use 'time' to measure duration
time curl -X POST http://localhost:8000/api/v4/occupation/finalizar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM",
    "selected_unions": [
      "TEST-02+1", "TEST-02+2", "TEST-02+3", "TEST-02+4", "TEST-02+5",
      "TEST-02+6", "TEST-02+7", "TEST-02+8", "TEST-02+9", "TEST-02+10"
    ]
  }'
```

**Expected:**
- [ ] Total time < 1.0 second (check `time` output)
- [ ] Returns 200 OK
- [ ] `unions_processed: 10`
- [ ] All 10 unions updated successfully

**Note:** Performance depends on:
- Google Sheets API latency (300-500ms typical)
- Batch update optimization (single API call)
- Network conditions

---

## Error Handling Tests

### 10. Non-Existent Spool (404)

```bash
curl http://localhost:8000/api/v4/uniones/DOES-NOT-EXIST/disponibles?operacion=ARM
```

- [ ] Returns 404 Not Found
- [ ] Error message: "Spool DOES-NOT-EXIST not found"

---

### 11. Invalid Operacion (422)

```bash
curl http://localhost:8000/api/v4/uniones/TEST-02/disponibles?operacion=INVALID
```

- [ ] Returns 422 Validation Error
- [ ] FastAPI validation message about pattern mismatch

---

### 12. Ownership Violation (403)

**Setup:**
1. Worker 1 runs INICIAR
2. Worker 2 tries to FINALIZAR

```bash
# Worker 1
curl -X POST http://localhost:8000/api/v4/occupation/iniciar \
  -H "Content-Type: application/json" \
  -d '{"tag_spool": "TEST-02", "worker_id": 93, "worker_nombre": "MR(93)", "operacion": "ARM"}'

# Worker 2 (different ID)
curl -X POST http://localhost:8000/api/v4/occupation/finalizar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 94,
    "worker_nombre": "JD(94)",
    "operacion": "ARM",
    "selected_unions": ["TEST-02+1"]
  }'
```

- [ ] Returns 403 Forbidden
- [ ] Error: "NO_AUTORIZADO" or "Worker JD(94) no es propietario"

---

### 13. Empty Selection (Cancellation)

```bash
# After INICIAR, send empty selection
curl -X POST http://localhost:8000/api/v4/occupation/finalizar \
  -H "Content-Type: application/json" \
  -d '{
    "tag_spool": "TEST-02",
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM",
    "selected_unions": []
  }'
```

- [ ] Returns 200 OK
- [ ] `action_taken: "CANCELAR"`
- [ ] `unions_processed: 0`
- [ ] Message contains "cancelada"
- [ ] Lock released

---

## API Documentation Review

### 14. Swagger UI Validation

**Navigate to:** http://localhost:8000/docs

**Verify:**
- [ ] `/api/v3/` endpoints grouped under `v3-occupation` tag
- [ ] `/api/v4/` endpoints grouped under `v4-unions` tag
- [ ] Legacy `/api/occupation/` endpoints visible
- [ ] Request/response schemas documented

**Test via Swagger:**
1. [ ] Expand `POST /api/v4/occupation/iniciar`
2. [ ] Click "Try it out"
3. [ ] Fill sample data
4. [ ] Execute
5. [ ] Verify response matches schema

---

## Integration Validation Summary

After completing all tests:

- [ ] All v4.0 endpoints functional
- [ ] Version detection working (v3.0 spools rejected)
- [ ] Backward compatibility maintained (v3.0 endpoints work)
- [ ] Performance target met (< 1s for 10 unions)
- [ ] Error handling comprehensive (400/403/404/409/422/500)
- [ ] ARM-before-SOLD validation enforced
- [ ] Metrología auto-trigger working (if 100% SOLD complete)
- [ ] Metadata events logged correctly
- [ ] API documentation accurate

---

## Troubleshooting

### Backend Not Starting
```bash
# Check Redis
redis-cli ping

# Check virtual environment
source venv/bin/activate
which python  # Should be in venv/

# Check logs
tail -f logs/app.log
```

### Connection Errors
```bash
# Verify Redis connection
python -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"

# Check Google Sheets credentials
echo $GOOGLE_PRIVATE_KEY | head -c 50
echo $GOOGLE_SHEET_ID
```

### Test Data Issues
```bash
# Reset test spool
# 1. Clear Redis lock
redis-cli DEL "spool:TEST-02:lock"

# 2. Manually update Operaciones sheet:
#    - Ocupado_Por = NULL
#    - Uniones_ARM_Completadas = 0
#    - Uniones_SOLD_Completadas = 0
```

---

**Phase 11 Manual Validation Complete:** All endpoints tested and verified.
