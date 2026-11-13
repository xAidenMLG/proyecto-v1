# DECISIONS — Registro de decisiones

> Incluye decisiones APROBADAS, CONGELADAS, DESCARTADAS y sus razones.
> Actualizado en FASE 6 (2026-11-09).

---

## A. Decisiones estructurales congeladas (fases anteriores)

| # | Decisión | Estado |
|---|---|---|
| A1 | Contrato `dark-director/1` rev 3.2 congelado; phrasegen excluido de DMD v1 | VIGENTE, intacto |
| A2 | `dark_triphop.py` receta congelada (referencia de calidad, golden vigilado) | VIGENTE, intocable |
| A3 | `forge/` (todo el directorio) y `styles.py` solo-lectura para DMD | VIGENTE, 0 cambios |
| A4 | Arquitectura híbrida B/C: jazz_engine emite vocabulario midi-forge/1; MIDI Forge es el ÚNICO motor | VIGENTE |
| A5 | DMD no importa el motor salvo vía `forge_link` (perezoso, sin bytecode) | VIGENTE |
| A6 | Improvisación del sax vía `lead.phrases` nativo; Rhodes vía buffer post-generación | VIGENTE (Fase 4, re-validado Fase 5) |

## B. Decisiones FASE 5 (esta misión)

| # | Decisión | Razón | Alternativa descartada |
|---|---|---|---|
| B1 | **Un universo activo: `dark_triphop`.** Doom ARCHIVADO (no borrado): recetas registradas, perfiles operables, docs históricos intactos | Dirección comercial del usuario; «no destruir historia» | Borrar recetas doom (rompería compatibilidad y la misión lo prohíbe) |
| B2 | Unificación SIN tocar el contrato: metadata `IDENTIDAD_ACTIVA`/`IDENTIDADES_ARCHIVADAS` en `identities/__init__.py`; sin códigos E/W nuevos | Un nuevo código W sería un cambio de contrato; innecesario | Nueva revisión rev 3.3 con código de deprecación |
| B3 | Perfiles de identidad como DATO en `jazz_engine/profiles.py`; mecanismo genérico agnóstico | Separación mecanismo/decisión musical exigida por §2.E de la misión; portabilidad | Personalidades dentro de improv.py (acoplado) |
| B4 | Sax = frases nativas `lead.phrases` + `params.bends` del bloque lead (mecanismo existente); cero duplicación de scoop/fall/humanización | §2: no duplicar MIDI Forge | Motor de notas propio para el sax |
| B5 | Rhodes melódico como notas de buffer (Buf.add) post-generación, escuchando al sax real | Interacción real (no paralela); repara choques con prioridad correcta | Frases escritas para Rhodes (no permite escuchar al sax) |
| B6 | Drums/vibes como transformación PURA del proyecto (layers/fills/params en vocabulario nativo) | El resultado sigue siendo midi-forge/1 y generable SIN jazz_engine | Notas de buffer para batería (frágil, fuera de vocabulario) |
| B7 | Silencio del sax = apagar el bloque lead en secciones sin frase y sin material del compositor | El generativo nativo llenaría los huecos (improvisación constante prohibida) | Dejar el generativo (violaba el objetivo musical) |
| B8 | Desarrollo de motivo con verificación de diferencia audiblemente (≥30% eventos); reintentos deterministas | Detectado en prueba: reharmonize sobre la misma armonía producía frases idénticas | Aceptar transformaciones nulas |
| B9 | Presupuesto de eco del vibes evaluado sobre secciones CON frase del sax | El eco responde al sax; el criterio previo (coordinador antes del sax) dejaba ecos imposibles | Mantener `vibes_interviene` estático |
| B10 | Dados por sección (`seed\|motor\|sección`) en vez de streams compartidos | Robustez determinista; una tanda mala no silencia un mecanismo entero | Stream único compartido |
| B11 | Presets de variación (balanced/melodic/atmospheric/groove/sparse) como multiplicadores de densidad, NO como identidades | §12: variación controlada sin multiplicar recetas ni campos públicos | Nuevas identidades/fields de contrato |
| B12 | Pipeline mejorado normaliza SIEMPRE con `adapter.normalize` (paso oficial) | Canales/mono/defaults por rol; paridad con `run_generate` | Ctx directo sin normalizar (provocaba fallos de guardrails) |
| B13 | Comparativo 06 = sax+vibes (no vibes solo) | Con lead generativo denso no hay huecos: vibes solo no tiene efecto audible; el control válido es 02_sax | Vibes aislado sin sax |

