# Esquema de Base de Datos

```mermaid
erDiagram
    USUARIOS ||--o{ TURNOS : crea
    PROVEEDORES ||--o{ TURNOS : abastece
    PRODUCTOS ||--o{ TURNOS : contiene
    TURNOS ||--o| REMITOS : origina
    CAMIONES ||--o{ REMITOS : realiza
    CHOFERES ||--o{ REMITOS : conduce
    DEPOSITOS ||--o{ REMITOS : recibe
    REMITOS ||--o{ REMITO_ITEMS : contiene
    PRODUCTOS ||--o{ REMITO_ITEMS : es
    REMITOS ||--o{ VALIDACIONES_CALIDAD : tiene
    USUARIOS ||--o{ VALIDACIONES_CALIDAD : valida
    REMITOS ||--o{ MOVIMIENTOS_STOCK : genera
    PRODUCTOS ||--o{ MOVIMIENTOS_STOCK : es
    DEPOSITOS ||--o{ MOVIMIENTOS_STOCK : registra

    USUARIOS {
        int id PK
        string nombre
        string email
        string password_hash
        string rol
    }
    PROVEEDORES {
        int id PK
        string nombre
        string cuit
    }
    PRODUCTOS {
        int id PK
        string codigo
        string nombre
        string tipo
        boolean requiere_prueba_fisica
    }
    DEPOSITOS {
        int id PK
        string nombre
        string tipo
        boolean lugar_disponible
    }
    CHOFERES {
        int id PK
        string nombre
        string dni
        string telefono
    }
    CAMIONES {
        int id PK
        string patente
    }
    TURNOS {
        int id PK
        date fecha_estimada
        int producto_id FK
        int proveedor_id FK
        int creado_por FK
        string estado
    }
    REMITOS {
        int id PK
        int turno_id FK
        int camion_id FK
        int chofer_id FK
        string tipo
        string numero_remito
        date fecha
        string numero_precinto
        int deposito_id FK
        string estado_general
    }
    REMITO_ITEMS {
        int id PK
        int remito_id FK
        int producto_id FK
        int cantidad
        string unidad
    }
    VALIDACIONES_CALIDAD {
        int id PK
        int remito_id FK
        int usuario_id FK
        string estado
        string motivo_rechazo
        string resultado_prueba_fisica
        date fecha_inicio
        date fecha_resolucion
    }
    MOVIMIENTOS_STOCK {
        int id PK
        int remito_id FK
        int producto_id FK
        int deposito_id FK
        string tipo
        int cantidad
        date fecha
    }
```

## Notas sobre campos clave

- **`TURNOS.estado`**: `pendiente` / `confirmado` / `cancelado`. Lo carga el Analista de Insumos al coordinar una entrega con el proveedor, o la Guardia si el camión llega sin turno previo.
- **`VALIDACIONES_CALIDAD.estado`**: `pendiente` / `aprobado` / `rechazado`. Mientras está en `pendiente`, el camión "está en estudio".
- **`VALIDACIONES_CALIDAD.motivo_rechazo`**: se completa solo si `estado = rechazado`. Es lo que la Guardia consulta para informarle al chofer por qué no puede ingresar.
- **`VALIDACIONES_CALIDAD.resultado_prueba_fisica`**: solo aplica a productos con `requiere_prueba_fisica = true` (azúcar, leche en polvo); queda nulo para el resto.
- **`DEPOSITOS.lugar_disponible`**: lo controla el Depósito de Insumos antes de asignar una ubicación al remito.
- **`REMITOS.estado_general`**: resume el estado global del remito para la vista de Guardia (por ejemplo: `en_estudio_calidad`, `rechazado`, `esperando_lugar`, `listo_para_ingreso`, `ingresado`).
