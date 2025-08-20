import smtplib
import ssl
import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class BulkMailerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Massen-Mailer (Gmail SMTP)")
        self.root.geometry("650x550")

        # Gmail Login
        tk.Label(root, text="Ihre Gmail-Adresse:").pack()
        self.email_entry = tk.Entry(root, width=50)
        self.email_entry.pack()

        tk.Label(root, text="App-Passwort:").pack()
        self.password_entry = tk.Entry(root, show="*", width=50)
        self.password_entry.pack()

        # CSV
        self.csv_file = None
        tk.Button(root, text="CSV-Datei mit E-Mails hochladen", command=self.load_csv).pack(pady=5)
        self.csv_label = tk.Label(root, text="Keine CSV geladen")
        self.csv_label.pack()

        # PDF
        self.pdf_file = None
        tk.Button(root, text="PDF hochladen (optional)", command=self.load_pdf).pack(pady=5)
        self.pdf_label = tk.Label(root, text="Kein PDF geladen")
        self.pdf_label.pack()

        # Betreff & Nachricht
        tk.Label(root, text="E-Mail Betreff:").pack()
        self.subject_entry = tk.Entry(root, width=60)
        self.subject_entry.pack()

        tk.Label(root, text="E-Mail Nachricht (nutzen Sie {name} für Personalisierung):").pack()
        self.message_text = tk.Text(root, height=6, width=70)
        self.message_text.pack()

        # Logging Option
        self.log_var = tk.BooleanVar()
        tk.Checkbutton(root, text="Protokoll speichern (send_log.csv)", variable=self.log_var).pack()

        # Fortschrittsbalken
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        # Senden-Button
        tk.Button(root, text="E-Mails senden", command=self.send_emails).pack(pady=10)

    def load_csv(self):
        self.csv_file = filedialog.askopenfilename(filetypes=[("CSV-Dateien", "*.csv")])
        if self.csv_file:
            self.csv_label.config(text=f"Geladen: {self.csv_file.split('/')[-1]}")
            print(f"[INFO] CSV geladen: {self.csv_file}")

    def load_pdf(self):
        self.pdf_file = filedialog.askopenfilename(filetypes=[("PDF-Dateien", "*.pdf")])
        if self.pdf_file:
            self.pdf_label.config(text=f"Geladen: {self.pdf_file.split('/')[-1]}")
            print(f"[INFO] PDF geladen: {self.pdf_file}")

    def send_emails(self):
        if not self.csv_file or not self.email_entry.get() or not self.password_entry.get():
            messagebox.showerror("Fehler", "Bitte Gmail-Adresse, Passwort und CSV-Datei angeben.")
            return

        sender_email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        subject = self.subject_entry.get().strip()
        body_template = self.message_text.get("1.0", tk.END).strip()

        # E-Mails laden (flexibel)
        recipients = []
        with open(self.csv_file, newline="") as f:
            try:
                reader = csv.DictReader(f)
                rows = list(reader)
                if reader.fieldnames and "email" in [c.lower() for c in reader.fieldnames]:
                    for row in rows:
                        email = row.get("email") or row.get("Email") or row.get("EMAIL")
                        name = row.get("name") or row.get("Name") or row.get("NAME") or "Freund"
                        if email:
                            recipients.append((email.strip(), name.strip()))
                else:
                    f.seek(0)
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 1:
                            email = row[0].strip()
                            name = row[1].strip() if len(row) > 1 else "Freund"
                            if email:
                                recipients.append((email, name))
            except Exception as e:
                print(f"[FEHLER] CSV-Parsing fehlgeschlagen: {e}")

        if not recipients:
            messagebox.showerror("Fehler", "Keine gültigen E-Mail-Adressen in der CSV gefunden.")
            return

        print(f"[INFO] Beginne mit dem Senden von {len(recipients)} E-Mails...")
        self.progress["maximum"] = len(recipients)
        self.progress["value"] = 0
        self.root.update_idletasks()

        results = []
        sent_count = 0

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, password)
                print("[INFO] Erfolgreich bei Gmail SMTP eingeloggt.")

                for i, (receiver_email, name) in enumerate(recipients):
                    msg = MIMEMultipart()
                    msg["From"] = sender_email
                    msg["To"] = receiver_email
                    msg["Subject"] = subject

                    body = body_template.replace("{name}", name if name else "Freund")
                    msg.attach(MIMEText(body, "plain"))

                    if self.pdf_file:
                        with open(self.pdf_file, "rb") as f:
                            attach = MIMEApplication(f.read(), _subtype="pdf")
                            attach.add_header('Content-Disposition','attachment',filename=self.pdf_file.split("/")[-1])
                            msg.attach(attach)

                    try:
                        server.sendmail(sender_email, receiver_email, msg.as_string())
                        print(f"[ERFOLG] Gesendet an {receiver_email}")
                        results.append((receiver_email, "ERFOLG"))
                        sent_count += 1
                    except Exception as e:
                        print(f"[FEHLER] {receiver_email}: {e}")
                        results.append((receiver_email, f"FEHLER: {e}"))

                    self.progress["value"] = i + 1
                    self.root.update_idletasks()

            if self.log_var.get():
                with open("send_log.csv", "w", newline="") as log_file:
                    writer = csv.writer(log_file)
                    writer.writerow(["E-Mail", "Status"])
                    writer.writerows(results)
                print("[INFO] Protokoll gespeichert: send_log.csv")

            if sent_count > 0:
                messagebox.showinfo("Fertig", f"E-Mails gesendet: {sent_count}/{len(recipients)}")
            else:
                messagebox.showerror("Fehler", "Keine E-Mails wurden gesendet. Siehe Protokoll.")

        except Exception as e:
            print(f"[FEHLER] SMTP-Verbindung fehlgeschlagen: {e}")
            messagebox.showerror("SMTP Fehler", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = BulkMailerApp(root)
    root.mainloop()
