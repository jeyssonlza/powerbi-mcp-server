"""Herramientas para el modelo semántico Power BI.

23 herramientas:
- list_tables, describe_table, list_measures, list_relationships, search_objects
- add_table, add_calculated_table, rename_table, delete_table
- add_data_column, add_calculated_column, update_column, delete_column
- add_measure, update_measure, delete_measure, validate_dax
- add_relationship, update_relationship, delete_relationship, diagnose_relationships, classify_schema
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.session import session


def _tool(func):
    """Decorador: captura errores del dominio y los devuelve estructurados."""
    import functools
    from powerbi_mcp.core.exceptions import PowerBIMCPError
    from powerbi_mcp.core.logger import get_logger

    logger = get_logger(__name__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PowerBIMCPError as exc:
            logger.warning("Error en '%s': %s", func.__name__, exc)
            return {"ok": False, **exc.to_dict()}
        except Exception as exc:
            logger.exception("Error inesperado en '%s'", func.__name__)
            return {
                "ok": False,
                "error": exc.__class__.__name__,
                "code": "unexpected_error",
                "message": str(exc),
            }

    return wrapper


def _commit_model(
    reason: str,
    *,
    action: str,
    object_type: str,
    object_name: str,
    dry_run: bool,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Persiste el modelo activo y registra changelog + auditoría."""
    from powerbi_mcp.docs.changelog import record_change
    from powerbi_mcp.pbip.writer import save_semantic_model
    from powerbi_mcp.security.audit import audit

    project = session.require()
    try:
        save_result = save_semantic_model(project, reason=reason, dry_run=dry_run)
    finally:
        if dry_run:
            session.reload()
    if not dry_run:
        record_change(
            project.root_path,
            action=action,
            object_type=object_type,
            object_name=object_name,
            description=reason,
        )
    audit(action, target=object_name, status="success", details={"dry_run": dry_run})
    return {"ok": True, "dry_run": dry_run, "save": save_result, **payload}


