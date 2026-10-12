import json
import os
import re
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from groq import Groq

MODEL = "openai/gpt-oss-20b"
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 8


# ============================================================
# GROQ
# ============================================================

def _groq_client() -> Groq:
    api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY en .streamlit/secrets.toml")
    return Groq(api_key=api_key)


def _query(sb, table: str, columns: str = "*", order: str | None = None, limit: int = 1000):
    q = sb.table(table).select(columns)
    if order:
        q = q.order(order, desc=True)
    if limit:
        q = q.limit(limit)
    return q.execute().data or []


def _to_float(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _date_filter(q, field: str, start_date: str = "", end_date: str = ""):
    if start_date:
        q = q.gte(field, start_date)
    if end_date:
        q = q.lte(field, end_date)
    return q


def _confirmed_sales(sb, start_date: str = "", end_date: str = ""):
    q = sb.table("salidas").select(
        "id,numero,fecha,tipo_salida,id_cliente,id_empleado,numero_documento,observaciones,estado,total_venta,total_costo,utilidad,created_at"
    )
    q = _date_filter(q, "fecha", start_date, end_date)
    rows = q.order("fecha", desc=True).limit(3000).execute().data or []
    return [r for r in rows if r.get("tipo_salida") == "VENTA" and r.get("estado") == "CONFIRMADO"]


# ============================================================
# INVENTARIO
# ============================================================

def tool_inventory_summary(sb) -> dict[str, Any]:
    rows = _query(sb, "v_stock", "*", "codigo", 2000)
    unidades = sum(_to_float(r.get("stock")) for r in rows)
    costo = sum(_to_float(r.get("stock")) * _to_float(r.get("precio_compra")) for r in rows)
    venta = sum(_to_float(r.get("stock")) * _to_float(r.get("precio_venta")) for r in rows)
    low = [r for r in rows if bool(r.get("stock_bajo"))]
    return {
        "productos": len(rows),
        "unidades_totales": unidades,
        "valor_a_costo": costo,
        "valor_a_precio_venta": venta,
        "utilidad_potencial": venta - costo,
        "productos_stock_bajo": len(low),
        "productos_sin_stock": sum(_to_float(r.get("stock")) <= 0 for r in rows),
    }


def tool_products(sb, query: str = "") -> list[dict[str, Any]]:
    rows = _query(sb, "v_stock", "*", "codigo", 2000)
    q = (query or "").strip().lower()
    if not q:
        return rows[:50]
    return [
        r for r in rows
        if q in " ".join(str(r.get(k, "")) for k in ("codigo", "nombre", "categoria", "marca", "unidad")).lower()
    ][:50]


def tool_low_stock(sb) -> list[dict[str, Any]]:
    rows = _query(sb, "v_stock", "*", "stock", 2000)
    return [
        {
            "codigo": r.get("codigo"),
            "producto": r.get("nombre"),
            "stock": r.get("stock"),
            "stock_minimo": r.get("stock_minimo"),
            "unidad": r.get("unidad"),
            "stock_bajo": r.get("stock_bajo"),
        }
        for r in rows
        if bool(r.get("stock_bajo")) or _to_float(r.get("stock")) <= 0
    ]


def tool_product_detail(sb, codigo: str) -> dict[str, Any]:
    rows = tool_products(sb, codigo)
    if not rows:
        return {"encontrado": False, "mensaje": f"No encontré el producto '{codigo}'."}
    return {"encontrado": True, "producto": rows[0]}


def tool_category(sb, categoria: str) -> list[dict[str, Any]]:
    rows = _query(sb, "v_stock", "*", "codigo", 2000)
    q = (categoria or "").strip().lower()
    return [r for r in rows if q in str(r.get("categoria", "")).lower()][:100]


def tool_inventory_health(sb) -> list[dict[str, Any]]:
    """Estimación simple de cobertura con ventas confirmadas de los últimos 30 días."""
    stock = _query(sb, "v_stock", "*", "codigo", 2000)
    sales = _confirmed_sales(sb)
    if not sales:
        return [{**r, "consumo_diario_30d": 0, "cobertura_dias": None, "riesgo": "SIN VENTAS RECIENTES"} for r in stock]

    cutoff = date.today().toordinal() - 30
    ids = {r["id"] for r in sales}
    details = _query(sb, "detalle_salidas", "id_salida,id_producto,cantidad", "id_salida", 10000)
    valid = [d for d in details if d.get("id_salida") in ids]
    consumed = {}
    for d in valid:
        pid = d.get("id_producto")
        consumed[pid] = consumed.get(pid, 0) + _to_float(d.get("cantidad"))

    out = []
    for r in stock:
        pid = r.get("id_producto")
        daily = consumed.get(pid, 0) / 30
        current = _to_float(r.get("stock"))
        minimum = _to_float(r.get("stock_minimo"))
        coverage = current / daily if daily > 0 else None
        if current <= 0:
            risk = "SIN STOCK"
        elif current <= minimum:
            risk = "CRÍTICO"
        elif coverage is not None and coverage <= 7:
            risk = "REPOSICIÓN URGENTE"
        elif coverage is not None and coverage <= 15:
            risk = "VIGILANCIA"
        else:
            risk = "NORMAL"
        out.append({
            "codigo": r.get("codigo"),
            "producto": r.get("nombre"),
            "stock": current,
            "stock_minimo": minimum,
            "consumo_diario_30d": round(daily, 3),
            "cobertura_dias": round(coverage, 1) if coverage is not None else None,
            "riesgo": risk,
        })
    return out


# ============================================================
# VENTAS
# ============================================================

def tool_sales_summary(sb, start_date: str = "", end_date: str = "") -> dict[str, Any]:
    sales = _confirmed_sales(sb, start_date, end_date)
    return {
        "periodo": {"desde": start_date or "inicio del historial", "hasta": end_date or "fin del historial"},
        "operaciones_confirmadas": len(sales),
        "total_venta": sum(_to_float(r.get("total_venta")) for r in sales),
        "total_costo": sum(_to_float(r.get("total_costo")) for r in sales),
        "utilidad": sum(_to_float(r.get("utilidad")) for r in sales),
        "margen_porcentaje": (
            sum(_to_float(r.get("utilidad")) for r in sales)
            / sum(_to_float(r.get("total_venta")) for r in sales) * 100
            if sum(_to_float(r.get("total_venta")) for r in sales) else 0
        ),
    }


def tool_sales_by_employee(sb, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    sales = _confirmed_sales(sb, start_date, end_date)
    emps = {r["id"]: f"{r.get('nombres','')} {r.get('apellidos','')}".strip() for r in _query(sb, "empleados", "id,nombres,apellidos,cargo", "apellidos", 1000)}
    agg = {}
    for s in sales:
        eid = s.get("id_empleado")
        agg.setdefault(eid or 0, {"empleado": emps.get(eid, "Sin responsable"), "ventas": 0, "costo": 0, "utilidad": 0, "operaciones": 0})
        agg[eid or 0]["ventas"] += _to_float(s.get("total_venta"))
        agg[eid or 0]["costo"] += _to_float(s.get("total_costo"))
        agg[eid or 0]["utilidad"] += _to_float(s.get("utilidad"))
        agg[eid or 0]["operaciones"] += 1
    return sorted(agg.values(), key=lambda x: x["ventas"], reverse=True)


def tool_sales_by_client(sb, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    sales = _confirmed_sales(sb, start_date, end_date)
    clients = {r["id"]: r.get("razon_social") for r in _query(sb, "clientes", "id,razon_social", "razon_social", 1000)}
    agg = {}
    for s in sales:
        cid = s.get("id_cliente")
        agg.setdefault(cid or 0, {"cliente": clients.get(cid, "Sin cliente"), "ventas": 0, "costo": 0, "utilidad": 0, "operaciones": 0})
        agg[cid or 0]["ventas"] += _to_float(s.get("total_venta"))
        agg[cid or 0]["costo"] += _to_float(s.get("total_costo"))
        agg[cid or 0]["utilidad"] += _to_float(s.get("utilidad"))
        agg[cid or 0]["operaciones"] += 1
    return sorted(agg.values(), key=lambda x: x["ventas"], reverse=True)


def tool_sales_by_product(sb, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    sales = _confirmed_sales(sb, start_date, end_date)
    ids = {s["id"] for s in sales}
    if not ids:
        return []
    details = _query(sb, "detalle_salidas", "id_salida,id_producto,cantidad,precio_unitario,costo_unitario,subtotal_venta,subtotal_costo", "id_salida", 10000)
    products = {p["id"]: p for p in _query(sb, "productos", "id,codigo,nombre", "codigo", 2000)}
    agg = {}
    for d in details:
        if d.get("id_salida") not in ids:
            continue
        pid = d.get("id_producto")
        p = products.get(pid, {})
        agg.setdefault(pid, {"codigo": p.get("codigo"), "producto": p.get("nombre"), "cantidad_vendida": 0, "venta": 0, "costo": 0, "utilidad": 0})
        agg[pid]["cantidad_vendida"] += _to_float(d.get("cantidad"))
        agg[pid]["venta"] += _to_float(d.get("subtotal_venta"))
        agg[pid]["costo"] += _to_float(d.get("subtotal_costo"))
        agg[pid]["utilidad"] += _to_float(d.get("subtotal_venta")) - _to_float(d.get("subtotal_costo"))
    return sorted(agg.values(), key=lambda x: x["venta"], reverse=True)


def tool_sales_detail(sb, start_date: str = "", end_date: str = "", employee: str = "", client: str = "") -> list[dict[str, Any]]:
    sales = _confirmed_sales(sb, start_date, end_date)
    emps = {r["id"]: f"{r.get('nombres','')} {r.get('apellidos','')}".strip() for r in _query(sb, "empleados", "id,nombres,apellidos", "apellidos", 1000)}
    clients = {r["id"]: r.get("razon_social") for r in _query(sb, "clientes", "id,razon_social", "razon_social", 1000)}
    e = employee.lower().strip()
    c = client.lower().strip()
    out = []
    for s in sales:
        ename = emps.get(s.get("id_empleado"), "Sin responsable")
        cname = clients.get(s.get("id_cliente"), "Sin cliente")
        if e and e not in ename.lower():
            continue
        if c and c not in cname.lower():
            continue
        out.append({**s, "empleado": ename, "cliente": cname})
    return out[:200]


def tool_recent_outputs(sb, limit: int = 20) -> list[dict[str, Any]]:
    limit = min(max(int(limit or 20), 1), 50)
    rows = _query(sb, "salidas", "id,numero,fecha,tipo_salida,id_cliente,id_empleado,numero_documento,estado,total_venta,total_costo,utilidad", "fecha", limit)
    emps = {r["id"]: f"{r.get('nombres','')} {r.get('apellidos','')}".strip() for r in _query(sb, "empleados", "id,nombres,apellidos", "apellidos", 1000)}
    clients = {r["id"]: r.get("razon_social") for r in _query(sb, "clientes", "id,razon_social", "razon_social", 1000)}
    return [{**r, "empleado": emps.get(r.get("id_empleado"), "Sin responsable"), "cliente": clients.get(r.get("id_cliente"), "Sin cliente")} for r in rows]


# ============================================================
# COMPRAS / PROVEEDORES
# ============================================================

def tool_purchase_summary(sb, start_date: str = "", end_date: str = "") -> dict[str, Any]:
    q = sb.table("ingresos").select("id,numero,fecha,id_proveedor,id_empleado,estado,total")
    q = _date_filter(q, "fecha", start_date, end_date)
    rows = q.order("fecha", desc=True).limit(3000).execute().data or []
    confirmed = [r for r in rows if r.get("estado") == "CONFIRMADO"]
    return {
        "compras_confirmadas": len(confirmed),
        "total_compras": sum(_to_float(r.get("total")) for r in confirmed),
        "compras_anuladas": sum(1 for r in rows if r.get("estado") == "ANULADO"),
    }


def tool_supplier_products(sb, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    q = sb.table("ingresos").select("id,fecha,id_proveedor,estado")
    q = _date_filter(q, "fecha", start_date, end_date)
    incomes = q.limit(3000).execute().data or []
    incomes = [r for r in incomes if r.get("estado") == "CONFIRMADO"]
    ids = {r["id"] for r in incomes}
    if not ids:
        return []
    suppliers = {r["id"]: r.get("razon_social") for r in _query(sb, "proveedores", "id,razon_social", "razon_social", 1000)}
    details = _query(sb, "detalle_ingresos", "id_ingreso,id_producto,cantidad,costo_unitario,subtotal", "id_ingreso", 10000)
    products = {r["id"]: r for r in _query(sb, "productos", "id,codigo,nombre", "codigo", 2000)}
    agg = {}
    income_supplier = {r["id"]: r.get("id_proveedor") for r in incomes}
    for d in details:
        if d.get("id_ingreso") not in ids:
            continue
        pid = d.get("id_producto")
        sid = income_supplier.get(d.get("id_ingreso"))
        key = sid or 0
        p = products.get(pid, {})
        agg.setdefault(key, {"proveedor": suppliers.get(sid, "Sin proveedor"), "unidades": 0, "importe": 0, "productos": set()})
        agg[key]["unidades"] += _to_float(d.get("cantidad"))
        agg[key]["importe"] += _to_float(d.get("subtotal"))
        if p.get("codigo"):
            agg[key]["productos"].add(p["codigo"])
    out = []
    for r in agg.values():
        r["productos_distintos"] = len(r.pop("productos"))
        out.append(r)
    return sorted(out, key=lambda x: x["unidades"], reverse=True)


def tool_supplier_detail(sb, query: str = "") -> list[dict[str, Any]]:
    rows = _query(sb, "proveedores", "id,razon_social,ruc,telefono,email,direccion,activo", "razon_social", 1000)
    q = query.lower().strip()
    return [r for r in rows if not q or q in str(r.get("razon_social", "")).lower() or q in str(r.get("ruc", "")).lower()]


def tool_client_detail(sb, query: str = "") -> list[dict[str, Any]]:
    rows = _query(sb, "clientes", "id,razon_social,ruc,telefono,email,direccion,activo", "razon_social", 1000)
    q = query.lower().strip()
    return [r for r in rows if not q or q in str(r.get("razon_social", "")).lower() or q in str(r.get("ruc", "")).lower()]


# ============================================================
# CONSULTA ABIERTA / ESQUEMA
# ============================================================

ALLOWED_DB_OBJECTS = {
    "categorias", "marcas", "unidades", "empleados", "proveedores", "clientes",
    "almacenes", "productos", "inventario", "ingresos", "detalle_ingresos",
    "salidas", "detalle_salidas", "kardex", "v_stock", "v_kardex",
    "v_agrobot_ventas", "v_agrobot_detalle_ventas", "v_agrobot_compras",
    "v_agrobot_detalle_compras", "v_agrobot_stock",
}

SCHEMA = {
    "categorias": ["id", "nombre", "activo"],
    "marcas": ["id", "nombre", "activo"],
    "unidades": ["id", "nombre", "abreviatura", "activo"],
    "empleados": ["id", "nombres", "apellidos", "cargo", "documento", "activo"],
    "proveedores": ["id", "razon_social", "ruc", "telefono", "email", "direccion", "activo"],
    "clientes": ["id", "razon_social", "ruc", "telefono", "email", "direccion", "activo"],
    "almacenes": ["id", "nombre", "direccion", "activo"],
    "productos": ["id", "codigo", "nombre", "descripcion", "id_categoria", "id_marca", "id_unidad", "precio_compra", "precio_venta", "stock_minimo", "activo"],
    "inventario": ["id", "id_producto", "id_almacen", "stock", "updated_at"],
    "ingresos": ["id", "numero", "fecha", "id_proveedor", "id_empleado", "tipo", "numero_documento", "observaciones", "estado", "total", "created_at"],
    "detalle_ingresos": ["id", "id_ingreso", "id_producto", "cantidad", "costo_unitario", "subtotal"],
    "salidas": ["id", "numero", "fecha", "tipo_salida", "id_cliente", "id_empleado", "numero_documento", "observaciones", "estado", "total_venta", "total_costo", "utilidad", "created_at"],
    "detalle_salidas": ["id", "id_salida", "id_producto", "cantidad", "precio_unitario", "costo_unitario", "subtotal_venta", "subtotal_costo"],
    "kardex": ["id", "fecha", "id_producto", "tipo_movimiento", "referencia", "cantidad_entrada", "cantidad_salida", "saldo", "costo_unitario", "observaciones"],
    "v_stock": ["id_producto", "codigo", "nombre", "categoria", "marca", "unidad", "precio_compra", "precio_venta", "stock_minimo", "stock", "almacen", "stock_bajo"],
    "v_kardex": ["id", "fecha", "id_producto", "tipo_movimiento", "referencia", "cantidad_entrada", "cantidad_salida", "saldo", "costo_unitario", "observaciones", "codigo", "nombre"],
    "v_agrobot_ventas": ["id", "numero", "fecha", "tipo_salida", "estado", "id_cliente", "cliente", "id_empleado", "empleado", "total_venta", "total_costo", "utilidad"],
    "v_agrobot_detalle_ventas": ["id", "id_salida", "fecha", "estado", "cliente", "empleado", "codigo", "producto", "cantidad", "precio_unitario", "costo_unitario", "subtotal_venta", "subtotal_costo"],
    "v_agrobot_compras": ["id", "numero", "fecha", "estado", "id_proveedor", "proveedor", "id_empleado", "empleado", "total"],
    "v_agrobot_detalle_compras": ["id", "id_ingreso", "fecha", "estado", "proveedor", "empleado", "codigo", "producto", "cantidad", "costo_unitario", "subtotal"],
    "v_agrobot_stock": ["id_producto", "codigo", "producto", "categoria", "marca", "unidad", "stock", "stock_minimo", "precio_compra", "precio_venta", "valor_costo", "valor_venta", "estado_stock"],
}

RELATIONS = [
    "productos.id = inventario.id_producto",
    "productos.id_categoria = categorias.id",
    "productos.id_marca = marcas.id",
    "productos.id_unidad = unidades.id",
    "salidas.id_empleado = empleados.id",
    "salidas.id_cliente = clientes.id",
    "detalle_salidas.id_salida = salidas.id",
    "detalle_salidas.id_producto = productos.id",
    "ingresos.id_proveedor = proveedores.id",
    "ingresos.id_empleado = empleados.id",
    "detalle_ingresos.id_ingreso = ingresos.id",
    "detalle_ingresos.id_producto = productos.id",
    "kardex.id_producto = productos.id",
]


def tool_schema(sb) -> dict[str, Any]:
    return {"tablas_y_vistas": SCHEMA, "relaciones": RELATIONS}


def _safe_read_sql(sql: str) -> tuple[bool, str]:
    s = (sql or "").strip()
    if not s:
        return False, "SQL vacío."
    if len(s) > 9000:
        return False, "La consulta es demasiado larga."
    if ";" in s or "--" in s or "/*" in s or "*/" in s:
        return False, "Solo se permite una consulta sin comentarios ni múltiples sentencias."
    if not re.match(r"^(select|with)\b", s, re.I):
        return False, "Solo se permiten SELECT o WITH."
    forbidden = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|comment|copy|do|execute|call|vacuum|refresh|merge|upsert|set_config|current_setting|pg_sleep|dblink|lo_import|lo_export)\b", re.I)
    if forbidden.search(s):
        return False, "La consulta contiene una operación o función no permitida."
    if re.search(r"\b(pg_catalog|information_schema|auth|storage)\b", s, re.I):
        return False, "Esquema no permitido."
    allowed_pattern = r"\b(?:" + "|".join(re.escape(x) for x in sorted(ALLOWED_DB_OBJECTS, key=len, reverse=True)) + r")\b"
    if not re.search(allowed_pattern, s, re.I):
        return False, "La consulta no referencia objetos permitidos de AgroInventario."
    return True, s


def tool_general_query(sb, sql: str) -> dict[str, Any]:
    ok, checked = _safe_read_sql(sql)
    if not ok:
        return {"error": checked}
    try:
        data = sb.rpc("agrobot_select", {"p_sql": checked}).execute().data
        if isinstance(data, list):
            return {"filas": data[:100], "cantidad": len(data)}
        return {"resultado": data}
    except Exception as exc:
        return {"error": f"No se pudo ejecutar la consulta abierta: {exc}"}


# ============================================================
# TOOLS GROQ
# ============================================================

def _fn(name, description, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


DATE_PROPS = {
    "start_date": {"type": "string", "description": "YYYY-MM-DD o vacío"},
    "end_date": {"type": "string", "description": "YYYY-MM-DD o vacío"},
}

TOOLS = [
    _fn("consultar_resumen_inventario", "Resumen actual del inventario."),
    _fn("buscar_productos", "Busca productos por código, nombre, categoría o marca.", {"query": {"type": "string"}}, ["query"]),
    _fn("consultar_producto", "Consulta un producto específico.", {"codigo": {"type": "string"}}, ["codigo"]),
    _fn("consultar_stock_bajo", "Lista productos con stock bajo o sin stock."),
    _fn("consultar_salud_stock", "Analiza riesgo, consumo reciente y cobertura estimada del stock."),
    _fn("consultar_categoria", "Lista productos de una categoría.", {"categoria": {"type": "string"}}, ["categoria"]),
    _fn("consultar_kardex", "Consulta movimientos del Kardex.", {"codigo": {"type": "string"}, **DATE_PROPS}, ["codigo", "start_date", "end_date"]),
    _fn("resumen_ventas", "Resumen de ventas confirmadas.", DATE_PROPS),
    _fn("ventas_por_empleado", "Ranking de ventas confirmadas por empleado.", DATE_PROPS),
    _fn("ventas_por_cliente", "Ranking de ventas confirmadas por cliente.", DATE_PROPS),
    _fn("ventas_por_producto", "Productos más vendidos en ventas confirmadas.", DATE_PROPS),
    _fn("detalle_ventas", "Detalle de ventas confirmadas con filtros opcionales.", {**DATE_PROPS, "employee": {"type": "string"}, "client": {"type": "string"}}, ["start_date", "end_date", "employee", "client"]),
    _fn("resumen_compras", "Resumen de compras/ingresos confirmados.", DATE_PROPS),
    _fn("productos_por_proveedor", "Ranking de proveedores por unidades y productos recibidos.", DATE_PROPS),
    _fn("consultar_proveedores", "Busca proveedores.", {"query": {"type": "string"}}, ["query"]),
    _fn("consultar_clientes", "Busca clientes.", {"query": {"type": "string"}}, ["query"]),
    _fn("ultimas_salidas", "Últimas salidas registradas.", {"limit": {"type": "integer"}}, ["limit"]),
    _fn("consultar_esquema", "Devuelve tablas, columnas y relaciones disponibles para consultas abiertas."),
    _fn("consultar_base_datos", "Ejecuta una consulta SELECT/WITH de solo lectura sobre AgroInventario. Úsala para preguntas nuevas, complejas, cruces, comparaciones, tendencias, promedios, máximos, mínimos y cualquier análisis no cubierto por una herramienta específica.", {"sql": {"type": "string"}}, ["sql"]),
]


SYSTEM_PROMPT = f"""
Eres AgroBot, el agente inteligente de AgroInventario.
Fecha actual del sistema: {date.today().isoformat()}.

PRINCIPIO CENTRAL:
No existe un catálogo cerrado de preguntas. Debes intentar responder cualquier pregunta relacionada con los datos, operaciones y análisis de AgroInventario.

DATOS REALES:
- Para datos actuales debes consultar Supabase mediante las herramientas.
- Nunca inventes números, productos, empleados, clientes, proveedores, ventas, compras, stock o utilidades.
- Una venta real se considera solo cuando tipo_salida='VENTA' y estado='CONFIRMADO'.
- No mezcles ventas ANULADAS con ventas confirmadas.

SELECCIÓN DE HERRAMIENTAS:
- Usa una herramienta específica cuando resuelva la pregunta directamente.
- Si la pregunta requiere un cruce, cálculo, comparación, histórico, filtro, tendencia o dato que no tenga una herramienta específica, usa consultar_esquema y luego consultar_base_datos.
- Puedes hacer varias consultas de solo lectura si una sola no basta.
- No inventes tablas ni columnas. Usa exclusivamente el esquema entregado por consultar_esquema.
- Para preguntas sobre proveedores y productos recibidos, relaciona ingresos + detalle_ingresos + proveedores + productos.
- Para empleados y ventas, relaciona salidas + empleados.
- Para clientes y ventas, relaciona salidas + clientes.
- Para productos vendidos, relaciona salidas + detalle_salidas + productos.
- Para stock, prioriza v_stock/v_agrobot_stock.

SQL ABIERTO:
- Solo SELECT o WITH.
- Una sola sentencia.
- Usa LIMIT cuando el resultado pueda ser grande.
- No escribas INSERT, UPDATE, DELETE, DROP, ALTER, CREATE ni funciones administrativas.
- No muestres SQL al usuario salvo que lo pida explícitamente.

FECHAS:
- Si el usuario dice hoy/este mes/este año, calcula el periodo usando la fecha actual.
- Si no especifica periodo, usa todo el historial disponible cuando sea razonable.

RESPUESTA:
- Español.
- Claro, profesional y directo.
- Dinero en S/ con dos decimales.
- Cantidades con separador de miles.
- Cuando ayude, usa tablas pequeñas.
- Explica de dónde sale el dato en lenguaje sencillo.
- Si no hay datos, dilo claramente.
- Si una consulta falla, explica que no se pudo consultar esa información y no inventes una respuesta.
- Este agente es de SOLO LECTURA: no modifica ni elimina datos.
"""


def _execute_tool(sb, name: str, args: dict[str, Any]):
    if name == "consultar_resumen_inventario": return tool_inventory_summary(sb)
    if name == "buscar_productos": return tool_products(sb, args.get("query", ""))
    if name == "consultar_producto": return tool_product_detail(sb, args.get("codigo", ""))
    if name == "consultar_stock_bajo": return tool_low_stock(sb)
    if name == "consultar_salud_stock": return tool_inventory_health(sb)
    if name == "consultar_categoria": return tool_category(sb, args.get("categoria", ""))
    if name == "consultar_kardex": return tool_kardex(sb, args.get("codigo", ""), args.get("start_date", ""), args.get("end_date", ""))
    if name == "resumen_ventas": return tool_sales_summary(sb, args.get("start_date", ""), args.get("end_date", ""))
    if name == "ventas_por_empleado": return tool_sales_by_employee(sb, args.get("start_date", ""), args.get("end_date", ""))
    if name == "ventas_por_cliente": return tool_sales_by_client(sb, args.get("start_date", ""), args.get("end_date", ""))
    if name == "ventas_por_producto": return tool_sales_by_product(sb, args.get("start_date", ""), args.get("end_date", ""))
    if name == "detalle_ventas": return tool_sales_detail(sb, args.get("start_date", ""), args.get("end_date", ""), args.get("employee", ""), args.get("client", ""))
    if name == "resumen_compras": return tool_purchase_summary(sb, args.get("start_date", ""), args.get("end_date", ""))
    if name == "productos_por_proveedor": return tool_supplier_products(sb, args.get("start_date", ""), args.get("end_date", ""))
    if name == "consultar_proveedores": return tool_supplier_detail(sb, args.get("query", ""))
    if name == "consultar_clientes": return tool_client_detail(sb, args.get("query", ""))
    if name == "ultimas_salidas": return tool_recent_outputs(sb, args.get("limit", 20))
    if name == "consultar_esquema": return tool_schema(sb)
    if name == "consultar_base_datos": return tool_general_query(sb, args.get("sql", ""))
    return {"error": f"Herramienta no reconocida: {name}"}


def ask_agrobot(sb, history: list[dict[str, str]], user_text: str) -> str:
    client = _groq_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_text})

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.15,
            max_completion_tokens=2200,
            include_reasoning=False,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content or "No pude generar una respuesta."
        messages.append(message)
        for call in message.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = _execute_tool(sb, call.function.name, args)
            except Exception as exc:
                result = {"error": f"Error de herramienta: {exc}"}
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False, default=str)[:30000],
            })
    return "No pude completar el análisis después de varias consultas. Intenta reformular la pregunta."


