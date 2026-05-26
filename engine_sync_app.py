import os
import sys
import json
import sqlite3
import re
import threading
import locale
import webbrowser
from datetime import datetime
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image
except ImportError:
    pass

from tinytag import TinyTag
import customtkinter as ctk

# ================= CONFIGURAÇÃO DE DOAÇÃO =================
URL_DOACAO = "https://linktr.ee/leh.deejay82"
# ==========================================================

# ================= DICTIONÁRIO INTERNACIONAL (IDIOMAS) =================
STRINGS = {
    "pt": {
        "title": "Engine DJ - Mirror Sync",
        "music_folder": "Pasta de Músicas (PC):",
        "db_file": "Banco de Dados (m.db):",
        "browse": "Procurar",
        "sync_btn": "Iniciar Sincronização",
        "status_idle": "Pronto para iniciar. Verifique se o Engine está fechado.",
        "status_counting": "Contando arquivos de áudio...",
        "status_fase1": "Fase 1: Mapeando arquivos ({current}/{total})...",
        "status_fase2": "Fase 2: Reconstruindo a árvore de Playlists...",
        "status_saving": "Fase 3: Gravando no banco de dados...",
        "status_done": "Sincronização concluída com sucesso!",
        "error_db": "Erro: Arquivo m.db não encontrado!",
        "error_paths": "Por favor, selecione as pastas antes de iniciar.",
        "success_msg": "Operação finalizada!\nMúsicas novas injetadas: {novas}\nSua coleção foi sincronizada.",
        "collection_name": "- MY COLLECTION",
        "donation_text": "Este app te ajudou? Gostaria de me incentivar a mante-lo atualizado me pagando um cafezinho? ☕ Clique aqui ☺️"
    },
    "en": {
        "title": "Engine DJ - Mirror Sync",
        "music_folder": "Music Folder (Computer):",
        "db_file": "Database File (m.db):",
        "browse": "Browse",
        "sync_btn": "Start Synchronization",
        "status_idle": "Ready to start. Make sure Engine DJ is closed.",
        "status_counting": "Counting audio files...",
        "status_fase1": "Phase 1: Mapping files ({current}/{total})...",
        "status_fase2": "Phase 2: Rebuilding Playlist tree...",
        "status_saving": "Phase 3: Saving to database...",
        "status_done": "Synchronization completed successfully!",
        "error_db": "Error: m.db file not found!",
        "error_paths": "Please select the paths before starting.",
        "success_msg": "Operation finished!\nNew tracks injected: {novas}\nYour collection is synced.",
        "collection_name": "- MY COLLECTION",
        "donation_text": "Did this app help you? How about buying me a coffee? ☕ Click here."
    },
    "es": {
        "title": "Engine DJ - Mirror Sync",
        "music_folder": "Carpeta de Música (PC):",
        "db_file": "Base de Datos (m.db):",
        "browse": "Buscar",
        "sync_btn": "Iniciar Sincronización",
        "status_idle": "Listo para empezar. Cierre Engine DJ antes.",
        "status_counting": "Contando archivos de audio...",
        "status_fase1": "Phase 1: Mapeando archivos ({current}/{total})...",
        "status_fase2": "Phase 2: Reconstruyendo árbol de Playlists...",
        "status_saving": "Phase 3: Guardando en la base de datos...",
        "status_done": "¡Sincronización completada con éxito!",
        "error_db": "¡Error: Archivo m.db no encontrado!",
        "error_paths": "Por favor, seleccione las rutas antes de empezar.",
        "success_msg": "¡Operación finalizada!\nNuevas canciones inyectadas: {novas}\nSu colección está sincronizada.",
        "collection_name": "- MY COLLECTION",
        "donation_text": "¿Te ayudó esta app? ¿Qué tal si me invitas a un café? ☕ Clic aquí."
    }
}

def obter_idioma_sistema():
    try:
        lang, _ = locale.getdefaultlocale()
        if lang:
            sigla = lang.split("_")[0].lower()
            if sigla in STRINGS:
                return sigla
    except:
        pass
    return "en"

# ================= INTERFACE GRÁFICA =================
ctk.set_appearance_mode("Dark")

class EngineSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.lang = obter_idioma_sistema()
        self.txt = STRINGS[self.lang]
        
        self.title(self.txt["title"])
        self.geometry("650x510")
        self.resizable(False, False)
        
        # Força a cor de fundo da janela para o cinza escuro blindado
        self.configure(fg_color="#242424")
        
        # 1. Truque para a Barra de Tarefas (Desvincula do Python no Windows)
        if os.name == 'nt':
            try:
                import ctypes
                myappid = 'lehdeejay.enginesync.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        # 2. Localizador inteligente de recursos para quando compilar em .exe/.app
        def caminho_recurso(caminho_relativo):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_path, caminho_relativo)
        
        self.caminho_recurso = caminho_recurso # Salva a função para usar depois

        # 3. Carregamento de Ícone Inteligente (Windows vs Mac)
        if sys.platform.startswith('win'): 
            caminho_icone = self.caminho_recurso("sync_icon.ico")
            if os.path.exists(caminho_icone):
                try:
                    self.iconbitmap(caminho_icone)
                except Exception:
                    pass
        elif sys.platform.startswith('darwin'):
            # No Mac, o ícone é injetado pelo PyInstaller (.icns), não pela janela.
            pass 
        
        self.config_file = "engine_sync_config.json"
        self.path_musicas = ctk.StringVar()
        self.path_db = ctk.StringVar()
        self.status_var = ctk.StringVar(value=self.txt["status_idle"])
        
        self.carregar_config()
        self.construir_ui()

    def construir_ui(self):
        # --- ÁREA DA LOGO OU TÍTULO ---
        img_carregada = False
        try:
            # Usa o localizador inteligente para achar a logo
            img_caminho = self.caminho_recurso("logo_engine.png")
            if os.path.exists(img_caminho):
                imagem_logo = Image.open(img_caminho)
                ctk_logo = ctk.CTkImage(light_image=imagem_logo, dark_image=imagem_logo, size=(480, 90))
                lbl_titulo = ctk.CTkLabel(self, text="", image=ctk_logo)
                img_carregada = True
        except Exception as e:
            print(f"Erro ao carregar a logo: {e}")
            
        if not img_carregada:
            lbl_titulo = ctk.CTkLabel(self, text="ENGINE DJ SYNC", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00E5A3")
            
        lbl_titulo.pack(pady=(25, 5))

        frame_config = ctk.CTkFrame(self)
        frame_config.pack(padx=30, pady=15, fill="x")

        lbl_pasta = ctk.CTkLabel(frame_config, text=self.txt["music_folder"], font=ctk.CTkFont(weight="bold"))
        lbl_pasta.grid(row=0, column=0, padx=15, pady=(15, 2), sticky="w")
        
        entry_pasta = ctk.CTkEntry(frame_config, textvariable=self.path_musicas, width=420)
        entry_pasta.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")
        
        btn_pasta = ctk.CTkButton(frame_config, text=self.txt["browse"], width=100, fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", font=ctk.CTkFont(weight="bold"), command=self.procurar_pasta)
        btn_pasta.grid(row=1, column=1, padx=(0, 15), pady=(0, 15))

        lbl_db = ctk.CTkLabel(frame_config, text=self.txt["db_file"], font=ctk.CTkFont(weight="bold"))
        lbl_db.grid(row=2, column=0, padx=15, pady=(0, 2), sticky="w")
        
        entry_db = ctk.CTkEntry(frame_config, textvariable=self.path_db, width=420)
        entry_db.grid(row=3, column=0, padx=15, pady=(0, 20), sticky="w")
        
        btn_db = ctk.CTkButton(frame_config, text=self.txt["browse"], width=100, fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", font=ctk.CTkFont(weight="bold"), command=self.procurar_db)
        btn_db.grid(row=3, column=1, padx=(0, 15), pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self, textvariable=self.status_var, font=ctk.CTkFont(size=14))
        self.lbl_status.pack(pady=(10, 5))

        self.progress_bar = ctk.CTkProgressBar(self, width=590, height=12, progress_color="#00E5A3")
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        self.btn_sync = ctk.CTkButton(self, text=self.txt["sync_btn"], font=ctk.CTkFont(size=16, weight="bold"), 
                                      height=45, fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", 
                                      command=self.iniciar_sincronizacao)
        self.btn_sync.pack(pady=(15, 10), fill="x", padx=60)

        self.btn_doacao = ctk.CTkButton(self, text=self.txt["donation_text"], font=ctk.CTkFont(size=12, underline=True),
                                        fg_color="transparent", text_color="#00E5A3", hover_color=None,
                                        hover=False, cursor="hand2", command=self.abrir_link_doacao)
        self.btn_doacao.pack(pady=(10, 10))

    def abrir_link_doacao(self):
        webbrowser.open(URL_DOACAO)

    def procurar_pasta(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.path_musicas.set(pasta)
            self.salvar_config()

    def procurar_db(self):
        arquivo = filedialog.askopenfilename(filetypes=[("Engine DB", "*.db")])
        if arquivo:
            self.path_db.set(arquivo)
            self.salvar_config()

    def carregar_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.path_musicas.set(data.get("pasta_musicas", ""))
                    self.path_db.set(data.get("path_db", ""))
            except:
                pass

    def salvar_config(self):
        data = {"pasta_musicas": self.path_musicas.get(), "path_db": self.path_db.get()}
        try:
            with open(self.config_file, "w") as f:
                json.dump(data, f)
        except:
            pass

    def iniciar_sincronizacao(self):
        if not self.path_musicas.get() or not self.path_db.get():
            self.status_var.set(self.txt["error_paths"])
            return
        if not os.path.exists(self.path_db.get()):
            self.status_var.set(self.txt["error_db"])
            return

        self.btn_sync.configure(state="disabled")
        self.status_var.set(self.txt["status_counting"])
        self.progress_bar.set(0)

        threading.Thread(target=self.motor_sincronizacao, daemon=True).start()

    def formatar_caminho_engine(self, caminho_windows, caminho_db):
        pasta_db2 = os.path.dirname(caminho_db)
        pasta_engine_library = os.path.dirname(pasta_db2)
        caminho_relativo = os.path.relpath(caminho_windows, pasta_engine_library)
        return caminho_relativo.replace("\\", "/")

    def motor_sincronizacao(self):
        pasta = self.path_musicas.get()
        db_path = self.path_db.get()
        nome_colecao = self.txt["collection_name"]

        arquivos_totais = []
        for raiz, _, arquivos in os.walk(pasta):
            for arquivo in arquivos:
                # Suporte aos formatos principais
                if arquivo.lower().endswith(('.mp3', '.flac', '.wav', '.aiff', '.m4a')):
                    arquivos_totais.append(os.path.join(raiz, arquivo))
        
        total_arquivos = len(arquivos_totais)
        if total_arquivos == 0:
            self.after(0, self.finalizar_sync, 0)
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT uuid FROM Information LIMIT 1")
