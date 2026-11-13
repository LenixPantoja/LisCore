# Módulo de Alarmas y Críticos — CoreLab LIS

Este documento tiene dos partes:

- **Parte 1 — Puesta en marcha y parametrización.** Para el administrador del sistema y el director técnico del laboratorio. Qué hay que instalar y configurar para que el módulo funcione bien.
- **Parte 2 — Manual de uso.** Para bacteriólogos y auxiliares. Qué hacer cuando aparece una alarma.

---

## ¿Qué hace el módulo?

Cuando un resultado de laboratorio pasa un límite peligroso, el sistema:

1. Lo detecta en el momento en que llega, ya sea desde el analizador o digitado en el LIS.
2. Avisa en cualquier pantalla del sistema con una tarjeta y un sonido, y muestra un contador en el botón **Alarmas y Críticos** del menú.
3. Guía al bacteriólogo para avisar al médico y registrar el aviso, con verificación de lectura.
4. Controla el tiempo: si nadie registra el aviso a tiempo, la alarma se **escala** sola.
5. Deja todo registrado: quién avisó, a quién, por qué medio, a qué hora y qué conducta se tomó.

Hay tres niveles de alarma:

| Nivel | Significado | Qué hacer |
|---|---|---|
| **Pánico** (rojo) | Riesgo vital para el paciente. | Avisar al médico **de inmediato**. |
| **Crítico** (naranja) | Valor muy alterado. | Avisar dentro del turno, en el tiempo configurado. |
| **Delta** (azul) | Cambio brusco frente al resultado anterior del mismo paciente. | Revisar si el cambio es real y avisar. |

---

# PARTE 1 — Puesta en marcha y parametrización

## 1. Instalación (una sola vez)

### 1.1 Scripts de base de datos

Correr en pgAdmin, **en este orden**, los scripts de `migrations/sql/`. Se pueden correr varias veces sin problema y ninguno borra datos.

| Script | Qué hace |
|---|---|
| `062_alarmas_criticos.sql` | Crea las tablas de reglas, alarmas e historial, crea los permisos y carga 14 **reglas sugeridas inactivas**. |
| `063_alarmas_mensajes_clinicos.sql` | Agrega el **mensaje clínico** (posible patología) a cada límite. |
| `064_alarmas_embarazo.sql` | Permite reglas para **embarazadas** y por semanas de gestación. |
| `065_alarmas_por_empresa.sql` | Permite reglas **exclusivas de una empresa** (cliente). |

Si el backend se despliega antes que un script, el módulo sigue funcionando sin esa función. Sin el 062, la pantalla muestra *"El módulo de alarmas no está instalado"*.

### 1.2 Despliegue

1. Desplegar el **backend** y luego el **frontend**.
2. En cada computador, recargar con **Ctrl + F5**.

La detección corre sola dentro del backend: no hay que programar tareas ni servicios aparte. Revisa los resultados al instante y además hace un barrido cada minuto.

### 1.3 Permisos

El script 062 crea tres permisos y los asigna así:

| Permiso | Permite | Se asignó automáticamente a |
|---|---|---|
| `Alarms:List` | Ver la bandeja, el contador del menú y los avisos. | Roles que validan resultados y roles que administran pruebas. |
| `Alarms:Manage` | Registrar la notificación, la confirmación del médico, escalar, agregar notas y cerrar alarmas. | Los mismos roles. |
| `Alarms:Rules` | Crear, editar, activar y eliminar valores críticos. | Roles que editan pruebas. |

Revise en **Usuarios › Roles** que:

- Los **bacteriólogos** tengan `Alarms:List` y `Alarms:Manage`.
- Los **auxiliares** que vayan a llamar al médico tengan también esos dos permisos. Si solo deben ver las alarmas, basta con `Alarms:List`.
- Solo el **director técnico o el coordinador** tengan `Alarms:Rules`.

Quien no tiene permiso no ve el contador ni recibe avisos, y no le aparecen errores.

## 2. Datos que el módulo necesita

El módulo usa información que se registra en otras pantallas. Si esa información falta, el módulo funciona peor:

| Dato | Dónde se registra | Para qué lo usa el módulo |
|---|---|---|
| **Médico de la orden** | Ingreso de la orden. | Saber a quién avisar. |
| **Teléfono y correo del médico** | Maestros › Médicos. | Botones *Llamar*, *WhatsApp* y *Correo*. Sin teléfono, el bacteriólogo tiene que buscarlo. |
| **Fecha de nacimiento y sexo del paciente** | Pacientes. | Elegir la regla por edad y sexo. Sin fecha de nacimiento, las reglas con rango de edad no aplican. |
| **Embarazo y semanas de gestación** | Ingreso de la orden. | Reglas para embarazadas. Si no se escriben las semanas, solo aplican las reglas de embarazo **sin** rango de semanas. |
| **Empresa de la orden** | Ingreso de la orden. | Reglas exclusivas por cliente. |

