# ZEUES v4.0 - Esquema Completo de la Aplicación

> **Propósito:** Visualizar desde una sola vista todos los flujos, condiciones, datos capturados y árboles de decisión de la aplicación ZEUES.

> **Paleta de colores Blueprint Industrial:**
> - `#001F3F` Navy - Base/Principal
> - `#FF6B35` Orange - Acento/Acción
> - `#0D9488` Teal - Completado/Aprobado
> - `#D97706` Amber - Pausa/Advertencia
> - `#BE123C` Rose - Error/Rechazo
> - `#881337` Crimson - Bloqueado/Crítico
> - `#475569` Slate - Neutro/Cancelado
> - `#4338CA` Indigo - Conflicto/Especial
> - `#0891B2` Cyan - Metrología/Inspección
> - `#0369A1` Sky - Información/Datos

---

## 1. Flujo General de la Aplicación (UI)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    P1["🏠 P1: SELECCIONA OPERACIÓN"]
    P2["👷 P2: SELECCIONA TRABAJADOR"]
    P3["⚡ P3: TIPO DE ACCIÓN"]
    P4["📦 P4: SELECCIONA SPOOL"]
    P4b_unions["🔗 P4b: SELECCIONA UNIONES"]
    P4b_metro["🔍 P4b: RESULTADO METROLOGÍA"]
    P5["✅ P5: CONFIRMACIÓN"]
    P6["🎉 P6: ÉXITO"]

    P1 -->|"ARM / SOLD / MET / REP"| P2
    P2 -->|"Trabajador filtrado por rol"| P3

    P3 -->|"INICIAR"| P4
    P3 -->|"FINALIZAR"| P4
    P3 -->|"INSPECCIÓN"| P4

    P4 -->|"INICIAR (1 spool)"| P6
    P4 -->|"FINALIZAR v4.0"| P4b_unions
    P4 -->|"FINALIZAR REP"| P5
    P4 -->|"INSPECCIÓN"| P4b_metro

    P4b_unions -->|"N uniones seleccionadas"| P5
    P4b_unions -->|"0 uniones → Liberar"| P5
    P4b_metro -->|"APROBADO / RECHAZADO"| P6

    P5 -->|"CONFIRMAR"| P6
    P6 -->|"5s auto-redirect"| P1

    style P1 fill:#001F3F,color:#fff,stroke:#FF6B35,stroke-width:2px
    style P2 fill:#0369A1,color:#fff
    style P3 fill:#FF6B35,color:#fff
    style P4 fill:#001F3F,color:#fff
    style P4b_unions fill:#0369A1,color:#fff
    style P4b_metro fill:#0891B2,color:#fff
    style P5 fill:#D97706,color:#fff
    style P6 fill:#0D9488,color:#fff
```

---

## 2. Árbol de Decisión P3: ¿Qué acciones ve el usuario?

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    START["P3: ¿Qué operación?"]

    START -->|"ARM o SOLD"| ARM_SOLD_OPTS["INICIAR / FINALIZAR"]
    START -->|"METROLOGÍA"| MET_OPTS["INSPECCIÓN"]
    START -->|"REPARACIÓN"| REP_OPTS["INICIAR / FINALIZAR"]

    style START fill:#001F3F,color:#fff,stroke:#FF6B35,stroke-width:2px
    style ARM_SOLD_OPTS fill:#FF6B35,color:#fff
    style MET_OPTS fill:#0891B2,color:#fff
    style REP_OPTS fill:#D97706,color:#fff
```

---

