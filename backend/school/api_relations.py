from __future__ import annotations

from typing import Any, Dict, List, Tuple

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse


def _get_db_info() -> Dict[str, str]:
    info: Dict[str, str] = {"vendor": connection.vendor or "-", "name": "-", "version": ""}
    try:
        info["name"] = connection.settings_dict.get("NAME") or "-"
    except Exception:
        pass

    version = ""
    try:
        with connection.cursor() as cursor:
            # Try common version queries
            try:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0] or ""
            except Exception:
                try:
                    cursor.execute("SELECT sqlite_version()")
                    version = cursor.fetchone()[0] or ""
                except Exception:
                    version = ""
    except Exception:
        version = ""
    info["version"] = version
    return info


def _snake_to_label(s: str) -> str:
    return s.replace("_", " ").strip().title()


def _safe_entity_name(name: str) -> str:
    # Mermaid entity names should not contain spaces or hyphens; use underscores
    return "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in name)


def _build_mermaid() -> Tuple[str, Dict[str, int], int]:
    """
    Build Mermaid ER diagram from Django models and relations.
    Returns (mermaid_string, model_stats, total_relations)
    """
    models = list(apps.get_models())
    model_stats = {"with_fk": 0, "with_m2m": 0}
    edges: List[str] = []
    entities: List[str] = ["erDiagram"]

    for m in models:
        meta = m._meta
        entity_name = _safe_entity_name(meta.db_table or meta.model_name)
        # Collect attributes
        attrs: List[str] = []
        for f in meta.get_fields():
            # Only display concrete, non-relational fields as attributes
            try:
                is_rel = f.is_relation  # type: ignore[attr-defined]
            except Exception:
                is_rel = False

            if getattr(f, "many_to_many", False) or getattr(f, "one_to_many", False):
                # Skip m2m and reverse fk in attributes list
                continue
            if is_rel and getattr(f, "many_to_one", False):
                # Skip FK field in attributes list to keep diagram clean
                continue
            if is_rel and getattr(f, "one_to_one", False):
                # Skip O2O attribute field
                continue

            try:
                label = f.name
                typ = getattr(f, "get_internal_type", lambda: "Field")()
                attrs.append(f"        {str(typ).lower()} {label}")
            except Exception:
                # Fallback
                attrs.append(f"        string {getattr(f, 'name', 'field')}")

        # Entity block
        entities.append(f"    {entity_name} {{")
        if attrs:
            entities.extend(attrs)
        else:
            entities.append("        string id")
        entities.append("    }")

    # Build relationships
    total_relations = 0
    for m in models:
        meta = m._meta
        src = _safe_entity_name(meta.db_table or meta.model_name)

        has_fk = False
        has_m2m = False

        for f in meta.get_fields():
            if getattr(f, "many_to_one", False) and f.concrete and f.related_model:
                has_fk = True
                dst = _safe_entity_name(f.related_model._meta.db_table or f.related_model._meta.model_name)
                label = f.name
                # Many to One: }o--||  (child many, parent one)
                edges.append(f"    {src} }}o--|| {dst} : {label}")
                total_relations += 1

            elif getattr(f, "one_to_one", False) and f.concrete and f.related_model:
                has_fk = True  # still a relation category
                dst = _safe_entity_name(f.related_model._meta.db_table or f.related_model._meta.model_name)
                label = f.name
                # One to One: ||--|| 
                edges.append(f"    {src} ||--|| {dst} : {label}")
                total_relations += 1

            elif getattr(f, "many_to_many", False) and f.related_model:
                has_m2m = True
                dst = _safe_entity_name(f.related_model._meta.db_table or f.related_model._meta.model_name)
                label = f.name
                # Many to Many: }o--o{ 
                edges.append(f"    {src} }}o--o{{ {dst} : {label}")
                total_relations += 1

        if has_fk:
            model_stats["with_fk"] += 1
        if has_m2m:
            model_stats["with_m2m"] += 1

    lines = entities + edges
    mermaid = "\n".join(lines)
    return mermaid, model_stats, total_relations


def _collect_constraints_and_indexes() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    constraints_out: List[Dict[str, Any]] = []
    indexes_out: List[Dict[str, Any]] = []
    introspection = connection.introspection

    try:
        table_names = introspection.table_names()
    except Exception:
        table_names = []

    try:
        with connection.cursor() as cursor:
            for table in table_names:
                try:
                    cons = introspection.get_constraints(cursor, table)
                except Exception:
                    cons = {}
                for cname, cdef in (cons or {}).items():
                    cols = cdef.get("columns") or []
                    fk = cdef.get("foreign_key")
                    unique = cdef.get("unique", False)
                    pk = cdef.get("primary_key", False)
                    chk = cdef.get("check", False)
                    is_index = cdef.get("index", False)

                    if is_index:
                        indexes_out.append(
                            {
                                "table": table,
                                "name": cname,
                                "def": f"INDEX ({', '.join(cols)})",
                            }
                        )
                        continue

                    desc = ""
                    if pk:
                        desc = f"PRIMARY KEY ({', '.join(cols)})"
                    elif unique:
                        desc = f"UNIQUE ({', '.join(cols)})"
                    elif fk:
                        to_table, to_col = fk
                        desc = f"FOREIGN KEY ({', '.join(cols)}) -> {to_table}({to_col})"
                    elif chk:
                        desc = "CHECK (...)"
                    else:
                        desc = f"CONSTRAINT ({', '.join(cols)})"

                    constraints_out.append(
                        {
                            "table": table,
                            "name": cname,
                            "def": desc,
                        }
                    )
    except Exception:
        # Fail silently; return what we have
        pass

    return constraints_out, indexes_out


@login_required
def api_data_relations(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "forbidden"}, status=403)

    db_info = _get_db_info()
    mermaid, model_stats, total_relations = _build_mermaid()
    constraints, indexes = _collect_constraints_and_indexes()

    # Collect table stats (name and row count) for 'school_' tables only (safe and concise)
    tables: List[Dict[str, Any]] = []
    try:
        with connection.cursor() as cursor:
            # Introspect all tables, filter to public schema school_*
            try:
                table_names = connection.introspection.table_names()
            except Exception:
                table_names = []
            visible = [t for t in table_names if t.startswith("school_")]
            for t in sorted(visible):
                cnt = None
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{t}"')
                    cnt = int(cursor.fetchone()[0] or 0)
                except Exception:
                    cnt = None
                tables.append({"name": t, "count": cnt})
    except Exception:
        tables = []

    payload = {
        "db_info": db_info,
        "total_models": len(list(apps.get_models())),
        "model_stats": model_stats,
        "total_relations": total_relations,
        "constraints": constraints,
        "indexes": indexes,
        "tables": tables,
        "mermaid": mermaid,
    }
    return JsonResponse(payload)