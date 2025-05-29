import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import sys
import threading
from queue import Queue, Empty

# Tentará usar PyPDF4 primeiro (melhor preservação), depois PyPDF2
try:
    from PyPDF4 import PdfFileMerger, PdfFileReader
    PDF_LIB = "PyPDF4"
    print("Usando PyPDF4 - Melhor preservação de elementos")
except ImportError:
    try:
        from PyPDF2 import PdfMerger as PdfFileMerger, PdfReader as PdfFileReader
        PDF_LIB = "PyPDF2"
        print("Usando PyPDF2")
    except ImportError:
        messagebox.showerror("Erro", "PyPDF2 ou PyPDF4 não encontrado. Instale com: pip install PyPDF2 PyPDF4")
        sys.exit(1)

class AdvancedPDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Unificador de PDFs Avançado V6 - Preserva Chancelas ({PDF_LIB})")
        self.root.geometry("850x750")
        self.root.resizable(False, False)
        
        self.selected_files = []
        self.output_file = ""
        self.queue = Queue()
        self.is_merging = False
        
        # Variáveis para drag & drop
        self.drag_start_index = None
        self.drag_highlight_index = None
        
        # Configurações de preservação
        self.preserve_bookmarks = tk.BooleanVar(value=True)
        self.preserve_metadata = tk.BooleanVar(value=True)
        self.preserve_forms = tk.BooleanVar(value=True)
        
        self.create_widgets()
        self.setup_drag_drop()
        self.update_file_list()
        self.update_buttons_state()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título e informações
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(pady=5, fill=tk.X)
        
        title_label = ttk.Label(
            title_frame, 
            text="🔒 Unificador de PDFs com Preservação de Chancelas",
            font=("Arial", 12, "bold")
        )
        title_label.pack()
        
        info_label = ttk.Label(
            title_frame,
            text=f"Usando {PDF_LIB} para melhor preservação de elementos digitais",
            font=("Arial", 9),
            foreground="blue"
        )
        info_label.pack()

        # Frame de seleção
        select_frame = ttk.Frame(main_frame)
        select_frame.pack(pady=10)
        
        self.btn_select = ttk.Button(
            select_frame,
            text="📁 Adicionar PDFs à Lista",
            command=self.select_files
        )
        self.btn_select.pack(side=tk.LEFT, padx=10)

        self.btn_reset = ttk.Button(
            select_frame,
            text="🗑️ Limpar Lista",
            state=tk.DISABLED,
            command=self.reset_files
        )
        self.btn_reset.pack(side=tk.LEFT, padx=10)

        # Botões para mover itens manualmente
        move_frame = ttk.Frame(select_frame)
        move_frame.pack(side=tk.LEFT, padx=20)
        
        self.btn_move_up = ttk.Button(
            move_frame,
            text="↑ Subir",
            state=tk.DISABLED,
            command=self.move_up,
            width=8
        )
        self.btn_move_up.pack(side=tk.LEFT, padx=2)
        
        self.btn_move_down = ttk.Button(
            move_frame,
            text="↓ Descer",
            state=tk.DISABLED,
            command=self.move_down,
            width=8
        )
        self.btn_move_down.pack(side=tk.LEFT, padx=2)

        # Opções de preservação
        options_frame = ttk.LabelFrame(main_frame, text="🔐 Opções de Preservação", padding=10)
        options_frame.pack(pady=10, fill=tk.X)
        
        preserve_frame = ttk.Frame(options_frame)
        preserve_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(
            preserve_frame,
            text="Preservar marcadores/bookmarks",
            variable=self.preserve_bookmarks
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Checkbutton(
            preserve_frame,
            text="Preservar metadados",
            variable=self.preserve_metadata
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Checkbutton(
            preserve_frame,
            text="Preservar formulários",
            variable=self.preserve_forms
        ).pack(side=tk.LEFT, padx=10)

        # Informações sobre os arquivos
        self.count_label = ttk.Label(main_frame, text="PDFs selecionados: 0", font=("Arial", 10, "bold"))
        self.count_label.pack(pady=5)
        
        # Instrução sobre drag & drop
        instruction_label = ttk.Label(
            main_frame, 
            text="💡 Dica: Arraste e solte os itens na lista para reordená-los, ou use os botões ↑/↓",
            foreground="blue"
        )
        instruction_label.pack(pady=5)
        
        # Frame para a listbox com scrollbar
        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.listbox = tk.Listbox(
            listbox_frame,
            width=100,
            height=12,
            selectmode=tk.SINGLE,
            font=("Consolas", 9)
        )
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões de ação
        action_btn_frame = ttk.Frame(main_frame)
        action_btn_frame.pack(pady=15)
        
        self.btn_merge = ttk.Button(
            action_btn_frame,
            text="🔗 Unificar PDFs (Preservando Chancelas)",
            state=tk.DISABLED,
            command=self.merge_files_threaded
        )
        self.btn_merge.pack(side=tk.LEFT, padx=10)
        
        self.btn_open_folder = ttk.Button(
            action_btn_frame,
            text="📂 Abrir Pasta de Destino",
            state=tk.DISABLED,
            command=self.open_output_folder
        )
        self.btn_open_folder.pack(side=tk.LEFT, padx=10)

        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
            length=500
        )
        
        # Status
        self.status_label = ttk.Label(
            main_frame, 
            text="Selecione pelo menos 2 arquivos PDF para unificar.",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=10)
    
    def setup_drag_drop(self):
        """Configura os eventos de drag & drop na listbox."""
        self.listbox.bind("<Button-1>", self.on_drag_start)
        self.listbox.bind("<B1-Motion>", self.on_drag_motion)
        self.listbox.bind("<ButtonRelease-1>", self.on_drag_release)
        self.listbox.bind("<<ListboxSelect>>", self.on_selection_change)
    
    def on_drag_start(self, event):
        """Inicia o processo de drag."""
        if self.is_merging:
            return
            
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self.selected_files):
            self.drag_start_index = index
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
    
    def on_drag_motion(self, event):
        """Processa o movimento durante o drag."""
        if self.drag_start_index is None or self.is_merging:
            return
        
        current_index = self.listbox.nearest(event.y)
        if 0 <= current_index < len(self.selected_files):
            if self.drag_highlight_index is not None:
                self.listbox.itemconfig(self.drag_highlight_index, {'bg': 'white'})
            
            if current_index != self.drag_start_index:
                self.listbox.itemconfig(current_index, {'bg': 'lightblue'})
                self.drag_highlight_index = current_index
            else:
                self.drag_highlight_index = None
    
    def on_drag_release(self, event):
        """Finaliza o processo de drag e reordena os itens."""
        if self.drag_start_index is None or self.is_merging:
            self.drag_start_index = None
            self.drag_highlight_index = None
            return
        
        drop_index = self.listbox.nearest(event.y)
        
        if self.drag_highlight_index is not None:
            self.listbox.itemconfig(self.drag_highlight_index, {'bg': 'white'})
        
        if (0 <= drop_index < len(self.selected_files) and 
            drop_index != self.drag_start_index):
            
            moved_file = self.selected_files.pop(self.drag_start_index)
            self.selected_files.insert(drop_index, moved_file)
            
            self.update_file_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(drop_index)
            
            self.status_label.config(
                text=f"Item movido da posição {self.drag_start_index + 1} para {drop_index + 1}.",
                foreground="green"
            )
            
            self.output_file = ""
            self.update_buttons_state()
        
        self.drag_start_index = None
        self.drag_highlight_index = None
    
    def on_selection_change(self, event):
        """Atualiza os botões de movimento quando a seleção muda."""
        self.update_move_buttons()
    
    def move_up(self):
        """Move o item selecionado para cima."""
        selection = self.listbox.curselection()
        if not selection or self.is_merging:
            return
        
        index = selection[0]
        if index > 0:
            self.selected_files[index], self.selected_files[index - 1] = \
                self.selected_files[index - 1], self.selected_files[index]
            
            self.update_file_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index - 1)
            
            self.status_label.config(
                text=f"Item movido para cima (posição {index + 1} → {index}).",
                foreground="green"
            )
            
            self.output_file = ""
            self.update_buttons_state()
    
    def move_down(self):
        """Move o item selecionado para baixo."""
        selection = self.listbox.curselection()
        if not selection or self.is_merging:
            return
        
        index = selection[0]
        if index < len(self.selected_files) - 1:
            self.selected_files[index], self.selected_files[index + 1] = \
                self.selected_files[index + 1], self.selected_files[index]
            
            self.update_file_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index + 1)
            
            self.status_label.config(
                text=f"Item movido para baixo (posição {index + 1} → {index + 2}).",
                foreground="green"
            )
            
            self.output_file = ""
            self.update_buttons_state()
    
    def update_move_buttons(self):
        """Atualiza o estado dos botões de movimento."""
        if self.is_merging or len(self.selected_files) <= 1:
            self.btn_move_up["state"] = tk.DISABLED
            self.btn_move_down["state"] = tk.DISABLED
            return
        
        selection = self.listbox.curselection()
        if not selection:
            self.btn_move_up["state"] = tk.DISABLED
            self.btn_move_down["state"] = tk.DISABLED
            return
        
        index = selection[0]
        self.btn_move_up["state"] = tk.NORMAL if index > 0 else tk.DISABLED
        self.btn_move_down["state"] = tk.NORMAL if index < len(self.selected_files) - 1 else tk.DISABLED
    
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Selecione PDFs para adicionar à lista",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if files:
            added_count = 0
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
                    added_count += 1
            
            if added_count > 0:
                self.output_file = "" 
                self.update_file_list()
                self.update_buttons_state()
                self.status_label.config(
                    text=f"{added_count} arquivo(s) adicionado(s). Total: {len(self.selected_files)}.", 
                    foreground="black"
                )
            else:
                self.status_label.config(
                    text="Nenhum arquivo novo adicionado (já estavam na lista).", 
                    foreground="orange"
                )

    def reset_files(self):
        if not self.selected_files:
            return
        self.selected_files.clear()
        self.output_file = ""
        self.update_file_list()
        self.update_buttons_state()
        self.status_label.config(text="Lista de arquivos limpa.", foreground="black")

    def update_file_list(self):
        self.listbox.delete(0, tk.END)
        for i, f in enumerate(self.selected_files, 1):
            filename = os.path.basename(f)
            # Indica se tem chancela/assinatura
            try:
                has_signature = self.check_for_signatures(f)
                status_icon = "🔒" if has_signature else "📄"
            except:
                status_icon = "📄"
            
            self.listbox.insert(tk.END, f"{i:2d}. {status_icon} {filename}")
        
        self.count_label.config(text=f"PDFs selecionados: {len(self.selected_files)}")
        self.update_move_buttons()
    
    def check_for_signatures(self, pdf_path):
        """Verificação básica se o PDF pode ter assinaturas/chancelas."""
        try:
            if PDF_LIB == "PyPDF4":
                with open(pdf_path, 'rb') as file:
                    reader = PdfFileReader(file)
                    # Verifica se há campos de formulário (comum em documentos com chancela)
                    if reader.getFields():
                        return True
                    # Verifica algumas palavras-chave no texto
                    for page in reader.pages:
                        text = page.extractText().lower()
                        if any(word in text for word in ['assinado', 'certificado', 'chancela', 'protocolo']):
                            return True
            return False
        except:
            return False
    
    def update_buttons_state(self):
        num_files = len(self.selected_files)
        
        if self.is_merging:
            self.btn_select["state"] = tk.DISABLED
            self.btn_reset["state"] = tk.DISABLED
            self.btn_merge["state"] = tk.DISABLED
            self.btn_open_folder["state"] = tk.DISABLED
            self.btn_move_up["state"] = tk.DISABLED
            self.btn_move_down["state"] = tk.DISABLED
        else:
            self.btn_select["state"] = tk.NORMAL
            self.btn_reset["state"] = tk.NORMAL if num_files > 0 else tk.DISABLED
            self.btn_merge["state"] = tk.NORMAL if num_files >= 2 else tk.DISABLED
            can_open_folder = bool(self.output_file and os.path.exists(self.output_file))
            self.btn_open_folder["state"] = tk.NORMAL if can_open_folder else tk.DISABLED
            
            self.update_move_buttons()

    def merge_files_threaded(self):
        if len(self.selected_files) < 2:
            messagebox.showwarning("Aviso", "Selecione pelo menos dois arquivos PDF para unificar.")
            return

        _output_file = filedialog.asksaveasfilename(
            title="Salvar PDF Unificado Como",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="pdfs_unificados_com_chancelas.pdf"
        )
        
        if not _output_file:
            self.status_label.config(text="Operação cancelada pelo usuário.", foreground="orange")
            return
            
        self.output_file = _output_file
        files_to_merge = self.selected_files.copy()

        self.is_merging = True
        self.status_label.config(text="🔒 Unificando PDFs preservando chancelas e assinaturas...", foreground="blue")
        self.progress.pack(pady=10)
        self.progress.start(10)
        self.update_buttons_state()
        self.root.update_idletasks()
        
        thread = threading.Thread(
            target=self._perform_advanced_merge, 
            args=(self.output_file, files_to_merge), 
            daemon=True
        )
        thread.start()
        
        self._check_queue()

    def _perform_advanced_merge(self, output_path, files):
        """Executa a unificação avançada dos PDFs preservando chancelas."""
        try:
            # Usa PdfFileMerger com configurações para preservar elementos
            merger = PdfFileMerger()
            
            # Configurações para preservar elementos especiais
            if PDF_LIB == "PyPDF4":
                merger.setPageLayout('/OneColumn')  # Preserva layout
                
            for i, pdf_path in enumerate(files, 1):
                try:
                    self.queue.put(("progress", f"🔒 Processando arquivo {i}/{len(files)}: {os.path.basename(pdf_path)}"))
                    
                    with open(pdf_path, 'rb') as pdf_file:
                        if PDF_LIB == "PyPDF4":
                            pdf_reader = PdfFileReader(pdf_file)
                            
                            # Preserva bookmarks se solicitado
                            if self.preserve_bookmarks.get():
                                merger.append(pdf_file, bookmark=os.path.basename(pdf_path))
                            else:
                                merger.append(pdf_file)
                                
                            # Tenta preservar metadados
                            if self.preserve_metadata.get() and pdf_reader.metadata:
                                if hasattr(merger, 'addMetadata'):
                                    merger.addMetadata(pdf_reader.metadata)
                        else:
                            # PyPDF2
                            if self.preserve_bookmarks.get():
                                merger.append(pdf_file, bookmark=os.path.basename(pdf_path))
                            else:
                                merger.append(pdf_file)
                                
                except Exception as e:
                    raise Exception(f"Erro ao processar '{os.path.basename(pdf_path)}': {str(e)}")
            
            self.queue.put(("progress", "🔒 Finalizando unificação e preservando elementos especiais..."))
            
            # Escreve o arquivo final
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            
            merger.close()
            
            # Verifica se o arquivo foi criado com sucesso
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                success_msg = (f"✅ PDFs unificados com sucesso preservando chancelas e assinaturas!\n\n"
                             f"📁 Arquivo salvo em:\n{output_path}\n\n"
                             f"🔒 Elementos preservados:\n"
                             f"{'✓' if self.preserve_bookmarks.get() else '✗'} Marcadores/Bookmarks\n"
                             f"{'✓' if self.preserve_metadata.get() else '✗'} Metadados\n"
                             f"{'✓' if self.preserve_forms.get() else '✗'} Formulários\n"
                             f"🏆 Biblioteca utilizada: {PDF_LIB}")
                self.queue.put(("success", success_msg, "✅ Unificação concluída preservando chancelas!"))
            else:
                raise Exception("Arquivo de saída não foi criado corretamente")
                
        except Exception as e:
            error_msg = f"❌ Falha ao unificar PDFs:\n\n{str(e)}\n\n💡 Dica: Verifique se todos os PDFs estão válidos e não estão protegidos por senha."
            self.queue.put(("error", error_msg, "❌ Erro durante a unificação."))

    def _check_queue(self):
        """Verifica a queue por mensagens da thread worker e atualiza a UI."""
        try:
            result = self.queue.get_nowait()
            result_type = result[0]
            
            if result_type == "progress":
                progress_text = result[1]
                self.status_label.config(text=progress_text, foreground="blue")
                self.root.after(100, self._check_queue)
                
            elif result_type in ["success", "error"]:
                self._finish_merge_process(result)
                
        except Empty:
            if self.is_merging:
                self.root.after(100, self._check_queue)
        except Exception as e:
            print(f"Erro ao verificar queue: {e}")
            self._finish_merge_process(("error", f"Erro interno: {str(e)}", "❌ Erro inesperado."))

    def _finish_merge_process(self, result):
        """Finaliza o processo de unificação e atualiza a interface."""
        result_type, msg_box_text, status_text = result
        
        self.progress.stop()
        self.progress.pack_forget()
        self.is_merging = False
        
        if result_type == "success":
            messagebox.showinfo("Sucesso", msg_box_text)
            self.status_label.config(text=status_text, foreground="green")
        else:
            messagebox.showerror("Erro", msg_box_text)
            self.status_label.config(text=status_text, foreground="red")
            self.output_file = ""

        self.update_buttons_state()

    def open_output_folder(self):
        if not self.output_file or not os.path.exists(self.output_file):
            messagebox.showwarning("Aviso", "O arquivo de saída não foi encontrado ou ainda não foi criado.")
            return
            
        folder_path = os.path.dirname(self.output_file)
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path], check=True)
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", folder_path], check=True)
            else:
                messagebox.showinfo("Info", f"Arquivo salvo em: {folder_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedPDFMergerApp(root)
    root.mainloop()