## 3. Flujo Completo: ARMADO (ARM)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph PREREQ["🔒 PREREQUISITOS"]
        MAT{"¿Fecha_Materiales<br/>existe?"}
        MAT -->|"No"| BLOCK_MAT["❌ DependenciasNoSatisfechasError<br/>(materiales no recibidos)"]
        MAT -->|"Sí"| ROLE{"¿Trabajador tiene<br/>rol Armador o Ayudante?"}
        ROLE -->|"No"| BLOCK_ROL["❌ RolNoAutorizadoError"]
        ROLE -->|"Sí"| READY["✅ Puede operar"]
    end

    subgraph INICIAR_ARM["🟢 INICIAR ARM"]
        I1{"¿Spool tiene<br/>Armador asignado?"}
        I1 -->|"Sí"| I1_ERR["❌ OperacionYaIniciadaError"]
        I1 -->|"No"| I2{"¿Spool ocupado<br/>por otro?"}
        I2 -->|"Sí"| I2_ERR["❌ SpoolOccupiedError"]
        I2 -->|"No (P4 filtra)"| I3["📝 ESCRIBE<br/>─────────────────<br/>Ocupado_Por = trabajador<br/>Fecha_Ocupacion = ahora<br/>Estado_Detalle = 'trabajando ARM'"]
        I3 --> I4["📋 Metadata: INICIAR_SPOOL"]
    end

    subgraph FINALIZAR_ARM["🟠 FINALIZAR ARM"]
        F1["Seleccionar uniones<br/>(checkbox en P4b)"]
        F1 --> F2{"¿Cuántas uniones<br/>seleccionadas?"}
        F2 -->|"0"| CANCEL["CANCELADO<br/>📝 Limpia Ocupado_Por"]
        F2 -->|"< total disponibles"| PAUSAR_ARM
        F2 -->|"= total disponibles"| COMPLETAR_ARM

        subgraph PAUSAR_ARM["⏸️ PAUSAR"]
            PA1["📝 Por cada unión seleccionada<br/>─────────────────<br/>ARM_WORKER = trabajador<br/>ARM_FECHA_INICIO = Fecha_Ocupacion<br/>ARM_FECHA_FIN = ahora()"]
            PA1 --> PA2["📝 En Operaciones<br/>─────────────────<br/>Ocupado_Por = vacío<br/>Fecha_Ocupacion = vacío<br/>Estado_Detalle = 'ARM parcial'"]
        end

        subgraph COMPLETAR_ARM["✅ COMPLETAR"]
            CA1["📝 Por cada unión seleccionada<br/>─────────────────<br/>ARM_WORKER = trabajador<br/>ARM_FECHA_INICIO = Fecha_Ocupacion<br/>ARM_FECHA_FIN = ahora()"]
            CA1 --> CA2["📝 En Operaciones<br/>─────────────────<br/>Ocupado_Por = vacío<br/>Fecha_Ocupacion = vacío<br/>Fecha_Armado = hoy<br/>Armador = trabajador<br/>Estado_Detalle = 'ARM completado'"]
        end
    end

    READY --> INICIAR_ARM
    READY --> FINALIZAR_ARM

    style BLOCK_MAT fill:#BE123C,color:#fff
    style BLOCK_ROL fill:#BE123C,color:#fff
    style I1_ERR fill:#BE123C,color:#fff
    style I2_ERR fill:#BE123C,color:#fff
    style CANCEL fill:#475569,color:#fff
    style COMPLETAR_ARM fill:#0D9488,color:#fff
    style PAUSAR_ARM fill:#D97706,color:#fff
```

### Máquina de Estados ARM

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE
    PENDIENTE --> EN_PROGRESO: INICIAR [Materiales + Sin armador]
    EN_PROGRESO --> PAUSADO: PAUSAR
    EN_PROGRESO --> COMPLETADO: COMPLETAR [todas las uniones]
    EN_PROGRESO --> PENDIENTE: CANCELAR
    PAUSADO --> EN_PROGRESO: REANUDAR
    PAUSADO --> PENDIENTE: CANCELAR
    COMPLETADO --> [*]

    note right of PENDIENTE
        Armador = null
        Condición: Fecha_Materiales debe existir
    end note

    note right of EN_PROGRESO
        Armador = MR(93)
        Ocupado_Por = MR(93)
    end note

    note right of COMPLETADO
        Fecha_Armado = 02-03-2026
        Desbloquea SOLD
    end note
```

---

