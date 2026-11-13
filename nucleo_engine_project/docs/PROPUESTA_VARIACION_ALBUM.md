# PROPUESTA — Variación de álbum (FASE 7 candidata)

> FASE 6 §9.2: propuesta DOCUMENTADA, sin expansión de código. Diseño para que
> un álbum de ~13 canciones no suene como 13 copias de una receta, ni como
> 13 géneros distintos.

## 1. Principio

**Consistencia de identidad, diversidad de composición.** La identidad vive en
la receta `dark_triphop` + perfil de identidad DTH (groove, registros, celdas,
comportamientos). La diversidad de un álbum debe venir —en este orden— de:

1. **Composición** (documento dark-director/1): tonalidad, progresiones,
   estructura, energías, densidades, material escrito. Es la fuente principal
   y ya está soportada hoy (matriz de generalización FASE 6).
2. **Perfil de producción**: qué motores participan y con qué actitud
   (`original … atmospheric`).
3. **Seed**: variación de frases/motivos con la misma identidad.

## 2. Espacio de variación recomendado por canción

| Dimensión | Rango sano | Riesgo si se abusa |
|---|---|---|
| Perfil | alternar original/sax/full/atmospheric | todo-full = saturación del álbum |
| BPM | 76–92 | >95 deja de ser trip hop |
| Tonalidad | relativas menores cercanas (Dm, Gm, Cm, Am, F#m…) | semitonos consecutivos rompen continuidad |
| Estructura | 36–64 compases, 5–10 secciones | <30 compases no desarrolla |
| Energía media | 0.35–0.6 con picos ≤0.85 | clímax permanente |
| Densidad media | B1–B2 dominante, B3 puntual | fatiga |
| Seeds | 1 por canción | — |

Regla de oro: **una sola dimensión "especial" por canción** (o el break con
tape_stop, o el bridge tenso, o la textura vibes, no todo a la vez).

## 3. Mecánica propuesta (FASE 7, si se aprueba)

Un `album.json` (side-file, NO contrato) con una lista de entradas:

```json
{
  "album": "Noches Largas",
  "identidad": "dark_triphop",
  "curva_energia": [0.4, 0.55, 0.5, 0.7, 0.45, 0.8, 0.5],
  "canciones": [
    {"doc": "docs/cancion_01.json", "perfil": "sax", "seed": 3101},
    {"doc": "docs/cancion_02.json", "perfil": "full", "seed": 3102}
  ]
}
```

Y un comando fino que recorra la lista llamando a `scripts/produce.py`
(algorithm = el que ya existe; el generador de álbumes solo decide *qué*
ejecutar y valida la curva de energía del conjunto). **No** generaría documentos
por sí mismo: los docs los escribe el compositor (humano o flujo aparte).

## 4. Chequeos de álbum (nuevos, baratos)

- Ningún par de canciones consecutivas con mismo perfil + misma tonalidad + BPM
  igual (colchón de variedas).
- Distribución de perfiles: máximo ~40% del álbum en un mismo perfil.
- Al menos una pieza `original` o `sparse` por cada 5 canciones (respiro).
- Verificación de hashes al final (manifiesto del álbum).

## 5. Pendientes previos (bloqueos honestos)

1. **Escucha del usuario** de `output/fase6_paquete_auditivo/` (identidad
   mantenida fuera de Nocturno Terminal).
2. **F6-L1** (DECISIONS.md): si se conecta `density.sax/rhodes` al scheduler,
   los presets de variación cambiarán de carácter → re-generar comparativos y
   re-validar auditivamente ANTES de construir álbumes sobre ellos.
3. Decidir stems/mixdown para Suno (fuera del alcance de FASE 6).
