# Diagrama de Flujo — Entrenamiento del Clasificador

## Flujo General

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USUARIO ESCRIBE PROBLEMA                    │
│                   "mi contraseña no funciona"                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POST /api/classify/                               │
│              classify(text) busca keywords                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
    ¿Score >= 1?          ¿Score >= 1?         ¿Score >= 1?
   "contraseña"           "teclado"            (otros)
    score=4               score=0              score=0
         │                     │                     │
         YES                   NO                    NO
         │                     │                     │
         ▼                     ▼                     ▼
   Incluir en            Ignorar           Ignorar
   top 3                                   
         │
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 RESPONSE /api/classify/                              │
│      {                                                               │
│        "suggestions": [                                             │
│          {                                                          │
│            "service_id": 3,                                         │
│            "service_name": "Reset de Contraseña",                   │
│            "score": 4                                               │
│          }                                                          │
│        ]                                                            │
│      }                                                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    USUARIO VE SUGERENCIA
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
    ACEPTA             RECHAZA             IGNORA Y ELIGE
    (Caso A)           (Caso B)              (Caso C)
```

---

## Caso A: ACEPTA LA SUGERENCIA

```
┌──────────────────────────────────────────────────────────────────┐
│  Usuario ve "Reset de Contraseña" y acepta la sugerencia         │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ POST /api/classify/feedback/         │
            │ {                                    │
            │   "problem_description": "...",      │
            │   "suggested_service": 3,            │
            │   "chosen_service": 3,               │
            │   "accepted": true                   │
            │ }                                    │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ Guardar ClassificationFeedback       │
            │ trained=False (pendiente)            │
            └──────────────────────────────────────┘
                                   │
                    (Espera 2am o manual train)
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ Celery: run_training()               │
            │ procesa feedback con trained=False   │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ _adjust_weights(feedback)            │
            │ if feedback.accepted == True:        │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ Para cada keyword que matcheó:       │
            │ "contraseña" in texto → TRUE        │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ Subir weight                         │
            │ "contraseña"                         │
            │ weight: 4 → 5 (MIN=1, MAX=10)       │
            │ save()                               │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ feedback.trained = True              │
            │ save()                               │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ RESULTADO:                           │
            │ Próxima vez que alguien escriba      │
            │ "contraseña" → score más ALTO       │
            │ para "Reset de Contraseña"          │
            └──────────────────────────────────────┘
```

---

## Caso B: RECHAZA LA SUGERENCIA

```
┌──────────────────────────────────────────────────────────────────┐
│  Usuario ve "Reset de Contraseña" pero necesita                  │
│  "Soporte de Impresora" → rechaza                                │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ POST /api/classify/feedback/         │
            │ {                                    │
            │   "problem_description": "...",      │
            │   "suggested_service": 3,            │
            │   "chosen_service": 6,               │
            │   "accepted": false                  │
            │ }                                    │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ Guardar ClassificationFeedback       │
            │ trained=False (pendiente)            │
            └──────────────────────────────────────┘
                                   │
                    (Espera 2am o manual train)
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ Celery: run_training()               │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ _adjust_weights(feedback)            │
            │ if feedback.accepted == False AND    │
            │    feedback.suggested_service != None│
            └──────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
   PENALIZAR             PENALIZAR              APRENDER
   SERVICIO MALO         SERVICIO MALO         SERVICIO BUENO
        │                          │                          │
        │              Keywords que              Palabras nuevas
        │              matchearon mal            del texto
        │                          │                          │
        ▼                          ▼                          ▼
   Service 3            Service 3                 Service 6
   "contraseña"         "password"              extract_candidates(texto)
   weight: 4 → 3        weight: 4 → 3           "impresora", "funciona"
   (penalizar)          (penalizar)             weight: 1 (nuevo)
        │                          │                          │
        │              if weight < 1:                         │
        │                 DELETE                             │
        │              else:                                 │
        │                 weight -= 1                         │
        │                 save()                              │
        │                          │                          │
        └──────────────────────────┴──────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ feedback.trained = True              │
            │ save()                               │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │ RESULTADO:                           │
            │ • "contraseña" debilitado para       │
            │   "Reset" (de 4 a 3)                 │
            │ • Nuevas palabras aprendidas para    │
            │   "Soporte de Impresora"             │
            │ • Próxima vez: mejor sugerencia      │
            └──────────────────────────────────────┘
