# Configuración de Google Sheets - Guía para Administración

**Proyecto:** ZEUES - Sistema de Trazabilidad de Manufactura
**Fecha:** 7 de noviembre de 2025
**Audiencia:** Equipo de Administración

---

## 1. Convención de Nombres de Columnas

Para garantizar la correcta integración con el sistema, **todas las columnas del Google Sheets deben seguir esta convención**:

### Formato Estándar
```
Palabra_Principal_De_Columna
```

**Reglas:**
- **Espacios reemplazados por guión bajo** (`_`)
- **Cada palabra inicia con mayúscula** (PascalCase con underscores)
- Sin tildes ni caracteres especiales
- Sin espacios al inicio o final

### Ejemplos Correctos ✅
- `Fecha_Armado`
- `Trabajador_Armado`
- `Fecha_Soldado`
- `Estado_Armado`
- `Codigo_Spool`
- `Nombre_Proyecto`

### Ejemplos Incorrectos ❌
- `fecha armado` (minúsculas, con espacio)
- `Fecha armado` (con espacio)
- `fecha_armado` (minúsculas)
- `FECHA_ARMADO` (todo mayúsculas)
- `FechaArmado` (sin guión bajo)

---

## 2. Columnas Requeridas - Hoja "Operaciones"

### Columnas Obligatorias para el MVP

| Columna | Nombre Estandarizado | Tipo de Dato | Descripción |
|---------|---------------------|--------------|-------------|
| A | `Codigo_Spool` | Texto | Identificador único del spool |
| B | `Proyecto` | Texto | Nombre del proyecto |
| C | `Cliente` | Texto | Nombre del cliente (opcional) |
| G | `Estado_Armado` | Texto | Estado: "PENDIENTE", "EN_PROCESO", "COMPLETADO" |
| V | `Trabajador_Inicio_Armado` | Texto | Nombre del trabajador que inició |
| W | `Fecha_Inicio_Armado` | Fecha/Hora | Timestamp de inicio (formato: YYYY-MM-DD HH:MM:SS) |
| BA | `Trabajador_Fin_Armado` | Texto | Nombre del trabajador que completó |
| BB | `Fecha_Fin_Armado` | Fecha/Hora | Timestamp de finalización |
| BC | `Estado_Soldado` | Texto | Estado: "PENDIENTE", "EN_PROCESO", "COMPLETADO" |
| BD | `Trabajador_Inicio_Soldado` | Texto | Nombre del trabajador que inició |
| BE | `Fecha_Inicio_Soldado` | Fecha/Hora | Timestamp de inicio |

### Validación de Nombres
Antes de lanzar el sistema, **verificar que los nombres de columna en la fila 1 del Sheets coincidan exactamente** con los nombres estandarizados.

---

## 3. Creación de Hoja "Trabajadores"

### Instrucciones de Configuración

1. **Crear nueva pestaña** en el Google Sheets llamada: `Trabajadores`

2. **Estructura de columnas** (fila 1):

| Columna A | Columna B | Columna C | Columna D |
|-----------|-----------|-----------|-----------|
| `Id_Trabajador` | `Nombre_Completo` | `Rol` | `Activo` |

3. **Descripción de cada columna**:

   - **Id_Trabajador**: Identificador único (puede ser número correlativo: 1, 2, 3...)
   - **Nombre_Completo**: Nombre y apellido del trabajador (ej: "Juan Pérez")
   - **Rol**: Especialización del trabajador. Valores permitidos:
     - `ARMADOR` (solo realiza armado)
     - `SOLDADOR` (solo realiza soldado)
     - `AMBOS` (puede hacer ambas acciones)
   - **Activo**: Estado del trabajador. Valores permitidos:
     - `SI` (trabajador activo, aparece en el sistema)
     - `NO` (trabajador inactivo, no aparece en la app)

4. **Ejemplo de datos** (filas 2-5):

| Id_Trabajador | Nombre_Completo | Rol | Activo |
|---------------|----------------|-----|--------|
| 1 | Juan Pérez | ARMADOR | SI |
| 2 | María González | ARMADOR | SI |
| 3 | Carlos López | SOLDADOR | SI |
| 4 | Ana Martínez | SOLDADOR | SI |

### Consideraciones Importantes

- **Los trabajadores inactivos** (`Activo = NO`) no aparecerán en la interfaz de la tablet
- **El campo `Rol`** determina qué acciones puede registrar cada trabajador en la app
- Mantener nombres consistentes entre la hoja "Trabajadores" y las columnas de registro en "Operaciones"
- Se recomienda no eliminar trabajadores, solo marcarlos como `NO` en la columna Activo

---

## 4. Permisos del Google Sheets

### Configuración Requerida

1. **Compartir el Google Sheets** con la cuenta del Service Account:
   ```
   zeues-service@[proyecto-id].iam.gserviceaccount.com
   ```

2. **Nivel de permiso**: **Editor** (para que el sistema pueda leer y escribir)

3. **Verificar acceso**:
   - Click en "Compartir" (botón superior derecho)
   - Agregar el email del Service Account
   - Seleccionar rol "Editor"
   - Desmarcar "Notificar a las personas" si no desea enviar email

---

## 5. Lista de Verificación Pre-Lanzamiento

Antes de iniciar el sistema en producción, verificar:

- [ ] Todas las columnas de la hoja "Operaciones" tienen nombres estandarizados
- [ ] La hoja "Trabajadores" está creada con la estructura correcta
- [ ] Al menos 4 trabajadores están registrados y activos (2 armadores + 2 soldadores)
- [ ] El Service Account tiene permisos de Editor en el Sheets
- [ ] Los spools activos tienen `Estado_Armado = "PENDIENTE"` para comenzar
- [ ] El formato de fechas está configurado en el Sheets (YYYY-MM-DD HH:MM:SS)

---

## 6. Contacto y Soporte

Para dudas o problemas con la configuración del Google Sheets:
- Contactar al equipo técnico antes de modificar estructuras
- No eliminar columnas sin consultar
- Mantener un respaldo del Sheets antes de cambios masivos

---

**Última actualización:** 7 de noviembre de 2025
