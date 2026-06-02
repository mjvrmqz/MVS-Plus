from PyPDF2 import PdfReader
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Hide main Tk window
Tk().withdraw()

# Open file picker
pdf_path = askopenfilename(
    title="Select PDF",
    filetypes=[("PDF Files", "*.pdf")]
)

if not pdf_path:
    print("No file selected. Exiting.")
    exit()

reader = PdfReader(pdf_path)
acroform = reader.trailer["/Root"]["/AcroForm"].get_object()

movement_answers = {}
chapter_answers = {}

for field_ref in acroform["/Fields"]:
    field = field_ref.get_object()
    name = field.get("/T")
    value = field.get("/V")
    if value is None:
        continue
    name_str = str(name)
    value_str = str(value)

    if name_str.startswith("Chapter"):
        chapter_answers[name_str] = value_str
    elif not name_str.startswith("SubmitButton"):
        movement_answers[name_str] = value_str

# Print Movements
print("=== MOVEMENTS ===")
for k in sorted(movement_answers, key=lambda x: int(x)):
    print(f"{k}: {movement_answers[k]}")

# Print Chapters
print("\n=== CHAPTERS ===")
for k in sorted(chapter_answers, key=lambda x: int(x.split()[-1])):
    print(f"{k}: {chapter_answers[k]}")