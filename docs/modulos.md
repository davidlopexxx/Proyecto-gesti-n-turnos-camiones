# Listado de Módulos

En base al problema que definimos en la propuesta (control de acceso, validación de calidad y gestión de stock para el ingreso y egreso de camiones), identificamos los siguientes módulos para el desarrollo:

| Módulo | Descripción | Prioridad |
|---|---|---|
| Autenticación y roles | Login con JWT y manejo de roles (Guardia, Calidad, Depósito de Insumos, Analista de Insumos, Depósito de Expedición), cada uno con acceso solo a sus pantallas | MVP |
| Gestión de turnos | Alta de turnos anticipados por el Analista de Insumos (fecha estimada y producto a recibir), y alta manual desde Guardia cuando el camión llega sin turno cargado | MVP |
| Control de acceso (Guardia) | Registro del camión y el chofer al llegar, carga de fotos de la documentación, y visualización del estado de aprobación antes de autorizar el ingreso | MVP |
| Validación de calidad | Carga del resultado del protocolo (pendiente / aprobado / rechazado), registro de la prueba física para productos que la requieren, y motivo de rechazo cuando corresponda | MVP |
| Gestión de depósito de insumos | Visualización de los remitos ya aprobados por Calidad, asignación de la ubicación de descarga según disponibilidad, y marcado de espera si no hay lugar | MVP |
| Actualización de stock | Registro de los movimientos de stock generados por cada remito (entrada o salida) | MVP |
| Panel del Analista de Insumos | Vista del stock disponible por depósito, para decidir qué reponer | MVP |
| Remitos de salida (Expedición) | Alta del remito de salida con el detalle de productos, cantidad de cajas y número de precinto | Nice to have |
| Verificación de precintos en salida | Chequeo de que el precinto físico coincida con el declarado en el remito antes de dejar salir al camión | Nice to have |
| Reportes básicos | Indicadores simples como tiempo de espera promedio o cantidad de camiones rechazados en un período | Nice to have |
| Notificaciones automáticas entre áreas | Avisos cuando cambia el estado de un remito | Fuera de alcance |
| Gestión de órdenes de compra | Seguimiento de los tickets que el Analista de Insumos envía al área de Compras (externa a la empresa en cuanto a este sistema) | Fuera de alcance |

Priorizamos los módulos de la entrada (turnos, control de acceso y validación de calidad) porque son los que resuelven el problema central que planteamos: hoy nadie puede confirmar de forma rápida y confiable si un camión ya fue aprobado por Calidad antes de descargarlo. Los módulos de Expedición y reportes quedan como segunda etapa, para sumar si el tiempo del equipo lo permite.