# ============================================================
# CHATBOX
# ============================================================

def render_agrobot(sb):
    st.markdown("""
    <style>
    .agrobot-hero{background:linear-gradient(110deg,#5420A8,#8E2BD0,#199447);padding:30px;border-radius:24px;color:white;margin-bottom:18px;box-shadow:0 14px 32px rgba(84,32,168,.18)}
    .agrobot-kicker{font-size:16px;font-weight:900;letter-spacing:1px}
    .agrobot-title{font-size:30px;font-weight:950;margin-top:5px}
    .agrobot-sub{font-size:16px;opacity:.96;margin-top:7px}
    .agrobot-info{border:1px solid #E8DDF4;background:white;border-radius:16px;padding:15px 18px;margin-bottom:16px;font-size:16px}
    .agrobot-info b{color:#5420A8}
    </style>
    <div class="agrobot-hero">
      <div class="agrobot-kicker">AGROINVENTARIO · IA</div>
      <div class="agrobot-title">🤖 AgroBot</div>
      <div class="agrobot-sub">Agente inteligente conectado a los datos reales de AgroInventario.</div>
    </div>
    <div class="agrobot-info"><b>Chat libre.</b> Puedes preguntar en lenguaje natural sobre inventario, ventas, compras, proveedores, clientes, empleados, productos, Kardex, utilidad, alertas, comparaciones y análisis. No hay una lista cerrada de preguntas.</div>
    """, unsafe_allow_html=True)

    if "agrobot_messages" not in st.session_state:
        st.session_state["agrobot_messages"] = []

    c1, c2 = st.columns([7, 1])
    with c1:
        st.caption("AgroBot consulta Supabase cuando necesita datos actuales y puede combinar varias fuentes.")
    with c2:
        if st.button("🗑️ Limpiar", use_container_width=True):
            st.session_state["agrobot_messages"] = []
            st.rerun()

    for msg in st.session_state["agrobot_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Escribe cualquier pregunta sobre AgroInventario...")
    if prompt:
        history = list(st.session_state["agrobot_messages"])
        st.session_state["agrobot_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("🤖 Analizando datos de AgroInventario..."):
                try:
                    answer = ask_agrobot(sb, history, prompt)
                except Exception as exc:
                    answer = f"⚠️ AgroBot no pudo completar la consulta: {exc}"
            st.markdown(answer)
        st.session_state["agrobot_messages"].append({"role": "assistant", "content": answer})