## C. Defectos heredados encontrados y corregidos (higiene)

| # | Defecto | Corrección |
|---|---|---|
| C1 | `tests/dmd/test_recetas.py`: `finally` hacía `pop("doom_triphop")` incondicional (borraba la receta real según el orden de ejecución) | Restaurar estado previo en el `finally` |
| C2 | `tests/dmd/test_forge_link.py`: test escrito para el layout de auditoría (sin forge/ hermano) | Adaptado al layout final; la garantía del sandbox auditado sigue cubierta por el env var |
| C3 | Snapshot Fase 2 con inconsistencia aparente en registro de recetas | Era el defecto C1 bajo pytest; el registro real es correcto |

## D. Reglas musicales del universo (vigentes)

1. El groove mantiene el movimiento; la armonía proporciona el viaje; la atmósfera define el mundo; los instrumentos dan vida; la interacción crea la narrativa.
2. El sax NO tiene obligación de tocar en todas las secciones; establece motivo → desarrolla → desaparece.
3. El Rhodes es subordinado: soporte por defecto, respuestas breves, tope de notas, registro bajo el sax.
4. El vibráfono es intermitente (≤40% de compases); pocas notas con intención.
5. La batería conserva el groove trip-hop; fills solo en transiciones marcadas; ruptura con reconstrucción.
6. Prohibido: jam de jazz, arpegios genéricos, densidad constante, clímax permanentes.

## E. Decisiones FASE 6 (esta misión)

| # | Decisión | Razón | Alternativa descartada |
|---|---|---|---|
| F6-1 | **Perfiles de producción como DATO en `jazz_engine/production.py`** (`original/sax/sax_rhodes/drums/sax_vibes/full/atmospheric`), integrados en `coordinator.normalize_config` (preset = base, config explícita gana) | Reutiliza el ÚNICO mecanismo de config existente; presets reproducibles = configs exactas de los comparativos FASE 5 | Segundo sistema de configuración (prohibido por la misión §5) |
| F6-2 | **`density.sax`/`density.rhodes` NO se conectan al scheduler (F6-L1, CONGELADO)**. Los presets de variación siguen afectando solo drums/vibes + decisiones de perfil | Cualquier conexión cambiaría las decisiones del scheduler y rompería la regeneración byte-idéntica de las referencias aprobadas (02/03/07/08 usan ese comportamiento). Prioridad absoluta: conservar la calidad validada. Corrección diferida a revisión con escucha | Conectar `sax_density`/density al scheduler ahora (rompería 08_atmospheric y 02_sax dorados) |
| F6-3 | **`production="original"` = camino ORIGINAL OFICIAL** (`adapter.normalize` + `forge.engine.generate`, como `fase5_comparativos.py`); `config=None` sigue delegando 1:1 sin normalizar (contrato FASE 5 congelado) | La referencia dorada 01 se generó con normalize+generate; así el perfil reproduce el hash exacto | Hacer que `config=None` normalice (rompería el test de delegación FASE 5) |
| F6-4 | Errores claros: perfil desconocido → ValueError con lista de válidos; `original` + overrides de motores → ValueError | Misión §5.6 (fail-fast, configuración explícita) | Ignorar claves en silencio |
| F6-5 | Notas de motor (Rhodes/vibes eco) añadidas a la EVIDENCIA (sin efecto en bytes) | La auditoría necesita distinguir notas del motor del comping del compilador (los checks por-buffer contaban el comping y daban falsos fallos) | Checks post-hoc sobre buffers (imposible separar comping de motor) |
| F6-6 | Matriz de generalización = 5 composiciones × 6 perfiles (+sax_vibes en 2) = 32 runs committed con evidencia | Diversidad de contextos (tonalidad 5, BPM 78–92, 36–64 compases, 5–10 secciones, chord_bars 1–2, material escrito denso, tape_stop, sax sin focus) frente a volumen | Cientos de runs idénticos o solo cambio de seed (insuficiente, misión §6) |
| F6-7 | Sobreajuste: sin correcciones de código. 12/13 secuencias repetidas son recurrencia de motivo DENTRO de una composición (mecanismo de identidad por diseño) y pares sax/full idénticos por determinismo; 1/13 es un fragmento de 1 intervalo (colisión trivial) | La identidad REQUIERE consistencia; no hay fórmula congelada entre composiciones | "Arreglar" la recurrencia de motivos (destruiría la identidad) |
| F6-8 | `scripts/produce.py` = envoltorio fino sobre compilador + jazz_engine (sin render nuevo) + `--verify` de regeneración; índice automático | Misión §9: reutilizar herramientas existentes | Sistema de renderizado paralelo |
| F6-9 | Referencias doradas: sin duplicación de MIDI; se congelan IN SITU con `GOLDEN.md` + `manifests/golden_fase5.json` (34 archivos) + `manifests/verificar_golden.py` | La estructura existente ya contenía MIDI+config+proyecto+evidencia; faltaba catálogo de comportamiento/validación y manifiesto | Copiar los 8 escenarios a un directorio "golden" nuevo |
| F6-10 | Paquete auditivo copia 4 referencias doradas (hash-verificadas) para escucha de una sola carpeta | Comodidad de escucha explícita del paquete §10; la integridad queda anclada por hashes.json | Solo punteros (el usuario tendría que cazar archivos) |