## 4. Flujo Completo: SOLDADURA (SOLD)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph PREREQ_SOLD["🔒 PREREQUISITOS SOLD"]
        ARM_OK{"¿ARM completado?<br/>(Fecha_Armado ≠ null<br/>o Uniones_ARM ≥ 1)"}
        ARM_OK -->|"No"| BLOCK_ARM["❌ DependenciasNoSatisfechasError<br/>'ARM debe completarse primero'"]
        ARM_OK -->|"Sí"| MAT2{"¿Fecha_Materiales?"}
        MAT2 -->|"No"| BLOCK_MAT2["❌ DependenciasNoSatisfechasError"]
        MAT2 -->|"Sí"| ROLE2{"¿Rol Soldador<br/>o Ayudante?"}
        ROLE2 -->|"No"| BLOCK_ROL2["❌ RolNoAutorizadoError"]
        ROLE2 -->|"Sí"| READY2["✅ Puede operar"]
    end

    subgraph INICIAR_SOLD["🟢 INICIAR SOLD"]
        IS1{"¿Soldador asignado?"}
        IS1 -->|"Sí"| IS_ERR["❌ OperacionYaIniciadaError"]
        IS1 -->|"No"| IS2["📝 ESCRIBE<br/>─────────────────<br/>Ocupado_Por = trabajador<br/>Fecha_Ocupacion = ahora<br/>Estado_Detalle = 'trabajando SOLD'"]
    end

    subgraph FINALIZAR_SOLD["🟠 FINALIZAR SOLD"]
        FS1["Seleccionar uniones<br/>(solo tipos: BW, BR, SO, FILL, LET)<br/>⚠️ Excluye FW (ARM-only)"]
        FS1 --> FS2{"¿Cuántas?"}
        FS2 -->|"0"| FS_CANCEL["CANCELADO"]
        FS2 -->|"< total"| FS_PAUSAR["⏸️ PAUSAR<br/>─────────────────<br/>SOL_WORKER + SOL_FECHA_INICIO/FIN<br/>Estado = 'SOLD parcial (pausado)'"]
        FS2 -->|"= total"| FS_COMPLETAR

        subgraph FS_COMPLETAR["✅ COMPLETAR SOLD"]
            FSC1["📝 Por cada unión<br/>─────────────────<br/>SOL_WORKER = trabajador<br/>SOL_FECHA_INICIO<br/>SOL_FECHA_FIN"]
            FSC1 --> FSC2["📝 Operaciones<br/>─────────────────<br/>Fecha_Soldadura = hoy<br/>Soldador = trabajador"]
            FSC2 --> FSC3{"¿TODAS las uniones<br/>ARM+SOLD completas?"}
            FSC3 -->|"Sí"| FSC4["🔔 AUTO-TRIGGER:<br/>METROLOGIA_AUTO_TRIGGERED<br/>Spool entra a cola de inspección"]
            FSC3 -->|"No"| FSC5["Sin trigger automático"]
        end
    end

    READY2 --> INICIAR_SOLD
    READY2 --> FINALIZAR_SOLD

    style BLOCK_ARM fill:#BE123C,color:#fff
    style BLOCK_MAT2 fill:#BE123C,color:#fff
    style BLOCK_ROL2 fill:#BE123C,color:#fff
    style IS_ERR fill:#BE123C,color:#fff
    style FSC4 fill:#0891B2,color:#fff
```

### Máquina de Estados SOLD

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE
    PENDIENTE --> EN_PROGRESO: INICIAR [ARM completado + Materiales]
    EN_PROGRESO --> PAUSADO: PAUSAR
    EN_PROGRESO --> COMPLETADO: COMPLETAR
    EN_PROGRESO --> PENDIENTE: CANCELAR
    PAUSADO --> EN_PROGRESO: REANUDAR
    PAUSADO --> PENDIENTE: CANCELAR
    COMPLETADO --> [*]

    note right of PENDIENTE
        Soldador = null
        Requiere: ARM completado
    end note

    note right of COMPLETADO
        Fecha_Soldadura = fecha
        Si todas uniones listas → trigger Metrología
    end note
```

---

