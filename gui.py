import tkinter as tk
from tkinter import ttk, messagebox
from core.batch import batch_screen
from core.visualization.viewer import show_molecule, show_pair

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image as RLImage
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4

from PIL import Image, ImageTk
import datetime


# =========================
# GUI SETUP
# =========================

root = tk.Tk()
root.title("AgniKristal™ Research Platform")
root.geometry("750x750")

logo = tk.PhotoImage(file="logo.png")

logo_label = ttk.Label(root, image=logo)
logo_label.pack(pady=10)

title_label = ttk.Label(
    root,
    text="AgniKristal™ Co-crystal Screening Engine",
    font=("Arial", 16, "bold")
)
title_label.pack(pady=10)


# =========================
# LOGO DISPLAY
# =========================

from PIL import Image, ImageTk
import os

try:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")

    logo_img = Image.open(logo_path)
    logo_img = logo_img.resize((140, 140))

    logo_photo = ImageTk.PhotoImage(logo_img)

    logo_label = tk.Label(root, image=logo_photo)
    logo_label.image = logo_photo
    logo_label.pack(pady=10)

except Exception as e:
    print("Logo loading error:", e)


# =========================
# INPUT SECTION
# =========================

api_label = ttk.Label(root, text="API SMILES:")
api_label.pack()

api_entry = ttk.Entry(root, width=85)
api_entry.pack(pady=5)


# ⭐ NEW FUNCTION
# =========================
# VIEW API MOLECULE
# =========================

def view_api_molecule():

    smiles = api_entry.get().strip()

    if not smiles:
        messagebox.showerror("Error", "Enter API SMILES first")
        return

    try:
        show_molecule(smiles)
    except Exception as e:
        messagebox.showerror("Viewer Error", str(e))


# ⭐ NEW BUTTON
view_button = ttk.Button(
    root,
    text="View API Molecule (3D)",
    command=view_api_molecule
)
view_button.pack(pady=5)


coformer_label = ttk.Label(
    root,
    text="Coformers (One per line: Name,SMILES)"
)
coformer_label.pack()

coformer_textbox = tk.Text(root, height=8, width=85)
coformer_textbox.pack(pady=5)


# =========================
# RESULTS SECTION
# =========================

result_label = ttk.Label(root, text="Results:")
result_label.pack()

result_text = tk.Text(root, height=8, width=85)
result_text.pack(pady=5)


# =========================
# GRAPH SECTION
# =========================

graph_label = ttk.Label(root, text="Score Visualization:")
graph_label.pack()

graph_frame = ttk.Frame(root)
graph_frame.pack(pady=10)


# =========================
# PDF GENERATOR
# =========================

def generate_pdf(api_smiles, results):

    filename = f"AgniKristal_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    try:
        logo = RLImage("logo.png", width=90, height=90)
        elements.append(logo)
        elements.append(Spacer(1, 0.2 * inch))
    except:
        pass

    elements.append(Paragraph(
        "<b>AgniKristal™ Co-crystal Screening Report</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        "<b>AgniKristal™ Research Platform</b>",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"<b>API SMILES:</b> {api_smiles}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 0.3 * inch))

    data = [["Coformer", "Final Score", "Prediction"]]

    for r in results:
        data.append([
            r["Coformer"],
            str(r["Final Score"]),
            r["Prediction"]
        ])

    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))

    elements.append(table)
    doc.build(elements)

    messagebox.showinfo("Success", f"PDF Report Generated:\n{filename}")

# =========================
# INTERACTION VIEWER
# =========================

def view_interaction():

    api = api_entry.get().strip()

    text = coformer_textbox.get("1.0", tk.END).strip().split("\n")

    if not text:
        messagebox.showerror("Error", "Enter a coformer first")
        return

    try:
        name, smiles = text[0].split(",")

        show_pair(api, smiles.strip())

    except Exception as e:
        messagebox.showerror("Error", str(e))

# =========================
# SCREENING FUNCTION
# =========================

