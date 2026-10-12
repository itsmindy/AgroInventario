"""AgroMail: reportes PDF/XLSX por Gmail, envío manual y programación diaria."""
from __future__ import annotations
import io, os, smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from apscheduler.schedulers.background import BackgroundScheduler

TZ = ZoneInfo("America/Lima")


def _setting(key: str, default=None):
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


def _fetch(sb, table: str, cols: str = "*", order: str | None = None, limit: int = 5000) -> pd.DataFrame:
    q = sb.table(table).select(cols).limit(limit)
    if order: q = q.order(order, desc=True)
    return pd.DataFrame(q.execute().data or [])


def collect_reports(sb) -> dict[str, pd.DataFrame]:
    """Crea datasets actuales; ventas y compras solo confirmadas."""
    stock = _fetch(sb, "v_stock", "*", "codigo")
    sales = _fetch(sb, "salidas", "id,numero,fecha,tipo_salida,estado,total_venta,total_costo,utilidad,id_empleado,id_cliente", "fecha")
    if not sales.empty:
        sales = sales[(sales["tipo_salida"] == "VENTA") & (sales["estado"] == "CONFIRMADO")].copy()
    purchases = _fetch(sb, "ingresos", "id,numero,fecha,estado,id_proveedor,id_empleado,total", "fecha")
    if not purchases.empty: purchases = purchases[purchases["estado"] == "CONFIRMADO"].copy()
    kardex = _fetch(sb, "v_kardex", "*", "fecha")
    alerts = stock.copy()
    if not alerts.empty:
        alerts["stock"] = pd.to_numeric(alerts.get("stock", 0), errors="coerce").fillna(0)
        alerts["stock_minimo"] = pd.to_numeric(alerts.get("stock_minimo", 0), errors="coerce").fillna(0)
        alerts["riesgo"] = alerts.apply(lambda r: "SIN STOCK" if r.stock <= 0 else ("CRÍTICO" if r.stock <= r.stock_minimo else "NORMAL"), axis=1)
        alerts = alerts[alerts["riesgo"] != "NORMAL"].copy()
    return {"Inventario": stock, "Ventas confirmadas": sales, "Compras confirmadas": purchases, "Kardex": kardex, "Alertas de stock": alerts}


