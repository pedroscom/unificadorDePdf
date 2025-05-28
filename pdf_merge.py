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
        self.root.title("Unificador de PDFs Avançado V4")
        self.root.geometry("800x650")
        self.root.resizable(False, False)
        
        self.selected_files = []
        self.output_file = ""
        self.queue = Queue()  # Queue for thread communication
        self.is_merging = False  # Flag to track merging state
        
        self.create_widgets()
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

        self.count_label = ttk.Label(main_frame, text="PDFs selecionados: 0")
        self.count_label.pack(pady=5)
        
        self.listbox = tk.Listbox(
            main_frame,
            width=100,
            height=15,
            selectmode=tk.SINGLE
        )
        self.listbox.pack(pady=10)
        
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
        for f in self.selected_files:
            self.listbox.insert(tk.END, os.path.basename(f))
        self.count_label.config(text=f"PDFs selecionados: {len(self.selected_files)}")
    
    def update_buttons_state(self):
        num_files = len(self.selected_files)
        
        if self.is_merging:
            self.btn_select["state"] = tk.DISABLED
            self.btn_reset["state"] = tk.DISABLED
            self.btn_merge["state"] = tk.DISABLED
            self.btn_open_folder["state"] = tk.DISABLED
        else:
            self.btn_select["state"] = tk.NORMAL
            self.btn_reset["state"] = tk.NORMAL if num_files > 0 else tk.DISABLED
            self.btn_merge["state"] = tk.NORMAL if num_files >= 2 else tk.DISABLED
            # Habilita abrir pasta apenas se o arquivo foi criado com sucesso
            can_open_folder = bool(self.output_file and os.path.exists(self.output_file))
            self.btn_open_folder["state"] = tk.NORMAL if can_open_folder else tk.DISABLED

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
        self.status_label.config(text="Unificando PDFs, aguarde...", foreground="blue")
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
            success_msg = f"PDFs unificados com sucesso!\n\nArquivo salvo em:\n{output_path}"
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