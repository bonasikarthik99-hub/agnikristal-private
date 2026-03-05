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


root.mainloop()