> **Recomendación:** pida al personal de admisión que registre siempre el médico y, en embarazadas, las semanas de gestación.

## 3. Configurar los valores críticos

Los valores críticos se configuran **en cada prueba**:

**Maestros › Pruebas › (editar la prueba) › sección "Valores críticos"**

Son **independientes** de los rangos de referencia. El rango "CRÍTICO" de los rangos de referencia solo marca el resultado en el reporte y no genera alarmas.

### 3.1 Reglas sugeridas

El script 062 dejó **14 reglas sugeridas inactivas**, con valores habituales en adultos: potasio, sodio, glucosa, calcio, calcio iónico, magnesio, hemoglobina, hematocrito, plaquetas, leucocitos, INR, PTT, creatinina y bilirrubina total. Aparecen con la etiqueta **"Sugerida"**.

> ⚠ **No las active sin revisarlas.** Los límites y los mensajes clínicos son solo una propuesta. El director técnico debe ajustarlos a la política del laboratorio y a la población que atiende.

### 3.2 Campos de una regla

Botón **Agregar regla**, o **Editar regla** en una existente:

| Campo | Explicación |
|---|---|
| **Empresa (cliente)** | Vacío = aplica a todas las órdenes. Con una empresa, la regla es **exclusiva** de esa empresa (ej. una clínica renal con límites propios de creatinina). |
| **Sexo** | Ambos, hombres o mujeres. |
| **Edad desde / hasta** y **Edad en** | Rango de edad en años, meses o días. Vacío = todas las edades. La edad se calcula **a la fecha de la orden**. |
| **Embarazo** | *Aplica a todas*, *Solo embarazadas* (con semanas de gestación opcionales) o *Solo no embarazadas*. |
| **Pánico bajo / Crítico bajo / Crítico alto / Pánico alto** | Límites de la alarma. Deje vacío el que no aplique. |
| **Posible patología** (debajo de cada límite) | Mensaje clínico que verá el bacteriólogo y que se le comunica al médico. Ej.: plaquetas > 1000 → "Trombosis". |
| **Delta (%)** y **Comparar con últimos N días** | Genera alarma Delta si el resultado cambia ese porcentaje o más frente al resultado anterior del mismo paciente, de otra orden, dentro de esos días. |
| **Avisar al médico en (min)** | Tiempo meta para registrar el aviso. Si se pasa, la alarma se **escala** automáticamente. Se sugiere 15 min para pánico y 30 min para crítico. |
| **Bloquear validación** | Si se marca, **no se puede validar** ese resultado en Laboratorio hasta registrar la notificación al médico. Recomendado para los pánicos. |
| **Regla activa** | Solo las reglas activas generan alarmas. |
| **Nota** | Texto interno, por ejemplo "Aprobado por dirección, nov-2026". |

**Cómo se comparan los límites:** la alarma salta si el resultado es **estrictamente menor** que el límite bajo o **estrictamente mayor** que el límite alto. Con pánico alto en 500, un resultado de 500 **no** es pánico y uno de 500.1 **sí**.

Los límites deben ser coherentes: pánico bajo ≤ crítico bajo < crítico alto ≤ pánico alto. El formulario no deja guardar valores contradictorios y muestra en palabras cómo funcionará la regla.

### 3.3 Varias reglas para la misma prueba

Una prueba puede tener varias reglas. El sistema usa **la más específica para cada paciente**, en este orden:

1. Regla de la **empresa** de la orden.
2. Regla de **embarazadas con rango de semanas**.
3. Regla de **embarazadas** sin semanas, o de **no embarazadas**.
4. Regla por **sexo**.
5. Regla por **edad**.
6. Regla general.

*Ejemplo:* hemoglobina con una regla general (pánico < 7) y otra para embarazadas de 28 a 40 semanas (pánico < 8):

- una gestante de 30 semanas usa la de embarazo;
- una gestante sin semanas registradas, o una paciente no embarazada, usa la general.

### 3.4 Después de activar reglas

- Las reglas aplican a los resultados que lleguen **desde ese momento**.
- Para revisar también los resultados de las últimas 24 horas, use **Revisar últimas 24 h**, en la misma sección.

### 3.5 Eliminar o desactivar

- Una regla que **nunca generó alarmas** se puede **Eliminar**.
- Una regla que **ya generó alarmas** no se puede eliminar, para conservar la trazabilidad. Desactívela con el interruptor **Activa**.

## 4. Comportamiento automático (para tenerlo en cuenta)

