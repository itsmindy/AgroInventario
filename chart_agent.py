
"""AgroCharts: agente de gráficos dinámicos con datos reales de Supabase."""

import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# CONSULTAS A SUPABASE
# =========================================================

def _fetch(sb, table, columns="*", order=None, limit=5000):
    query = sb.table(table).select(columns).limit(limit)

    if order:
        query = query.order(order, desc=True)

    return pd.DataFrame(query.execute().data or [])


def _numeric(df, columns):
    df = df.copy()

    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    return df


def _stock(sb):
    """Obtiene el stock calculado desde la vista existente v_stock."""
    df = _fetch(sb, "v_stock", "*", "codigo")

    if df.empty:
        return df

    return _numeric(
        df,
        [
            "stock",
            "stock_minimo",
            "precio_compra",
            "precio_venta",
        ],
    )


def _sales(sb):
    """Solo utiliza ventas confirmadas."""
    df = _fetch(
        sb,
        "salidas",
        (
            "id,numero,fecha,tipo_salida,estado,total_venta,"
            "total_costo,utilidad,id_empleado,id_cliente"
        ),
        "fecha",
    )

    if df.empty:
        return df

    required = {"tipo_salida", "estado"}
    if not required.issubset(df.columns):
        raise ValueError(
            "La tabla salidas no contiene las columnas esperadas."
        )

    df = df[
        (df["tipo_salida"].astype(str).str.upper() == "VENTA")
        & (df["estado"].astype(str).str.upper() == "CONFIRMADO")
    ].copy()

    df = _numeric(df, ["total_venta", "total_costo", "utilidad"])

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    return df


def _purchases(sb):
    df = _fetch(sb, "ingresos", "id,fecha,estado,total", "fecha")

    if df.empty:
        return df

    if "estado" in df.columns:
        df = df[
            df["estado"].astype(str).str.upper() == "CONFIRMADO"
        ].copy()

    df = _numeric(df, ["total"])

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    return df


# =========================================================
# INTERPRETACIÓN DE LA SOLICITUD
# =========================================================

