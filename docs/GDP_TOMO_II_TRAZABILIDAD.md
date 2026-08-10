# GDP Pavimentos Pro — Tomo II GDP-2024 con trazabilidad

## Objetivo

Esta etapa reemplaza el uso demostrativo del catálogo del Tomo II por un motor normativo separado, auditable y trazable. El motor consulta las combinaciones tabuladas del GDP-2024 Tomo II y devuelve únicamente alternativas asociadas a una celda de la tabla correspondiente.

## Cobertura implementada

- Definiciones estructurales: Tabla 301-01, página 38.
- Catálogo de 6 años: Tablas 301-02 a 301-06, páginas 39-41.
- Catálogo de 8 años: Tablas 301-07 a 301-11, páginas 42-44.
- Catálogo de 10 años: Tablas 301-12 a 301-16, páginas 44-46.
- Catálogo de 12 años: Tablas 301-17 a 301-21, páginas 47-49.
- Categorías TPD: hasta 500, 800, 1200, 2000 y 3500 veh/día.
- Categorías CBR: 3, 4, 6, 9 y 11 %.
- Categorías de pesados: 3, 4, 5, 7, 8.5, 14 y 15 %.
- Períodos: 6, 8, 10 y 12 años sin interpolación.

## Límites de aplicabilidad

El motor no emite estructura normativa cuando:

- TPD > 3500 veh/día.
- CBR < 3 %.
- Vehículos pesados > 15 %.
- El período solicitado no es 6, 8, 10 o 12 años.

Los controles se devuelven como una matriz de criterios, de forma que la interfaz pueda explicar por qué un caso está dentro o fuera del alcance.

## Trazabilidad conservada por alternativa

Cada alternativa devuelve:

- fuente normativa;
- decreto de adopción;
- tabla y página de definición de la estructura;
- tabla y página de asignación;
- criterio normalizado de consulta;
- contenido original de la celda fuente (`celda_original`);
- nota de extracción cuando una celda requirió conservación especial o revisión.

La conservación de `celda_original` evita transformar silenciosamente una ambigüedad editorial en una regla de software.

## Archivos de esta etapa

- `gdp_tomo2.py`: motor de clasificación, consulta y trazabilidad.
- `pages/06_Tomo_II_GDP_2024.py`: interfaz Streamlit integrada como página nativa.
- `tests/test_gdp_tomo2.py`: pruebas de límites y contrato de trazabilidad.
- `.github/workflows/validate-tomo2.yml`: validación automática de sintaxis y pruebas.

## Criterio de integración

La página nueva complementa la pestaña histórica de Estructura del `app.py` monolítico. Esto reduce el riesgo de regresión sobre la versión piloto mientras se valida el nuevo catálogo. Una etapa posterior puede sustituir internamente la pestaña histórica y reutilizar el mismo motor `gdp_tomo2.py` sin duplicar reglas.
