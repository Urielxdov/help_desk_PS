# Help Desk ERP — Plan de Ejecución Técnica

> Sistema de Help Desk multi-tenant con clasificación automática por departamento,  
> balance de carga inteligente y pipeline de datos limpios orientado a ML.  
> Stack: Angular + Django REST Framework + PostgreSQL + Redis + Celery

---

## Índice

- [Visión general](#visión-general)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Estrategia de clasificación](#estrategia-de-clasificación)
- [Pipeline de datos limpios](#pipeline-de-datos-limpios)
- [Sprint 1 — Cimientos](#sprint-1--cimientos-semanas-1-2)
- [Sprint 2 — Core de tickets](#sprint-2--core-de-tickets-y-datos-limpios-semanas-3-4)
- [Sprint 3 — Asignación y clasificación](#sprint-3--asignación-automática-y-clasificación-semanas-5-6)
- [Sprint 4 — Dashboard y conocimiento](#sprint-4--dashboard-reportes-y-base-de-conocimiento-semanas-7-8)
- [Sprint 5 — Pulido y entrega](#sprint-5--pulido-pruebas-y-entrega-semanas-9-10)
- [Modelo de base de datos](#modelo-de-base-de-datos)
- [Roadmap post-MVP](#roadmap-post-mvp)
- [Reglas de arquitectura](#reglas-de-arquitectura)
- [Decisiones técnicas clave (ADRs)](#decisiones-técnicas-clave-adrs)

---

## Visión general

### Problema que resuelve

El sistema administra la carga de un Help Desk vinculado a un ERP empresarial. Permite:

- Recibir tickets de usuarios finales con descripción en lenguaje natural
- Clasificar automáticamente el ticket al departamento correcto usando keywords
- Asignar al agente con menor carga dentro del departamento
- Permitir que el HD Manager fije la fecha de compromiso
- Acumular datos limpios y etiquetados para entrenar modelos ML en fases futuras

### Fases del producto

```
Fase 1 (MVP · 10 semanas)
  └── HD operativo: tickets, asignación, balance de carga, SLA, clasificación por keywords

Fase 2 (Post-MVP)
  └── Clasificación con regresión logística entrenada con datos propios
  └── Reformulación de descripciones vía LLM (descripción limpia para el agente)
  └── Feedback loop: rating de respuestas → reentrenamiento del modelo

Fase 3 (Largo plazo)
  └── Descomposición de problemas complejos en árbol de tareas
  └── Asignación multi-agente por habilidad + carga
  └── Predicción de SLA basada en histórico
```

---

## Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | Angular 17+ | SPA con módulos por dominio |
| Backend | Django 4.2 + DRF 3.15 | Multi-tenant, maduro, ecosistema ML en Python |
| Multi-tenant | django-tenants | Schema por organización en PostgreSQL |
| Auth | SimpleJWT | JWT stateless, refresh token |
| Base de datos | PostgreSQL 16 | Schema isolation, pg_trgm para búsqueda |
| Caché / Cola | Redis 7 | Sesiones, Celery broker |
| Tareas async | Celery 5 + Celery Beat | WorkloadSnapshot, escalación SLA, emails |
| Clasificación v1 | scikit-learn (TF-IDF) | Sin entrenamiento previo, funciona con keywords |
| Contenedores | Docker + Docker Compose | Ambiente reproducible |
| CI/CD | GitHub Actions | Tests + deploy automático |
| Storage | S3 / MinIO | Adjuntos de tickets |
| Documentación API | drf-spectacular (OpenAPI) | Swagger automático |

---

## Arquitectura

### Patrón: DDD ligero en monorepo

Un solo repositorio Django organizado por dominios. Cada dominio es autónomo y se comunica con otros únicamente por eventos. Diseñado para extraer dominios a microservicios en el futuro sin reescritura.

```
helpdesk/
├── config/                        # Configuración central Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py                    # Router central /api/v1/
│   └── wsgi.py
│
├── shared/                        # Infraestructura transversal
│   ├── models.py                  # BaseModel, SoftDeleteModel, AuditModel
│   ├── permissions.py             # IsTenantAdmin, IsHDManager, IsAgent
│   ├── exceptions.py              # DomainException, NotFoundError, etc.
│   ├── middleware.py              # TenantMiddleware
│   ├── events.py                  # DomainEvent, publish_event()
│   ├── responses.py               # Formato de respuesta unificado
│   ├── pagination.py
│   ├── utils.py
│   └── mixins.py                  # TenantFilterMixin, AuditMixin
│
├── domains/
│   ├── tenants/                   # Registro de organizaciones
│   ├── users/                     # Usuarios, roles, departamentos
│   ├── tickets/                   # Ciclo de vida del ticket
│   ├── assignments/               # Asignación y balance de carga
│   └── classification/            # Clasificación por departamento ← NÚCLEO
│
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── docker-compose.yml
```

### Regla de dependencia entre dominios

```
tenants       → no depende de nadie
users         → depende de tenants
tickets       → depende de users
assignments   → depende de tickets + users
classification → depende de tickets + users (solo lee, nunca escribe en ellos)
```

> Comunicación entre dominios: únicamente por eventos (`shared/events.py`).  
> Nunca importar modelos de un dominio en otro directamente.

### Contenedores Docker

```
nginx          → Reverse proxy (puerto 80 público)
  ├── angular  → Frontend SPA (puerto interno 80)
  └── django   → API REST (puerto interno 8000)
celery         → Worker: tareas async
postgres       → Base de datos (schema por tenant)
redis          → Caché + broker de Celery
```

---

## Estrategia de clasificación

> Esta es la decisión técnica más importante del proyecto.  
> La clasificación es el núcleo del sistema y debe ser evolutiva sin romper nada.

### Interfaz única para las 3 capas

Todas las capas implementan la misma interfaz. Cambiar de capa no requiere tocar el resto del sistema.

```python
@dataclass
class ClassificationResult:
    department_id: str
    confidence: float              # 0.0 a 1.0
    method: str                    # 'keyword' | 'ml_v1' | 'ml_v2'
    suggested_keywords: list[str]
    requires_human_review: bool    # True si confidence < umbral configurable
```

### Capa 1 — Keywords + TF-IDF (Sprint 3 · disponible desde el día 1)

Compara el texto normalizado del ticket contra las keywords de cada departamento usando similitud coseno. No requiere datos históricos. Funciona desde el primer ticket.

```python
class KeywordClassificationStrategy:
    def classify(self, description: str) -> ClassificationResult:
        # TF-IDF sobre keywords de cada departamento
        # Similitud coseno → depto con mayor score
        # confidence < 0.4 → requires_human_review = True
```

### Capa 2 — Regresión logística (Fase 2 · cuando haya 500+ tickets etiquetados)

```python
# El dataset ya está listo gracias al pipeline de Fase 1
X = Ticket.objects.values_list('description_normalized', flat=True)
y = Ticket.objects.values_list('department_id', flat=True)
# Entrenar LogisticRegression con los datos propios del tenant
```

### Capa 3 — Transformer fine-tuned (Fase 3)

Modelo de lenguaje ajustado al dominio específico del cliente usando el histórico acumulado.

### Evaluación continua del modelo

Cada clasificación se registra en `ClassificationLog`. Cuando el agente acepta o corrige el departamento sugerido, `was_correct` se actualiza. La precisión del modelo es consultable en cualquier momento:

```sql
SELECT
    method,
    COUNT(*) as total,
    AVG(was_correct::int) as precision
FROM classification_classificationlog
GROUP BY method;
```

---

## Pipeline de datos limpios

> Los datos limpios desde el primer ticket son la base de todo el ML futuro.  
> Esta es la razón por la que el dominio `classification` existe desde Sprint 2.

### Al crear cada ticket

```
1. Guardar description original → NUNCA se modifica
2. Normalizar texto:
   - Convertir a minúsculas
   - Eliminar acentos y caracteres especiales
   - Eliminar stopwords en español
   - Lematizar tokens
   → Guardar en description_normalized
3. Clasificar usando la capa activa
   → Guardar department_id sugerido + confidence + method
4. Si confidence < umbral → requires_review = True
5. Registrar en ClassificationLog
6. Cuando agente confirma o corrige → actualizar was_correct
```

### Campos adicionales en `Ticket` para ML

```
description_normalized    text       Texto limpio para clasificación
classification_method     varchar    keyword | ml_v1 | ml_v2 | manual
classification_score      float      Confianza de la clasificación (0.0-1.0)
requires_review           bool       Agente debe confirmar el departamento
reviewed_by               uuid FK    Quién confirmó/corrigió
reviewed_at               timestamp
```

### Por qué keywords en Department son esenciales

Las `keywords` de cada departamento son el vocabulario de entrenamiento de Capa 1 y el corpus inicial de Capa 2. Deben mantenerse actualizadas por el HD Manager. Mientras más específicas y representativas, mejor la clasificación automática.

**Ejemplo:**

```
Departamento IT:
keywords = "servidor caído vpn red wifi impresora correo outlook
            windows error pantalla azul acceso sistema contraseña"

Departamento RRHH:
keywords = "nómina vacaciones permiso incapacidad contrato
            alta baja prestaciones seguro médico"
```

---

## Sprint 1 — Cimientos (Semanas 1-2)

**Objetivo:** Proyecto levantado, login funcional, CRUD de usuarios y departamentos.

### Tareas

#### Setup del proyecto

- [ ] Inicializar repositorio con estructura DDD (`config/`, `shared/`, `domains/`)
- [ ] Configurar `settings/base.py`, `development.py`, `production.py`
- [ ] Instalar y configurar `django-tenants` con schema por organización
- [ ] Implementar `shared/models.py` (`BaseModel`, `SoftDeleteModel`, `AuditModel`)
- [ ] Implementar `shared/exceptions.py` + handler global DRF
- [ ] Implementar `shared/permissions.py` (`IsTenantMember`, `IsHDManager`, etc.)
- [ ] Implementar `shared/middleware.py` (`TenantMiddleware` por subdominio y header)
- [ ] Implementar `shared/events.py` (`DomainEvent`, `publish_event`)
- [ ] Implementar `shared/responses.py` (formato de respuesta unificado)
- [ ] Docker Compose: nginx + django + postgres + redis + celery
- [ ] Variables de entorno en `.env.example`

#### Dominio `tenants`

- [ ] Modelos: `Tenant`, `TenantConfig`
- [ ] Endpoints: `POST /api/v1/tenants/`, `GET/PATCH /api/v1/tenants/{id}/`
- [ ] Tests: creación de tenant, schema aislado

#### Dominio `users`

- [ ] Modelos: `User`, `Position`, `Department` (con campo `keywords`), `UserProfile`
- [ ] Auth: `POST /api/v1/auth/login/`, `POST /api/v1/auth/refresh/`
- [ ] Endpoints usuarios: CRUD completo + soft delete
- [ ] Endpoints departamentos: CRUD + `GET /departments/{id}/agents/`
- [ ] Tests: login, creación de usuario, permisos por rol

### Entregable

```
✓ docker compose up --build → sistema corre
✓ POST /auth/login/ → devuelve JWT
✓ CRUD de usuarios y departamentos funcionando
✓ Aislamiento por tenant verificado
```

---

## Sprint 2 — Core de tickets y datos limpios (Semanas 3-4)

**Objetivo:** Tickets creables con datos normalizados desde el primer registro.

### Tareas

#### Dominio `tickets`

- [ ] Modelos: `Ticket` (con campos ML), `TicketDetail`, `TicketHistory`, `Comment`, `Attachment`, `TicketWatcher`
- [ ] Generador de `folio` automático (`HD-YYYY-NNNNN`)
- [ ] Cálculo automático de `sla_deadline` al crear (basado en `Department.sla_hours`)
- [ ] Workflow de estados: `open → in_progress → pending_user → resolved → closed`
- [ ] Endpoints: CRUD completo + comments + attachments + history + status + deadline
- [ ] Tests: ciclo de vida completo del ticket

#### Dominio `classification` (estructura base)

- [ ] `TextPipeline.normalize(text)`: normalización de texto en español
- [ ] Guardar `description_normalized` al crear cada ticket
- [ ] Implementar `ClassificationLog` model
- [ ] Stub de `ClassificationService` que devuelve `requires_human_review=True` (Capa 1 viene en Sprint 3)

#### Notificaciones

- [ ] Modelo `Notification` (`recipient`, `type`, `channel`, `payload`, `read_at`)
- [ ] Celery task: email al crear ticket (confirmación al usuario)
- [ ] Celery task: email al asignar ticket (aviso al agente)

### Entregable

```
✓ Tickets se crean con description + description_normalized
✓ Folio generado automáticamente
✓ SLA deadline calculado al crear
✓ Historial de cambios registrado en TicketHistory
✓ Email de confirmación enviado al crear ticket
```

---

## Sprint 3 — Asignación automática y clasificación (Semanas 5-6)

**Objetivo:** Tickets se asignan solos, clasificación por keywords funciona, SLA vigilado.

### Tareas

#### Dominio `assignments`

- [ ] Modelos: `Assignment` (con `method` e `is_current`), `WorkloadSnapshot`
- [ ] `LoadBalancer.get_agent(department)`: agente con menor `total_active`
- [ ] Celery Beat task: capturar `WorkloadSnapshot` cada 5 minutos
- [ ] Signal: al crear ticket → disparar asignación automática
- [ ] Endpoints: `POST /assignments/auto/`, `POST /assignments/manual/`, `PATCH /assignments/{id}/reassign/`, `GET /assignments/workload/`
- [ ] Tests: balance de carga con múltiples agentes

#### Dominio `classification` — Capa 1

- [ ] `KeywordClassificationStrategy`: TF-IDF sobre `Department.keywords`
- [ ] `ClassificationService.classify()`: devuelve `ClassificationResult`
- [ ] Umbral de confianza configurable por tenant (`TenantConfig`)
- [ ] Integrar clasificación al crear ticket: sugerir departamento + score
- [ ] UI Angular: mostrar departamento sugerido + score al agente para confirmar
- [ ] Al confirmar/corregir → actualizar `ClassificationLog.was_correct`
- [ ] Endpoint: `GET /classification/accuracy/` → precisión actual del modelo

#### Escalación automática por SLA

- [ ] Celery Beat task: cada hora revisar tickets con `sla_deadline` vencido
- [ ] Si vencido y no resuelto → cambiar estado a `escalated`
- [ ] Notificar al HD Manager con detalle del ticket
- [ ] Registrar escalación en `TicketHistory`

### Entregable

```
✓ Al crear ticket → clasificación sugiere departamento con score
✓ Al crear ticket → se asigna automáticamente al agente con menor carga
✓ WorkloadSnapshot se actualiza cada 5 minutos
✓ Tickets vencidos se escalan automáticamente al HD Manager
✓ ClassificationLog registra precisión del modelo
```

---

## Sprint 4 — Dashboard, reportes y base de conocimiento (Semanas 7-8)

**Objetivo:** Dashboard operativo, usuarios finales usando el sistema, datos de rating fluyendo.

### Tareas

#### Dashboard HD Manager (Angular)

- [ ] Carga actual por agente (desde `WorkloadSnapshot`)
- [ ] Tickets por estado en tiempo real (WebSocket o polling)
- [ ] % SLA cumplido por departamento
- [ ] Precisión de clasificación automática (`ClassificationLog`)
- [ ] Top 5 categorías de tickets por volumen
- [ ] Tiempo promedio de resolución por departamento

#### Base de conocimiento

- [ ] Modelos: `ServiceQuestion`, `TicketAnswer` (con `rating` y `approved_for_training`)
- [ ] `ServiceManual`: documentos por departamento
- [ ] Endpoints: CRUD de preguntas por departamento
- [ ] Al crear ticket → mostrar preguntas del departamento asignado
- [ ] Al responder → agente califica con rating 1-5
- [ ] HD Manager puede marcar respuesta como `approved_for_training`
- [ ] Endpoint: `GET /knowledge/training-dataset/` → exportar dataset aprobado

#### Portal usuario final (Angular)

- [ ] Vista: mis tickets + estado actual
- [ ] Acción: responder comentarios del agente
- [ ] Acción: marcar ticket como resuelto desde su lado
- [ ] CSAT: encuesta de 1-5 estrellas al cerrar ticket
- [ ] Notificaciones in-app en tiempo real (Django Channels + WebSocket)

### Entregable

```
✓ Dashboard operativo con métricas en tiempo real
✓ Usuarios finales pueden ver y responder sus tickets
✓ Datos de rating y satisfacción fluyendo hacia la DB
✓ Dataset de entrenamiento exportable (approved_for_training=True)
```

---

## Sprint 5 — Pulido, pruebas y entrega (Semanas 9-10)

**Objetivo:** Sistema listo para producción con documentación completa.

### Tareas

#### Testing

- [ ] Cobertura mínima 70% por dominio con `pytest-django`
- [ ] Tests de integración: flujo completo de ticket (crear → asignar → resolver)
- [ ] Tests de clasificación: precisión de keywords vs departamentos
- [ ] Tests de carga: 100 tickets concurrentes con balance de carga
- [ ] Tests de seguridad: aislamiento entre tenants verificado

#### CI/CD

- [ ] GitHub Actions: lint (`ruff`) + tests en cada PR
- [ ] GitHub Actions: build Docker + deploy a staging en merge a `main`
- [ ] Variables de entorno por ambiente (dev / staging / prod)
- [ ] Health check endpoints: `GET /health/`, `GET /health/db/`, `GET /health/redis/`

#### Documentación

- [ ] Swagger / OpenAPI con `drf-spectacular` (`GET /api/docs/`)
- [ ] README de cada dominio con decisiones de diseño
- [ ] ADRs (Architecture Decision Records) para las 5 decisiones principales
- [ ] Guía de onboarding para nuevos desarrolladores
- [ ] Guía de operación: cómo agregar un departamento, cómo reentrenar el modelo

### Entregable

```
✓ Pipeline CI/CD funcional
✓ Swagger completo y actualizado
✓ Cobertura de tests ≥ 70%
✓ Deploy a producción documentado
✓ Sistema listo para recibir el primer tenant real
```

---

## Modelo de base de datos

### Schema público (compartido entre tenants)

| Tabla | Descripción | Viene de |
|---|---|---|
| `Tenant` | Registro de organizaciones | Nuevo |
| `TenantConfig` | Configuración por org (SLA, umbral ML) | ser_mstr1 (parcial) |

### Schema por tenant (aislado por organización)

| Tabla | Descripción | Viene de |
|---|---|---|
| `User` | Usuarios del sistema | ser_usr_det |
| `Position` | Puestos/cargos | Nuevo |
| `Department` | Departamentos con keywords y SLA | ser_mstr1 |
| `UserProfile` | Perfil extendido del usuario | Nuevo |
| `Ticket` | Ticket principal + campos ML | req_mstr1 |
| `TicketDetail` | Asignación, deadline, cierre | req_mstr1_det + req_appoint |
| `TicketHistory` | Auditoría de cambios | Nuevo |
| `Comment` | Conversación del ticket | req_chat |
| `Attachment` | Archivos adjuntos | req_adj |
| `TicketWatcher` | CC y suscriptores | req_mailCC |
| `Notification` | Notificaciones in-app y email | Nuevo |
| `Assignment` | Historial de asignaciones | Nuevo |
| `WorkloadSnapshot` | Foto de carga por agente | Nuevo |
| `ClassificationLog` | Registro y evaluación de clasificaciones | Nuevo |
| `ServiceQuestion` | Preguntas por departamento | ser_quest |
| `TicketAnswer` | Respuestas + rating para ML | req_answ |
| `ServiceManual` | Base de conocimiento | ser_manu |

### Campos clave en `Ticket` para ML

```
description             text    Original del usuario — NUNCA se modifica
description_normalized  text    Texto limpio para clasificación y ML
classification_method   varchar keyword | ml_v1 | ml_v2 | manual
classification_score    float   Confianza 0.0-1.0
requires_review         bool    Agente debe confirmar el departamento
reformulated_desc       text    Descripción reescrita por LLM (Fase 2)
```

---

## Roadmap post-MVP

### Fase 2 — Automatización con ML (cuando haya 500+ tickets etiquetados)

- Regresión logística entrenada con datos propios por tenant
- Reformulación de descripciones vía LLM (Claude API / OpenAI)
- Feedback loop: rating de respuestas → reentrenamiento automático
- Versionado de modelos por tenant
- Endpoint de reentrenamiento bajo demanda para HD Manager

### Fase 3 — Árbol de tareas con ML avanzado

- Descomposición de tickets complejos en sub-tareas asignables
- Asignación multi-agente por habilidad + carga
- Predicción de SLA basada en histórico de tickets similares
- Transformer fine-tuned con vocabulario del dominio del cliente

---

## Reglas de arquitectura

### Lo que SÍ va en `shared/`

- Modelos abstractos base (`BaseModel`, `SoftDeleteModel`, `AuditModel`)
- Permisos usados por más de un dominio
- Handler de excepciones global
- Middleware de tenant
- Contrato de eventos entre dominios
- Formato de respuesta HTTP unificado
- Utilidades genéricas sin lógica de negocio

### Lo que NO va en `shared/`

- Lógica de balance de carga → `assignments/services.py`
- Modelo `Ticket` → `tickets/models.py`
- Serializers de usuario → `users/api/serializers.py`
- Tareas Celery de un dominio → en ese dominio
- Cualquier cosa que solo use un dominio → en ese dominio

> Si en la semana 6 sigues agregando cosas a `shared/`, hay un problema en la separación de dominios.

### Convenciones de código

- Formato: `ruff` + `black`
- Tests: `pytest-django`, un archivo por capa (`test_models`, `test_services`, `test_api`)
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`)
- Branches: `feature/`, `fix/`, `refactor/` → PR → `main`
- Nunca importar entre dominios directamente — solo por eventos o IDs

---

## Decisiones técnicas clave (ADRs)

### ADR-001: DDD ligero en monorepo vs microservicios

**Decisión:** Monorepo con dominios aislados.  
**Razón:** Equipo pequeño, plazo de 10 semanas, los dominios ya están aislados para extraerse en el futuro sin reescritura.

### ADR-002: Schema por tenant vs campo tenant_id

**Decisión:** Schema por tenant con `django-tenants`.  
**Razón:** Aislamiento real de datos, sin riesgo de filtrar información entre organizaciones, más fácil de auditar y de hacer backup por cliente.

### ADR-003: WorkloadSnapshot vs COUNT() en tiempo real

**Decisión:** Celery toma una foto de carga cada 5 minutos.  
**Razón:** Un `COUNT()` en tiempo real con joins en tablas grandes bajo carga es un cuello de botella garantizado. El snapshot es eventual pero suficientemente fresco para el caso de uso.

### ADR-004: Interfaz única de clasificación con estrategias intercambiables

**Decisión:** `ClassificationService` con strategy pattern, misma interfaz para keywords, ML v1 y ML v2.  
**Razón:** Permite evolucionar el modelo de clasificación sin tocar tickets, assignments ni ninguna otra parte del sistema.

### ADR-005: Guardar `description` original y `description_normalized` por separado

**Decisión:** Dos campos en `Ticket`, el original nunca se modifica.  
**Razón:** Trazabilidad, posibilidad de reentrenar con datos distintos, y el LLM de Fase 2 necesita el original para reformular, no la versión ya procesada.

---

*Documento generado como referencia de arquitectura y plan de ejecución*  
*Actualizar al final de cada sprint con decisiones tomadas y desviaciones del plan*