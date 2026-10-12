# AgroInventario — AgroCharts + AgroMail

Esta entrega añade dos módulos al proyecto existente sin reemplazar `ai_agent.py` ni cambiar la conexión a Supabase:

- **AgroCharts** (`chart_agent.py`): gráficos Plotly interactivos a partir de datos consultados en Supabase.
- **AgroMail** (`mail_agent.py`): envío manual de reportes por Gmail con confirmación explícita, adjuntando PDF consolidado y Excel con hojas de inventario, ventas confirmadas, compras confirmadas, Kardex y alertas.
- **`app.py`**: integra los dos módulos en el menú lateral, conservando el CSS y el diseño actual.
- **`requirements.txt`**: incorpora APScheduler para la programación diaria.

## Instalar en VS Code

1. Haz una copia de seguridad de tu proyecto actual.
2. Copia los archivos nuevos `chart_agent.py` y `mail_agent.py` en la misma carpeta donde están `app.py` y `ai_agent.py`.
3. Sustituye tu `app.py` por el `app.py` incluido en esta entrega. No reemplaces `ai_agent.py`.
4. Sustituye/actualiza `requirements.txt` por el incluido.
5. Crea la carpeta `.streamlit` si no existe. Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completa los valores reales.
6. En la terminal de VS Code ejecuta:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Configurar Gmail de forma segura

1. En la cuenta remitente de Google, activa la verificación en dos pasos.
2. Crea una **contraseña de aplicación** de Google. Usa esa contraseña, no la contraseña habitual de Gmail.
3. Completa en `.streamlit/secrets.toml` `GMAIL_SENDER`, `GMAIL_APP_PASSWORD` y `GMAIL_REPORT_TO`.
4. `GMAIL_REPORT_TO` es el destinatario del envío automático. El formulario de AgroMail permite elegir otro destinatario para cada envío manual.
5. Nunca compartas `secrets.toml` ni lo subas al repositorio. Añade `.streamlit/secrets.toml` al `.gitignore`.

Ejemplo de configuración (no uses estos valores ficticios literalmente):

```toml
SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
SUPABASE_KEY = "TU_SUPABASE_ANON_KEY"
GROQ_API_KEY = "TU_GROQ_API_KEY"
GMAIL_SENDER = "tu-cuenta@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
GMAIL_REPORT_TO = "destinatario@empresa.com"
```

## Enviar cuando tú quieras

En la aplicación abre **✉️ AgroMail**, revisa el destinatario, asunto y mensaje, marca la casilla de confirmación y pulsa **ENVIAR AHORA**. El correo no se envía solo por abrir la pantalla; requiere pulsar el botón y confirmar. Se adjunta un PDF y un Excel.

## Envío automático diario a las 08:00 de Perú

En **AgroMail**, pulsa **Activar / verificar programación diaria** una vez que Gmail esté configurado. El trabajo diario usa la zona horaria `America/Lima` y envía los cinco informes a `GMAIL_REPORT_TO`.

**Limitación importante:** APScheduler está integrado en el proceso de Streamlit, por lo que el proceso debe permanecer encendido para ejecutar el trabajo. Si el hosting duerme, reinicia o apaga el proceso, el envío puede omitirse. Para fiabilidad de producción, ejecuta `send_daily_reports(sb)` desde un cron/tarea programada en un servidor siempre activo o un servicio de tareas programadas. No se envía ningún correo de prueba al instalar.

## Datos y límites

- Las ventas incluidas son solo `tipo_salida = VENTA` y `estado = CONFIRMADO`.
- Las compras incluidas son solo registros con `estado = CONFIRMADO`.
- Los reportes se construyen con los datos existentes en Supabase; si no hay filas, el informe lo refleja en blanco/sin registros, sin inventar valores.
- Los gráficos son análisis visuales; no modifican datos en Supabase.
