# Documentación Técnica — Sistema de Recomendación NeuMF
## Arquitectura Propuesta: Azure Container Apps Jobs

**Proyecto:** ICO Distribuidora — Sistema de Recomendación de Productos  
**Autores:** Torres Díaz, Camila Milagros | Ortiz, Belén  
**Universidad:** UPC — TDP TP1 — 2026  
**Versión:** 2.0 (arquitectura sin AML, sin ADF, sin Data Lake Gen2)

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Componentes del Sistema](#2-componentes-del-sistema)
3. [Capa de Datos — Azure SQL Database](#3-capa-de-datos--azure-sql-database)
4. [Capa de Almacenamiento — Azure Blob Storage](#4-capa-de-almacenamiento--azure-blob-storage)
5. [Pipeline ML — Azure Container Apps Jobs](#5-pipeline-ml--azure-container-apps-jobs)
6. [Capa API — FastAPI en Container Apps](#6-capa-api--fastapi-en-container-apps)
7. [Capa Frontend — Next.js en Static Web Apps](#7-capa-frontend--nextjs-en-static-web-apps)
8. [CI/CD — GitHub Actions](#8-cicd--github-actions)
9. [Scheduling y Timeline Diario](#9-scheduling-y-timeline-diario)
10. [Escalabilidad](#10-escalabilidad)
11. [Costos Estimados](#11-costos-estimados)
12. [Archivos de Configuración](#12-archivos-de-configuración)
13. [Comparativa con Arquitectura Original](#13-comparativa-con-arquitectura-original)

---

## 1. Visión General

### 1.1 Objetivo del Sistema

Sistema de recomendación de productos para vendedores de ICO Distribuidora. Combina un modelo de aprendizaje profundo (NeuMF) con tres scores de negocio para generar recomendaciones personalizadas por cliente. Las recomendaciones se pre-calculan cada noche y se sirven vía API REST con latencia < 20 ms.

### 1.2 Decisión de Arquitectura

Se optó por **Azure Container Apps Jobs** en lugar de Azure Machine Learning (AML) Serverless Compute por las siguientes razones:

| Criterio | AML Serverless | Container Apps Jobs |
|----------|---------------|---------------------|
| Complejidad de setup | Alta (AML Workspace, Environments, Datastores) | Baja (Dockerfile + YAML) |
| Costo mensual (ML jobs) | ~$2.63 | ~$3.53 |
| Dependencia de servicio adicional | AML Workspace (~$0–$10/mes base) | Ninguna (ya se usa Container Apps para FastAPI) |
| Debugging | Logs en AML Studio | Logs directos en Container Apps |
| Escalabilidad | Alta (GPU VMs disponibles) | Media (CPU optimizado, GPU limitado) |
| Adecuación al proyecto | Sobredimensionado | Exacta para 800 clientes / 1,843 productos |

Para el volumen de datos actual y proyectado de ICO Distribuidora, Container Apps Jobs cubre todos los requisitos sin la complejidad operativa de un workspace AML.

### 1.3 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│  GitHub Repository                                                   │
│  └── push main → GitHub Actions                                     │
│      ├── Build imagen Docker → Azure Container Registry             │
│      └── Deploy → Container Apps + Static Web Apps                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│ Static Web Apps │ │Container Apps│ │  Container Apps Jobs  │
│   (Next.js)     │ │   (FastAPI)  │ │  clean / train / batch│
└────────┬────────┘ └──────┬───────┘ └──────────┬───────────┘
         │                 │                     │
         │    API Mgmt     │                     │
         └────────────────►│◄────────────────────┤
                           │                     │
                           ▼                     ▼
                  ┌────────────────┐   ┌──────────────────┐
                  │  Azure SQL DB  │   │  Azure Blob       │
                  │  Serverless    │   │  Storage          │
                  │  oltp | results│   │  /processed/      │
                  └────────────────┘   │  /models/         │
                           ▲           └──────────────────┘
                           │
                    FastAPI sirve
                    predicciones
                    pre-calculadas
                    en < 20 ms
```

---

## 2. Componentes del Sistema

| Componente | Servicio Azure | Rol |
|-----------|---------------|-----|
| Frontend | Azure Static Web Apps | Interfaz del vendedor (Next.js) |
| API Gateway | Azure API Management | Rate limiting, políticas, punto de entrada único |
| API REST | Azure Container Apps (Service) | FastAPI — sirve recomendaciones y gestiona pedidos |
| Autenticación | Azure Entra ID (OAuth2/OIDC) | Autenticación de vendedores |
| Pipeline ML | Azure Container Apps (Jobs) | Ejecuta clean.py, train.py, batch_inference.py |
| Base de datos | Azure SQL Database Serverless | Datos transaccionales (oltp) y predicciones (results) |
| Almacenamiento ML | Azure Blob Storage | Artefactos: parquets, índices, modelo .pt |
| Registro de imágenes | Azure Container Registry | Imágenes Docker de los jobs y la API |
| CI/CD | GitHub Actions | Build, test y despliegue automático |
| Experiment tracking | MLflow (en Container Apps) | Registro de métricas y parámetros por experimento |

---

## 3. Capa de Datos — Azure SQL Database

### 3.1 Configuración

```
SKU: Azure SQL Database Serverless
  vCores: 0.5–4 (escala automáticamente)
  Pausa automática: 1 hora sin actividad → costo $0
  Almacenamiento: 32 GB
  Backup: 7 días automático
  Costo estimado: $5–15 USD/mes
```

### 3.2 Schema OLTP (fuente de datos)

Contiene los datos transaccionales del negocio. Es la fuente de verdad del sistema.

```sql
-- Clientes registrados
CREATE TABLE oltp.clientes (
    cliente_id        VARCHAR(20) PRIMARY KEY,
    nombre            VARCHAR(100),
    sede_cliente      VARCHAR(50),
    tipo_cliente      VARCHAR(30),
    descuento_cliente DECIMAL(5,2) DEFAULT 0,
    creado_en         DATETIME DEFAULT GETDATE()
);

-- Catálogo de productos
CREATE TABLE oltp.productos (
    producto_id       VARCHAR(20) PRIMARY KEY,
    nombre            VARCHAR(100),
    categoria_producto VARCHAR(50),
    precio_unitario   DECIMAL(10,2),
    costo_unitario    DECIMAL(10,2),
    stock             INT DEFAULT 0,
    fecha_vencimiento DATE,
    fecha_ingreso_catalogo DATE,
    activo            BIT DEFAULT 1
);

-- Cabecera de ventas
CREATE TABLE oltp.ventas (
    venta_id          INT PRIMARY KEY IDENTITY,
    cliente_id        VARCHAR(20) REFERENCES oltp.clientes,
    vendedor_id       VARCHAR(20),
    fecha_venta       DATETIME DEFAULT GETDATE(),
    subtotal          DECIMAL(10,2),
    impuesto          DECIMAL(10,2),
    descuento         DECIMAL(10,2) DEFAULT 0,
    total             DECIMAL(10,2),
    forma_pago        VARCHAR(30)
);

-- Detalle de ventas (interacciones usuario-ítem para NeuMF)
CREATE TABLE oltp.detalle_venta (
    detalle_id        INT PRIMARY KEY IDENTITY,
    venta_id          INT REFERENCES oltp.ventas,
    producto_id       VARCHAR(20) REFERENCES oltp.productos,
    cantidad          INT,
    precio_unit       DECIMAL(10,2),
    subtotal          DECIMAL(10,2)
);
```

### 3.3 Schema Results (salida del sistema)

Contiene las predicciones pre-calculadas que sirve FastAPI.

```sql
CREATE TABLE results.predicciones (
    cliente_id        VARCHAR(20)  NOT NULL,
    producto_id       VARCHAR(20)  NOT NULL,
    rank_general      INT          NOT NULL,
    score_final       DECIMAL(8,6) NOT NULL,
    ncf_score         DECIMAL(8,6) NOT NULL,
    s_urgency         DECIMAL(8,6) NOT NULL,
    s_rotation        DECIMAL(8,6) NOT NULL,
    s_novelty         DECIMAL(8,6) NOT NULL,
    es_urgente        BIT          NOT NULL DEFAULT 0,
    es_nuevo          BIT          NOT NULL DEFAULT 0,
    es_baja_rotacion  BIT          NOT NULL DEFAULT 0,
    dias_para_vencer  INT,
    dias_en_catalogo  INT,
    rotacion_diaria   DECIMAL(8,6),
    stock             INT,
    fecha_generacion  DATE         NOT NULL,
    PRIMARY KEY (cliente_id, producto_id)
);

CREATE INDEX idx_pred_cliente  ON results.predicciones(cliente_id);
CREATE INDEX idx_pred_urgente  ON results.predicciones(cliente_id, es_urgente);
CREATE INDEX idx_pred_rotacion ON results.predicciones(cliente_id, es_baja_rotacion);
CREATE INDEX idx_pred_nuevo    ON results.predicciones(cliente_id, es_nuevo);
```

---

## 4. Capa de Almacenamiento — Azure Blob Storage

### 4.1 Configuración

```
Cuenta: icorecomendador
Container: ml-artifacts
Redundancia: LRS (Locally Redundant Storage)
Acceso: Managed Identity desde Container Apps Jobs
Costo estimado: $1–2 USD/mes
```

### 4.2 Estructura de carpetas

```
ml-artifacts/
│
├── processed/                          ← Generado por clean-job (diario)
│   ├── pares_entrenamiento.parquet     ← Pares (usuario, ítem, label, weight)
│   ├── indices.json                    ← Mapeos user_idx↔cliente_id, item_idx↔producto_id
│   └── contexto_productos.parquet      ← Features de productos para business scores
│
└── models/                             ← Generado por train-job (mensual)
    ├── modelo_ncf.pt                   ← Modelo en producción (el más reciente)
    └── history/
        ├── modelo_ncf_2026-04-01.pt    ← Backup por fecha de entrenamiento
        ├── modelo_ncf_2026-05-01.pt
        └── ...
```

### 4.3 Flujo de lectura/escritura

| Archivo | Escribe | Lee |
|---------|---------|-----|
| `/processed/pares_entrenamiento.parquet` | clean-job | train-job |
| `/processed/indices.json` | clean-job | train-job, batch-job |
| `/processed/contexto_productos.parquet` | clean-job | batch-job |
| `/models/modelo_ncf.pt` | train-job | batch-job |
| `/models/history/*.pt` | train-job | (referencia histórica) |

---

## 5. Pipeline ML — Azure Container Apps Jobs

Los tres scripts Python del pipeline se ejecutan como **Jobs** en Azure Container Apps. Un Job es un contenedor efímero que:
1. Se aprovisiona automáticamente cuando el cron trigger dispara
2. Ejecuta el script Python
3. Se destruye al terminar

No hay ninguna VM que permanezca encendida entre ejecuciones — el costo es cero cuando no hay trabajo.

### 5.1 clean-job — Preparación de datos

**Script:** `ml/clean.py`  
**Cuándo:** Todos los días a las **01:00 AM**  
**Dónde:** Contenedor efímero en Container Apps, imagen `ml-jobs:latest`  
**Duración estimada:** ~15 minutos  
**Costo por ejecución:** ~$0.03

#### Qué hace

```
01:00 AM — clean-job arranca
│
├── [1] Conecta a Azure SQL (schema oltp)
│       Extrae datos actualizados:
│       - oltp.clientes     → quiénes son los usuarios
│       - oltp.productos    → catálogo con stock, vencimiento, etc.
│       - oltp.ventas       → historial de pedidos
│       - oltp.detalle_venta → qué compró cada cliente (interacciones)
│
├── [2] Genera pares de entrenamiento
│       Para cada interacción real (cliente compró producto):
│       └── label=1, weight=f(cantidad, frecuencia)
│       Muestreo negativo 1:4:
│       └── Por cada positivo, 4 negativos aleatorios (label=0, weight=1.0)
│
├── [3] Construye índices de mapeo
│       cliente_id → user_idx  (entero 0..n_users-1)
│       producto_id → item_idx (entero 0..n_items-1)
│
├── [4] Calcula features de contexto por producto
│       - dias_para_vencer  = fecha_vencimiento - hoy
│       - dias_en_catalogo  = hoy - fecha_ingreso_catalogo
│       - rotacion_diaria   = unidades_vendidas / dias_en_catalogo
│       - baja_rotacion     = rotacion_diaria < percentil_25
│
├── [5] Sube artefactos a Blob Storage /processed/
│       - pares_entrenamiento.parquet
│       - indices.json
│       - contexto_productos.parquet
│
└── Contenedor se destruye
```

#### Por qué se ejecuta diariamente

El batch nocturno (batch-job) necesita el `contexto_productos.parquet` actualizado con el stock y días para vencer de **hoy**. Si clean-job no corriera diariamente, las predicciones usarían datos de stock y vencimiento desactualizados.

El entrenamiento (train-job) usa el historial completo acumulado — al correr clean.py antes del entrenamiento mensual, el modelo incorpora todas las ventas hasta la fecha.

---

### 5.2 train-job — Entrenamiento del modelo

**Script:** `ml/train.py`  
**Cuándo:** Día 1 de cada mes a las **03:00 AM**  
**Dónde:** Contenedor efímero en Container Apps, imagen `ml-jobs:latest`  
**Duración estimada:** ~40 minutos  
**Costo por ejecución:** ~$0.23

#### Qué hace

```
03:00 AM día 1/mes — train-job arranca
│
├── [1] Descarga artefactos desde Blob Storage /processed/
│       - pares_entrenamiento.parquet  (generado por clean-job de las 01:00 AM)
│       - indices.json
│
├── [2] Construye datasets PyTorch
│       Train: 80% de los pares (shuffle=True)
│       Val:   20% de los pares (shuffle=False)
│
├── [3] Inicializa modelo NeuMF
│       GMF path: Embedding(n_users, k=64) + Embedding(n_items, k=64)
│                 → Hadamard product → vector 64 dims
│       MLP path: Embedding(n_users, k=64) + Embedding(n_items, k=64)
│                 → Concat(128) → Dense(128, ReLU) → Dense(64, ReLU)
│                 → Dense(32, ReLU) → vector 32 dims
│       Fusion:   Concat([64, 32]) → 96 dims → Dense(1) → Sigmoid
│       Parámetros entrenables: ~500,000
│
├── [4] Loop de entrenamiento (20 épocas)
│       Por cada época:
│       ├── Forward pass: preds = model(users, items)
│       ├── Loss: BCELoss(preds, labels) * weights → mean
│       ├── Backward: optimizer.zero_grad() + loss.backward()
│       ├── Update: Adam(lr=0.001).step()
│       └── Validación: val_loss + val_AUC
│
├── [5] Guarda mejor modelo (mayor val_AUC)
│       checkpoint = {
│           epoch, model_state, n_users, n_items, k, mlp_layers, val_auc
│       }
│
├── [6] Evaluación NDCG@10 (leave-one-out)
│       Para cada usuario con ≥ 2 compras:
│       - Ítem test = el de mayor item_idx (proxy del más reciente)
│       - Pool = 1 positivo + 99 negativos aleatorios
│       - Calcula NDCG@10, HitRate@10, Precision@10
│
├── [7] Registra en MLflow
│       Parámetros: epochs, batch_size, k, lr, val_split, n_users, n_items
│       Métricas por época: train_loss, val_loss, val_auc
│       Métricas finales: best_val_auc, ndcg_at_10, hitrate_at_10, precision_at_10
│       Artefacto: modelo_ncf.pt
│
├── [8] Sube modelo a Blob Storage
│       /models/modelo_ncf.pt                    ← sobreescribe producción
│       /models/history/modelo_ncf_YYYY-MM-DD.pt ← backup fechado
│
└── Contenedor se destruye
    batch-job de esa misma noche usa el modelo nuevo
```

#### Hiperparámetros

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| k (embedding dim) | 64 | Balance expresividad/costo computacional |
| MLP layers | [128, 64, 32] | Arquitectura estándar NeuMF (He et al. 2017) |
| Epochs | 20 | Convergencia típica para este tamaño de dataset |
| Batch size | 1024 | Alineado con documentación técnica |
| Learning rate | 0.001 | Adam con lr estándar |
| Val split | 80/20 | Split estándar de entrenamiento |
| Negative sampling | 1:4 | Ratio estándar para feedback implícito |

---

### 5.3 batch-job — Inferencia nocturna

**Script:** `ml/batch_inference.py`  
**Cuándo:** Todos los días a las **02:00 AM** (después de clean-job)  
**Dónde:** Contenedor efímero en Container Apps, imagen `ml-jobs:latest`  
**Duración estimada:** ~25 minutos  
**Costo por ejecución:** ~$0.08

#### Qué hace

```
02:00 AM — batch-job arranca
│
├── [1] Descarga desde Blob Storage
│       - /models/modelo_ncf.pt
│       - /processed/indices.json
│       - /processed/contexto_productos.parquet
│
├── [2] Carga modelo NeuMF en PyTorch (modo eval)
│
├── [3] Lee contexto de productos
│       Construye vectores de features para todos los ítems:
│       - dias_vencer_vec[j]    → días para vencer del ítem j
│       - dias_catalogo_vec[j]  → días en catálogo del ítem j
│       - rotacion_vec[j]       → rotación diaria del ítem j
│       - stock_vec[j]          → stock actual del ítem j
│
├── [4] Calcula business scores (una sola vez para todos los ítems)
│       s_urgency[j]  = sigmoid inversa en dias_para_vencer
│                       inflexión en 15 días (sigma=15)
│       s_novelty[j]  = sigmoid inversa en dias_en_catalogo
│                       inflexión en 30 días
│       s_rotation[j] = sigmoid inversa en rotacion_diaria
│                       inflexión en percentil_25 de rotación
│
├── [5] Define máscara de exclusión
│       excluir[j] = True si stock <= 0 OR dias_para_vencer < 0
│       (productos sin stock o vencidos no se recomiendan)
│
├── [6] Para cada usuario u (800 clientes):
│       ├── ncf_scores = model.predict_all(u, n_items)
│       │     → vector de 1,843 scores NCF
│       │
│       ├── score_final = 0.50 * ncf_scores
│       │               + 0.25 * s_urgency
│       │               + 0.15 * s_novelty
│       │               + 0.10 * s_rotation
│       │
│       ├── Aplica filtros duros: score_final[excluir] = 0.0
│       │
│       └── Top-10 por score_final → 10 filas para este cliente
│
├── [7] Inserta en Azure SQL (results.predicciones)
│       800 clientes × 10 productos = 8,000 filas
│       Inserción en batches de 5,000 para eficiencia
│       DELETE FROM predicciones primero (reemplaza por completo)
│
└── Contenedor se destruye
    FastAPI puede servir las nuevas predicciones
```

#### Fórmula score_final

```
score_final = 0.50 × ncf_score
            + 0.25 × s_urgency(dias_para_vencer)
            + 0.15 × s_novelty(dias_en_catalogo)
            + 0.10 × s_rotation(rotacion_diaria)

Filtros duros:
  stock <= 0           → score_final = 0  (sin stock)
  dias_para_vencer < 0 → score_final = 0  (vencido)

Flags de negocio:
  es_urgente       = dias_para_vencer <= 30 AND >= 0
  es_nuevo         = dias_en_catalogo <= 90
  es_baja_rotacion = rotacion_diaria < percentil_25
```

---

## 6. Capa API — FastAPI en Container Apps

### 6.1 Configuración

```
Servicio: Azure Container Apps (always-on service, no job)
Imagen: recomendador-api:latest (desde Azure Container Registry)
Scale-to-zero: desactivado (siempre disponible durante horario laboral)
Min replicas: 1
Max replicas: 3 (escala por carga HTTP)
CPU: 0.5 vCPU
RAM: 1 GB
Costo estimado: $0–9 USD/mes
```

### 6.2 Endpoints principales

```
GET  /recomendar/{cliente_id}
     → SELECT TOP 10 FROM results.predicciones
       WHERE cliente_id = ? ORDER BY rank_general
     → Latencia < 20 ms (datos pre-calculados)

GET  /recomendar/urgentes/{cliente_id}
     → WHERE cliente_id = ? AND es_urgente = 1

GET  /recomendar/nuevos/{cliente_id}
     → WHERE cliente_id = ? AND es_nuevo = 1

GET  /recomendar/baja-rotacion/{cliente_id}
     → WHERE cliente_id = ? AND es_baja_rotacion = 1

POST /pedidos
     → INSERT INTO oltp.ventas + oltp.detalle_venta

GET  /pedidos/{id}
     → SELECT venta + detalles

GET  /clientes (cartera del vendedor)
GET  /productos
GET  /health   → status + fecha_generacion predicciones
```

### 6.3 Flujo de autenticación

```
Vendedor hace login
│
├── POST /auth/login {usuario, password}
│   └── FastAPI valida contra oltp.vendedores
│       └── Retorna JWT firmado (exp: 8 horas)
│
├── Todas las requests siguientes llevan:
│   Authorization: Bearer <jwt>
│   └── API Management valida el token antes de pasar a FastAPI
│
└── FastAPI extrae vendedor_id del token
    └── Filtra datos por vendedor (cartera asignada)
```

---

## 7. Capa Frontend — Next.js en Static Web Apps

### 7.1 Configuración

```
Servicio: Azure Static Web Apps
Plan: Free (suficiente para tesis)
Framework: Next.js (App Router)
Build: GitHub Actions → az staticwebapp deploy
CDN: Global (automático)
Dominio: *.azurestaticapps.net
Costo: $0 USD/mes
```

### 7.2 Rutas principales

```
/                     → Redirige a /inicio
/(vendedor)/inicio    → Dashboard: stats del mes + últimos pedidos
/(vendedor)/clientes  → Tabla de cartera asignada al vendedor
/(vendedor)/carrito   → Selección de productos + recomendaciones del modelo
/(vendedor)/historial → Historial de pedidos con filtros y paginación
/(vendedor)/historial/[id] → Detalle de pedido específico
```

---

## 8. CI/CD — GitHub Actions

### 8.1 Workflow: deploy-api.yml

**Trigger:** push a `main` que modifica `backend/` o `ml/`

```yaml
Pasos:
1. Checkout del repositorio
2. Login a Azure Container Registry (via OIDC con Entra ID)
3. docker build -t <acr>.azurecr.io/ml-jobs:latest .
4. docker build -t <acr>.azurecr.io/recomendador-api:latest ./backend
5. docker push (ambas imágenes)
6. az containerapp update --name recomendador-api --image nueva-imagen
7. az containerapp job update --name clean-job   --image ml-jobs:latest
8. az containerapp job update --name train-job   --image ml-jobs:latest
9. az containerapp job update --name batch-job   --image ml-jobs:latest
```

### 8.2 Workflow: deploy-frontend.yml

**Trigger:** push a `main` que modifica `frontend/`

```yaml
Pasos:
1. Checkout del repositorio
2. npm install && npm run build
3. Azure/static-web-apps-deploy → sube /out/ al CDN
```

### 8.3 Workflow: trigger-train.yml

**Trigger:** `workflow_dispatch` (manual desde GitHub UI)

```yaml
Pasos:
1. Login a Azure
2. az containerapp job start --name train-job
   (fuerza entrenamiento fuera del schedule mensual)
3. az containerapp job execution show (monitorea hasta completar)
```

---

## 9. Scheduling y Timeline Diario

### 9.1 Schedules configurados

| Job | Cron Expression | Hora | Frecuencia |
|-----|----------------|------|-----------|
| clean-job | `0 1 * * *` | 01:00 AM | Todos los días |
| batch-job | `0 2 * * *` | 02:00 AM | Todos los días |
| train-job | `0 3 1 * *` | 03:00 AM | Día 1 de cada mes |

### 9.2 Timeline de un día típico

```
00:00 ─────────────────────────────────────────────────── 23:59

01:00 AM ┌──────────────┐
         │  clean-job   │ Lee SQL oltp → parquets actualizados → Blob
         │   ~15 min    │ Stock y vencimientos de HOY incorporados
         └──────────────┘
               │
               ▼ /processed/ actualizado en Blob Storage
               │
02:00 AM ┌──────────────┐
         │  batch-job   │ Blob (modelo+parquets) → 8,000 predicciones → SQL
         │   ~25 min    │ Cada cliente tiene su Top-10 listo para hoy
         └──────────────┘
               │
               ▼ results.predicciones actualizado en Azure SQL
               │
08:00 AM  Vendedores entran a la app
          FastAPI: SELECT TOP 10 → respuesta en < 20 ms
          (sin inferencia en tiempo real)

17:00 PM  Vendedor registra pedidos durante el día
          → INSERT INTO oltp.ventas (fuente de datos para mañana)

23:59     Fin del día — mañana clean-job incorpora los pedidos de hoy
```

### 9.3 Timeline día 1 de cada mes

```
01:00 AM  clean-job    → parquets con historial completo actualizado
02:00 AM  batch-job    → predicciones con modelo ANTERIOR (del mes pasado)
03:00 AM  train-job    → entrena NeuMF con todo el historial → modelo nuevo
~03:40 AM train-job termina → modelo_ncf.pt actualizado en Blob

Al día siguiente (día 2):
02:00 AM  batch-job    → ahora usa el modelo nuevo
          Las predicciones mejoran incorporando el último mes de compras
```

---

## 10. Escalabilidad

### 10.1 Límites actuales y proyección

| Clientes | Estrategia | Tiempo batch | Costo adicional |
|----------|-----------|-------------|----------------|
| 800 (actual) | 1 instancia, 2 CPU | ~25 min | baseline |
| 3,000 | 1 instancia, 4 CPU (scale-up) | ~50 min | +~$0.05/noche |
| 10,000 | 4 instancias paralelas, 2 CPU c/u | ~40 min | +~$0.25/noche |
| 50,000 | 10 instancias paralelas, 4 CPU c/u | ~50 min | +~$1.50/noche |
| 200,000+ | Migrar a AML con GPU | ~60 min | evaluar AML |

### 10.2 Cómo se activa el paralelismo

Container Apps Jobs soporta `parallelism` nativo. Con un cambio en el YAML y un ajuste mínimo al script:

```yaml
# container-apps-job.yaml
properties:
  configuration:
    replicaCompletionCount: 4
    parallelism: 4   # 4 contenedores simultáneos
  template:
    containers:
      - args: ["--shard", "$(JOB_EXECUTION_NAME)", "--total-shards", "4"]
```

```python
# batch_inference.py — ajuste para sharding
parser.add_argument("--shard",        type=int, default=0)
parser.add_argument("--total-shards", type=int, default=1)

mis_usuarios = [u for u in range(n_users)
                if u % args.total_shards == args.shard]
```

Cada instancia procesa 1/N de los clientes y escribe su porción en SQL. El tiempo total se divide por N.

---

## 11. Costos Estimados

### 11.1 Desglose mensual

| Servicio | SKU / Uso | Costo/mes |
|---------|-----------|-----------|
| Azure SQL Database | Serverless, 0.5–4 vCores | $5–$15 |
| Azure Blob Storage | LRS, ~1 GB | $1–$2 |
| Container Apps — clean-job | 30 corridas × 15 min × 2 CPU | ~$0.90 |
| Container Apps — batch-job | 30 corridas × 25 min × 2 CPU | ~$2.40 |
| Container Apps — train-job | 1 corrida × 40 min × 2 CPU | ~$0.23 |
| Container Apps — FastAPI | 1 réplica always-on | $0–$9 |
| Azure Container Registry | Basic tier | ~$5 |
| Azure Static Web Apps | Free plan | $0 |
| API Management | Consumption tier | $0–$10 |
| Azure Entra ID | Free tier (~800 usuarios) | $0 |
| GitHub Actions | Free tier (2,000 min/mes) | $0 |
| **TOTAL** | | **~$14–$44 USD/mes** |

### 11.2 Comparativa con arquitectura original

| Arquitectura | Costo/mes |
|-------------|-----------|
| Doc original (AML + SQL Server dedicado) | $160–$230 |
| Doc ajustado (AML Serverless + SQL Serverless) | $8–$37 |
| **Propuesta (Container Apps Jobs + SQL Serverless)** | **$14–$44** |

---

## 12. Archivos de Configuración

### 12.1 Dockerfile (imagen compartida ml-jobs)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para pyodbc (Azure SQL)
RUN apt-get update && apt-get install -y \
    gcc g++ unixodbc-dev curl gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements-ml.txt .
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-ml.txt

# Código fuente
COPY ml/      ./ml/
COPY scripts/ ./scripts/

# Variables de entorno requeridas en tiempo de ejecución:
# AZURE_STORAGE_CONNECTION_STRING
# AZURE_SQL_CONNECTION_STRING

CMD ["python", "ml/batch_inference.py"]
```

### 12.2 clean-job.yaml

```yaml
# az containerapp job create --yaml clean-job.yaml
name: clean-job
resourceGroup: ico-distribuidora-rg
location: eastus

properties:
  environmentId: /subscriptions/.../managedEnvironments/ico-env
  configuration:
    triggerType: Schedule
    scheduleTriggerConfig:
      cronExpression: "0 1 * * *"      # 01:00 AM todos los días
      parallelism: 1
      replicaCompletionCount: 1
    replicaTimeout: 1800               # 30 min máximo
    replicaRetryLimit: 1
  template:
    containers:
      - name: clean-job
        image: <acr>.azurecr.io/ml-jobs:latest
        command: ["python", "ml/clean.py"]
        resources:
          cpu: 1.0
          memory: 2Gi
        env:
          - name: AZURE_SQL_CONNECTION_STRING
            secretRef: sql-connection-string
          - name: AZURE_STORAGE_CONNECTION_STRING
            secretRef: storage-connection-string
```

### 12.3 train-job.yaml

```yaml
name: train-job
resourceGroup: ico-distribuidora-rg
location: eastus

properties:
  environmentId: /subscriptions/.../managedEnvironments/ico-env
  configuration:
    triggerType: Schedule
    scheduleTriggerConfig:
      cronExpression: "0 3 1 * *"      # 03:00 AM día 1 de cada mes
      parallelism: 1
      replicaCompletionCount: 1
    replicaTimeout: 5400               # 90 min máximo
    replicaRetryLimit: 1
  template:
    containers:
      - name: train-job
        image: <acr>.azurecr.io/ml-jobs:latest
        command: ["python", "ml/train.py"]
        resources:
          cpu: 2.0
          memory: 4Gi
        env:
          - name: AZURE_STORAGE_CONNECTION_STRING
            secretRef: storage-connection-string
          - name: MLFLOW_TRACKING_URI
            value: "http://mlflow-server"
```

### 12.4 batch-job.yaml

```yaml
name: batch-job
resourceGroup: ico-distribuidora-rg
location: eastus

properties:
  environmentId: /subscriptions/.../managedEnvironments/ico-env
  configuration:
    triggerType: Schedule
    scheduleTriggerConfig:
      cronExpression: "0 2 * * *"      # 02:00 AM todos los días
      parallelism: 1
      replicaCompletionCount: 1
    replicaTimeout: 3600               # 60 min máximo
    replicaRetryLimit: 1
  template:
    containers:
      - name: batch-job
        image: <acr>.azurecr.io/ml-jobs:latest
        command: ["python", "ml/batch_inference.py"]
        resources:
          cpu: 2.0
          memory: 4Gi
        env:
          - name: AZURE_STORAGE_CONNECTION_STRING
            secretRef: storage-connection-string
          - name: AZURE_SQL_CONNECTION_STRING
            secretRef: sql-connection-string
```

### 12.5 requirements-ml.txt

```
torch>=2.0.0
pandas>=2.0.0
pyarrow>=12.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
mlflow>=2.10.0
azure-storage-blob>=12.19.0
pyodbc>=5.0.0
sqlalchemy>=2.0.0
```

---

## 13. Comparativa con Arquitectura Original

| Componente | Arquitectura Original (doc) | Arquitectura Propuesta |
|-----------|----------------------------|----------------------|
| Compute ML | AML Serverless (VMs efímeras) | Container Apps Jobs (contenedores efímeros) |
| Scheduling | AML Schedules | Cron trigger nativo en Container Apps |
| Model Registry | AML Model Registry (MLflow integrado) | Azure Blob Storage + MLflow standalone |
| ETL Orquestación | Azure Data Factory | Eliminado — clean.py lee SQL directamente |
| Almacenamiento ML | Azure Data Lake Storage Gen2 | Azure Blob Storage (equivalente, más simple) |
| Framework ML | TensorFlow/Keras (doc) | PyTorch (implementación actual, superior para investigación) |
| Base de datos | Azure SQL Server dedicado ($150–200/mes) | Azure SQL Database Serverless ($5–15/mes) |
| Autenticación | Entra ID + APIM (producción completa) | JWT propio + APIM (simplificado para prototipo) |
| Frontend | Azure Static Web Apps | Azure Static Web Apps (igual) |
| API | FastAPI en Container Apps | FastAPI en Container Apps (igual) |
| CI/CD | GitHub Actions | GitHub Actions (igual) |
| **Costo total** | **$160–$230/mes** | **$14–$44/mes** |

### Funcionalidades equivalentes mantenidas

- Pre-cálculo nocturno de predicciones para los 800 clientes
- Latencia de API < 20 ms (datos pre-calculados en SQL)
- Reentrenamiento mensual automático del modelo NeuMF
- Tracking de experimentos con MLflow
- Score híbrido: NCF + urgency + novelty + rotation
- Filtros duros: stock = 0 y productos vencidos excluidos
- Top-10 por cliente con flags de negocio (es_urgente, es_nuevo, es_baja_rotacion)
- Escalabilidad horizontal vía paralelismo de jobs

---

*Documentación generada el 2026-05-03*  
*Sistema de Recomendación NeuMF — ICO Distribuidora*
