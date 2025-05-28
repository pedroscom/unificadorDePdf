import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PyPDF2 import PdfMerger
import subprocess
import sys
import threading
from queue import Queue, Empty

class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Unificador de PDFs Avançado V5 - Com Drag & Drop")
        self.root.geometry("800x700")
        self.root.resizable(False, False)
        
        self.selected_files = []
        self.output_file = ""
        self.queue = Queue()  # Queue for thread communication
        self.is_merging = False  # Flag to track merging state
        
        # Variáveis para drag & drop
        self.drag_start_index = None
        self.drag_highlight_index = None
        
        self.create_widgets()
        self.setup_drag_drop()
        self.update_file_list()
        self.update_buttons_state()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        select_frame = ttk.Frame(main_frame)
        select_frame.pack(pady=5)
        
        self.btn_select = ttk.Button(
            select_frame,
            text="Adicionar PDFs à Lista",
            command=self.select_files
        )
        self.btn_select.pack(side=tk.LEFT, padx=10)

        self.btn_reset = ttk.Button(
            select_frame,
            text="Limpar Lista",
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

        self.count_label = ttk.Label(main_frame, text="PDFs selecionados: 0")
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
            height=15,
            selectmode=tk.SINGLE,
            font=("Arial", 10)
        )
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        action_btn_frame = ttk.Frame(main_frame)
        action_btn_frame.pack(pady=10)
        
        self.btn_merge = ttk.Button(
            action_btn_frame,
            text="Unificar PDFs",
            state=tk.DISABLED,
            command=self.merge_files_threaded
        )
        self.btn_merge.pack(side=tk.LEFT, padx=10)
        
        self.btn_open_folder = ttk.Button(
            action_btn_frame,
            text="Abrir Pasta de Destino",
            state=tk.DISABLED,
            command=self.open_output_folder
        )
        self.btn_open_folder.pack(side=tk.LEFT, padx=10)

        # Progress bar - inicialmente oculta
        self.progress = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
            length=400
        )
        
        self.status_label = ttk.Label(main_frame, text="Selecione pelo menos 2 arquivos PDF para unificar.")
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
            # Remove highlight anterior
            if self.drag_highlight_index is not None:
                self.listbox.itemconfig(self.drag_highlight_index, {'bg': 'white'})
            
            # Adiciona highlight atual
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
        
        # Remove qualquer highlight
        if self.drag_highlight_index is not None:
            self.listbox.itemconfig(self.drag_highlight_index, {'bg': 'white'})
        
        # Reordena apenas se necessário e válido
        if (0 <= drop_index < len(self.selected_files) and 
            drop_index != self.drag_start_index):
            
            # Move o item na lista
            moved_file = self.selected_files.pop(self.drag_start_index)
            self.selected_files.insert(drop_index, moved_file)
            
            # Atualiza a interface
            self.update_file_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(drop_index)
            
            self.status_label.config(
                text=f"Item movido da posição {self.drag_start_index + 1} para {drop_index + 1}.",
                foreground="green"
            )
            
            # Limpa o arquivo de saída quando a ordem muda
            self.output_file = ""
            self.update_buttons_state()
        
        # Reset das variáveis de drag
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
            # Troca os itens
            self.selected_files[index], self.selected_files[index - 1] = \
                self.selected_files[index - 1], self.selected_files[index]
            
            # Atualiza a interface
            self.update_file_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index - 1)
            
            self.status_label.config(
                text=f"Item movido para cima (posição {index} → {index}).",
                foreground="green"
            )
            
            # Limpa o arquivo de saída quando a ordem muda
            self.output_file = ""
            self.update_buttons_state()
    
    def move_down(self):
        """Move o item selecionado para baixo."""
        selection = self.listbox.curselection()
        if not selection or self.is_merging:
            return
        
        index = selection[0]
        if index < len(self.selected_files) - 1:
            # Troca os itens
            self.selected_files[index], self.selected_files[index + 1] = \
                self.selected_files[index + 1], self.selected_files[index]
            
            # Atualiza a interface
            self.update_file_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index + 1)
            
            self.status_label.config(
                text=f"Item movido para baixo (posição {index + 1} → {index + 2}).",
                foreground="green"
            )
            
            # Limpa o arquivo de saída quando a ordem muda
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
            self.listbox.insert(tk.END, f"{i:2d}. {filename}")
        self.count_label.config(text=f"PDFs selecionados: {len(self.selected_files)}")
        self.update_move_buttons()
    
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
            # Habilita abrir pasta apenas se o arquivo foi criado com sucesso
            can_open_folder = bool(self.output_file and os.path.exists(self.output_file))
            self.btn_open_folder["state"] = tk.NORMAL if can_open_folder else tk.DISABLED
            
            # Atualiza botões de movimento
            self.update_move_buttons()

    def merge_files_threaded(self):
        if len(self.selected_files) < 2:
            messagebox.showwarning("Aviso", "Selecione pelo menos dois arquivos PDF para unificar.")
            return

        # Solicita o nome do arquivo de saída
        _output_file = filedialog.asksaveasfilename(
            title="Salvar PDF Unificado Como",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="pdfs_unificados.pdf"
        )
        
        if not _output_file:
            self.status_label.config(text="Operação cancelada pelo usuário.", foreground="orange")
            return
            
        self.output_file = _output_file
        files_to_merge = self.selected_files.copy()

        # Atualiza interface para estado de processamento
        self.is_merging = True
        self.status_label.config(text="Unificando PDFs na ordem especificada, aguarde...", foreground="blue")
        self.progress.pack(pady=10)
        self.progress.start(10)  # Velocidade da animação
        self.update_buttons_state()
        self.root.update_idletasks()
        
        # Inicia o processo de unificação em thread separada
        thread = threading.Thread(
            target=self._perform_merge, 
            args=(self.output_file, files_to_merge), 
            daemon=True
        )
        thread.start()
        
        # Inicia verificação da queue
        self._check_queue()

    def _perform_merge(self, output_path, files):
        """Executa a unificação dos PDFs em thread separada."""
        try:
            merger = PdfMerger()
            
            for i, pdf in enumerate(files, 1):
                try:
                    merger.append(pdf)
                    # Simula progresso (opcional - para feedback visual)
                    progress_msg = f"Processando arquivo {i} de {len(files)}: {os.path.basename(pdf)}"
                    self.queue.put(("progress", progress_msg))
                except Exception as e:
                    raise Exception(f"Erro ao processar '{os.path.basename(pdf)}': {str(e)}")
            
            merger.write(output_path)
            merger.close()
            
            # Sucesso
            success_msg = f"PDFs unificados com sucesso na ordem especificada!\n\nArquivo salvo em:\n{output_path}"
            self.queue.put(("success", success_msg, "Unificação concluída com sucesso!"))
            
        except Exception as e:
            # Erro
            error_msg = f"Falha ao unificar PDFs:\n\n{str(e)}"
            self.queue.put(("error", error_msg, "Erro durante a unificação."))

    def _check_queue(self):
        """Verifica a queue por mensagens da thread worker e atualiza a UI."""
        try:
            result = self.queue.get_nowait()
            result_type = result[0]
            
            if result_type == "progress":
                # Atualiza status de progresso
                progress_text = result[1]
                self.status_label.config(text=progress_text, foreground="blue")
                self.root.after(100, self._check_queue)
                
            elif result_type in ["success", "error"]:
                # Finaliza o processo
                self._finish_merge_process(result)
                
        except Empty:
            # Queue vazia - continua verificando
            if self.is_merging:
                self.root.after(100, self._check_queue)
        except Exception as e:
            print(f"Erro ao verificar queue: {e}")
            self._finish_merge_process(("error", f"Erro interno: {str(e)}", "Erro inesperado."))

    def _finish_merge_process(self, result):
        """Finaliza o processo de unificação e atualiza a interface."""
        result_type, msg_box_text, status_text = result
        
        # Para a animação e oculta a barra de progresso
        self.progress.stop()
        self.progress.pack_forget()
        self.is_merging = False
        
        # Exibe mensagem apropriada
        if result_type == "success":
            messagebox.showinfo("Sucesso", msg_box_text)
            self.status_label.config(text=status_text, foreground="green")
        else:  # error
            messagebox.showerror("Erro", msg_box_text)
            self.status_label.config(text=status_text, foreground="red")
            self.output_file = ""  # Limpa o caminho de saída em caso de erro

        # Atualiza estado dos botões
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
    app = PDFMergerApp(root)
    root.mainloop()