def run_screening():

    api_smiles = api_entry.get().strip()

    if not api_smiles:
        messagebox.showerror("Error", "Please enter API SMILES.")
        return

    coformer_text = coformer_textbox.get("1.0", tk.END).strip()

    if not coformer_text:
        messagebox.showerror("Error", "Please enter at least one coformer.")
        return

    coformers = []
    lines = coformer_text.split("\n")

    for line in lines:
        try:
            name, smiles = line.split(",")
            coformers.append((name.strip(), smiles.strip()))
        except:
            messagebox.showerror(
                "Format Error",
                "Each line must be: Name,SMILES"
            )
            return

    results = batch_screen(api_smiles, coformers)

    result_text.delete("1.0", tk.END)

    for r in results:
        result_text.insert(
            tk.END,
            f"{r['Coformer']}  |  "
            f"Score: {r['Final Score']}  |  "
            f"{r['Prediction']}\n"
        )

    generate_pdf(api_smiles, results)

    for widget in graph_frame.winfo_children():
        widget.destroy()

    fig, ax = plt.subplots(figsize=(6, 3))

    names = [r["Coformer"] for r in results]
    scores = [r["Final Score"] for r in results]

    ax.bar(names, scores)
    ax.set_ylabel("Final Score")
    ax.set_title("Coformer Screening Scores")
    ax.tick_params(axis='x', rotation=45)

    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().pack()


# =========================
# RUN BUTTON
# =========================

run_button = ttk.Button(
    root,
    text="Run Screening",
    command=run_screening
)
run_button.pack(pady=10)


# =========================
# INTERACTION VIEWER BUTTON
# =========================

interaction_button = ttk.Button(
    root,
    text="View API + First Coformer Interaction",
    command=view_interaction
)
interaction_button.pack(pady=5)


# =========================
# PROCESS ALTERNATIVES (DAPAGLIFLOZIN)
# =========================

def open_process_alternatives():

    from core.process_alternatives import (
        get_alternatives, list_steps, DISCLAIMER
    )

    win = tk.Toplevel(root)
    win.title("Dapagliflozin Process Alternatives")
    win.geometry("1100x480")

    top = ttk.Frame(win)
    top.pack(fill="x", padx=10, pady=8)

    ttk.Label(top, text="Step:").pack(side="left")

    step_var = tk.StringVar(value="All")
    step_box = ttk.Combobox(
        top,
        textvariable=step_var,
        values=["All"] + list_steps(),
        state="readonly",
        width=40
    )
    step_box.pack(side="left", padx=5)

    columns = ("reagent", "conditions", "pros", "cons", "maturity", "cost", "likelihood")
    headings = ("Reagent / option", "Conditions", "Pros", "Cons", "Maturity", "Cost vs baseline", "Likelihood (heuristic)")
    widths = (240, 170, 200, 200, 100, 100, 110)

    tree = ttk.Treeview(win, columns=columns, show="headings", height=14)
    for col, head, width in zip(columns, headings, widths):
        tree.heading(col, text=head)
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh(*_):
        tree.delete(*tree.get_children())
        step = None if step_var.get() == "All" else step_var.get()
        for row in get_alternatives(step=step):
            tree.insert("", tk.END, values=tuple(row[c] for c in columns))

    step_box.bind("<<ComboboxSelected>>", refresh)
    refresh()

    ttk.Label(win, text=DISCLAIMER, wraplength=1050).pack(pady=6)


process_button = ttk.Button(
    root,
    text="Case Study: Dapagliflozin Process Alternatives",
    command=open_process_alternatives
)
process_button.pack(pady=5)


# =========================
# COMPANY EXPERIMENTAL DATA ANALYSIS
# =========================

