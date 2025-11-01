# 💼 Interfaccia Admin con NiceGUI 3.2.0 e FastAPI

Questo documento mostra come creare un'interfaccia **admin** utilizzando **NiceGUI 3.2.0** integrata con **FastAPI**, che visualizza i risultati di un'API in una **AG Grid** e utilizza **dialog modali auto-espandibili**.

---

## 📦 Requisiti

Installa i pacchetti necessari:

```bash
pip install nicegui==3.2.0 fastapi pandas
```

---

## 💻 Codice completo (`main.py`)

```python
from fastapi import FastAPI
from nicegui import ui
import pandas as pd

# --- FastAPI backend ---
app = FastAPI()

@app.get("/api/data")
def get_data():
    '''Restituisce dati di esempio come JSON.'''
    df = pd.DataFrame([
        {"id": 1, "nome": "Mario", "città": "Milano", "vendite": 1200},
        {"id": 2, "nome": "Lucia", "città": "Torino", "vendite": 980},
        {"id": 3, "nome": "Gianni", "città": "Roma", "vendite": 1430},
    ])
    return df.to_dict(orient="records")


# --- NiceGUI UI (montata su FastAPI) ---
@ui.page('/')
def index():
    ui.label('💼 Pannello Admin con AG Grid e Dialog Auto-Espandibile').classes('text-xl mb-4')

    # Griglia collegata a un endpoint API FastAPI
    grid = ui.aggrid({
        'columnDefs': [
            {'headerName': 'ID', 'field': 'id', 'width': 80},
            {'headerName': 'Nome', 'field': 'nome'},
            {'headerName': 'Città', 'field': 'città'},
            {'headerName': 'Vendite', 'field': 'vendite'},
        ],
        'rowSelection': 'single',
    }).classes('w-full h-64')

    # Popola la grid chiamando l'API interna
    async def load_data():
        from httpx import AsyncClient
        async with AsyncClient() as client:
            r = await client.get('http://localhost:8080/api/data')
            grid.options['rowData'] = r.json()
            await grid.update()

    ui.button('🔄 Aggiorna dati', on_click=load_data).classes('mb-4')

    # --- Dialog modale auto-espandibile ---
    with ui.dialog() as dialog:
        dialog.classes('auto-dialog')
        with ui.card().classes('p-4'):
            ui.label('📋 Dettagli Record Selezionato').classes('text-lg mb-2')
            details = ui.label('Nessun record selezionato')
            ui.button('Chiudi', on_click=dialog.close)

    # Quando l'utente clicca su una riga, mostra il dialog con i dettagli
    @grid.on('rowClicked')
    async def on_row_clicked(e):
        row = e.args['data']
        details.text = f"ID: {row['id']} | Nome: {row['nome']} | Città: {row['città']} | Vendite: {row['vendite']}"
        await details.update()
        dialog.open()  # si apre adattandosi automaticamente al contenuto

    # carica i dati iniziali
    ui.timer(0.1, load_data, once=True)


# --- CSS opzionale per ottimizzare la dimensione automatica ---
ui.add_head_html('''
<style>
.auto-dialog .q-dialog__inner {
    align-items: flex-start !important;   /* evita che venga centrato verticalmente */
}
.auto-dialog .q-card {
    width: auto !important;
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
}
</style>
''')

# --- Avvio combinato di FastAPI + NiceGUI ---
ui.run_with(app, port=8080)
```

---

## 🧠 Spiegazione passo-passo

| Sezione | Descrizione |
|----------|-------------|
| **FastAPI backend** | Espone `/api/data` che restituisce dati JSON (simulando i risultati reali delle tue API). |
| **AG Grid** | Mostra i dati ricevuti dall'API. La proprietà `rowSelection: 'single'` consente di selezionare una sola riga. |
| **Dialog modale** | Contiene un `ui.card()` che si **auto-adatta** al contenuto. Nessuna larghezza o altezza fissa viene imposta. |
| **CSS `.auto-dialog`** | Rimuove la centratura verticale e consente espansione fluida fino al 90 % dello schermo. |
| **Evento `on_row_clicked`** | Quando l'utente clicca una riga, il dialog mostra i dettagli e si apre automaticamente. |
| **`ui.run_with(app)`** | Collega NiceGUI e FastAPI sullo stesso server. |

---

## 🚀 Avvio

Esegui:

```bash
python main.py
```

Poi apri **http://localhost:8080** nel browser.

Cliccando su una riga della griglia, si aprirà un **dialog modale auto-espandibile** che mostra i dettagli del record selezionato, ridimensionandosi automaticamente alla larghezza del contenuto.

---

## 🎨 Dialog Auto-Espandibili vs Dimensioni Fisse

### Auto-Espansione (Raccomandato)

```python
with ui.dialog().classes('auto-dialog') as dialog:
    with ui.card():
        # Il contenuto determina la dimensione
        ui.label('Contenuto dinamico')
```

```css
.auto-dialog .q-card {
    width: auto !important;
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
}
```

**Vantaggi:**
- Si adatta automaticamente al contenuto
- Responsive su diverse risoluzioni
- Meno codice da mantenere

### Dimensioni Fisse (Sconsigliato)

```python
with ui.dialog() as dialog:
    with ui.card().style("width: 800px; height: 600px"):
        # Dimensione fissa
```

**Svantaggi:**
- Richiede calcoli manuali
- Non responsive
- Può tagliare il contenuto

---

## 📐 Ridimensionamento Manuale (Resizable)

Per permettere all'utente di ridimensionare manualmente il dialog:

```python
with ui.dialog().classes('resizeable-dialog') as dialog:
    with ui.card():
        ui.label('Trascina l\'angolo per ridimensionare')
```

```css
.resizeable-dialog .q-card {
    resize: both;
    overflow: auto;
    min-width: 300px;
    min-height: 200px;
}
```

**Nota**: Combina auto-espansione iniziale con ridimensionamento manuale per la massima flessibilità.

---

## 🔗 Risorse Utili

- **NiceGUI Documentation**: https://nicegui.io/documentation
- **AG Grid Options**: https://www.ag-grid.com/javascript-data-grid/grid-options/
- **Quasar Dialog**: https://quasar.dev/vue-components/dialog (NiceGUI usa Quasar sotto)
- **FastAPI Integration**: https://nicegui.io/documentation/section_configuration_deployment#fastapi

---

**Last Updated**: 2025-01-30
**Author**: Genropy Team
