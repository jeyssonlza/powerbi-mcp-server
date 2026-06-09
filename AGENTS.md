# Power BI — Playbook de orquestación de MCPs

> Reglas para que el agente (Claude / OpenCode) coordine **dos servidores MCP de
> Power BI** como un equipo. Lee esto antes de trabajar con proyectos Power BI.

---

## 🧩 Contexto: hay DOS MCPs complementarios

| MCP | Trabaja sobre | Fortaleza | Power BI |
|-----|---------------|-----------|----------|
| **`powerbi-modeling-mcp`** (Microsoft) | Modelo **en vivo** | Ejecuta DAX real, calculation groups, trace de rendimiento | **Abierto** |
| **`powerbi`** (propio) | **Archivos PBIP** en disco | IA/ML, documentación, seguridad/PII, calidad de datos, visuales HTML | **Cerrado** |

**Regla de oro:** tú (el agente) eres el **director de orquesta**. Los MCPs no se
coordinan entre sí — tú decides qué herramienta usar de cada uno y en qué orden.

---

## 🎯 Quién hace qué (no competir, complementar)

```
ETL / transformar fuentes      → Power BI Desktop (Power Query). Ningún MCP lo reemplaza.
Medidas DAX validadas en vivo  → powerbi-modeling-mcp (ejecuta y verifica el resultado)
Trace / rendimiento            → powerbi-modeling-mcp
IA (anomalías/forecast/cluster)→ powerbi  (Microsoft NO lo tiene)
Documentación / diccionario    → powerbi
Seguridad / masking PII        → powerbi
Calidad de datos / perfilado   → powerbi
Visuales HTML / temas          → powerbi
```

---

## 📏 Reglas para DAX y medidas (obligatorias)

1. **Antes** de crear o editar una medida, usa `describe_table` para ver las
   **columnas reales y sus tipos**. Nunca inventes nombres de columnas.
2. **Siempre** ejecuta `validate_dax` antes de `add_measure`.
3. Si Power BI está **abierto** (modelo en vivo), usa **Microsoft** para
   **ejecutar el DAX** y confirmar que el resultado es correcto, antes de
   persistir con el MCP propio.
4. Usa `DIVIDE(a, b)` en vez de `a / b` (evita división por cero).
5. Usa variables `VAR ... RETURN` para legibilidad en medidas complejas.
6. Formato estándar: monetario `"#,0.00"`, porcentaje `"0.0%"`, entero `"#,0"`.
7. Nombres de medidas en **Title Case** (ej. `Total Sales`, `Profit Margin %`).
8. Crea siempre la medida con `add_measure(..., strict=True, description=...)`.

---

## 📚 Playbooks por tarea (sigue el orden)

### ▶ Crear una medida
```
1. [powerbi]    describe_table            → ver columnas/tipos reales
2.              escribir DAX              → DIVIDE, VAR, formato
3. [powerbi]    validate_dax              → sintaxis + referencias
4. [Microsoft]  ejecutar DAX (si en vivo) → verificar el resultado real
5. [powerbi]    add_measure(strict=True)  → persistir con formato y descripción
6. [powerbi]    get_changelog / documentar el cambio
```

### ▶ Analizar y mejorar un modelo
```
1. [powerbi]    open_project + list_tables + describe_table
2. [powerbi]    analyze_data_quality + detect_anomalies   → revisar los datos
3. [Microsoft]  trace / ejecutar DAX (si en vivo)         → rendimiento real
4. [powerbi]    run_best_practices + optimize_dax         → sugerencias
5. [powerbi]    generate_documentation                    → dejar constancia
```

### ▶ Documentar un proyecto
```
1. [powerbi]    open_project
2. [powerbi]    generate_documentation + generate_data_dictionary
```

### ▶ Analítica avanzada (IA)
```
1. [powerbi]    open_project
2. [powerbi]    detect_anomalies / forecast_series / run_clustering / rfm_segmentation
3. [powerbi]    (opcional) integrar el resultado al modelo como tabla DAX o M
```

### ▶ Seguridad / datos sensibles
```
1. [powerbi]    create_backup                 → antes de cualquier cambio
2. [powerbi]    mask_data                     → enmascarar PII (email, nombre, etc.)
```

---

## 🔒 Reglas de seguridad y buenas prácticas

- **MCP propio (`powerbi`)** → trabaja con Power BI Desktop **CERRADO** (evita
  bloqueos de archivo y sobrescrituras).
- **MCP Microsoft** → requiere Power BI Desktop **ABIERTO** (modelo en vivo).
- **Siempre** `create_backup` antes de modificar el modelo.
- El proyecto debe estar guardado como **PBIP** (carpeta), no PBIX binario.
- Nunca expongas credenciales ni secretos en respuestas o logs.

---

## ⚡ Resumen de decisión rápida

```
¿Power BI ABIERTO y quiero DAX validado ejecutando?  → Microsoft
¿Power BI CERRADO y quiero analizar/documentar/asegurar? → powerbi (propio)
¿IA, calidad, docs, seguridad, visuales?  → siempre powerbi (propio)
¿Transformar fuentes (ETL real)?  → Power Query en Power BI Desktop
```

> Cuando una tarea cruce ambos mundos, **orquesta en secuencia**: primero el que
> prepara/valida, luego el que analiza/documenta. Uno termina, empieza el otro.