## 5. Flujo Completo: METROLOGÍA

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph PREREQ_MET["🔒 PREREQUISITOS METROLOGÍA"]
        MET1{"¿ARM completado?<br/>(Fecha_Armado ≠ null)"}
        MET1 -->|"No"| MET_B1["❌ DependenciasNoSatisfechasError"]
        MET1 -->|"Sí"| MET2{"¿SOLD completado?<br/>(Fecha_Soldadura ≠ null)"}
        MET2 -->|"No"| MET_B2["❌ DependenciasNoSatisfechasError"]
        MET2 -->|"Sí"| MET3{"¿Ya fue aprobado?<br/>(Fecha_QC ≠ null)"}
        MET3 -->|"Sí"| MET_B3["❌ OperacionYaCompletadaError"]
        MET3 -->|"No"| MET4{"¿Estado contiene<br/>RECHAZADO o BLOQUEADO?"}
        MET4 -->|"Sí"| MET_B4["❌ OperacionYaCompletadaError<br/>(en ciclo de reparación)"]
        MET4 -->|"No"| MET5{"¿Spool ocupado?"}
        MET5 -->|"Sí"| MET_B5["❌ SpoolOccupiedError"]
        MET5 -->|"No"| MET6{"¿Rol Metrologia?"}
        MET6 -->|"No"| MET_B6["❌ RolNoAutorizadoError"]
        MET6 -->|"Sí"| MET_READY["✅ Puede inspeccionar"]
    end

    subgraph INSPECCION["🔍 INSPECCIÓN INSTANTÁNEA (sin TOMAR)"]
        MET_READY --> DECISION{"¿Resultado?"}
        DECISION -->|"APROBADO"| APROBADO
        DECISION -->|"RECHAZADO"| RECHAZADO

        subgraph APROBADO["✅ APROBADO"]
            A1["📝 ESCRIBE<br/>─────────────────<br/>Fecha_QC_Metrología = hoy<br/>Estado_Detalle = 'APROBADO ✓'"]
            A1 --> A2["🏁 SPOOL TERMINADO<br/>Ciclo productivo completo"]
        end

        subgraph RECHAZADO["❌ RECHAZADO"]
            R1["Extraer ciclo actual<br/>de Estado_Detalle"]
            R1 --> R2{"¿Ciclo + 1 ≥ 3?"}
            R2 -->|"Sí"| R3["🚫 BLOQUEADO<br/>Estado: 'BLOQUEADO - Contactar supervisor'<br/>No se puede reparar más"]
            R2 -->|"No"| R4["📝 Estado_Detalle =<br/>'RECHAZADO (Ciclo N/3)<br/>- Pendiente reparación'"]
            R4 --> R5["➡️ Entra a cola de REPARACIÓN"]
        end
    end

    style MET_B1 fill:#BE123C,color:#fff
    style MET_B2 fill:#BE123C,color:#fff
    style MET_B3 fill:#BE123C,color:#fff
    style MET_B4 fill:#BE123C,color:#fff
    style MET_B5 fill:#BE123C,color:#fff
    style MET_B6 fill:#BE123C,color:#fff
    style APROBADO fill:#0D9488,color:#fff
    style RECHAZADO fill:#BE123C,color:#fff
    style R3 fill:#881337,color:#fff
```

### Máquina de Estados Metrología

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE
    PENDIENTE --> APROBADO: aprobar [ARM+SOLD completos, libre]
    PENDIENTE --> RECHAZADO: rechazar [mismas condiciones]
    APROBADO --> [*]: Spool terminado ✓
    RECHAZADO --> [*]: Entra a cola Reparación

    note right of RECHAZADO
        Ciclo se incrementa
        Si ciclo ≥ 3 → BLOQUEADO
    end note
```

---

## 6. Flujo Completo: REPARACIÓN (Ciclos Acotados)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph PREREQ_REP["🔒 PREREQUISITOS REPARACIÓN"]
        REP1{"¿Estado contiene<br/>BLOQUEADO?"}
        REP1 -->|"Sí"| REP_B1["🚫 SpoolBloqueadoError<br/>3 rechazos consecutivos<br/>Contactar supervisor"]
        REP1 -->|"No"| REP2{"¿Estado contiene<br/>RECHAZADO o<br/>REPARACION_PAUSADA?"}
        REP2 -->|"No"| REP_B2["❌ OperacionNoDisponibleError"]
        REP2 -->|"Sí"| REP3{"¿Spool ocupado?"}
        REP3 -->|"Sí"| REP_B3["❌ SpoolOccupiedError"]
        REP3 -->|"No"| REP_READY["✅ Puede reparar<br/>(cualquier rol activo)"]
    end

    subgraph CICLO_REP["🔄 CICLO DE REPARACIÓN"]
        TOMAR["🟢 TOMAR<br/>─────────────────<br/>Ocupado_Por = trabajador<br/>Estado = 'EN_REPARACION (N/3)'"]
        TOMAR --> WORKING{"Trabajando..."}

        WORKING -->|"Pausar"| PAUSAR_REP["⏸️ PAUSAR<br/>─────────────────<br/>Limpia Ocupado_Por<br/>Estado = 'REPARACION_PAUSADA'"]
        WORKING -->|"Completar"| COMPLETAR_REP["✅ COMPLETAR<br/>─────────────────<br/>Limpia Ocupado_Por<br/>Limpia Fecha_QC_Metrología<br/>Estado = 'PENDIENTE_METROLOGIA'"]
        WORKING -->|"Cancelar"| CANCELAR_REP["↩️ CANCELAR<br/>─────────────────<br/>Limpia Ocupado_Por<br/>Restaura 'RECHAZADO (N/3)'"]

        PAUSAR_REP -->|"Retomar"| TOMAR
        CANCELAR_REP -->|"Retomar"| TOMAR
        COMPLETAR_REP --> REINSPECCION["🔍 Vuelve a cola METROLOGÍA<br/>para re-inspección"]
    end

    REP_READY --> TOMAR

    subgraph REINSPECCION_FLOW["🔄 RE-INSPECCIÓN"]
        REINSPECCION --> MET_AGAIN{"¿Resultado<br/>metrología?"}
        MET_AGAIN -->|"APROBADO"| FINAL_OK["✅ APROBADO<br/>Fecha_QC = hoy<br/>Ciclo productivo completo"]
        MET_AGAIN -->|"RECHAZADO"| CICLO_CHECK{"¿Nuevo ciclo ≥ 3?"}
        CICLO_CHECK -->|"Sí"| BLOQUEADO["🚫 BLOQUEADO<br/>Contactar supervisor"]
        CICLO_CHECK -->|"No"| NUEVO_CICLO["Ciclo N+1/3<br/>Vuelve a cola reparación"]
    end

    style REP_B1 fill:#881337,color:#fff
    style REP_B2 fill:#BE123C,color:#fff
    style REP_B3 fill:#BE123C,color:#fff
    style BLOQUEADO fill:#881337,color:#fff
    style FINAL_OK fill:#0D9488,color:#fff
    style COMPLETAR_REP fill:#0D9488,color:#fff