## F. Hallazgos y observaciones FASE 6 (no requieren código)

| # | Hallazgo | Estado |
|---|---|---|
| F6-L1 | density.sax/rhodes inertes en decisiones de actividad (solo drums/vibes consumen density) | CONGELADO (F6-2); test_18 de fase6 lo fija |
| F6-O1 | Cola de release de la última nota del lead generativo puede salir ~1–2 beats del final del proyecto en estructuras cortas con chorus final (forge, protegido; su validador lo acepta: vigila inicios) | Documentado; sin acción |
| F6-O2 | El presupuesto del vibes siempre se satura (usadas == budget): es el diseño del coordinador (cuota = cap de presencia ≤40% de secciones; el echo_prob 0.5 sigue gateando notas reales) | Observación musical para escucha |
| F6-O3 | El drums engine no consume la seed de motores (transformación pura; el azar de layers lo pone el proyecto/forge) → perfil drums: seed no cambia el MIDI | Documentado; el check de variación por seed se aplica solo a sax/rhodes/vibes |
| F6-D1 | Detalle de contrato descubierto al generalizar: `ending.tape_stop.semitones` exige ENTERO 1–12 (la especificación de forge usa −8.4 interno) | Los docs de la matriz usan 8 (entero) |
| F6-D2 | Sax share en composición sin sax en focus (Casa de Espejos) = 0.5: el scheduler del sax es guiado por TIPO de sección (identidad), no por focus; no monopoliza y el protagonismo lo absorben Rhodes/vibes | Comportamiento válido pendiente de escucha |

## G. Decisiones FASE 7 — Harmonic Familiarity Engine

| # | Decisión | Justificación | Alternativa rechazada |
|---|---|---|---|
| F7-1 | La biblioteca vive en GRADOS funcionales; la adaptación traduce a la tonalidad/modo real | Una progresión sirve en cualquier tonalidad; familiaridad = movimiento de raíces, no notas concretas | Almacenar acordes concretos por tonalidad (explosión combinatoria) |
| F7-2 | Punto de integración ÚNICO: reescribir `sections[].chords` pre-enhance en `render.generate` | sax/Rhodes/vibes/bajos/pad heredan la armonía por el camino normal; 0 duplicación de MIDI Forge | Un motor de acompañamiento propio (violación del mandato: forge es el único motor) |
| F7-3 | La calidad del acorde sale de la ESCALA de la composición cuando el modo del arquetipo se relaja; manda el caso del numeral cuando coincide; excepción V/VII mayor en menor | Diatonía garantizada (verificado: 11.264 acordes, 0 violaciones) preservando el intento del arquetipo | Caso manda siempre (produce Fm7 fuera de escala en Am — F7-L1) |
| F7-4 | Secciones con material del compositor conservan su armonía (default `respetar_material: true`) | El material escrito JAMÁS se arriesga (misma regla que FASE 5) | Reescribir y arriesgar choques con el lead escrito |
| F7-5 | Cuota de ≤4 progresiones distintas por canción (CUOTA_DISTINTAS) con reasignación determinista | Una canción real vive de 2-4 progresiones; el greedy suelto repartía 6-7 (F7-L2) | Confiar solo en pesos de scoring (inestable) o 1 progresión fija (repetitivo) |
| F7-6 | `production: original` + harmony → ValueError | El camino ORIGINAL es inviolable (misma filosofía que F6 para overrides) | Aplicar armonía sin motores en original (rompería la reproducibilidad dorada) |
| F7-7 | Activación como clave `harmony` en el side-config existente + flags `--harmony*` en CLI/produce | Sin segundo sistema de config; contrato intacto | Campos nuevos en el JSON público (prohibido E109) |
| F7-8 | Colas de aproximación en rich: división a medio slot (dicts {chord, bars}) y solo con `chord_bars ≥ 1` | Transición musical entre secciones sin tocar `chord_bars` estructural | Cambiar el ritmo armónico (alteraría el groove aprobado) |

