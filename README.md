# Propuesta de Trabajo Final Integrador
## Sistema de Gestión de Turnos, Acceso y Remitos de Camiones

**Equipo:** Leandro López y Ángel López

---

## 1. Problema y contexto

El proyecto aborda el proceso de ingreso y egreso de camiones en una fábrica de alimentos (golosinas), incluyendo el control de acceso, la validación de calidad de los insumos y la gestión de remitos, tanto de entrada como de salida.

**Actores involucrados:**

- **Chofer/transportista:** llega con insumos para descargar o retira producto terminado.
- **Guardia/Portería:** recibe al chofer fuera del establecimiento, controla la documentación, y una vez aprobado el ingreso por Calidad y Depósito, autoriza la entrada física y controla los precintos en la salida.
- **Laboratorio/Calidad:** valida el protocolo de calidad de cada insumo que ingresa, con una prueba física adicional para los casos de azúcar y leche en polvo. También audita la mercadería en la línea de producción antes de que se empaquete, por lo que lo que llega a Expedición ya está aprobado.
- **Depósito de Insumos:** verifica si hay lugar disponible en el depósito de destino y coordina la descarga; si no hay lugar, el camión espera afuera hasta que se libere.
- **Depósito de Expedición:** arma pallets con producto ya aprobado, genera los remitos de salida (con código de producto y cantidad de cajas) y coloca los precintos de seguridad.
- **Administración/Compras:** concilia los remitos de entrada y salida.

**Problema central:** hoy, la autorización de un camión depende de una cadena de avisos manuales entre tres áreas (Calidad → Insumos → Guardia), sin una fuente de información común. Esto genera camiones colapsados esperando afuera de la fábrica, y un riesgo más serio: que Depósito descargue mercadería sin que Calidad haya confirmado realmente su aprobación, porque no existe una forma simple de verificar ese estado sin volver a preguntar. En la salida, el control de integridad (que el precinto físico coincida con el remito) también depende de un chequeo manual sin registro.

**Impacto:** tiempos muertos y fastidio de los transportistas, riesgo de incumplimiento del protocolo de calidad, y falta de trazabilidad sobre quién aprobó una descarga y cuándo — algo especialmente sensible en una empresa alimenticia ante una eventual auditoría.

**Valor agregado de la solución:** un estado único y consultable del remito (en revisión / aprobado / rechazado, con lugar asignado o no) que las tres áreas consultan desde la misma fuente, con registro auditable de cada aprobación. Depósito ya no puede asumir que un camión está aprobado si el sistema no lo confirma.

---

## 2. Solución propuesta y stack tecnológico

**Tecnologías elegidas:**

- **Backend:** Python + FastAPI + SQLModel (ORM)
- **Frontend:** React + TypeScript (Vite) + Tailwind CSS, con TanStack Query/Table/Form para consumo de datos y formularios, y Zustand para estado global
- **Base de datos:** PostgreSQL
- **Autenticación:** JWT (OAuth2 Password Flow)
- **Despliegue:** backend en Render/Railway, frontend en Vercel/Netlify, base de datos en Render o Supabase
- **Entornos de desarrollo:** IntelliJ IDEA (backend) y Visual Studio Code (frontend)

**Justificación:** para definir el stack, el equipo relevó los contenidos del programa de Programación IV correspondientes a este cuatrimestre y detectó las herramientas que se van a trabajar en profundidad durante el año (FastAPI, SQLModel, React, TypeScript, TanStack Query/Table/Form, Zustand, JWT). De ese análisis se concluyó que estas son las tecnologías más convenientes para el proyecto, ya que el equipo las va a ir incorporando y practicando en paralelo a su desarrollo. Python es además el lenguaje usado desde el inicio de la carrera. FastAPI resuelve de entrada la documentación automática de la API (Swagger/ReDoc) y la validación de datos con Pydantic, mientras que SQLModel simplifica la persistencia contra PostgreSQL. React con rutas protegidas y JWT permite diferenciar bien los roles (Guardia, Laboratorio, Depósito, Compras/Logística, Administración), cada uno con su login y sus vistas.

