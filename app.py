import io
import ssl
import requests
import pandas as pd
from flask import Flask, render_template_string, redirect, url_for

app = Flask(__name__)

# ================== CONFIGURACIÓN ==================
SHEET_ID = "1crXQPxRr5NilAOpXO4oz_izzixBt8_ZT"  # ID de tu Google Sheet
HOJAS = [
    "DOCENCIA", "PTC", "UNIDAD DE EDUCACION INCLUYENTE",
    "TUTORIAS", "ALUMNOS PUEBLOS ORIGINARIOS", "SERVICIO SOCIAL"
]

# Si en tu Mac aún sale el error SSL (CERTIFICATE_VERIFY_FAILED),
# puedes poner esto en True TEMPORALMENTE mientras arreglas certificados:
ALLOW_INSECURE_SSL = False
if ALLOW_INSECURE_SSL:
    ssl._create_default_https_context = ssl._create_unverified_context
# ===================================================

sheets = {}
errores = []

def cargar_sheets():
    """Lee todas las hojas desde Drive (CSV) y devuelve (dict_sheets, lista_errores)."""
    tmp_sheets = {}
    tmp_errores = []
    for hoja in HOJAS:
        hoja_formateada = hoja.replace(" ", "+")
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={hoja_formateada}"
        try:
            r = requests.get(url, timeout=25, verify=not ALLOW_INSECURE_SSL)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            tmp_sheets[hoja] = df
        except Exception as e:
            tmp_errores.append(f"Error leyendo '{hoja}': {e}")
            tmp_sheets[hoja] = pd.DataFrame()
    return tmp_sheets, tmp_errores

# Carga inicial
sheets, errores = cargar_sheets()

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Coordinaciones</title>
        <link rel="stylesheet"
              href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
        <style>
            .search-input { margin-bottom: 10px; width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
            .topbar { display: flex; gap: 12px; align-items: center; justify-content: space-between; }
            .errors { margin-top: 10px; }
        </style>
    </head>
    <body>
    <div class="container mt-4">
        <div class="topbar">
            <h1 class="mb-3">Coordinaciones</h1>
            <a class="btn btn-primary" href="{{ url_for('reload_data') }}">🔄 Recargar datos de Drive</a>
        </div>

        {% if errores %}
        <div class="alert alert-warning errors" role="alert">
            <div><strong>Aviso:</strong> hubo problemas cargando algunas hojas.</div>
            <ul class="mb-0">
            {% for e in errores %}<li>{{ e }}</li>{% endfor %}
            </ul>
        </div>
        {% endif %}

        <ul class="nav nav-tabs" id="myTab" role="tablist">
    """

    # pestañas
    for i, nombre in enumerate(sheets.keys()):
        active = "active" if i == 0 else ""
        html += f'''
            <li class="nav-item" role="presentation">
                <button class="nav-link {active}" id="tab-{i}" data-bs-toggle="tab"
                        data-bs-target="#content-{i}" type="button" role="tab">{nombre}</button>
            </li>
        '''

    html += '</ul><div class="tab-content mt-3">'

    # contenido de cada pestaña
    for i, (nombre, df) in enumerate(sheets.items()):
        active = "show active" if i == 0 else ""
        html += f'<div class="tab-pane fade {active}" id="content-{i}" role="tabpanel">'
        html += f'<input type="text" class="search-input" placeholder="Buscar en {nombre}..." onkeyup="filtrar(this, \'table-{i}\')">'

        if df is None or df.empty:
            html += '<div class="alert alert-light">No hay datos para mostrar en esta hoja.</div>'
        else:
            html += f'<div class="table-responsive"><table class="table table-bordered table-sm" id="table-{i}">'
            html += "<thead><tr>" + "".join([f"<th>{col}</th>" for col in df.columns]) + "</tr></thead><tbody>"

            # === FILAS DE DATOS ===
            max_rows = 500
            for _, fila in df.head(max_rows).iterrows():
                html += "<tr>" + "".join([f"<td>{fila[col]}</td>" for col in df.columns]) + "</tr>"

            # === FILA DE TOTALES ===
            totales = df.sum(numeric_only=True)
            html += "<tr style='font-weight:bold; background:#f2f2f2'>"
            for col in df.columns:
                if col in totales:  # si la columna es numérica
                    html += f"<td>{totales[col]}</td>"
                else:
                    html += "<td></td>"
            html += "</tr>"

            html += "</tbody></table></div>"

        html += "</div>"

    html += """
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function filtrar(input, tableId) {
            var filtro = input.value.toLowerCase();
            var filas = document.querySelectorAll(`#${tableId} tbody tr`);
            filas.forEach(fila => {
                var texto = fila.innerText.toLowerCase();
                fila.style.display = texto.includes(filtro) ? '' : 'none';
            });
        }
    </script>
    </body>
    </html>
    """
    return render_template_string(html, errores=errores)

@app.route('/reload')
def reload_data():
    global sheets, errores
    sheets, errores = cargar_sheets()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