def register_model_tools(mcp) -> None:
    """Registra todas las herramientas del modelo en la instancia MCP."""

    # ========== EXPLORACIÓN ==========
    @mcp.tool()
    @_tool
    def list_tables() -> dict[str, Any]:
        """Lista las tablas del modelo activo con conteos resumidos.

        Returns:
            Lista de tablas con número de columnas y medidas.
        """
        from powerbi_mcp.pbip.parser import list_tables as _list

        return {"ok": True, "tables": _list(session.require())}

    @mcp.tool()
    @_tool
    def describe_table(table_name: str) -> dict[str, Any]:
        """Describe una tabla en detalle (columnas y medidas).

        Args:
            table_name: Nombre de la tabla.

        Returns:
            Descripción completa de la tabla.
        """
        from powerbi_mcp.pbip.parser import describe_table as _describe

        detail = _describe(session.require(), table_name)
        if detail is None:
            return {"ok": False, "code": "object_not_found", "message": f"Tabla '{table_name}' no existe."}
        return {"ok": True, "table": detail}

    @mcp.tool()
    @_tool
    def list_measures() -> dict[str, Any]:
        """Lista todas las medidas del modelo con su tabla y expresión.

        Returns:
            Lista de medidas.
        """
        from powerbi_mcp.pbip.parser import list_measures as _list

        return {"ok": True, "measures": _list(session.require())}

    @mcp.tool()
    @_tool
    def list_relationships() -> dict[str, Any]:
        """Lista las relaciones del modelo activo.

        Returns:
            Lista de relaciones.
        """
        from powerbi_mcp.pbip.parser import list_relationships as _list

        return {"ok": True, "relationships": _list(session.require())}

    @mcp.tool()
    @_tool
    def search_objects(term: str) -> dict[str, Any]:
        """Busca un término en nombres de tablas, columnas, medidas y páginas.

        Args:
            term: Texto a buscar (case-insensitive).

        Returns:
            Coincidencias agrupadas por categoría.
        """
        from powerbi_mcp.pbip.parser import search_objects as _search

        return {"ok": True, "matches": _search(session.require(), term)}

    # ========== TABLAS ==========
    @mcp.tool()
    @_tool
    def add_table(
        table_name: str,
        m_expression: str | None = None,
        is_hidden: bool = False,
        description: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea una tabla nueva (opcionalmente con origen Power Query M).

        Args:
            table_name: Nombre de la nueva tabla.
            m_expression: Expresión M que define el origen (opcional).
            is_hidden: Si la tabla se crea oculta.
            description: Descripción de la tabla.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación y persistencia.
        """
        from powerbi_mcp.model.tables import add_table as _add

        session.require()
        result = _add(
            session.require_semantic_model(), table_name, m_expression=m_expression,
            is_hidden=is_hidden, description=description,
        )
        return _commit_model(
            f"add_table {table_name}", action="added", object_type="table",
            object_name=table_name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def add_calculated_table(
        table_name: str,
        dax_expression: str,
        is_hidden: bool = False,
        description: str | None = None,
        strict: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea una tabla calculada definida por una expresión DAX.

        Args:
            table_name: Nombre de la nueva tabla.
            dax_expression: Expresión DAX que produce la tabla.
            is_hidden: Si la tabla se crea oculta.
            description: Descripción de la tabla.
            strict: Si es ``True``, rechaza DAX inválido.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación con validación DAX.
        """
        from powerbi_mcp.model.tables import add_calculated_table as _add

        session.require()
        result = _add(
            session.require_semantic_model(), table_name, dax_expression,
            is_hidden=is_hidden, description=description, strict=strict,
        )
        return _commit_model(
            f"add_calculated_table {table_name}", action="added", object_type="table",
            object_name=table_name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def rename_table(table_name: str, new_name: str, dry_run: bool = False) -> dict[str, Any]:
        """Renombra una tabla y actualiza las relaciones que la referencian.

        Args:
            table_name: Nombre actual.
            new_name: Nuevo nombre.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado del renombrado.
        """
        from powerbi_mcp.model.tables import rename_table as _rename

        session.require()
        result = _rename(session.require_semantic_model(), table_name, new_name)
        return _commit_model(
            f"rename_table {table_name} -> {new_name}", action="changed", object_type="table",
            object_name=new_name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def delete_table(
        table_name: str, cascade_relationships: bool = True, dry_run: bool = False
    ) -> dict[str, Any]:
        """Elimina una tabla y, opcionalmente, sus relaciones asociadas.

        Args:
            table_name: Tabla a eliminar.
            cascade_relationships: Si elimina también las relaciones de la tabla.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la eliminación.
        """
        from powerbi_mcp.model.tables import delete_table as _delete

        session.require()
        result = _delete(session.require_semantic_model(), table_name, cascade_relationships=cascade_relationships)
        if not result.get("deleted"):
            return {"ok": False, **result}
        return _commit_model(
            f"delete_table {table_name}", action="removed", object_type="table",
            object_name=table_name, dry_run=dry_run, payload=result,
        )

    # ========== COLUMNAS ==========
    @mcp.tool()
    @_tool
    def add_data_column(
        table_name: str,
        column_name: str,
        data_type: str,
        source_column: str | None = None,
        format_string: str | None = None,
        summarize_by: str | None = None,
        is_hidden: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Añade una columna de datos a una tabla.

        Args:
            table_name: Tabla destino.
            column_name: Nombre de la columna.
            data_type: Tipo de dato (string, int64, double, decimal, dateTime, boolean...).
            source_column: Columna del origen (por defecto, igual al nombre).
            format_string: Cadena de formato.
            summarize_by: Agregación por defecto (none, sum, count...).
            is_hidden: Si la columna se crea oculta.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación.
        """
        from powerbi_mcp.model.columns import add_data_column as _add

        session.require()
        result = _add(
            session.require_semantic_model(), table_name, column_name, data_type,
            source_column=source_column, format_string=format_string,
            summarize_by=summarize_by, is_hidden=is_hidden,
        )
        return _commit_model(
            f"add_data_column {table_name}[{column_name}]", action="added", object_type="column",
            object_name=f"{table_name}[{column_name}]", dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def add_calculated_column(
        table_name: str,
        column_name: str,
        expression: str,
        data_type: str = "automatic",
        format_string: str | None = None,
        is_hidden: bool = False,
        strict: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Añade una columna calculada (definida por DAX) a una tabla.

        Args:
            table_name: Tabla destino.
            column_name: Nombre de la columna.
            expression: Expresión DAX.
            data_type: Tipo de dato resultante.
            format_string: Cadena de formato.
            is_hidden: Si la columna se crea oculta.
            strict: Si es ``True``, rechaza DAX inválido.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación con validación DAX.
        """
        from powerbi_mcp.model.columns import add_calculated_column as _add

        session.require()
        result = _add(
            session.require_semantic_model(), table_name, column_name, expression,
            data_type=data_type, format_string=format_string, is_hidden=is_hidden, strict=strict,
        )
        return _commit_model(
            f"add_calculated_column {table_name}[{column_name}]", action="added", object_type="column",
            object_name=f"{table_name}[{column_name}]", dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def update_column(
        table_name: str,
        column_name: str,
        data_type: str | None = None,
        format_string: str | None = None,
        summarize_by: str | None = None,
        is_hidden: bool | None = None,
        data_category: str | None = None,
        new_name: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Modifica propiedades de una columna existente.

        Args:
            table_name: Tabla anfitriona.
            column_name: Columna a modificar.
            data_type: Nuevo tipo de dato (opcional).
            format_string: Nueva cadena de formato (opcional).
            summarize_by: Nueva agregación por defecto (opcional).
            is_hidden: Nueva visibilidad (opcional).
            data_category: Categoría de datos (opcional).
            new_name: Nuevo nombre (opcional).
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la modificación.
        """
        from powerbi_mcp.model.columns import update_column as _update

        session.require()
        result = _update(
            session.require_semantic_model(), table_name, column_name,
            data_type=data_type, format_string=format_string, summarize_by=summarize_by,
            is_hidden=is_hidden, data_category=data_category, new_name=new_name,
        )
        return _commit_model(
            f"update_column {table_name}[{column_name}]", action="changed", object_type="column",
            object_name=f"{table_name}[{column_name}]", dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def delete_column(table_name: str, column_name: str, dry_run: bool = False) -> dict[str, Any]:
        """Elimina una columna de una tabla.

        Args:
            table_name: Tabla anfitriona.
            column_name: Columna a eliminar.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la eliminación.
        """
        from powerbi_mcp.model.columns import delete_column as _delete

        session.require()
        result = _delete(session.require_semantic_model(), table_name, column_name)
        return _commit_model(
            f"delete_column {table_name}[{column_name}]", action="removed", object_type="column",
            object_name=f"{table_name}[{column_name}]", dry_run=dry_run, payload=result,
        )

    # ========== MEDIDAS Y DAX ==========
    @mcp.tool()
    @_tool
    def add_measure(
        table_name: str,
        measure_name: str,
        expression: str,
        format_string: str | None = None,
        display_folder: str | None = None,
        description: str | None = None,
        strict: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea una medida DAX en una tabla.

        Args:
            table_name: Tabla anfitriona de la medida.
            measure_name: Nombre de la medida (único en el modelo).
            expression: Expresión DAX.
            format_string: Cadena de formato (ej. '#,0', '0.0%').
            display_folder: Carpeta de visualización.
            description: Documentación de la medida.
            strict: Si es ``True``, rechaza DAX inválido.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación con validación DAX.
        """
        from powerbi_mcp.model.measures import add_measure as _add

        session.require()
        result = _add(
            session.require_semantic_model(), table_name, measure_name, expression,
            format_string=format_string, display_folder=display_folder,
            description=description, strict=strict,
        )
        return _commit_model(
            f"add_measure {measure_name}", action="added", object_type="measure",
            object_name=measure_name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def update_measure(
        measure_name: str,
        expression: str | None = None,
        format_string: str | None = None,
        display_folder: str | None = None,
        description: str | None = None,
        new_name: str | None = None,
        strict: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Modifica una medida existente.

        Args:
            measure_name: Nombre actual de la medida.
            expression: Nueva expresión DAX (opcional).
            format_string: Nueva cadena de formato (opcional).
            display_folder: Nueva carpeta de visualización (opcional).
            description: Nueva descripción (opcional).
            new_name: Nuevo nombre (opcional).
            strict: Si es ``True``, valida la nueva DAX.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la modificación.
        """
        from powerbi_mcp.model.measures import update_measure as _update

        session.require()
        result = _update(
            session.require_semantic_model(), measure_name,
            expression=expression, format_string=format_string, display_folder=display_folder,
            description=description, new_name=new_name, strict=strict,
        )
        return _commit_model(
            f"update_measure {measure_name}", action="changed", object_type="measure",
            object_name=new_name or measure_name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def delete_measure(measure_name: str, dry_run: bool = False) -> dict[str, Any]:
        """Elimina una medida del modelo.

        Args:
            measure_name: Nombre de la medida a eliminar.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la eliminación.
        """
        from powerbi_mcp.model.measures import delete_measure as _delete

        session.require()
        result = _delete(session.require_semantic_model(), measure_name)
        return _commit_model(
            f"delete_measure {measure_name}", action="removed", object_type="measure",
            object_name=measure_name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def validate_dax(expression: str, check_best_practices: bool = True) -> dict[str, Any]:
        """Valida una expresión DAX (sintaxis, semántica y buenas prácticas).

        Args:
            expression: Expresión DAX a validar.
            check_best_practices: Si incluye sugerencias de estilo/rendimiento.

        Returns:
            Resultado de la validación (errores, advertencias, referencias...).
        """
        from powerbi_mcp.model.dax_validator import validate_dax as _validate

        model = session.require().semantic_model if session.is_open else None
        result = _validate(expression, model=model, check_best_practices=check_best_practices)
        return {"ok": True, **result.to_dict()}

    # ========== RELACIONES ==========
    @mcp.tool()
    @_tool
    def add_relationship(
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        from_cardinality: str = "many",
        to_cardinality: str = "one",
        cross_filter: str = "oneDirection",
        is_active: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea una relación entre dos columnas de tablas distintas.

        Args:
            from_table: Tabla origen (lado "muchos" por defecto).
            from_column: Columna origen.
            to_table: Tabla destino (lado "uno" por defecto).
            to_column: Columna destino.
            from_cardinality: Cardinalidad origen (many/one).
            to_cardinality: Cardinalidad destino (one/many).
            cross_filter: Dirección del filtro (oneDirection/bothDirections).
            is_active: Si la relación se crea activa.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación con advertencias detectadas.
        """
        from powerbi_mcp.model.relationships import add_relationship as _add

        session.require()
        result = _add(
            session.require_semantic_model(), from_table, from_column, to_table, to_column,
            from_cardinality=from_cardinality, to_cardinality=to_cardinality,
            cross_filter=cross_filter, is_active=is_active,
        )
        return _commit_model(
            f"add_relationship {from_table}->{to_table}", action="added", object_type="relationship",
            object_name=result.get("name", ""), dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def update_relationship(
        name: str,
        cross_filter: str | None = None,
        is_active: bool | None = None,
        from_cardinality: str | None = None,
        to_cardinality: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Modifica propiedades de una relación existente.

        Args:
            name: Identificador de la relación.
            cross_filter: Nueva dirección de filtro (opcional).
            is_active: Nuevo estado activo (opcional).
            from_cardinality: Nueva cardinalidad origen (opcional).
            to_cardinality: Nueva cardinalidad destino (opcional).
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la modificación.
        """
        from powerbi_mcp.model.relationships import update_relationship as _update

        session.require()
        result = _update(
            session.require_semantic_model(), name,
            cross_filter=cross_filter, is_active=is_active,
            from_cardinality=from_cardinality, to_cardinality=to_cardinality,
        )
        return _commit_model(
            f"update_relationship {name}", action="changed", object_type="relationship",
            object_name=name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def delete_relationship(name: str, dry_run: bool = False) -> dict[str, Any]:
        """Elimina una relación por su identificador.

        Args:
            name: Identificador de la relación.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la eliminación.
        """
        from powerbi_mcp.model.relationships import delete_relationship as _delete

        session.require()
        result = _delete(session.require_semantic_model(), name)
        return _commit_model(
            f"delete_relationship {name}", action="removed", object_type="relationship",
            object_name=name, dry_run=dry_run, payload=result,
        )

    @mcp.tool()
    @_tool
    def diagnose_relationships() -> dict[str, Any]:
        """Diagnostica problemas en el grafo de relaciones del modelo.

        Returns:
            Relaciones rotas, pares ambiguos, bidireccionales y tablas aisladas.
        """
        from powerbi_mcp.model.relationships import diagnose_relationships as _diag

        return {"ok": True, **_diag(session.require_semantic_model())}

    @mcp.tool()
    @_tool
    def classify_schema() -> dict[str, Any]:
        """Clasifica el esquema del modelo (estrella vs. copo de nieve).

        Returns:
            Tipo de esquema y clasificación de tablas (hechos/dimensión).
        """
        from powerbi_mcp.model.relationships import classify_schema as _classify

        return {"ok": True, **_classify(session.require_semantic_model())}
