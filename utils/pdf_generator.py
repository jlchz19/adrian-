from fpdf import FPDF
import os
from datetime import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Resumen Financiero por Bolsillos', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(user, sources, transactions):
    pdf = PDF()
    pdf.add_page()
    
    # Info del usuario
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Usuario: {user.username}', 0, 1)
    pdf.cell(0, 10, f'Fecha de generacion: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
    pdf.ln(5)
    
    # Resumen de Bolsillos
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Estado Actual de Bolsillos (Fondos)', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    total_global = 0
    for s in sources:
        pdf.cell(0, 8, f'- {s.name} ({s.currency}): ${s.remaining_amount:.2f}', 0, 1)
        total_global += s.remaining_amount
        
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, f'Total Global Disponible: ${total_global:.2f}', 0, 1)
    pdf.ln(10)
    
    # Tabla de transacciones
    pdf.set_font('Arial', 'B', 9)
    # Encabezados
    pdf.cell(22, 10, 'Fecha', 1)
    pdf.cell(15, 10, 'Hora', 1)
    pdf.cell(30, 10, 'Tipo', 1)
    pdf.cell(40, 10, 'Bolsillo Afectado', 1)
    pdf.cell(60, 10, 'Descripcion', 1)
    pdf.cell(25, 10, 'Monto', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for t in transactions:
        pdf.cell(22, 10, str(t.date), 1)
        pdf.cell(15, 10, str(t.time.strftime('%H:%M')), 1)
        
        tipo = t.type.replace('_', ' ').capitalize()
        pdf.cell(30, 10, tipo, 1)
        
        bolsillo = f"{t.source.name[:15]}..." if len(t.source.name) > 15 else t.source.name
        pdf.cell(40, 10, bolsillo, 1)
        
        desc = t.description[:35] + '...' if len(t.description) > 35 else t.description
        pdf.cell(60, 10, desc, 1)
        
        signo = '+' if t.type in ['ingreso_nuevo', 'ingreso_adicional'] else '-'
        pdf.cell(25, 10, f'{signo}{t.amount:.2f}', 1)
        pdf.ln()
        
    os.makedirs('tmp', exist_ok=True)
    pdf_path = f'tmp/report_{user.id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.pdf'
    pdf.output(pdf_path)
    return pdf_path
