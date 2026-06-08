#!/usr/bin/env python3
"""Script de validación de la refactorización de server.py."""

import ast
import sys
from pathlib import Path
from collections import defaultdict

def extract_functions(file_path):
    """Extrae nombres de funciones decoradas con @mcp.tool() de un archivo."""
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Busca funciones decoradas con @mcp.tool()
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == 'tool':
                            functions.append(node.name)
                elif isinstance(decorator, ast.Name):
                    if decorator.id == 'tool':
                        functions.append(node.name)
    return functions

def count_lines(file_path):
    """Cuenta las líneas de código de un archivo."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return len(f.readlines())

def main():
    """Valida la refactorización."""
    base_dir = Path("C:/Users/jeyss/Desktop/mcp visual PBI/src/powerbi_mcp")
    tools_dir = base_dir / "tools"
    server_file = base_dir / "server.py"

    print("=" * 70)
    print("VALIDACIÓN DE REFACTORIZACIÓN: server.py -> 8 módulos de tools")
    print("=" * 70)

    # Mapeo esperado
    expected = {
        "project_tools.py": 11,
        "model_tools.py": 23,
        "ai_tools.py": 8,
        "visuals_tools.py": 7,
        "analysis_tools.py": 5,
        "docs_tools.py": 3,
        "security_tools.py": 6,
        "pbi_api_tools.py": 5,
    }

    total_expected = sum(expected.values())
    print(f"\nHerramientas esperadas por módulo:")
    print("-" * 70)

    all_functions = set()
    total_found = 0

    for tool_file, expected_count in expected.items():
        tool_path = tools_dir / tool_file
        if not tool_path.exists():
            print(f"❌ {tool_file}: ARCHIVO NO ENCONTRADO")
            continue

        functions = extract_functions(tool_path)
        lines = count_lines(tool_path)
        total_found += len(functions)
        all_functions.update(functions)

        status = "✓" if len(functions) == expected_count else "✗"
        print(f"{status} {tool_file:25} {len(functions):3d}/{expected_count:3d} herramientas ({lines:4d} líneas)")

    print("-" * 70)
    print(f"{'TOTAL HERRAMIENTAS':25} {total_found:3d}/{total_expected:3d}")
    print(f"{'server.py':25} {count_lines(server_file):4d} líneas (refactorizado)")

    # Validación de integridad
    print("\n" + "=" * 70)
    print("VALIDACIÓN DE INTEGRIDAD")
    print("=" * 70)

    # Verificar que no hay duplicados
    if len(all_functions) == total_found:
        print("✓ Sin duplicados de funciones")
    else:
        print(f"✗ Se encontraron {total_found - len(all_functions)} duplicados")
        return 1

    # Verificar importaciones en server.py
    with open(server_file, 'r', encoding='utf-8') as f:
        server_content = f.read()

    imports_ok = all([
        "register_project_tools" in server_content,
        "register_model_tools" in server_content,
        "register_ai_tools" in server_content,
        "register_visuals_tools" in server_content,
        "register_analysis_tools" in server_content,
        "register_docs_tools" in server_content,
        "register_security_tools" in server_content,
        "register_pbi_api_tools" in server_content,
    ])

    if imports_ok:
        print("✓ Todos los módulos están importados en server.py")
    else:
        print("✗ Faltan importaciones en server.py")
        return 1

    # Verificar que __init__.py de tools exporta las funciones
    init_file = tools_dir / "__init__.py"
    with open(init_file, 'r', encoding='utf-8') as f:
        init_content = f.read()

    exports_ok = all([
        "register_project_tools" in init_content,
        "register_model_tools" in init_content,
        "register_ai_tools" in init_content,
        "register_visuals_tools" in init_content,
        "register_analysis_tools" in init_content,
        "register_docs_tools" in init_content,
        "register_security_tools" in init_content,
        "register_pbi_api_tools" in init_content,
    ])

    if exports_ok:
        print("✓ Todas las funciones se exportan desde tools/__init__.py")
    else:
        print("✗ Faltan exportaciones en tools/__init__.py")
        return 1

    print("\n" + "=" * 70)
    print("RESULTADO: REFACTORIZACIÓN EXITOSA")
    print("=" * 70)
    print(f"\n67 herramientas divididas en 8 módulos especializados")
    print(f"Total: {total_found} herramientas encontradas ({'CORRECTO' if total_found == 67 else 'INCORRECTO'})")

    return 0 if total_found == 67 else 1

if __name__ == "__main__":
    sys.exit(main())