```

### Máquina de Estados Reparación

```mermaid
stateDiagram-v2
    [*] --> RECHAZADO: Metrología rechaza
    RECHAZADO --> EN_REPARACION: TOMAR [No BLOQUEADO, libre]
    REPARACION_PAUSADA --> EN_REPARACION: TOMAR (retomar)
    EN_REPARACION --> REPARACION_PAUSADA: PAUSAR
    EN_REPARACION --> PENDIENTE_METROLOGIA: COMPLETAR
    EN_REPARACION --> RECHAZADO: CANCELAR
    REPARACION_PAUSADA --> RECHAZADO: CANCELAR
    PENDIENTE_METROLOGIA --> [*]: Re-inspección

    note right of RECHAZADO
        Ciclo N/3 embebido en Estado_Detalle
        Si N ≥ 3 → BLOQUEADO (no se puede TOMAR)
    end note

    note right of PENDIENTE_METROLOGIA
        Limpia Fecha_QC_Metrología
        para forzar re-inspección
    end note
```

---

## 7. Pipeline Completo: Ciclo de Vida de un Spool

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart LR
    subgraph MATERIALES["📦 MATERIALES"]
        M1["Fecha_Materiales<br/>(prerequisito externo)"]
    end

    subgraph ARM_PHASE["🔧 ARMADO"]
        ARM_P["PENDIENTE"] -->|"INICIAR"| ARM_E["EN PROGRESO"]
        ARM_E -->|"FINALIZAR<br/>(todas uniones)"| ARM_C["COMPLETADO"]
        ARM_E -.->|"PAUSAR"| ARM_PA["PAUSADO"]
        ARM_PA -.->|"REANUDAR"| ARM_E
    end

    subgraph SOLD_PHASE["🔥 SOLDADURA"]
        SOLD_P["PENDIENTE"] -->|"INICIAR"| SOLD_E["EN PROGRESO"]
        SOLD_E -->|"FINALIZAR<br/>(todas uniones)"| SOLD_C["COMPLETADO"]
        SOLD_E -.->|"PAUSAR"| SOLD_PA["PAUSADO"]
        SOLD_PA -.->|"REANUDAR"| SOLD_E
    end

    subgraph MET_PHASE["🔍 METROLOGÍA"]
        MET_P["PENDIENTE"] -->|"APROBADO"| MET_A["✅ APROBADO"]
        MET_P -->|"RECHAZADO"| MET_R["❌ RECHAZADO"]
    end

    subgraph REP_PHASE["🔄 REPARACIÓN"]
        REP_E["EN REPARACIÓN"] -->|"COMPLETAR"| REP_PM["PENDIENTE<br/>METROLOGÍA"]
        MET_R -->|"TOMAR"| REP_E
        REP_PM -->|"Re-inspección"| MET_P
        MET_R -->|"Ciclo ≥ 3"| BLOQ["🚫 BLOQUEADO"]
    end

    M1 -->|"Desbloquea"| ARM_P
    ARM_C -->|"Desbloquea"| SOLD_P
    SOLD_C -->|"Auto-trigger<br/>si todas uniones listas"| MET_P

    style M1 fill:#475569,color:#fff
    style ARM_C fill:#0D9488,color:#fff
    style SOLD_C fill:#0D9488,color:#fff
    style MET_A fill:#0D9488,color:#fff
    style MET_R fill:#BE123C,color:#fff
    style BLOQ fill:#881337,color:#fff
```

