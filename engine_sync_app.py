import os
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
        
        # Lógica de ícone multiplataforma (Windows = .ico / Mac = .icns)
        icone_arquivo = "sync_icon.ico" if os.name == 'nt' else "sync_icon.icns"
        if os.path.exists(icone_arquivo):
            try:
                self.iconbitmap(icone_arquivo)
            except Exception as e:
                print(f"Aviso: Ícone nativo não suportado no ambiente atual. ({e})")
        
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
            # Tenta encontrar a logo na mesma pasta do executável/script
            img_caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_engine.png")
            if os.path.exists(img_caminho):
                imagem_logo = Image.open(img_caminho)
                # O tamanho 480x90 mantido conforme seu código base
                ctk_logo = ctk.CTkImage(light_image=imagem_logo, dark_image=imagem_logo, size=(480, 90))
                lbl_titulo = ctk.CTkLabel(self, text="", image=ctk_logo)
                img_carregada = True
        except Exception as e:
            print(f"Erro ao carregar a logo: {e}")
            
        if not img_carregada:
            # Fallback para o texto verde se a logo não for encontrada
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
        row = cursor.fetchone()
        db_uuid = row[0] if row else ""
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        novas_musicas = 0
        for idx, caminho_completo in enumerate(arquivos_totais):
            if idx % 20 == 0 or idx == total_arquivos - 1:
                progresso = (idx + 1) / total_arquivos * 0.5 
                msg = self.txt["status_fase1"].format(current=idx+1, total=total_arquivos)
                self.after(0, lambda m=msg, p=progresso: [self.status_var.set(m), self.progress_bar.set(p)])

            caminho_engine = self.formatar_caminho_engine(caminho_completo, db_path)
            cursor.execute("SELECT id FROM Track WHERE path = ?", (caminho_engine,))
            if cursor.fetchone():
                continue 

            try:
                tag = TinyTag.get(caminho_completo)
                titulo = getattr(tag, 'title', None) or os.path.basename(caminho_completo)
                artista = getattr(tag, 'artist', None) or "Desconhecido"
                album = getattr(tag, 'album', None) or ""
                bpm = int(getattr(tag, 'bpm', 0) or 0)
                duracao = int(getattr(tag, 'duration', 0) or 0)
                try:
                    ano = int(str(getattr(tag, 'year', 0))[:4]) if getattr(tag, 'year', 0) else 0
                except ValueError:
                    ano = 0
                
                cursor.execute("""
                    INSERT INTO Track (path, filename, title, artist, album, length, bpm, year, isAnalyzed, isAvailable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
                """, (caminho_engine, os.path.basename(caminho_completo), titulo, artista, album, duracao, bpm, ano))
                novas_musicas += 1
            except:
                pass

        self.after(0, lambda: [self.status_var.set(self.txt["status_fase2"]), self.progress_bar.set(0.6)])
        
        cursor.execute("SELECT id FROM Playlist WHERE title = ? AND parentListId = 0", (nome_colecao,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("SELECT id FROM Playlist WHERE parentListId = 0 AND nextListId = 0")
            last_root = cursor.fetchone()
            cursor.execute("INSERT INTO Playlist (title, parentListId, isPersisted, nextListId, lastEditTime, isExplicitlyExported) VALUES (?, 0, 1, 0, ?, 1)", (nome_colecao, data_atual))
            my_collection_id = cursor.lastrowid
            if last_root:
                cursor.execute("UPDATE Playlist SET nextListId = ? WHERE id = ?", (my_collection_id, last_root[0]))
        else:
            my_collection_id = row[0]
            cte_query = "WITH RECURSIVE descendants(id) AS (SELECT id FROM Playlist WHERE parentListId = ? UNION ALL SELECT p.id FROM Playlist p INNER JOIN descendants d ON p.parentListId = d.id) SELECT id FROM descendants;"
            cursor.execute(cte_query, (my_collection_id,))
            descendants = [r[0] for r in cursor.fetchall()]
            
            if descendants:
                placeholders = ','.join('?' * len(descendants))
                cursor.execute(f"DELETE FROM PlaylistEntity WHERE listId IN ({placeholders})", descendants)
                cursor.execute(f"DELETE FROM Playlist WHERE id IN ({placeholders})", descendants)
            cursor.execute("DELETE FROM PlaylistEntity WHERE listId = ?", (my_collection_id,))

        cursor.execute("SELECT id, path FROM Track")
        mapa_tracks = {l[1].lower(): l[0] for l in cursor.fetchall()}

        mapa_playlists = {pasta.lower(): my_collection_id} 
        mapa_hierarquia = {my_collection_id: None}
        tracks_por_playlist = defaultdict(dict)

        for raiz, diretorios, arquivos in os.walk(pasta):
            parent_id = mapa_playlists.get(raiz.lower(), my_collection_id)
            diretorios.sort(reverse=True) 
            
            arquivos_validos = [f for f in arquivos if f.lower().endswith(('.mp3', '.flac', '.wav', '.aiff', '.m4a'))]
            tem_sub = len(diretorios) > 0
            tem_arquivos = len(arquivos_validos) > 0
            
            id_proxima_pasta = 0 
            playlist_alvo_id = parent_id

            # 1. Primeiro criamos TODAS as subpastas no banco (de Z para A)
            for d in diretorios:
                caminho_subpasta = os.path.join(raiz, d)
                cursor.execute("INSERT INTO Playlist (title, parentListId, isPersisted, nextListId, lastEditTime, isExplicitlyExported) VALUES (?, ?, 1, ?, ?, 1)", (d, parent_id, id_proxima_pasta, data_atual))
                novo_id = cursor.lastrowid
                id_proxima_pasta = novo_id # Atualiza o elo da corrente
                mapa_playlists[caminho_subpasta.lower()] = novo_id
                mapa_hierarquia[novo_id] = parent_id

            # 2. SÓ DEPOIS criamos a Playlist Gêmea. 
            # Como ela é inserida por último, ela aponta para a pasta "A", assumindo o topo da lista.
            if tem_sub and tem_arquivos:
                nome_pasta_atual = os.path.basename(raiz)
                if raiz == pasta:
                    nome_pasta_atual = "Faixas Soltas"
                nome_gemea = f"[ {nome_pasta_atual} ]"

                cursor.execute("""
                    INSERT INTO Playlist (title, parentListId, isPersisted, nextListId, lastEditTime, isExplicitlyExported)
                    VALUES (?, ?, 1, ?, ?, 1)
                """, (nome_gemea, parent_id, id_proxima_pasta, data_atual))
                gemea_id = cursor.lastrowid
                
                mapa_hierarquia[gemea_id] = parent_id
                playlist_alvo_id = gemea_id

            # 3. Vincular as músicas na playlist correta
            for arquivo in arquivos_validos:
                caminho_completo = os.path.join(raiz, arquivo)
                caminho_engine = self.formatar_caminho_engine(caminho_completo, db_path)
                track_id = mapa_tracks.get(caminho_engine.lower())
                
                if track_id:
                    curr_list_id = playlist_alvo_id
                    while curr_list_id is not None:
                        tracks_por_playlist[curr_list_id][track_id] = caminho_completo
                        curr_list_id = mapa_hierarquia.get(curr_list_id)

        self.after(0, lambda: [self.status_var.set(self.txt["status_saving"]), self.progress_bar.set(0.85)])
        
        for list_id, dict_tracks in tracks_por_playlist.items():
            id_proxima_entidade = 0 
            for track_id, caminho in sorted(dict_tracks.items(), key=lambda item: item[1], reverse=True):
                cursor.execute("INSERT INTO PlaylistEntity (listId, trackId, databaseUuid, nextEntityId, membershipReference) VALUES (?, ?, ?, ?, 0)", (list_id, track_id, db_uuid, id_proxima_entidade))
                id_proxima_entidade = cursor.lastrowid

        conn.commit()
        conn.close()
        
        self.after(0, lambda: self.finalizar_sync(novas_musicas))

    def finalizar_sync(self, novas_musicas):
        self.status_var.set(self.txt["status_done"])
        self.progress_bar.set(1.0)
        self.btn_sync.configure(state="normal")
        titulo_msg = "Sucesso" if self.lang == "pt" else "Success"
        messagebox.showinfo(title=titulo_msg, message=self.txt["success_msg"].format(novas=novas_musicas))

if __name__ == "__main__":
    app = EngineSyncApp()
    app.mainloop()
