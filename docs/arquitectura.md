# Arquitectura del Proyecto

## Arquitectura elegida

Vamos a desarrollar una API REST separada del frontend, organizada en capas:

- **Backend (FastAPI):** expone los endpoints agrupados por recurso (turnos, remitos, validaciones, stock, usuarios). La persistencia de datos se maneja con SQLModel contra una base PostgreSQL.
- **Frontend (React + TypeScript):** consume la API mediante TanStack Query, maneja el estado de sesión con Zustand, y muestra distintas pantallas según el rol del usuario logueado (rutas protegidas con React Router).
- **Base de datos (PostgreSQL):** modelo relacional, detallado en `/database/schema.md`.

## Tecnologías definitivas

- **Backend:** Python + FastAPI + SQLModel
- **Frontend:** React + TypeScript (Vite) + Tailwind CSS + TanStack Query/Table/Form + Zustand + React Router
- **Base de datos:** PostgreSQL
- **Autenticación:** JWT (OAuth2 Password Flow)
- **Despliegue:** backend en Render/Railway, frontend en Vercel/Netlify, base de datos en Render o Supabase

## Justificación

Elegimos separar el backend del frontend porque nos permite dividir el trabajo en paralelo entre los dos integrantes del equipo. Además, este es el stack que estamos viendo este cuatrimestre en Programación IV, así que lo vamos a poder profundizar a la vez que lo aplicamos acá.

La separación en capas dentro del backend hace que la lógica de aprobación (Calidad → disponibilidad de depósito → autorización de ingreso) esté centralizada en un solo lugar, sin repetirse en cada pantalla del frontend. Esto es importante porque son varias áreas (Guardia, Calidad, Depósito, Analista de Insumos) las que interactúan con el mismo remito en distintos momentos, y necesitamos que todas vean el mismo estado real, no una copia desactualizada.

## Fuera de alcance

Quedan fuera del desarrollo: la gestión interna del área de Compras (la negociación con proveedores), y el proceso de producción previo a que la mercadería llegue a Expedición ya aprobada.
