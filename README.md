# ICO Distribuidora — Sistema de Recomendación NeuMF (v2)

**Empresa distribuidora de alimentos | Sector HORECA | Perú**

Sistema de recomendación basado en **NeuMF (Neural Collaborative Filtering)**
que prioriza productos de baja rotación, próximos a vencer y nuevos,
alineados con el perfil histórico de cada cliente.

---

## Score Final

```
score_final = 0.55 × ncf_score
            + 0.20 × score_urgency   (sigmoide, inflexión en 15 días para vencer)
            + 0.15 × score_rotation  (sigmoide, inflexión en p25 de rotación_diaria)
            + 0.10 × score_novelty   (sigmoide, inflexión en 30 días en catálogo)

Filtros duros:
  stock <= 0            → score = 0
  dias_para_vencer < 0  → score = 0  (vencido)
```

---

## Arquitectura NeuMF

```
Usuario → Emb_GMF(k=64) ──→ element-wise × ──→ [64] ──┐
Producto → Emb_GMF(k=64) ─┘                            │
                                                         ├──→ Concat[96] → Dense(1) + Sigmoid → ncf_score
Usuario → Emb_MLP(k=64) ──→ Concat[128]                │
Producto → Emb_MLP(k=64) ─┘  → Dense(128,ReLU)        │
                               → Dense(64,ReLU)  → [32] ┘
                               → Dense(32,ReLU)
```

**Entrenamiento:** Adam | binary_crossentropy | 20 epochs | batch=256 | neg_sampling=1:4 | sample_weight=w_recency

---

## Estructura del Proyecto

```
repo_v2_tesis/
├── ml/
│   ├── ncf/model.py          # Arquitectura NeuMF (PyTorch)
│   ├── clean.py              # ETL: dataset_ml.csv → pares + contexto + índices
│   ├── train.py              # Entrenamiento del modelo
│   ├── evaluate.py           # NDCG@10, HitRate@10
│   └── batch_inference.py    # Inferencia diaria → predicciones SQLite
├── backend/
│   └── app/
│       ├── main.py           # FastAPI entry point
│       ├── database.py       # SQLAlchemy + SQLite async
│       ├── models/           # ORM models
│       ├── schemas/          # Pydantic v2
│       ├── routers/          # auth, recomendaciones, productos, clientes, pedidos, admin
│       └── services/seed.py  # Carga inicial de datos
├── frontend/                 # Next.js 14 (App Router)
├── notebooks/
│   └── 01_dataset.ipynb      # Generación del dataset_ml.csv
├── data/
│   ├── raw/                  # CSVs fuente
│   ├── processed/            # dataset_ml.csv, artefactos ML
│   └── db/ico.db             # SQLite (creado automáticamente)
├── scripts/
│   └── run_daily_batch.py    # Pipeline diario (ETL + inferencia)
├── requirements.txt
└── .env.example
```

---

## Inicio Rápido

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 3. Pipeline ML (primera vez)

```bash
# ETL: genera pares de entrenamiento y contexto de productos
python ml/clean.py

# Entrenamiento del modelo NeuMF
python ml/train.py

# Evaluación NDCG@10
python ml/evaluate.py

# Inferencia batch: genera predicciones en SQLite
python ml/batch_inference.py
```

### 4. Inicializar la BD y cargar datos de prueba

```bash
python -m backend.app.services.seed
```

### 5. Levantar el backend

```bash
uvicorn backend.app.main:app --reload --port 8000
```

### 6. Frontend (próximo paso)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Login con email/contraseña → JWT |
| GET | `/auth/me` | Usuario autenticado |
| GET | `/recomendar/{cliente_id}` | Top-K general |
| GET | `/recomendar/dashboard/{cliente_id}` | 3 secciones sin duplicados |
| GET | `/recomendar/proximos-vencer/{cliente_id}` | Urgentes |
| GET | `/recomendar/baja-rotacion/{cliente_id}` | Baja rotación |
| GET | `/recomendar/nuevos/{cliente_id}` | Nuevos en catálogo |
| GET | `/productos` | Catálogo con filtros |
| GET | `/clientes` | Cartera del vendedor |
| POST | `/pedidos` | Confirmar carrito → pedido |
| GET | `/pedidos` | Historial de pedidos |
| GET | `/admin/metricas` | NDCG@10, HitRate, tasa conversión |

**Documentación interactiva:** `http://localhost:8000/docs`

---

## Pipeline Diario

```bash
# Ejecutar cada noche (2 AM)
python scripts/run_daily_batch.py

# Forzar re-ETL aunque el dataset no haya cambiado
python scripts/run_daily_batch.py --force-clean
```

---

## Usuarios de Prueba (seed)

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | admin@ico.com | admin123 |
| Vendedor | juan@ico.com | vend123 |
| Vendedor | sofia@ico.com | vend123 |
| Vendedor | carlos@ico.com | vend123 |

---

## Stack Técnico

| Componente | Tecnología |
|---|---|
| Modelo ML | PyTorch 2.x — NeuMF (GMF + MLP) |
| Backend | FastAPI + uvicorn + SQLAlchemy |
| Base de datos | SQLite (dev) → SQL Server (prod) |
| Autenticación | JWT (python-jose + passlib/bcrypt) |
| Frontend | Next.js 14 (App Router) |
| Datos | pandas + pyarrow (parquet) |

---

## Métricas de Evaluación

| Métrica | Descripción | Objetivo |
|---|---|---|
| NDCG@10 | Calidad del ranking (mide posición del ítem relevante) | > 0.30 |
| HitRate@10 | % usuarios donde el ítem test está en Top-10 | > 0.50 |
| Tasa de conversión | % pedidos con ≥1 ítem recomendado | > 0.20 |
| Rotation Coverage | % productos baja rotación recomendados | > 0.40 |