def open_experimental_analysis():

    from tkinter import filedialog
    from core.experimental_data import (
        load_experiments, rank_routes, best_of_all
    )

    path = filedialog.askopenfilename(
        title="Select experimental data (CSV or Excel)",
        filetypes=[("Data files", "*.csv *.xlsx *.xls"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        df = load_experiments(path)
        ranked = rank_routes(df)
        best = best_of_all(df)
    except Exception as e:
        messagebox.showerror("Data Error", str(e))
        return

    win = tk.Toplevel(root)
    win.title("Route Ranking - Company Experimental Data")
    win.geometry("1150x600")

    for warning in df.attrs.get("warnings", []):
        ttk.Label(win, text=warning, foreground="#b00020").pack(anchor="w", padx=10)

    cols = ("company", "route_id", "overall_yield_pct", "cost_usd_per_kg",
            "p_exact_product", "safety_score", "score")
    heads = ("Company", "Route", "Overall yield %", "Cost USD/kg",
             "P(exact product)", "Safety", "Score")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=10)
    for c, h in zip(cols, heads):
        tree.heading(c, text=h)
        tree.column(c, width=150, anchor="w")
    tree.pack(fill="x", padx=10, pady=8)

    for _, r in ranked.iterrows():
        values = []
        for c in cols:
            v = r[c]
            values.append(f"{v:.3f}" if isinstance(v, float) else v)
        tree.insert("", tk.END, values=values)

    ttk.Label(
        win,
        text="Best of all companies (projection - this combination has not been run):",
        font=("Arial", 11, "bold")
    ).pack(anchor="w", padx=10, pady=(10, 2))

    box = tk.Text(win, height=14, width=140)
    box.pack(padx=10, pady=4)
    for _, s in best["steps"].iterrows():
        box.insert(
            tk.END,
            f"Step {int(s['step_no'])}: {s['step_name']}  <-  "
            f"{s['company']} ({s['reagents']}, {s['solvent']}, {s['temp_c']} C)  "
            f"yield {s['yield_pct']}%\n"
        )
    p = best["projected_p_exact_product"]
    box.insert(
        tk.END,
        f"\nProjected overall yield: {best['projected_overall_yield_pct']}%   "
        f"Projected P(exact product): "
        f"{'n/a (missing replicate data)' if p != p else f'{p:.2f}'}\n"
    )
    for note in best["notes"]:
        box.insert(tk.END, "NOTE: " + note + "\n")


experimental_button = ttk.Button(
    root,
    text="Analyze Company Experimental Data",
    command=open_experimental_analysis
)
experimental_button.pack(pady=5)


# =========================
# 3D STRUCTURE + EXACT-PRODUCT CHECK
# =========================

def open_3d_structure():

    import webbrowser
    from tkinter import filedialog

    smiles = api_entry.get().strip()

    try:
        from core import molecule3d
    except ImportError:
        messagebox.showerror(
            "RDKit missing",
            "Install RDKit first:  pip install rdkit matplotlib"
        )
        return

    if not smiles:
        smiles = molecule3d.DAPAGLIFLOZIN_SMILES

    from tkinter import simpledialog
    reference = simpledialog.askstring(
        "Target drug",
        "Reference SMILES of the target drug (with stereochemistry).\n"
        "Leave as is to check against dapagliflozin:",
        initialvalue=molecule3d.DAPAGLIFLOZIN_SMILES,
        parent=root
    )
    if not reference:
        return

    try:
        check = molecule3d.verify_product(smiles, reference_smiles=reference)
        folder = filedialog.askdirectory(title="Choose folder to save 3D files")
        if not folder:
            return
        html_target = os.path.join(folder, "agnikristal_3d_viewer.html")
        try:
            html_path = molecule3d.export_anomer_comparison_html(html_target, smiles)
        except ValueError:
            # not a C-aryl glycoside: single structure, no alpha/beta partner
            html_path = molecule3d.export_3d_html(html_target, smiles, label="Structure")
        png_path = molecule3d.export_3d_png(
            os.path.join(folder, "agnikristal_3d_structure.png"), smiles
        )
    except Exception as e:
        messagebox.showerror("3D Error", str(e))
        return

    messagebox.showinfo(
        "Exact product check",
        f"Verdict: {check['verdict']}\n"
        f"Formula: {check['formula']} (matches: {check['formula_matches']})\n"
        f"MW: {check['molecular_weight']}\n\n"
        f"Saved:\n{html_path}\n{png_path}"
    )
    webbrowser.open("file://" + os.path.abspath(html_path))


structure_button = ttk.Button(
    root,
    text="3D Structure + Exact-Product Check",
    command=open_3d_structure
)
structure_button.pack(pady=5)


# =========================
# ALTERNATIVE REAGENTS / SOLVENTS (ANY DRUG)
# =========================

def open_substitutions():

    from core.substitutions import lookup_table

    win = tk.Toplevel(root)
    win.title("Alternative Reagents and Solvents (any drug)")
    win.geometry("1100x520")

    ttk.Label(
        win,
        text="Reagents / solvents / steps (e.g. n-BuLi, DCM, LiAlH4, DMF, column chromatography):"
    ).pack(anchor="w", padx=10, pady=(10, 2))

    entry = ttk.Entry(win, width=100)
    entry.pack(padx=10, pady=4)

    cols = ("Found", "Alternative", "How it helps", "Cost vs original", "Maturity", "Re-check")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=16)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=170, anchor="w")
    tree.pack(fill="both", expand=True, padx=10, pady=8)

    def search():
        tree.delete(*tree.get_children())
        table = lookup_table(entry.get())
        if table.empty:
            messagebox.showinfo("No match", "Nothing in the knowledge base matches that text yet.")
            return
        for _, r in table.iterrows():
            tree.insert("", tk.END, values=tuple(r[c] for c in cols))

    ttk.Button(win, text="Find alternatives", command=search).pack(pady=4)
    entry.bind("<Return>", lambda e: search())
    ttk.Label(
        win,
        text="Literature-level guidance; confirm each swap experimentally for your drug."
    ).pack(pady=4)


substitution_button = ttk.Button(
    root,
    text="Alternative Reagents / Solvents (any drug)",
    command=open_substitutions
)
substitution_button.pack(pady=5)


root.mainloop()