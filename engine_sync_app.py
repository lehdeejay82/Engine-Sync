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
import urllib.request

try:
    from PIL import Image
except ImportError:
    pass

from tinytag import TinyTag
import customtkinter as ctk

# ================= IDENTIDADE DO APP ======================
VERSAO_ATUAL = "v1.0.0"
# ==========================================================

# ================= CONFIGURAÇÃO DE LINKS ==================
URL_DOACAO = "https://linktr.ee/leh.deejay82"

# TODO: COLOQUE SEU USUÁRIO E NOME DO REPOSITÓRIO AQUI:
GITHUB_API_URL = "https://api.github.com/repos/lehdeejay82/Engine-Sync/releases/latest"
GITHUB_RELEASE_URL = "https://github.com/lehdeejay82/Engine-Sync/releases/latest"
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
        "donation_text": "Este app te ajudou? Gostaria de me incentivar a mante-lo atualizado\nme pagando um cafezinho? ☕ Clique aqui ☺️",
        # Pop-up Update
        "update_title": "Atualização Disponível!",
        "update_msg": "Uma nova versão do Engine Sync está disponível!\n\nSua versão: {}\nNova versão: {}\n\nDeseja baixar a atualização agora?",
        "btn_yes": "Baixar Agora",
        "btn_no": "Lembrar Depois",
        "success_title": "Sucesso"
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
        "donation_text": "Did this app help you? Would you like to encourage me to keep it\nupdated by buying me a coffee? ☕ Click here ☺️",
        # Pop-up Update
        "update_title": "Update Available!",
        "update_msg": "A new version of Engine Sync is available!\n\nYour version: {}\nNew version: {}\n\nWould you like to download it now?",
        "btn_yes": "Download Now",
        "btn_no": "Remind Me Later",
        "success_title": "Success"
    },
    "es": {
        "title": "Engine DJ - Mirror Sync",
        "music_folder": "Carpeta de Música (PC):",
        "db_file": "Base de Datos (m.db):",
        "browse": "Buscar",
        "sync_btn": "Iniciar Sincronización",
        "status_idle": "Listo para empezar. Cierre Engine DJ antes.",
        "status_counting": "Contando arquivos de audio...",
        "status_fase1": "Phase 1: Mapeando archivos ({current}/{total})...",
        "status_fase2": "Phase 2: Reconstruyendo árbol de Playlists...",
        "status_saving": "Phase 3: Guardando en la base de datos...",
        "status_done": "¡Sincronización completada con éxito!",
        "error_db": "¡Error: Archivo m.db no encontrado!",
        "error_paths": "Por favor, seleccione las rutas antes de empezar.",
        "success_msg": "¡Operación finalizada!\nNuevas canciones inyectadas: {novas}\nSu colección está sincronizada.",
        "collection_name": "- MY COLLECTION",
        "donation_text": "¿Te ha resultado útil esta aplicación? ¿Te gustaría animarme a seguir\nactualizándola invitándome a un café? ☕ Haz clic aquí ☺️",
        # Pop-up Update
        "update_title": "¡Actualización Disponible!",
        "update_msg": "¡Una nova versión de Engine Sync está disponible!\n\nTu versão: {}\nNueva versión: {}\n\n¿Quieres descargarla ahora?",
        "btn_yes": "Descargar Ahora",
        "btn_no": "Recordarme Más Tarde",
        "success_title": "Éxito"
    }
}

def obter_idioma_sistema():
    try:
        # Se for Windows, força a leitura do Idioma da Interface (UI)
        if sys.platform.startswith('win'):
            import ctypes
            windll = ctypes.windll.kernel32
            idioma_id = windll.GetUserDefaultUILanguage()
            lang = locale.windows_locale.get(idioma_id, 'en_US')
        else:
            # Se for Mac/Linux, usa o método padrão
            lang, _ = locale.getdefaultlocale()
            
        if lang:
            sigla = lang.split("_")[0].lower()
            if sigla in STRINGS:
                return sigla
    except Exception:
        pass
    return "en"