### Hallazgos FASE 7

| # | Hallazgo | Estado |
|---|---|---|
| F7-L1 | Calidad por caso rompe diatonía en relajación de modo | RESUELTO (F7-3) |
| F7-L2 | Greedy dispersa 6-7 progresiones por canción | RESUELTO (F7-5) |
| F7-O1 | El bajo de forge sigue raíces: inversiones `/` solo colorean voicing | Documentado (groove estable) |
| F7-O2 | `harmony` pasa como clave opaca de config; production.py/coordinator.py 0 cambios | Por diseño |

## H. Decisiones FASE 8 — ALBUM PRODUCTION SYSTEM

| # | Decisión | Justificación | Alternativa rechazada |
|---|---|---|---|
| F8-1 | El álbum es un **side-file** `album.json` con esquema propio `dmd-album/1` (validación fail-fast A1xx con errores acumulados) | Misma filosofía que la side-config de motores (F7-7): sin segundo sistema de configuración, contrato intacto | Campos nuevos en dark-director/1 (prohibido E109) o contratos paralelos |
| F8-2 | **Reutilización del núcleo de produce.py**: refactor que expone `producir_cancion()` (misma lógica, mismos artefactos, CLI idéntico); el álbum no genera MIDI propio | Misión §2: coordinar los motores existentes; cero duplicación de render/perfiles | Orquestador con su propio render (violación directa) |
| F8-3 | Semillas derivadas documentadas: `seed = semilla_album + 101*(índice+1)` cuando el spec no declara seed | Determinismo transparente y auditable sin inventar magia | RNG del álbum (reproducibilidad opaca) |
| F8-4 | La asignación de perfiles es una SUGERENCIA determinista (greedy: no consecutivos, menor uso, orden canónico; frac_max y ventana de respiro). Lo explícito del compositor SIEMPRE gana; violar restricciones → aviso W-A4, nunca error | Misión §3: «no imponer diferencias artificiales»; el compositor manda | Restricciones duras que bloqueen el plan |
| F8-5 | Un documento inválido NO aborta el álbum: se registra (A2xx/W-A9 + estado `fallo`) y el resto se produce | Misión §8: fallos parciales sin perder pistas válidas | Fail-fast global en planificación (perdería 12 pistas válidas por 1 rota) |
| F8-6 | **Drift de especificación** (doc/perfil/seed/harmony cambian): el resultado aceptado se PRESERVA y la pista queda `pendiente`; requiere `--regen` explícito | Misión §8: regenerar selectivamente sin alterar resultados ya aceptados | Regeneración automática silenciosa (impredecible) |
| F8-7 | Diversidad POST por **huellas técnicas** (eventos rol+paso16avos+clase de altura; Jaccard ≥0.85 = «sospechoso») + duplicados exactos SHA256 | Barato, determinista, sin parsing MIDI propio; separado explícitamente del juicio musical | Análisis de audio (no hay FluidSynth) o juicios automáticos de calidad |
| F8-8 | `album/` depende de dark_director+jazz_engine+produce.py; NADA importa `album/` | Capa de orquestación pura; los motores no conocen álbumes | Integrar la capa dentro de jazz_engine (acoplamiento) |
| F8-9 | La biblioteca de familiaridad en álbumes: SOLO declaración explícita por pista; `original`+harmony → A113; `familiarity_auto` nunca predeterminada (W-A3 informativa si el compositor la escribe) | Misión §5 y coherencia con F7-6/F7-7 | Activar armonía por defecto o auto en todo el álbum |

### Hallazgos FASE 8

| # | Hallazgo | Estado |
|---|---|---|
| F8-O1 | `harmony_select.normalizar_activacion` NO comprueba la existencia del ID de progresión (se valida después en el motor) | Esquema de álbum lo verifica contra `harmony_library.por_id` (A113) |
| F8-O2 | La evidencia de armonía de produce.py leía la clave `id` donde el motor escribe `entrada` (elección vacía en evidencia desde FASE 7) | Corregido en FASE 8 (solo evidencia; sin efecto en bytes) |
| F8-O3 | Calles de Neon con material escrito: familiar_pop reescribe solo intro/chorus_2 — `respetar_material` funciona en álbumes | Confirmado en producción real |
| F8-I1 | **Incidente de entorno**: una limpieza de archivos de prueba de esta sesión borró accidentalmente `docs/` del árbol | RECUPERADO al 100% desde git HEAD y verificado byte a byte contra `manifests/tree_fase7.json` (8/8 archivos idénticos). Lección: las limpiezas internas deben listar rutas explícitas de prueba, nunca genéricas |