**Escalabilidad:** el stack elegido sobra en capacidad para el volumen de una planta con varios roles y un flujo diario acotado de camiones. Al ser una API REST separada del frontend, es sencillo sumar a futuro un cliente adicional (por ejemplo, una app para choferes) sin rehacer el backend.

**Limitaciones y riesgos:** separar frontend y backend en dos proyectos implica coordinar dos despliegues en la nube en vez de uno, y sincronizar los contratos de API entre ambos lados a medida que el proyecto avanza. Se acepta ese costo porque permite dividir el trabajo en paralelo entre los dos integrantes (frontend / backend) de forma más clara que con un enfoque monolítico, lo cual ayuda dado el tiempo acotado que tiene el equipo por semana.

---

## 3. Refinamiento, análisis de competencia y viabilidad

**Propuesta de valor refinada:** un sistema centralizado que reemplaza la cadena de avisos manuales entre Guardia, Laboratorio y Depósito por un estado único y auditable del remito, evitando que un camión sea descargado sin la aprobación real de calidad, y reduciendo el tiempo de espera de camiones fuera de la fábrica al eliminar el ida y vuelta telefónico entre áreas.

**Análisis de competencia y diferenciación:** existen soluciones de mercado tipo WMS/ERP (SAP WM, Odoo Inventory, sistemas de Yard Management genéricos) que cubren la gestión de depósito en general. Sin embargo, para una fábrica de un solo establecimiento representan una sobrecarga: están pensadas para múltiples plantas y flujos logísticos complejos, requieren licenciamiento o implementación costosa, y no traen resuelta de fábrica la regla de negocio específica de esta empresa — la validación cruzada de calidad antes de autorizar una descarga. Nuestra solución no compite en amplitud de funciones, sino en el ajuste exacto al proceso real de la planta, con un costo de desarrollo y despliegue prácticamente nulo.

**Plan de trabajo:**

| Etapa | Plazo | Foco |
|---|---|---|
| Propuesta y repositorio | hasta 30/08 | Documento de propuesta, definición de alcance, repo creado |
| Diseño y módulos (Regular) | hasta 27/09 | Esquema de base de datos, modelos SQLModel, endpoints REST, listado de módulos |
| Desarrollo del núcleo | hasta ~20/10 | Turnos, control de acceso, validación de calidad (el diferenciador del proyecto) |
| Desarrollo complementario | hasta ~05/11 | Depósito de insumos, expedición, panel de visibilidad |
| Cierre | hasta 14/11 | Despliegue, informe, video, repaso general |

**Evaluación de viabilidad:**

- **Técnica (riesgo bajo):** FastAPI, React y PostgreSQL son tecnologías maduras y con documentación abundante, y el equipo va a estar desarrollando práctica directa con ellas a lo largo del cuatrimestre, lo que reduce el riesgo de aprendizaje que normalmente implicaría adoptar un stack nuevo.
- **Operativa (riesgo bajo-medio):** el conocimiento del proceso real por parte de uno de los integrantes es una ventaja fuerte para el relevamiento, aunque requiere buena coordinación entre los dos, trabajando de forma remota y asincrónica.
- **Temporal (riesgo bajo-medio):** con un compromiso estimado de 10 horas semanales por integrante (20 horas semanales de equipo), y considerando las 7 semanas entre el 27/09 y el 14/11, el equipo dispone de aproximadamente 140 horas para el desarrollo. Es un margen ajustado pero razonable si se prioriza el núcleo del sistema (turnos, acceso y validación de calidad) antes que los módulos complementarios.

**Uso de IA:** se utilizó como herramienta para explorar casos borde del proceso relevado (por ejemplo, qué ocurre si el depósito no tiene lugar disponible) y para revisar la consistencia del flujo, pero las decisiones de alcance y arquitectura fueron discutidas y definidas por el equipo.



---

## Estructura del repositorio

- `/backend` — API REST (Python + FastAPI + SQLModel)
- `/frontend` — Aplicación web (React + TypeScript)
- `/database` — Esquema de base de datos (`schema.md`) y script de creación de tablas (`schema.sql`)
- `/docs` — Documentación del proyecto: listado de módulos y arquitectura