```

---

## Caso C: SIN SUGERENCIA (Score = 0)

```
┌──────────────────────────────────────────────────────────────────┐
│  Usuario escribe algo sin keywords registrados                    │
│  "necesito un cable USB"                                          │
│  → No hay sugerencia (score < 1)                                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ POST /api/classify/                  │
            │ → Response: "suggestions": []        │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Usuario navega catálogo manualmente  │
            │ elige "Soporte de Teclado/Mouse"    │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ POST /api/classify/feedback/         │
            │ {                                    │
            │   "problem_description": "...",      │
            │   "suggested_service": null,         │
            │   "chosen_service": 5,               │
            │   "accepted": false                  │
            │ }                                    │
            │ (false porque no hubo sugerencia)   │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Guardar ClassificationFeedback       │
            │ trained=False                        │
            └──────────────────────────────────────┘
                               │
                    (Espera 2am o manual train)
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Celery: run_training()               │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ _adjust_weights(feedback)            │
            │ elif feedback.suggested_service      │
            │      is None:                        │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Extraer palabras nuevas              │
            │ extract_candidates(                  │
            │   "necesito un cable USB"            │
            │ )                                    │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Palabras encontradas:                │
            │ "necesito" (>3 chars, no stopword)   │
            │ "cable" (>3 chars, no stopword)      │
            │ "usb" (>3 chars, no stopword)        │
            │                                      │
            │ (filtrados: "un" = stopword)         │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Para cada palabra nueva:             │
            │ create ServiceKeyword(                │
            │   service=5,                         │
            │   keyword="cable",                   │
            │   weight=1                           │
            │ )                                    │
            │ create ServiceKeyword(                │
            │   service=5,                         │
            │   keyword="usb",                     │
            │   weight=1                           │
            │ )                                    │
            │ create ServiceKeyword(                │
            │   service=5,                         │
            │   keyword="necesito",                │
            │   weight=1                           │
            │ )                                    │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ feedback.trained = True              │
            │ save()                               │
            └──────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ RESULTADO:                           │
            │ Nuevos keywords para                 │
            │ "Soporte de Teclado/Mouse":          │
            │ • "cable" (weight=1)                 │
            │ • "usb" (weight=1)                   │
            │ • "necesito" (weight=1)              │
            │                                      │
            │ Próxima vez que alguien escriba      │
            │ "necesito cable" →                   │
            │ "Soporte Teclado/Mouse" se sugerirá  │
            └──────────────────────────────────────┘
```

---

## Ciclo Completo (3 Días)

```
┌────────────────────────────────────────────────────────────────────┐
│ DÍA 1                                                               │
│ Usuario 1: "contraseña no funciona"                                │
│ Sistema: sugiere "Reset de Contraseña" (score=4)                  │
│ Usuario: ACEPTA ✓                                                  │
│ → feedback guardado, trained=false                                 │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│ DÍA 2 (2am - Celery)                                               │
│ run_training():                                                    │
│   - Procesa feedback de Usuario 1                                  │
│   - "contraseña" weight: 4 → 5                                     │
│   - feedback.trained = true                                        │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│ DÍA 2 (luego)                                                      │
│ Usuario 2: "contraseña"                                            │
│ Sistema: sugiere "Reset de Contraseña" (score=5) ← MÁS FUERTE     │
│ Usuario: ACEPTA ✓                                                  │
│ → feedback guardado, trained=false                                 │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│ DÍA 3 (2am - Celery)                                               │
│ run_training():                                                    │
│   - Procesa feedback de Usuario 2                                  │
│   - "contraseña" weight: 5 → 6                                     │
│   - feedback.trained = true                                        │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│ DÍA 3 (luego)                                                      │
│ Usuario 3: "mi password"                                           │
│ Sistema: sugiere "Reset de Contraseña" (score=6+4=10) ← MÁXIMO    │
│ Usuario: ACEPTA ✓                                                  │
│                                                                    │
│ CONCLUSIÓN: El sistema aprende progresivamente                     │
│ Cada aceptación refuerza los keywords correctos                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Matriz de Decisión

| Caso | suggested_service | chosen_service | accepted | Acción |
|------|---|---|---|---|
| A | 3 | 3 | TRUE | Subir weight de keywords que matchearon en service 3 |
| B | 3 | 6 | FALSE | Bajar weight en service 3, crear nuevos en service 6 |
| C | NULL | 5 | FALSE | Crear nuevos keywords en service 5 |
| D | 3 | 3 | FALSE | ❌ INVÁLIDO (contradictorio) |
| E | NULL | NULL | TRUE | ❌ INVÁLIDO (sin servicio elegido) |

---

## Timeline de Entrenamiento

```
MANUAL: POST /api/classify/train/
↓
Ejecuta train_classifier.delay() inmediatamente
↓
Procesa todos los feedback con trained=False
↓
Marca como trained=True

AUTOMÁTICO (Celery Beat): 2:00 AM diario
↓
Ejecuta train_classifier() automáticamente
↓
Procesa todos los feedback pendientes
↓
Marca como trained=True
```

---

## Ver Progreso

```bash
GET /api/classify/stats/
{
  "total_feedback": 150,      # Todos los feedbacks dados
  "accepted": 120,             # Cuántos fueron aceptaciones
  "rejected": 30,              # Cuántos fueron rechazos
  "acceptance_rate": 80.0,     # % de aciertos del sistema
  "pending_training": 5        # Feedbacks sin procesar aún
}
```

Si `pending_training > 0` → hay trabajo pendiente para la próxima ejecución de Celery.
