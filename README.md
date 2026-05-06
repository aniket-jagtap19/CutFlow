# 🪟 FENESTRA – Window & Door Fabrication Software

**D Sign Design Code Competition Entry**  
Built with Django + Python · HTML/CSS/JS · ReportLab · OpenPyXL

---

## Features

| Feature | Details |
|---|---|
| **Window/Door Schedule** | Add multiple windows with code, size, typology, glass, finish, mesh |
| **Profile Cut List** | Computed cuts for outer frame, sash, mullion, bead, mesh frame |
| **Bar Optimisation** | First-Fit Decreasing (FFD) heuristic across all profile types |
| **Glass Schedule** | Exact glass sizes + total area per window |
| **Hardware BOQ** | Per-typology hardware with quantities and cost |
| **PDF Quotation** | Professional 6-section PDF with cost breakdown |
| **Excel Report** | 5-sheet workbook: Summary, Cuts, Glass, Hardware, Bar Optimisation |
| **Live UI Preview** | Tabbed results with bar utilisation chart |

---

## Supported Typologies

- Sliding Window
- Casement Window
- Fixed / Picture Window
- Sliding Door
- Swing Door

---

## Setup & Run (Local)

### Requirements

```
Python 3.10+
pip
```

### Install

```bash
# Clone / unzip the project
cd fenestra_project

# Install dependencies
pip install django reportlab openpyxl

# Run migrations (no models, but initialises DB)
python manage.py migrate --run-syncdb

# Start dev server
python manage.py runserver
```

### Open in browser

```
http://127.0.0.1:8000/
```

---

## Deploy to DigitalOcean (Phase 2)

### Option A – App Platform (simplest)

1. Push repo to GitHub
2. Create new App on DigitalOcean → connect repo
3. Set environment: `DJANGO_SETTINGS_MODULE=fenestra.settings`
4. Build command: `pip install -r requirements.txt`
5. Run command: `gunicorn fenestra.wsgi`

### Option B – Droplet (full control)

```bash
# On Ubuntu 22.04 droplet
sudo apt update && sudo apt install python3-pip nginx -y
pip install gunicorn django reportlab openpyxl

# Clone project
git clone <repo> /var/www/fenestra
cd /var/www/fenestra

# Gunicorn service
gunicorn fenestra.wsgi:application --bind 0.0.0.0:8000 --daemon

# Configure nginx to proxy :80 → :8000
```

---

## Requirements File

```
django>=4.2
reportlab>=4.0
openpyxl>=3.1
gunicorn>=21.0
```

---

## Project Structure

```
fenestra/
├── manage.py
├── README.md
├── requirements.txt
├── fenestra/               # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── fabricator/             # Main app
│   ├── calculator.py       # Core engine: cuts, costs, bar optimisation
│   ├── reports.py          # PDF + Excel generators
│   ├── views.py            # HTTP endpoints
│   └── urls.py
└── templates/
    └── fabricator/
        └── index.html      # Single-page UI
```

---

## Calculation Logic

### Profile Cuts
- **Outer Frame**: 2 horizontal (= width) + 2 vertical (= height)
- **Sash**: 4 horizontal + 4 vertical (inset 15 mm each side; sliding = half-width sash)
- **Glass Bead**: Around each sash inner perimeter
- **Mullion**: Added for widths > 1200 mm
- **Mesh Frame**: Added if mesh option selected

### Bar Optimisation (FFD)
1. All required cuts aggregated across all windows
2. Sorted largest → smallest
3. Each piece placed in first bar with sufficient remaining space
4. Kerf = 5 mm, end waste = 10 mm per bar
5. Reports: bars needed, utilisation %, waste per profile

### Cost Calculation
- Profile cost = metres × ₹/m rate
- Glass cost = area (m²) × ₹/m² rate
- Hardware cost = item unit cost × quantity
- Finish surcharge = % on (profile + glass) cost
- GST = 18% on subtotal

---

## Evaluation Criteria Coverage

| Criterion | Implementation |
|---|---|
| All functionalities | ✅ Quotation, Profile BOQ, Bar Optimiser, Glass, Hardware |
| Code discipline | ✅ Docstrings on all functions, type hints, comments |
| Code organisation | ✅ Separated into calculator / reports / views / urls |
| UI/UX | ✅ Responsive, dark industrial theme, live tabs, toasts |
| Tutorials | ✅ This README + inline help text + sample data loader |

---

*Built for D Sign Design × Walchand College of Engineering Code Competition · 2026*