## I. Decisiones DMD STUDIO (aplicación local de composición)

| # | Decisión | Justificación | Alternativa rechazada |
|---|---|---|---|
| DS-1 | **Backend Python local (FastAPI + uvicorn) y SPA estática propia, sin Node ni build step** | La misión exige backend local Python, arranque con un solo BAT en Windows 10 y venv independiente. Los motores son librería estándar: solo la capa web tiene dependencias (`requirements-studio.txt`). | Next.js/Node (entorno extra en el PC del compositor, choque con la arquitectura pedida) |
| DS-2 | **La generación web ejecuta `scripts/produce.py::producir_cancion()` en un subproceso aislado** (`python -m studio.runner`) | Reutilización literal del pipeline real (misma función que el CLI y el álbum): determinismo byte a byte web==CLI verificado. El aislamiento evita que un fallo del pipeline deribe el servidor y permite timeout/cancelación | Reimplementar el pipeline en JS (prohibido) o importarlo en el proceso del servidor (menos aislado) |
| DS-3 | **La UI no contiene catálogos hardcodeados**: `studio/capabilities.py` lee en vivo contrato, perfiles, keywords F7 y estado de audio | La interfaz refleja las capacidades reales del backend; si un motor cambia, la UI lo muestra sin tocar JavaScript | Duplicar los catálogos en JS (fuente de divergencia) |
| DS-4 | **Validación SIEMPRE con el validador real** (`dark_director.validador.validar` + `compilador.compilar` en preview y en generate con `validate_first`) | Único árbitro del contrato rev 3.2; la UI muestra specs de campos (FIELD_SPECS) solo como guía, jamás como filtro autoridad | Validador JS espejo (inventaría reglas) |
| DS-5 | **Un documento = un objeto vivo en el cliente**: el editor visual solo toca campos conocidos; el JSON editor reemplaza el objeto completo. Los `x_*` y campos válidos desconocidos nunca se eliminan | La misión exige no perder campos válidos que la UI no conoce; el validador real rechaza lo inválido (E109) | Normalizar el doc al guardar (borraría lo desconocido) |
| DS-6 | **Persistencia por archivos** (`studio_data/`), escritura atómica, historial solo al terminar; jobs persistidos y `recover_interrupted()` al arrancar | Sin base de datos compleja; un corte de luz deja `interrupted` y el proyecto íntegro (misión F5) | SQLite (innecesario para el volumen local) |
| DS-7 | **Single-flight: una sola generación activa** (2ª petición → 409) + timeout duro de 15 min | Evita generaciones simultáneas conflictivas y estados zombis | Cola de trabajos (innecesaria en uso local de escritorio) |
| DS-8 | **Seguridad**: bind 127.0.0.1, ids por patrón estricto, todo bajo `studio_data/`, sin ejecución de comandos del cliente, JSON nunca `eval` | Misión F4; probado contra traversal en la suite | Servir en 0.0.0.0 o aceptar rutas del cliente |
| DS-9 | Las generaciones del estudio NO actualizan `output/produccion/INDICE.md` (viven en `studio_data/`) | El índice es una conveniencia del CLI bajo `output/`; no afecta al MIDI ni a la evidencia | Forzar el índice (mezclaría salidas del estudio con el árbol histórico) |
| DS-10 | El convertidor antiguo (`app.py` + `web/`) no se reutiliza ni se repara | La misión lo excluye explícitamente; DMD STUDIO es una aplicación nueva | Parchear la interfaz anterior |

### Hallazgos DMD STUDIO

| # | Hallazgo | Estado |
|---|---|---|
| DS-O1 | `harmony_library.biblioteca()` devuelve un dict id→entrada (no lista) | Adaptado en `capabilities.py` (solo lectura) |
| DS-O2 | Los artefactos de produce.py viven dentro de la carpeta de salida (`out_dir/doc.json`, etc.); `out.name` define el nombre del MIDI | El backend lista las subcarpetas y sirve los archivos por patrón estricto |
| DS-O3 | El archivo de índice del CLI se escribe aunque la salida no esté bajo `output/` | Con `indice=False` en el runner (DS-9) |
| DS-O4 | Nombres con acentos: la whitelist ASCII inicial rechazaba «Composición» | Relajado a lista negra de caracteres peligrosos (ids de carpeta siguen saliendo de slugify) |