| Situación | Qué hace el sistema |
|---|---|
| Llega un resultado que pasa un límite | Crea la alarma al instante. Las pruebas calculadas por fórmula se revisan en menos de 1 minuto. |
| Nadie registra el aviso dentro del tiempo meta | La alarma pasa a **Escalada** y lo deja en la trazabilidad. |
| La alarma **empeora** (ej. de crítico a pánico) | Vuelve a avisar con tarjeta y sonido. Si ya se había notificado, la deja otra vez **Sin notificar**. |
| El resultado se corrige a un valor normal **antes** de avisar | Cierra la alarma automáticamente y deja la explicación. |
| El resultado se corrige **después** de avisar | Deja la alarma abierta y anota el cambio. El bacteriólogo la cierra. |
| Se borra el resultado, se descarta la prueba o se anula la orden | Cierra la alarma automáticamente si no se había notificado. |
| Una alarma se cerró y el resultado vuelve con el **mismo** valor | No crea una alarma repetida. |
| Órdenes antiguas | Solo revisa órdenes de los **últimos 3 días**. Al reiniciar el backend revisa las últimas 12 horas. |
| Resultados no numéricos | No se evalúan, salvo valores como "<0.5" o ">1000", que se toman como 0.5 y 1000. |

**Origen del valor.** Cada alarma indica de dónde salió el resultado:

- **Analizador** y su nombre (ej. DYMINDUN73);
- **Digitado por** *usuario*, que indica si corrigió un valor que venía del equipo;
- **Calculado por fórmula**.

---

# PARTE 2 — Manual para bacteriólogos y auxiliares

## 1. ¿Cómo me entero de una alarma?

- **Tarjeta de aviso** en la esquina de la pantalla, en cualquier módulo del sistema. Muestra el nivel, la prueba, el valor, la posible patología, el paciente y la orden. **Tóquela** para ir directo a la alarma.
- **Sonido** tipo monitor clínico:
  - Pánico: dos ráfagas de 5 pulsos.
  - Crítico: 3 pulsos.
- **Contador** en el botón **Alarmas y Críticos** del menú, con las alarmas que faltan por avisar. Se pone rojo y parpadea si hay un pánico. Con el menú contraído aparece un punto rojo sobre la campana.

> **Sonido.** Se activa o silencia con el botón de parlante en la pantalla de Alarmas, y cada computador recuerda su preferencia. Si no suena:
> 1. Revise el volumen del equipo.
> 2. Haga clic una vez en cualquier parte de la página, porque el navegador exige una interacción antes de reproducir sonido.

## 2. La pantalla de Alarmas y Críticos

**Arriba, los indicadores:**
- alarmas abiertas;
- sin notificar;
- **fuera de tiempo**;
- tiempo medio de aviso y porcentaje avisado a tiempo (últimos 30 días).

**A la izquierda, la bandeja.** Las alarmas aparecen ordenadas: primero los pánicos y las que llevan más tiempo esperando. Cada una muestra:
- nivel, prueba y valor (con flecha ↑ alto / ↓ bajo);
- posible patología;
- número de orden, sede, paciente y área;
- una barra de tiempo: verde, luego amarilla y roja cuando se vence;
- su **estado**, en una cápsula de color:

| Estado | Significado |
|---|---|
| ● **Sin notificar** | Hay que avisar al médico. |
| ● **Escalada** | Se venció el tiempo o se escaló al coordinador. **Urgente.** |
| ● **Notificada** | Ya se avisó al médico. |
| ● **Médico confirmó** | El médico confirmó que recibió el resultado. |
| ● **Cerrada** | Gestión terminada. |

**Filtros:**
- por estado (Activas, Sin notificar, Escaladas…);
- por nivel y por área;
- búsqueda por **número de orden, documento, nombre del paciente o prueba**;
- las cerradas, por rango de fechas.

**A la derecha, el panel de detalle:**
1. **Paciente:** nombre, documento, edad, sexo, teléfono y embarazo.
2. **Resultado:** prueba, valor, límite superado, rango de referencia, límites de pánico y críticos, resultado anterior y **origen del valor**.
3. **Orden**, desplegable: número, sede, servicio, área, empresa y enlace **Abrir en Laboratorio**.
4. **Médico a notificar**, desplegable: datos y contacto.
5. **Trazabilidad**, desplegable o con el botón **Ver trazabilidad**: todo lo que ha pasado con la alarma.

## 3. Paso a paso: atender una alarma

1. **Abra la alarma.** Toque la tarjeta de aviso o pulse **Atender** en la bandeja.
2. **Revise el resultado.** Antes de llamar, mire en *Resultado*:
   - el **origen del valor**: ¿lo envió el analizador o lo digitaron?;
   - el **resultado anterior**: ¿el paciente ya venía con valores así?
   - Si sospecha un error de muestra (hemólisis, coágulo, contaminación con suero IV), vaya al paso 7.