---

## 8. Datos Capturados por Operación

### Tabla Resumen: ¿Qué se escribe y cuándo?

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph INICIAR["🟢 INICIAR (P5 Confirmation)"]
        I_OP["Operaciones<br/>─────────────────<br/>Ocupado_Por = 'MR(93)'<br/>Fecha_Ocupacion = datetime<br/>Estado_Detalle = builder"]
        I_META["Metadata<br/>─────────────────<br/>INICIAR_SPOOL<br/>worker_id, operacion"]
        I_UNION["Uniones<br/>─────────────────<br/>(nada - sin selección)"]
    end

    subgraph FINALIZAR_COMPLETAR["✅ FINALIZAR → COMPLETAR"]
        FC_UNION["Uniones (por cada seleccionada)<br/>─────────────────<br/>ARM/SOL_WORKER = 'MR(93)'<br/>ARM/SOL_FECHA_INICIO = Fecha_Ocupacion<br/>ARM/SOL_FECHA_FIN = now()"]
        FC_OP["Operaciones<br/>─────────────────<br/>Ocupado_Por = vacío<br/>Fecha_Ocupacion = vacío<br/>Fecha_Armado/Soldadura = hoy<br/>Armador/Soldador = worker<br/>Estado_Detalle = 'completado'"]
        FC_META["Metadata<br/>─────────────────<br/>FINALIZAR_SPOOL<br/>unions_processed, pulgadas"]
    end

    subgraph FINALIZAR_PAUSAR["⏸️ FINALIZAR → PAUSAR"]
        FP_UNION["Uniones (solo seleccionadas)<br/>─────────────────<br/>ARM/SOL_WORKER<br/>ARM/SOL_FECHA_INICIO<br/>ARM/SOL_FECHA_FIN"]
        FP_OP["Operaciones<br/>─────────────────<br/>Ocupado_Por = vacío<br/>Fecha_Ocupacion = vacío<br/>Estado_Detalle = 'parcial (pausado)'<br/>⚠️ NO escribe Fecha_Armado"]
    end

    subgraph METROLOGIA_WRITE["🔍 METROLOGÍA"]
        MW_AP["Si APROBADO<br/>─────────────────<br/>Fecha_QC_Metrología = hoy<br/>Estado = 'APROBADO ✓'"]
        MW_RE["Si RECHAZADO<br/>─────────────────<br/>Estado = 'RECHAZADO (Ciclo N/3)'<br/>⚠️ NO escribe Fecha_QC"]
    end

    subgraph REP_WRITE["🔄 REPARACIÓN COMPLETAR"]
        RW1["Operaciones<br/>─────────────────<br/>Ocupado_Por = vacío<br/>Fecha_Ocupacion = vacío<br/>Fecha_QC_Metrología = vacío ⚠️<br/>Estado = 'PENDIENTE_METROLOGIA'"]
        RW2["⚠️ Limpiar Fecha_QC es CRÍTICO<br/>para forzar re-inspección"]
    end
```

---

## 9. Tipos de Uniones y Elegibilidad

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart LR
    subgraph TIPOS["TIPOS DE UNIÓN"]
        BW["BW - Butt Weld"]
        BR["BR - Branch"]
        SO["SO - Socket"]
        FILL["FILL - Fillet"]
        LET["LET - Let"]
        FW["FW - Field Weld"]
    end

    subgraph SOLD_REQ["Requieren SOLD"]
        BW2["BW ✅"]
        BR2["BR ✅"]
        SO2["SO ✅"]
        FILL2["FILL ✅"]
        LET2["LET ✅"]
    end

    subgraph ARM_ONLY["Solo ARM"]
        FW2["FW ⚙️<br/>(ARM-only, sin soldadura)"]
    end

    BW --> BW2
    BR --> BR2
    SO --> SO2
    FILL --> FILL2
    LET --> LET2
    FW --> FW2

    subgraph METROLOGIA_TRIGGER["🔔 Auto-trigger Metrología"]
        TRIGGER["Se activa cuando:<br/>✅ TODOS los FW tienen ARM_FECHA_FIN<br/>✅ TODOS los BW/BR/SO/FILL/LET<br/>tienen SOL_FECHA_FIN"]
    end

    BW2 --> TRIGGER
    BR2 --> TRIGGER
    SO2 --> TRIGGER
    FILL2 --> TRIGGER
    LET2 --> TRIGGER
    FW2 --> TRIGGER
```

