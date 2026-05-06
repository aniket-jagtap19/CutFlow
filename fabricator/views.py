"""
CutFlow – Views
"""
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
    # fabricator/views.py (Additions)
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Project, SavedWindow

# --- AUTHENTICATION VIEWS ---
from .calculator import WindowEntry, compute_window, optimise_bars, aggregate_hardware
from .calculator import TYPOLOGY_LABELS, GLASS_OPTIONS, FINISH_OPTIONS, PROFILES
from .reports import generate_pdf_quotation, generate_excel_report


def index(request):
    ctx = {
        "typologies": TYPOLOGY_LABELS,
        "glass_options": GLASS_OPTIONS,
        "finish_options": FINISH_OPTIONS,
    }
    return render(request, "fabricator/index.html", ctx)


@csrf_exempt
def calculate(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        payload = json.loads(request.body)
        windows = payload.get("windows", [])
        if not windows:
            return JsonResponse({"error": "No windows provided"}, status=400)

        entries = [WindowEntry(
            code=w["code"], width=float(w["width"]), height=float(w["height"]),
            typology=w["typology"], glass_type=w["glass_type"],
            finish=w["finish"], mesh=bool(w.get("mesh", False)),
            qty=int(w.get("qty", 1)),
        ) for w in windows]

        results = [compute_window(e) for e in entries]
        bar_data = optimise_bars(results)
        agg_hw = aggregate_hardware(results)

        out_windows = []
        for r in results:
            e = r.entry
            out_windows.append({
                "code": e.code,
                "typology": TYPOLOGY_LABELS.get(e.typology, e.typology),
                "size": f"{int(e.width)} x {int(e.height)} mm",
                "qty": e.qty,
                "glass": GLASS_OPTIONS.get(e.glass_type, {}).get("label", ""),
                "finish": FINISH_OPTIONS.get(e.finish, {}).get("label", ""),
                "mesh": e.mesh,
                "glass_size": f"{r.glass_width:.0f} x {r.glass_height:.0f} mm",
                "glass_area": round(r.glass_area * e.qty, 4),
                "profile_cuts": [
                    {"label": pc.label, "length": pc.length,
                     "count": pc.count, "total_pcs": pc.count * e.qty}
                    for pc in r.profile_cuts
                ],
                "hardware": r.hardware,
                "costs": {
                    "profile": r.profile_cost,
                    "glass":   r.glass_cost,
                    "hardware":r.hardware_cost,
                    "finish":  r.finish_surcharge,
                    "subtotal":r.total_cost,
                    "gst":     round(r.total_cost * 0.18, 2),
                    "total":   round(r.total_cost * 1.18, 2),
                },
            })

        bar_summary = {}
        for pk, bars in bar_data.items():
            if not bars:
                continue
            bar_summary[PROFILES[pk]["label"]] = {
                "bars":  len(bars),
                "total_len": round(sum(b.bar_length for b in bars) / 1000, 2),
                "used":      round(sum(b.used for b in bars) / 1000, 2),
                "waste":     round(sum(b.waste for b in bars) / 1000, 2),
                "util":      round(sum(b.used for b in bars) /
                                   max(sum(b.bar_length for b in bars), 1) * 100, 1),
                "detail": [
                    {"bar": b.bar_id,
                     "cuts": [{"len": c[0], "label": c[1]} for c in b.cuts],
                     "used": round(b.used), "waste": round(b.waste),
                     "util": round(b.utilisation, 1)}
                    for b in bars
                ],
            }

        grand_total_ex_gst = sum(r.total_cost for r in results)
        return JsonResponse({
            "windows": out_windows,
            "bar_summary": bar_summary,
            "hardware_total": agg_hw,
            "grand_total_ex_gst": round(grand_total_ex_gst, 2),
            "gst": round(grand_total_ex_gst * 0.18, 2),
            "grand_total": round(grand_total_ex_gst * 1.18, 2),
        })
    except Exception as exc:
        import traceback; traceback.print_exc()
        return JsonResponse({"error": str(exc)}, status=400)


def _parse_and_compute(payload):
    windows = payload.get("windows", [])
    entries = [WindowEntry(
        code=w["code"], width=float(w["width"]), height=float(w["height"]),
        typology=w["typology"], glass_type=w["glass_type"],
        finish=w["finish"], mesh=bool(w.get("mesh", False)),
        qty=int(w.get("qty", 1)),
    ) for w in windows]
    return entries, [compute_window(e) for e in entries]


@csrf_exempt
def download_pdf(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        payload = json.loads(request.body)
        entries, results = _parse_and_compute(payload)
        bar_data = optimise_bars(results)
        pdf_bytes = generate_pdf_quotation(results, bar_data)
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = 'attachment; filename="CutFlow_quotation.pdf"'
        return resp
    except Exception as exc:
        import traceback; traceback.print_exc()
        return HttpResponse(str(exc), status=400)


@csrf_exempt
def download_excel(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        payload = json.loads(request.body)
        entries, results = _parse_and_compute(payload)
        bar_data = optimise_bars(results)
        xl_bytes = generate_excel_report(results, bar_data)
        resp = HttpResponse(xl_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = 'attachment; filename="CutFlow_boq.xlsx"'
        return resp
    except Exception as exc:
        return HttpResponse(str(exc), status=400)
    


@csrf_exempt
def api_register(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)
        
        user = User.objects.create_user(username=username, password=password)
        login(request, user) # Auto-login after register
        return JsonResponse({"message": "Registered and logged in successfully!"})

@csrf_exempt
def api_login(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user = authenticate(request, username=data.get("username"), password=data.get("password"))
        if user is not None:
            login(request, user)
            return JsonResponse({"message": "Logged in successfully", "username": user.username})
        else:
            return JsonResponse({"error": "Invalid credentials"}, status=400)

def api_logout(request):
    logout(request)
    return JsonResponse({"message": "Logged out successfully"})

# --- DATABASE SAVING VIEWS ---

@login_required
@csrf_exempt
def save_project(request):
    """Saves the current window schedule to the user's account."""
    if request.method == "POST":
        data = json.loads(request.body)
        project_name = data.get("project_name", "Untitled Project")
        windows = data.get("windows", [])

        # Create the project
        project = Project.objects.create(user=request.user, name=project_name)

        # Save all windows to the project
        for w in windows:
            SavedWindow.objects.create(
                project=project,
                code=w["code"],
                width=float(w["width"]),
                height=float(w["height"]),
                typology=w["typology"],
                glass_type=w["glass_type"],
                finish=w["finish"],
                mesh=bool(w.get("mesh", False)),
                qty=int(w.get("qty", 1))
            )
        
        return JsonResponse({"message": "Project saved successfully!", "project_id": project.id})
    # --- PAGE RENDER VIEWS ---

def login_page(request):
    # If already logged in, send them to the main calculator
    if request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('index')
    return render(request, "fabricator/login.html")

def register_page(request):
    if request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('index')
    return render(request, "fabricator/register.html")

# fabricator/views.py (Add to bottom)

@login_required
def api_get_projects(request):
    """Fetches all saved projects for the logged-in user."""
    # Get all projects for the user, newest first
    projects = Project.objects.filter(user=request.user).order_by('-created_at')
    
    data = []
    for p in projects:
        # Get all windows associated with this project
        windows = list(p.windows.values(
            'id', 'code', 'width', 'height', 'typology', 'glass_type', 'finish', 'mesh', 'qty'
        ))
        data.append({
            "id": p.id,
            "name": p.name,
            "created_at": p.created_at.strftime('%Y-%m-%d %H:%M'),
            "windows": windows
        })
        
    return JsonResponse({"projects": data})