3. **Pulse "Atender alarma".** Se abre la ventana de gestión.
4. **Contacte al médico:**
   - **Llamar:** marca el número del médico.
   - **WhatsApp:** abre WhatsApp con el mensaje ya escrito (paciente, orden, prueba, valor y posible patología). Envíelo y luego registre la notificación.
   - **¿Qué digo? Ver guion:** muestra el texto sugerido para la llamada.
   - Si la orden no tiene médico o el médico no tiene teléfono, avise al **servicio** que solicitó el examen.
5. **Verificación de lectura (obligatoria en llamada y presencial).** Pida al médico que **repita el valor y el nombre del paciente**. Si lo repite bien, marque la casilla *Verificación de lectura*.
6. **Registre la notificación:**
   - elija el medio (Llamada, WhatsApp, Presencial, Correo);
   - escriba **a quién avisó**, con nombre y cargo;
   - agregue una observación si hace falta (ej. "el médico indica repetir la muestra");
   - pulse **Registrar notificación**.

   La alarma pasa a **Notificada** y se guarda la hora, el usuario y el tiempo que tomó.
7. **Cierre la alarma.** Pulse **Cerrar alarma** y escriba la conducta. Puede elegir un motivo rápido o escribirlo:
   - "Médico informado; paciente en manejo";
   - "Paciente remitido a urgencias";
   - "Se repitió la muestra y se confirmó el valor".

   **Si el resultado no era válido** (muestra hemolizada, coagulada o insuficiente, error de digitación), puede cerrar la alarma **sin notificar**, pero tiene que escribir el motivo. Queda registrado.

Si el médico llama de vuelta para confirmar que recibió el resultado, pulse **El médico confirmó que recibió el resultado** antes de cerrar.

## 4. Situaciones frecuentes

| Situación | Qué hacer |
|---|---|
| **No contesta el médico** | Pulse **Agregar nota** (ej. "3 intentos, no contesta, 3:10 pm"). Si no logra comunicarse, pulse **Escalar al coordinador** y escriba a quién informó. |
| **La alarma pasó a "Escalada" sola** | Se venció el tiempo meta. Avise **ya** al médico o al coordinador y registre la notificación. |
| **Al validar en Laboratorio sale "Validación bloqueada"** | Ese resultado tiene un valor crítico que exige avisar primero. Registre la notificación en Alarmas y Críticos (toque el mensaje para ir directo) y vuelva a validar. |
| **El valor cambió después de crear la alarma** | El panel muestra "Luego cambió a…". Si empeoró de nivel, el sistema vuelve a avisar. Revise y notifique de nuevo si corresponde. |
| **El resultado era un error y ya lo corregí** | Si aún no se había avisado, la alarma se cierra sola. Si ya se avisó, ciérrela explicando la corrección. |
| **Ya avisé, pero quiero dejar constancia de otra llamada** | En la ventana *Atender* use **Registrar otro aviso**. |
| **Necesito ver el historial completo** | **Ver trazabilidad** muestra cada paso: detección, cambios, avisos, escalamientos y cierre, con usuario y hora. |

## 5. Reglas de oro

1. **Un pánico se avisa de inmediato.** No espere a terminar otra tarea.
2. **Siempre verificación de lectura:** el médico repite el valor y el nombre del paciente.
3. **Registre en el momento**, no al final del turno: la hora del registro es la que cuenta para el indicador.
4. **Nunca cierre una alarma real sin avisar.** Cerrar "sin notificar" es solo para resultados no válidos, con el motivo escrito.
5. Si hay dudas sobre la muestra, **repítala**, pero **avise igual** si el valor es de pánico y no puede descartarlo a tiempo.

---

## Preguntas frecuentes (soporte)

**Un resultado alterado no generó alarma. ¿Por qué?** Revise, en este orden:
1. La prueba tiene una regla **activa**, en Pruebas › Valores críticos.
2. El valor pasa el límite **estrictamente**: 500 no supera "mayor que 500".
3. La regla aplica a ese paciente: sexo, edad (con fecha de nacimiento registrada), embarazo y semanas, empresa.
4. La orden es de los **últimos 3 días** y no está anulada.
5. El resultado es numérico.
6. No había ya una alarma **cerrada** con ese mismo valor.
7. Si la regla se activó después de llegar el resultado, use **Revisar últimas 24 h**.

**No veo el botón ni el contador de alarmas.** Su rol no tiene el permiso `Alarms:List`. Solicítelo al administrador.

**No me deja crear ni editar valores críticos.** Requiere el permiso `Alarms:Rules`, que normalmente tiene solo el director técnico o el coordinador.

**La pantalla dice "El módulo de alarmas no está instalado".** Falta correr el script `062_alarmas_criticos.sql`.