# ================= POP-UP DE ATUALIZAÇÃO =================
class PopUpAtualizacao(ctk.CTkToplevel):
    def __init__(self, master, txt, versao_nova):
        super().__init__(master)
        
        self.title(txt["update_title"])
        self.geometry("400x250")
        self.resizable(False, False)
        self.configure(fg_color="#242424")

        # Toca o som de notificação nativo do sistema (Aviso de Atualização)
        if sys.platform.startswith('win'):
            try:
                import winsound
                # Usa MB_ICONEXCLAMATION para soar como um alerta/aviso
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except:
                self.bell()
        else:
            self.bell()
        
        if sys.platform.startswith('win') and hasattr(master, 'caminho_icone') and os.path.exists(master.caminho_icone):
            def aplicar_icone():
                try:
                    self.iconbitmap(master.caminho_icone)
                    self.wm_iconbitmap(master.caminho_icone)
                except Exception:
                    pass
            self.after(250, aplicar_icone)
        
        self.transient(master)
        self.grab_set()

        lbl_header = ctk.CTkLabel(self, text=txt["update_title"], font=ctk.CTkFont(size=20, weight="bold"), text_color="#00E5A3")
        lbl_header.pack(pady=(20, 10))

        lbl_msg = ctk.CTkLabel(self, text=txt["update_msg"].format(VERSAO_ATUAL, versao_nova), font=ctk.CTkFont(size=14))
        lbl_msg.pack(pady=(5, 20))

        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(pady=10)

        btn_baixar = ctk.CTkButton(frame_botoes, text=txt["btn_yes"], font=ctk.CTkFont(weight="bold"), fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", command=self.baixar_atualizacao)
        btn_baixar.pack(side="left", padx=10)

        btn_fechar = ctk.CTkButton(frame_botoes, text=txt["btn_no"], font=ctk.CTkFont(weight="bold"), fg_color="transparent", border_width=1, border_color="#555555", hover_color="#333333", command=self.destroy)
        btn_fechar.pack(side="left", padx=10)

    def baixar_atualizacao(self):
        webbrowser.open(GITHUB_RELEASE_URL)
        self.destroy()

# ================= INTERFACE GRÁFICA =================
ctk.set_appearance_mode("Dark")

class EngineSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.lang = obter_idioma_sistema()
        self.txt = STRINGS[self.lang]
        
        self.title(f"{self.txt['title']} ({VERSAO_ATUAL})") # Adiciona a versão no título da janela
        self.geometry("700x540")  # Modificado para 700x540 para evitar cortes nos textos
        self.resizable(False, False)
        
        self.configure(fg_color="#242424")
        
        if os.name == 'nt':
            try:
                import ctypes
                myappid = 'lehdeejay.enginesync.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        def caminho_recurso(caminho_relativo):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_path, caminho_relativo)
        
        self.caminho_recurso = caminho_recurso
        self.caminho_icone = self.caminho_recurso("sync_icon.ico")

        if sys.platform.startswith('win'): 
            if os.path.exists(self.caminho_icone):
                def aplicar_janela_icone():
                    try:
                        self.iconbitmap(self.caminho_icone)
                    except Exception:
                        pass
                self.after(200, aplicar_janela_icone)
        
        self.config_file = "engine_sync_config.json"
        self.path_musicas = ctk.StringVar()
        self.path_db = ctk.StringVar()
        self.status_var = ctk.StringVar(value=self.txt["status_idle"])
        
        self.carregar_config()
        self.construir_ui()
        
        # Dispara o espião do GitHub em segundo plano ao abrir o app
        threading.Thread(target=self.verificar_atualizacao, daemon=True).start()

    def verificar_atualizacao(self):
        try:
            req = urllib.request.Request(GITHUB_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    versao_github = data.get("tag_name", "")
                    
                    # Se a tag lá (ex: v1.1.0) for diferente da nossa (v1.0.0), dispara o Pop-up
                    if versao_github and versao_github != VERSAO_ATUAL:
                        self.after(1000, lambda: PopUpAtualizacao(self, self.txt, versao_github))
        except Exception:
            # Se não tiver internet ou o link estiver errado, morre em silêncio
            pass

    def construir_ui(self):
        img_carregada = False
        try:
            img_caminho = self.caminho_recurso("logo_engine.png")
            if os.path.exists(img_caminho):
                imagem_logo = Image.open(img_caminho)
                ctk_logo = ctk.CTkImage(light_image=imagem_logo, dark_image=imagem_logo, size=(480, 90))
                lbl_titulo = ctk.CTkLabel(self, text="", image=ctk_logo)
                img_carregada = True
        except Exception as e:
            pass
            
        if not img_carregada:
            lbl_titulo = ctk.CTkLabel(self, text="ENGINE DJ SYNC", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00E5A3")
            
        lbl_titulo.pack(pady=(25, 5))

        frame_config = ctk.CTkFrame(self)
        frame_config.pack(padx=30, pady=15, fill="x")

        lbl_pasta = ctk.CTkLabel(frame_config, text=self.txt["music_folder"], font=ctk.CTkFont(weight="bold"))
        lbl_pasta.grid(row=0, column=0, padx=15, pady=(15, 2), sticky="w")
        
        # Aumentado o width para 450 acompanhando o novo tamanho da janela
        entry_pasta = ctk.CTkEntry(frame_config, textvariable=self.path_musicas, width=450)
        entry_pasta.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")
        
        btn_pasta = ctk.CTkButton(frame_config, text=self.txt["browse"], width=100, fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", font=ctk.CTkFont(weight="bold"), command=self.procurar_pasta)
        btn_pasta.grid(row=1, column=1, padx=(0, 15), pady=(0, 15))

        lbl_db = ctk.CTkLabel(frame_config, text=self.txt["db_file"], font=ctk.CTkFont(weight="bold"))
        lbl_db.grid(row=2, column=0, padx=15, pady=(0, 2), sticky="w")
        
        # Aumentado o width para 450 acompanhando o novo tamanho da janela
        entry_db = ctk.CTkEntry(frame_config, textvariable=self.path_db, width=450)
        entry_db.grid(row=3, column=0, padx=15, pady=(0, 20), sticky="w")
        
        btn_db = ctk.CTkButton(frame_config, text=self.txt["browse"], width=100, fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", font=ctk.CTkFont(weight="bold"), command=self.procurar_db)
        btn_db.grid(row=3, column=1, padx=(0, 15), pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self, textvariable=self.status_var, font=ctk.CTkFont(size=14))
        self.lbl_status.pack(pady=(10, 5))

        # Aumentado o width para 620 para preencher o novo espaço estético da janela
        self.progress_bar = ctk.CTkProgressBar(self, width=620, height=12, progress_color="#00E5A3")
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        self.btn_sync = ctk.CTkButton(self, text=self.txt["sync_btn"], font=ctk.CTkFont(size=16, weight="bold"), 
                                      height=45, fg_color="#00E5A3", text_color="#000000", hover_color="#00b37e", 
                                      command=self.iniciar_sincronizacao)
        self.btn_sync.pack(pady=(15, 10), fill="x", padx=60)

        self.btn_doacao = ctk.CTkButton(self, text=self.txt["donation_text"], font=ctk.CTkFont(size=12, underline=True),
                                        fg_color="transparent", text_color="#00E5A3", hover_color=None,
                                        hover=False, cursor="hand2", command=self.abrir_link_doacao)
        self.btn_doacao.pack(pady=(5, 10))

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

            for d in diretorios:
                caminho_subpasta = os.path.join(raiz, d)
                cursor.execute("INSERT INTO Playlist (title, parentListId, isPersisted, nextListId, lastEditTime, isExplicitlyExported) VALUES (?, ?, 1, ?, ?, 1)", (d, parent_id, id_proxima_pasta, data_atual))
                novo_id = cursor.lastrowid
                id_proxima_pasta = novo_id 
                mapa_playlists[caminho_subpasta.lower()] = novo_id
                mapa_hierarquia[novo_id] = parent_id

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
        
        # Puxa o título diretamente do dicionário de idiomas
        titulo_msg = self.txt.get("success_title", "Success")
        messagebox.showinfo(title=titulo_msg, message=self.txt["success_msg"].format(novas=novas_musicas))

if __name__ == "__main__":
    app = EngineSyncApp()
    app.mainloop()
