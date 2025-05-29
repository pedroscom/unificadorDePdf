import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import sys
import threading
from queue import Queue, Empty
import fitz  # PyMuPDF

PDF_LIB = "PyMuPDF (fitz)"

class AdvancedPDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Unificador de PDFs Avançado V8 - Preserva Chancelas ({PDF_LIB})")
        # ... (restante do código de inicialização permanece igual) ...

    def _perform_advanced_merge(self, output_path, files):
        """Executa a unificação avançada dos PDFs preservando chancelas."""
        try:
            # Criar um novo documento PDF
            merged_pdf = fitz.open()
            
            for i, pdf_path in enumerate(files, 1):
                try:
                    self.queue.put(("progress", f"🔒 Processando arquivo {i}/{len(files)}: {os.path.basename(pdf_path)}"))
                    
                    # Abrir cada arquivo PDF
                    src_pdf = fitz.open(pdf_path)
                    
                    # Inserir todas as páginas no documento final
                    merged_pdf.insert_pdf(src_pdf)
                    
                    src_pdf.close()
                    
                except Exception as e:
                    raise Exception(f"Erro ao processar '{os.path.basename(pdf_path)}': {str(e)}")
            
            self.queue.put(("progress", "🔒 Finalizando unificação e preservando elementos especiais..."))
            
            # Salvar o PDF unificado
            merged_pdf.save(output_path, deflate=True, garbage=3)
            merged_pdf.close()
            
            # Verificar se o arquivo foi criado
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                success_msg = (f"✅ PDFs unificados com sucesso preservando chancelas!\n\n"
                             f"📁 Arquivo salvo em:\n{output_path}")
                self.queue.put(("success", success_msg, "✅ Unificação concluída!"))
            else:
                raise Exception("Arquivo de saída não foi criado corretamente")
                
        except Exception as e:
            error_msg = f"❌ Falha ao unificar PDFs:\n\n{str(e)}"
            self.queue.put(("error", error_msg, "❌ Erro durante a unificação."))

    # ... (restante do código permanece igual) ...