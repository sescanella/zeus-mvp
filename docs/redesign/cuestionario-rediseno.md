# Cuestionario — Rediseño ZEUES

**Para quién:** Sección A → el administrador de la planilla (oficina). Sección B → el coordinador de terreno (tablet).
**Tiempo estimado:** 15 minutos por persona, conversado.
**Cómo usarlo:** las preguntas con alternativas se marcan con una X; las abiertas se anotan tal cual las diga la persona. No hay respuestas correctas — queremos entender cómo trabajan de verdad.

---

## Sección A — Administrador de la planilla

### Bloque 1 · Cuando cargas spools nuevos

**A1.** Cuando cargas spools nuevos a la planilla, ¿cómo lo haces normalmente?

- [ ] De a uno, a medida que van llegando
- [ ] En lotes (por ejemplo, toda una NV u OT de una vez)
- [ ] De las dos formas, depende

**A2.** Cuando cargas spools nuevos, ¿ya se sabe cuáles hay que fabricar primero?

- [ ] Sí, yo sé el orden / la urgencia cuando los cargo
- [ ] No, eso lo decide el coordinador en terreno según lo que tenga disponible
- [ ] Lo conversamos entre los dos

**A3.** Hoy, después de que cargas un spool, el coordinador tiene que buscarlo y agregarlo a la app a mano. ¿Qué preferirías?

- [ ] Que todo spool que yo cargo aparezca solo en la app, sin que nadie lo busque
- [ ] Que el coordinador siga eligiendo cuáles ingresar (su lista es su plan de trabajo)
- [ ] Un aviso en la app de "hay N spools nuevos" y que el coordinador los agregue con un toque
- [ ] Me da lo mismo, eso es tema de terreno

**A4.** Cuando cargas un spool, ¿qué tan rápido necesita estar disponible para que terreno empiece a trabajarlo?

- [ ] Al instante (a veces cargo algo que se fabrica de inmediato)
- [ ] Dentro de la misma hora
- [ ] El mismo día está bien
- [ ] Da igual, siempre pasa tiempo entre que se carga y se fabrica

### Bloque 2 · Cómo sigues el avance

**A5.** Cuando abres la planilla para ver cómo va la fabricación, ¿qué columnas o datos miras realmente? *(respuesta abierta — pedir que muestre en pantalla si se puede)*

**A6.** ¿Hay algún dato del avance que hoy te falte o que tengas que calcular a mano? *(respuesta abierta)*

**A7.** ¿Cada cuánto necesitas que el avance esté actualizado en la planilla?

- [ ] Casi al momento (la miro varias veces al día y necesito que esté al día)
- [ ] Cada una hora aprox.
- [ ] Una vez al día es suficiente (ej: para el informe de la mañana)

**A8.** ¿Usas la planilla para algo más que mirar el avance?

- [ ] Hago filtros o tablas dinámicas
- [ ] Saco informes para terceros (cliente, gerencia)
- [ ] Copio datos a otros archivos
- [ ] Solo la miro
- Otro: _______________

### Bloque 3 · Una propuesta que queremos validar contigo

> Hoy cargas spools y ves el avance **en la misma planilla**. Estamos evaluando separarla en dos:
> **(1)** una hoja donde TÚ cargas spools, igual que siempre, y
> **(2)** otra hoja de solo-lectura donde ves el avance — con la garantía de que lo que muestra **nunca está desactualizado ni mal calculado**.

**A9.** ¿Esa separación te complica en algo tu forma de trabajar? *(respuesta abierta — atención a fórmulas, referencias entre hojas u otros archivos que dependan de la planilla actual)*

**A10.** Hoy, ¿qué datos corriges a mano directamente en la planilla y con qué frecuencia? *(respuesta abierta — ejemplos: fechas, nombres de trabajadores, estados, medidas)*

### Bloque 4 · Cuando terreno se equivoca

**A11.** Cuando en terreno registran algo mal (un trabajador equivocado, uniones de más, una fecha mala), ¿cómo te enteras y cómo lo arreglas hoy? *(respuesta abierta)*

**A12.** Estamos pensando que esas correcciones se hagan **desde la app con tu usuario**, quedando registrado quién corrigió, cuándo y qué cosa. ¿Te acomoda ser tú quien corrige?

- [ ] Sí, me acomoda
- [ ] Sí, pero debería poder hacerlo otra persona también
- [ ] Prefiero seguir corrigiendo en la planilla directamente
- ¿Desde dónde lo harías? — [ ] Computador · [ ] Tablet · [ ] Celular