def build_attachments(sb) -> list[tuple[str, bytes, str]]:
    reports = collect_reports(sb)
    stamp = datetime.now(TZ).strftime("%Y%m%d_%H%M")
    # Libro Excel con una hoja por informe
    xlsx_io = io.BytesIO()
    with pd.ExcelWriter(xlsx_io, engine="openpyxl") as writer:
        for name, df in reports.items():
            safe = name[:31]
            (df if not df.empty else pd.DataFrame({"resultado": ["Sin registros para este informe"]})).to_excel(writer, sheet_name=safe, index=False)
    # PDF consolidado con todas las secciones
    pdf_io = io.BytesIO()
    doc = SimpleDocTemplate(pdf_io, pagesize=landscape(A4), leftMargin=9*mm, rightMargin=9*mm, topMargin=10*mm, bottomMargin=10*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("AgroTitle", parent=styles["Title"], textColor=colors.HexColor("#5420A8"), fontSize=18)
    story = [Paragraph("AgroInventario · Reporte consolidado", title_style), Paragraph(f"Generado: {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')} (hora de Perú)", styles["Normal"]), Spacer(1, 10)]
    for name, df in reports.items():
        story.append(Paragraph(name, styles["Heading2"]))
        if df.empty:
            story.append(Paragraph("Sin registros para este informe.", styles["Normal"]))
        else:
            view = df.head(250).fillna("").astype(str)
            headers = [str(c)[:28] for c in view.columns]
            data = [headers] + [[str(v)[:70] for v in row] for row in view.values.tolist()]
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#5420A8")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#D8B9F0")),
                ("FONTSIZE", (0,0), (-1,-1), 6),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F5FC")]),
            ]))
            story.extend([table, Spacer(1, 10)])
    doc.build(story)
    return [
        (f"AgroInventario_reportes_{stamp}.pdf", pdf_io.getvalue(), "application/pdf"),
        (f"AgroInventario_reportes_{stamp}.xlsx", xlsx_io.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ]


def send_gmail(to_email: str, subject: str, body: str, attachments: list[tuple[str, bytes, str]]) -> None:
    sender = _setting("GMAIL_SENDER")
    app_password = _setting("GMAIL_APP_PASSWORD")
    if not sender or not app_password:
        raise RuntimeError("Configura GMAIL_SENDER y GMAIL_APP_PASSWORD en .streamlit/secrets.toml.")
    if not to_email or "@" not in to_email:
        raise ValueError("Ingresa un correo destinatario válido.")
    msg = EmailMessage()
    msg["From"] = sender; msg["To"] = to_email; msg["Subject"] = subject
    msg.set_content(body)
    for filename, payload, mime in attachments:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(payload, maintype=maintype, subtype=subtype, filename=filename)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(sender, app_password)
        server.send_message(msg)


def send_daily_reports(sb) -> None:
    recipient = _setting("GMAIL_REPORT_TO")
    if not recipient:
        raise RuntimeError("Configura GMAIL_REPORT_TO para habilitar el envío automático diario.")
    attachments = build_attachments(sb)
    now = datetime.now(TZ)
    send_gmail(recipient, f"AgroInventario · Reporte diario · {now:%d/%m/%Y}", "Adjuntamos los reportes actuales de inventario, ventas confirmadas, compras confirmadas, Kardex y alertas de stock. Los archivos reflejan los datos disponibles en Supabase al momento de generarlos.", attachments)


@st.cache_resource
def start_daily_scheduler(_sb):
    """Scheduler de proceso: funciona mientras este proceso de Streamlit permanezca activo."""
    scheduler = BackgroundScheduler(timezone=TZ)
    scheduler.add_job(send_daily_reports, "cron", hour=8, minute=0, args=[_sb], id="agroinventario_daily_reports", replace_existing=True, misfire_grace_time=3600, coalesce=True)
    scheduler.start()
    return scheduler


def render_mail_agent(sb) -> None:
    st.markdown("<div class='section'>✉️ AgroMail · Envío de reportes</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitulo'>Envía los informes cuando tú quieras o configura el envío automático diario.</div>", unsafe_allow_html=True)
    sender = _setting("GMAIL_SENDER", "")
    auto_to = _setting("GMAIL_REPORT_TO", "")
    if sender:
        st.success(f"Gmail configurado: {sender}")
    else:
        st.warning("Falta configurar Gmail en .streamlit/secrets.toml. No se enviará nada hasta completar la configuración.")
    st.caption("El paquete adjunto contiene un PDF consolidado y un Excel con hojas de inventario, ventas, compras, Kardex y alertas.")
    with st.form("agromail_manual_form"):
        recipient = st.text_input("Correo destinatario", value=auto_to, placeholder="destinatario@empresa.com")
        subject = st.text_input("Asunto", value=f"AgroInventario · Reportes · {datetime.now(TZ):%d/%m/%Y}")
        body = st.text_area("Mensaje", value="Hola,\n\nAdjunto los reportes actualizados de AgroInventario.\n\nSaludos.")
        confirmed = st.checkbox("Confirmo que deseo enviar estos reportes al destinatario indicado.")
        send = st.form_submit_button("📨 ENVIAR AHORA", type="primary", use_container_width=True)
    if send:
        if not confirmed:
            st.error("Marca la confirmación antes de enviar.")
        else:
            try:
                with st.spinner("Preparando informes y enviando el correo..."):
                    attachments = build_attachments(sb)
                    send_gmail(recipient, subject, body, attachments)
                st.success(f"Correo enviado a {recipient} con PDF y Excel adjuntos.")
            except Exception as exc:
                st.error(f"No se pudo enviar el correo: {exc}")
    st.divider()
    st.subheader("Envío automático diario · 08:00 a. m. hora de Perú")
    st.write("El sistema enviará los cinco informes al destinatario definido en GMAIL_REPORT_TO. No se activa un correo de prueba.")
    st.info("Importante: el programador integrado funciona mientras el proceso de Streamlit esté activo. Para garantizar el envío aunque la aplicación esté apagada, despliega el envío como tarea programada externa (por ejemplo, cron en un servidor siempre encendido).")
    if st.button("🕗 Activar / verificar programación diaria", use_container_width=True):
        try:
            scheduler = start_daily_scheduler(sb)
            st.success(f"Programación activa. Próximo envío: {scheduler.get_job('agroinventario_daily_reports').next_run_time} (hora de Perú).")
        except Exception as exc:
            st.error(f"No se pudo iniciar el programador: {exc}")