def _normalize(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _has(text, *terms):
    return any(term in text for term in terms)


def _interpret(prompt):
    """
    Interpreta la solicitud en lenguaje natural mediante reglas.
    No genera datos ni inventa resultados.
    """
    text = _normalize(prompt)

    # Tipo de gráfico solicitado
    if _has(text, "circular", "pastel", "dona", "donut", "porciones"):
        chart_type = "pie"
    elif _has(text, "linea", "lineas", "tendencia", "evolucion", "evolución"):
        chart_type = "line"
    elif _has(text, "dispersion", "dispersión", "correlacion", "correlación"):
        chart_type = "scatter"
    else:
        chart_type = "bar"

    # Cantidad solicitada: por defecto, hasta 10 elementos
    match = re.search(r"\b(\d{1,3})\b", text)
    top_n = int(match.group(1)) if match else 10
    top_n = max(1, min(top_n, 100))

    # Tema del gráfico
    if _has(text, "alerta", "critico", "critica", "bajo stock",
            "sin stock", "riesgo", "stock minimo"):
        topic = "stock_alerts"

    elif _has(text, "empleado", "vendedor", "trabajador"):
        topic = "sales_employee"

    elif _has(text, "utilidad", "ganancia", "rentabilidad"):
        topic = "sales_profit"

    elif _has(text, "venta", "ventas", "facturacion", "facturación"):
        topic = "sales"

    elif _has(text, "compra", "compras", "ingresos confirmados"):
        topic = "purchases"

    elif _has(text, "categoria", "categorias"):
        topic = "stock_category"

    elif _has(text, "valor del inventario", "valorizacion",
              "valorización", "costo del inventario"):
        topic = "stock_value"

    elif _has(text, "stock", "inventario", "producto", "productos"):
        topic = "stock"

    else:
        topic = None

    # Orden solicitado
    if _has(text, "menor stock", "menos stock", "stock mas bajo",
            "stock más bajo", "menor cantidad", "menos cantidad"):
        sort_order = "asc"
    else:
        sort_order = "desc"

    return {
        "topic": topic,
        "chart_type": chart_type,
        "top_n": top_n,
        "sort_order": sort_order,
        "normalized_prompt": text,
    }


# =========================================================
# GENERACIÓN DINÁMICA DE GRÁFICOS
# =========================================================

def _render_chart(df, chart_type, title, x, y, top_n=10, sort_order="desc"):
    if df.empty:
        st.info("No hay datos disponibles para generar este gráfico.")
        return

    df = df.copy()

    if y not in df.columns or x not in df.columns:
        st.warning("Los datos consultados no contienen las columnas necesarias.")
        return

    df[y] = pd.to_numeric(df[y], errors="coerce")
    df = df.dropna(subset=[x, y])

    if df.empty:
        st.info("No se encontraron valores válidos para graficar.")
        return

    ascending = sort_order == "asc"
    df = df.sort_values(y, ascending=ascending).head(top_n)

    if chart_type == "pie":
        fig = px.pie(
            df,
            names=x,
            values=y,
            title=title,
            hole=0.35,
        )
        fig.update_traces(
            textposition="inside",
            textinfo="label+percent",
            hovertemplate="%{label}<br>Valor: %{value:,.2f}<br>"
                          "Participación: %{percent}<extra></extra>",
        )

    elif chart_type == "line":
        df = df.sort_values(x)
        fig = px.line(
            df,
            x=x,
            y=y,
            markers=True,
            title=title,
            labels={x: "Periodo", y: y.replace("_", " ").title()},
        )

    elif chart_type == "scatter":
        fig = px.scatter(
            df,
            x=x,
            y=y,
            title=title,
            hover_data=list(df.columns),
        )

    else:
        fig = px.bar(
            df.sort_values(y, ascending=True),
            x=y,
            y=x,
            orientation="h",
            title=title,
            labels={x: "Elemento", y: y.replace("_", " ").title()},
            hover_data=list(df.columns),
        )

    fig.update_layout(
        template="plotly_dark",
        height=480,
        margin=dict(l=20, r=20, t=65, b=20),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Descargar datos CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="agrocharts_datos.csv",
        mime="text/csv",
        key=f"csv_{abs(hash(title))}",
    )


def _generate(sb, request):
    topic = request["topic"]
    chart_type = request["chart_type"]
    top_n = request["top_n"]
    sort_order = request["sort_order"]

    # Productos por stock
    if topic == "stock":
        df = _stock(sb)

        if df.empty:
            st.info("No hay productos en la vista v_stock.")
            return

        name = "nombre" if "nombre" in df.columns else "codigo"

        if "stock" not in df.columns:
            st.error("La vista v_stock no contiene la columna stock.")
            return

        df = df[df["stock"] > 0].copy()

        if df.empty:
            st.info("No hay productos con stock positivo.")
            return

        # El gráfico circular representa la participación de cada producto
        # dentro del conjunto seleccionado.
        if chart_type == "pie":
            title = f"Participación de los {top_n} productos con mayor stock"
        else:
            title = f"Productos según stock: {top_n} registros"

        _render_chart(
            df=df,
            chart_type=chart_type,
            title=title,
            x=name,
            y="stock",
            top_n=top_n,
            sort_order=sort_order,
        )
        return

    # Alertas de stock
    if topic == "stock_alerts":
        df = _stock(sb)

        if df.empty:
            st.info("No hay productos disponibles.")
            return

        if not {"stock", "stock_minimo"}.issubset(df.columns):
            st.error("Faltan columnas de stock para calcular las alertas.")
            return

        df["estado_stock"] = df.apply(
            lambda row: (
                "SIN STOCK" if row["stock"] <= 0
                else "CRÍTICO" if row["stock"] <= row["stock_minimo"]
                else "NORMAL"
            ),
            axis=1,
        )

        agg = (
            df.groupby("estado_stock", as_index=False)
            .size()
            .rename(columns={"size": "productos"})
        )

        _render_chart(
            agg, chart_type, "Estado actual del inventario",
            "estado_stock", "productos", top_n=top_n,
        )
        return

    # Valor del inventario por categoría
    if topic in ("stock_category", "stock_value"):
        df = _stock(sb)

        if df.empty:
            st.info("No hay productos disponibles.")
            return

        if not {"stock", "precio_compra"}.issubset(df.columns):
            st.error("Faltan columnas para calcular el valor del inventario.")
            return

        category = "categoria" if "categoria" in df.columns else None

        if topic == "stock_category" and category:
            group_column = category
            value_column = "stock"
            title = "Stock acumulado por categoría"
        else:
            group_column = category or (
                "nombre" if "nombre" in df.columns else "codigo"
            )
            value_column = "valor_inventario"
            df[value_column] = df["stock"] * df["precio_compra"]
            title = "Valor del inventario a precio de compra"

        agg = (
            df.groupby(group_column, dropna=False, as_index=False)[value_column]
            .sum()
            .sort_values(value_column, ascending=(sort_order == "asc"))
        )

        _render_chart(
            agg, chart_type, title, group_column, value_column,
            top_n=top_n, sort_order=sort_order,
        )
        return

    # Ventas confirmadas por mes
    if topic in ("sales", "sales_profit"):
        df = _sales(sb)

        if df.empty:
            st.info("No hay ventas confirmadas para graficar.")
            return

        if "fecha" not in df.columns:
            st.error("La tabla salidas no contiene la fecha de la operación.")
            return

        df = df.dropna(subset=["fecha"]).copy()
        df["mes"] = df["fecha"].dt.to_period("M").astype(str)

        metric = "utilidad" if topic == "sales_profit" else "total_venta"

        if metric not in df.columns:
            st.error(f"No se encontró la columna {metric} en las ventas.")
            return

        agg = df.groupby("mes", as_index=False)[metric].sum()

        _render_chart(
            agg,
            chart_type,
            "Utilidad mensual de ventas" if metric == "utilidad"
            else "Ventas confirmadas por mes",
            "mes",
            metric,
            top_n=top_n,
            sort_order=sort_order,
        )
        return

    # Compras confirmadas por mes
    if topic == "purchases":
        df = _purchases(sb)

        if df.empty:
            st.info("No hay ingresos confirmados para graficar.")
            return

        df = df.dropna(subset=["fecha"]).copy()
        df["mes"] = df["fecha"].dt.to_period("M").astype(str)

        agg = df.groupby("mes", as_index=False)["total"].sum()

        _render_chart(
            agg, chart_type, "Compras confirmadas por mes",
            "mes", "total", top_n=top_n, sort_order=sort_order,
        )
        return

    # Ventas por empleado
    if topic == "sales_employee":
        df = _sales(sb)

        if df.empty:
            st.info("No hay ventas confirmadas para graficar.")
            return

        employees = _fetch(sb, "empleados", "id,nombres,apellidos")

        if employees.empty or "id_empleado" not in df.columns:
            st.warning("No hay información suficiente para identificar vendedores.")
            return

        employees["empleado"] = (
            employees["nombres"].fillna("").astype(str)
            + " "
            + employees["apellidos"].fillna("").astype(str)
        ).str.strip()

        df = df.merge(
            employees[["id", "empleado"]],
            left_on="id_empleado",
            right_on="id",
            how="left",
        )
        df["empleado"] = df["empleado"].fillna("Sin responsable")

        agg = df.groupby("empleado", as_index=False)["total_venta"].sum()

        _render_chart(
            agg, chart_type, "Ventas confirmadas por empleado",
            "empleado", "total_venta",
            top_n=top_n, sort_order=sort_order,
        )
        return

    st.warning(
        "No pude identificar qué deseas analizar. Prueba con una solicitud "
        "como: 'gráfico circular de productos con mayor stock', "
        "'ventas mensuales en líneas' o 'alertas de stock en barras'."
    )


# =========================================================
# INTERFAZ AGROCHARTS
# =========================================================

def render_chart_agent(sb):
    st.markdown(
        "<div class='section'>📈 AgroCharts · Agente de gráficos</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitulo'>Escribe con tus propias palabras qué deseas "
        "graficar. El agente consultará los datos reales de Supabase.</div>",
        unsafe_allow_html=True,
    )

    with st.form("agrocharts_dynamic_form"):
        prompt = st.text_area(
            "¿Qué gráfico necesitas?",
            placeholder=(
                "Ej.: Quiero un gráfico circular con los productos "
                "de mayor stock.\n"
                "Ej.: Compara las ventas mensuales en un gráfico de líneas.\n"
                "Ej.: Muestra los 15 productos con menos stock en barras."
            ),
            height=110,
        )

        submitted = st.form_submit_button(
            "✨ Interpretar y generar gráfico",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    if not prompt.strip():
        st.warning("Escribe qué gráfico deseas generar.")
        return

    request = _interpret(prompt)

    with st.spinner("Analizando tu solicitud y consultando Supabase..."):
        try:
            if request["topic"] is None:
                st.warning(
                    "No identifiqué los datos que deseas analizar. "
                    "Menciona productos, stock, ventas, compras, categorías, "
                    "empleados o alertas."
                )
                return

            st.caption(
                f"Solicitud interpretada: {prompt.strip()} "
                f"· Tipo de gráfico: {request['chart_type']}"
            )

            _generate(sb, request)

            st.caption(
                "Fuente: datos consultados en Supabase. "
                "Los gráficos no utilizan cifras de demostración."
            )

        except Exception as exc:
            st.error(
                "No se pudo generar el gráfico. Verifica la conexión con "
                f"Supabase y las columnas disponibles. Detalle: {exc}"
            )