---

## 10. Filtrado de Spools en P4

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph FILTROS["🔎 ¿Qué spools ve el trabajador en P4?"]
        F_INICIAR["INICIAR ARM/SOLD<br/>─────────────────<br/>Ocupado_Por = vacío<br/>Filtro client-side post-fetch<br/>API: GET /api/spools/iniciar"]

        F_FINALIZAR["FINALIZAR ARM/SOLD<br/>─────────────────<br/>Ocupado_Por contiene (worker_id)<br/>API: GET /api/spools/ocupados"]

        F_METRO["INSPECCIÓN (MET)<br/>─────────────────<br/>ARM + SOLD completados<br/>Fecha_QC vacía<br/>No RECHAZADO/BLOQUEADO<br/>API: GET /api/spools/iniciar?op=MET"]

        F_INICIAR_REP["INICIAR REPARACIÓN<br/>─────────────────<br/>Estado: RECHAZADO o PAUSADA<br/>No BLOQUEADO<br/>Ocupado_Por = vacío<br/>API: GET /api/spools/iniciar?op=REP"]

        F_FINALIZAR_REP["FINALIZAR REPARACIÓN<br/>─────────────────<br/>Spools ocupados por trabajador<br/>API: GET /api/spools/ocupados"]
    end
```

---

## 11. Modelo de Datos: Relación Spool ↔ Uniones

```mermaid
erDiagram
    OPERACIONES ||--o{ UNIONES : "OT (1:N)"
    OPERACIONES ||--o{ METADATA : "TAG_SPOOL"
    TRABAJADORES ||--o{ ROLES : "Id"

    OPERACIONES {
        string TAG_SPOOL PK "Identificador único"
        string OT FK "Orden de Trabajo"
        string NV "Nota de Venta"
        date Fecha_Materiales "Prerequisito ARM"
        date Fecha_Armado "ARM completado"
        string Armador "Worker ARM"
        date Fecha_Soldadura "SOLD completado"
        string Soldador "Worker SOLD"
        date Fecha_QC_Metrologia "Metrología aprobada"
        string Ocupado_Por "Worker actual"
        datetime Fecha_Ocupacion "Inicio ocupación"
        string Estado_Detalle "Estado legible"
        int Total_Uniones "Formula auto"
        int Uniones_ARM "Formula auto"
        int Uniones_SOLD "Formula auto"
        float Pulgadas_ARM "Formula auto"
        float Pulgadas_SOLD "Formula auto"
    }

    UNIONES {
        string ID "OT+N_UNION (compuesto)"
        string OT FK "Orden de Trabajo"
        int N_UNION "Número de unión"
        string TAG_SPOOL FK "Spool (legacy)"
        float DN_UNION "Diámetro (pulgadas)"
        string TIPO_UNION "BW/BR/SO/FILL/LET/FW"
        datetime ARM_FECHA_INICIO "Inicio armado"
        datetime ARM_FECHA_FIN "Fin armado"
        string ARM_WORKER "Armador"
        datetime SOL_FECHA_INICIO "Inicio soldadura"
        datetime SOL_FECHA_FIN "Fin soldadura"
        string SOL_WORKER "Soldador"
    }

    METADATA {
        uuid ID PK "Evento único"
        datetime Timestamp "Chile timezone"
        string Evento_Tipo "INICIAR/FINALIZAR/etc"
        string TAG_SPOOL FK
        int Worker_ID FK
        string Operacion "ARM/SOLD/MET/REP"
        string Accion "INICIAR/COMPLETAR/etc"
        json Metadata_JSON "Contexto adicional"
        int N_UNION "Unión específica (opcional)"
    }

    TRABAJADORES {
        int Id PK
        string Nombre
        string Apellido
        bool Activo
    }

    ROLES {
        int Id FK "Worker ID"
        string Rol "Armador/Soldador/etc"
        bool Activo
    }
```

---

## 12. Roles y Permisos

| Operación | Roles Permitidos | Notas |
|---|---|---|
| **ARM** (INICIAR/FINALIZAR) | Armador, Ayudante | Ayudante puede armar |
| **SOLD** (INICIAR/FINALIZAR) | Soldador, Ayudante | Ayudante puede soldar |
| **METROLOGÍA** (Inspección) | Metrologia | Solo inspectores certificados |
| **REPARACIÓN** (INICIAR/FINALIZAR) | Cualquier trabajador activo | Sin restricción de rol |

---

## 13. Condiciones de Error

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart TD
    subgraph ERRORES["⚠️ MAPA DE ERRORES"]
        E404["404 - No Encontrado<br/>─────────────────<br/>SpoolNoEncontradoError<br/>WorkerNoEncontradoError"]
        E400["400 - Validación<br/>─────────────────<br/>DependenciasNoSatisfechasError<br/>OperacionYaIniciadaError<br/>OperacionYaCompletadaError<br/>OperacionNoIniciadaError<br/>OperacionNoDisponibleError<br/>InvalidStateTransitionError"]
        E403["403 - No Autorizado<br/>─────────────────<br/>NoAutorizadoError<br/>RolNoAutorizadoError<br/>SpoolBloqueadoError (≥3)<br/>ArmPrerequisiteError"]
        E409["409 - Conflicto<br/>─────────────────<br/>SpoolOccupiedError<br/>VersionConflictError"]
        E503["503 - Servicio<br/>─────────────────<br/>SheetsConnectionError<br/>SheetsRateLimitError"]
    end

    style E404 fill:#FF6B35,color:#fff
    style E400 fill:#D97706,color:#fff
    style E403 fill:#BE123C,color:#fff
    style E409 fill:#4338CA,color:#fff
    style E503 fill:#475569,color:#fff
```

---

## 14. Pulgadas-Diámetro: Métrica de Negocio

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#DBEAFE','primaryBorderColor':'#3B82F6','primaryTextColor':'#1E293B','secondaryColor':'#E0E7FF','tertiaryColor':'#F0F9FF','lineColor':'#475569','clusterBkg':'#F1F5F9','clusterBorder':'#94A3B8','nodeBorder':'#3B82F6','mainBkg':'#DBEAFE','edgeLabelBackground':'#F8FAFC'}}}%%
flowchart LR
    UNION1["Unión 1<br/>DN_UNION = 4.0\""]
    UNION2["Unión 2<br/>DN_UNION = 6.0\""]
    UNION3["Unión 3<br/>DN_UNION = 2.5\""]

    UNION1 --> SUM["Σ Pulgadas<br/>= 12.5\""]
    UNION2 --> SUM
    UNION3 --> SUM

    SUM --> DISPLAY["Mostrado en<br/>─────────────────<br/>P4b (selección uniones)<br/>P5 (confirmación)<br/>P6 (éxito)<br/>Metadata (audit)"]

    NOTE["La métrica pulgadas-diámetro<br/>es la suma de DN_UNION de las<br/>uniones seleccionadas/completadas.<br/>Es el KPI principal de productividad."]

    style SUM fill:#FF6B35,color:#fff
    style DISPLAY fill:#0369A1,color:#fff
    style NOTE fill:#001F3F,color:#fff
```

---

## 15. Resumen Visual: ¿Qué Pantalla Llama a Qué API?

| Pantalla | API Call | Método | Cuándo |
|---|---|---|---|
| **P1** | `GET /api/workers` | getWorkers() | Al montar (cachea en context) |
| **P3** | `GET /api/v4/uniones/{tag}/metricas` | getUnionMetricas() | Detección de versión v3.0/v4.0 |
| **P4** | `GET /api/spools/iniciar?op=X` | getSpoolsDisponible() | INICIAR, Metrología |
| **P4** | `GET /api/spools/ocupados?op=X&worker_id=Y` | getSpoolsOcupados() | FINALIZAR |
| **P4** | `POST /api/v4/occupation/iniciar` | iniciarSpool() | INICIAR spool único (inline) |
| **P4b Uniones** | `GET /api/v4/uniones/{tag}/disponibles?op=X` | getDisponiblesUnions() | FINALIZAR v4.0 |
| **P4b Metro** | `POST /api/metrologia/completar` | completarMetrologia() | APROBADO/RECHAZADO |
| **P5** | `POST /api/v4/occupation/iniciar` | iniciarSpool() | Confirmar INICIAR |
| **P5** | `POST /api/v4/occupation/finalizar` | finalizarSpool() | Confirmar FINALIZAR ARM/SOLD |
| **P5** | `POST /api/v4/occupation/iniciar` | iniciarSpool() | Confirmar INICIAR REP |
| **P5** | `POST /api/v4/occupation/finalizar` | finalizarSpool() | Confirmar FINALIZAR REP |
