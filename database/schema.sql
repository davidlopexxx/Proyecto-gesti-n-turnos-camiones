-- Esquema inicial de la base de datos
-- Sistema de Gestión de Turnos, Acceso y Remitos de Camiones

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL CHECK (rol IN ('guardia', 'calidad', 'deposito_insumos', 'analista_insumos', 'deposito_expedicion'))
);

CREATE TABLE proveedores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    cuit VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE productos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    tipo VARCHAR(50),
    requiere_prueba_fisica BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE depositos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('insumos', 'expedicion')),
    lugar_disponible BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE choferes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    dni VARCHAR(20) NOT NULL UNIQUE,
    telefono VARCHAR(30)
);

CREATE TABLE camiones (
    id SERIAL PRIMARY KEY,
    patente VARCHAR(15) NOT NULL UNIQUE
);

CREATE TABLE turnos (
    id SERIAL PRIMARY KEY,
    fecha_estimada DATE NOT NULL,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    proveedor_id INTEGER REFERENCES proveedores(id),
    creado_por INTEGER NOT NULL REFERENCES usuarios(id),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'confirmado', 'cancelado'))
);

CREATE TABLE remitos (
    id SERIAL PRIMARY KEY,
    turno_id INTEGER REFERENCES turnos(id),
    camion_id INTEGER NOT NULL REFERENCES camiones(id),
    chofer_id INTEGER NOT NULL REFERENCES choferes(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'salida')),
    numero_remito VARCHAR(50) NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    numero_precinto VARCHAR(50),
    deposito_id INTEGER REFERENCES depositos(id),
    estado_general VARCHAR(30) NOT NULL DEFAULT 'en_estudio_calidad'
);

CREATE TABLE remito_items (
    id SERIAL PRIMARY KEY,
    remito_id INTEGER NOT NULL REFERENCES remitos(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    unidad VARCHAR(20) NOT NULL,
    numero_lote VARCHAR(50),
    UNIQUE (producto_id, numero_lote)
);

CREATE TABLE validaciones_calidad (
    id SERIAL PRIMARY KEY,
    remito_id INTEGER NOT NULL REFERENCES remitos(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    motivo_rechazo TEXT,
    resultado_prueba_fisica VARCHAR(20) CHECK (resultado_prueba_fisica IN ('aprobado', 'rechazado')),
    fecha_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_resolucion DATE
);

CREATE TABLE movimientos_stock (
    id SERIAL PRIMARY KEY,
    remito_id INTEGER REFERENCES remitos(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    deposito_id INTEGER NOT NULL REFERENCES depositos(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'salida')),
    cantidad INTEGER NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX idx_camiones_patente ON camiones(patente);
CREATE INDEX idx_choferes_dni ON choferes(dni);
CREATE INDEX idx_remitos_estado_general ON remitos(estado_general);