### Bloque 5 · Datos de uniones

> Ya está decidido que los datos de las uniones (cuántas, medida, tipo) los ingresa terreno — tú no tienes que cargar nada de eso.

**A13.** De la información de uniones que captura terreno, ¿qué te sirve **ver** en la planilla?

- [ ] Solo los totales por spool (ej: "8 de 10 uniones soldadas")
- [ ] El detalle de cada unión (medida, tipo, quién la hizo, cuándo)
- [ ] Las pulgadas-diámetro (para avance / pago / informes)
- [ ] Nada, no uso esa información
- Otro: _______________

---

## Sección B — Coordinador de terreno

**B1.** Hoy, cuando terminas de registrar el armado de un spool, la app te abre **de inmediato** la pantalla para iniciar la soldadura. ¿Eso te ayuda o te estorba?

- [ ] Me ayuda, casi siempre sigo con la soldadura al tiro
- [ ] Me estorba, casi nunca sigo de inmediato y tengo que cerrarla
- [ ] Prefiero que la app me lo **ofrezca** (un aviso con "¿iniciar soldadura?") y yo decido
- [ ] Me da igual

**B2.** Imagina que cada tarjeta de spool muestra directamente un botón grande con lo que sigue: "INICIAR ARMADO", "FINALIZAR SOLDADURA", "METROLOGÍA" — sin tener que entrar a elegir operación y acción. ¿Te serviría?

- [ ] Sí, mucho — sabría de un vistazo qué toca en cada spool
- [ ] Más o menos, igual me gusta confirmar paso a paso
- [ ] No, prefiero el flujo actual

**B3.** Cuando registras trabajo, ¿sueles registrar varias acciones seguidas del **mismo** trabajador?

- [ ] Sí, casi siempre (ej: el mismo armador hace varios spools seguidos)
- [ ] A veces
- [ ] No, voy alternando entre trabajadores
- *(Si sí/a veces):* ¿te serviría que la app te proponga al último trabajador usado para confirmarlo con un toque?  [ ] Sí · [ ] No

---

## Apéndice interno (no mostrar al entrevistado)

Qué decisión destraba cada pregunta. Referencias: OP-x = `informe-ux-terreno-v1.md` §3; 5IN-xx = issues Linear ZEUS-by-KM.

| Pregunta | Decisión que destraba |
|---|---|
| A1, A2 | OP-4: si los lotes vienen con orden conocido desde oficina, la bandeja automática es viable; si el orden lo pone terreno, gana la lista curada + badge |
| A3 | OP-4: preferencia directa del admin entre manual / automático / híbrido (la tercera opción ES el híbrido recomendado) |
| A4 | OP-4 y OP-7: define la frecuencia necesaria del sync planilla→app (hoy cache 60s + poller 30s; post-Fase 2 es configurable) |
| A5, A6 | 5IN-39 (export DB→hoja reporte): qué columnas debe tener la hoja reporte para que el admin no pierda nada |
| A7 | 5IN-39: frecuencia del job de export (cada N min vs diario) |
| A8 | 5IN-39: si hay fórmulas/informes colgando de la planilla actual, la hoja reporte debe conservar nombres/orden de columnas o se rompen |
| A9 | Valida el corazón de Fase 2 (v6 §5.2, hoja intake + hoja reporte). Si aparece un bloqueo duro aquí, hay que repensar la Fase 2 |
| A10 | 5IN-40 (sync intake→DB): qué ediciones manuales debe soportar el upsert de datos maestros, y cuáles son ediciones de *ejecución* que migran al flujo de corrección |
| A11 | OP-5 etapa 1: cómo se detectan errores hoy define qué deben decir los toasts/historial |
| A12 | OP-5 etapa 2 + 5IN-41/5IN-44: confirma quién tiene el rol corrector y desde qué dispositivo (afecta si la UI de corrección se diseña para desktop) |
| A13 | 5IN-39: nivel de detalle de uniones en la hoja reporte. Nota: la precarga de uniones desde oficina ya fue descartada — esta pregunta es solo sobre LECTURA |
| B1 | OP-6: chaining push vs oferta — decisión directa del usuario afectado |
| B2 | OP-1: valida la acción directa en la card antes de invertir en el rediseño |
| B3 | OP-2: valida worker sticky/recientes |

**Después de la entrevista:** volcar las respuestas a `informe-ux-terreno-v1.md` §7 y revisar si cambia la prioridad de las olas (§5) o el alcance de la Fase 2 del v6.
