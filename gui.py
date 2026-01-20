#!/usr/bin/env python3
"""
Spotify to YouTube Music Transfer - GUI Version (CSV)

Interface gráfica para transferir playlists do Spotify (via CSV do Exportify)
para o YouTube Music.
"""

import csv
import json
import os
import threading
import time
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ytmusicapi import YTMusic

# Configuração do tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class OAuthSetupDialog(ctk.CTkToplevel):
    """Dialog para configurar OAuth do Google."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.result = None

        self.title("Configurar YouTube Music OAuth")
        self.geometry("550x400")
        self.resizable(False, False)

        # Centralizar
        self.transient(parent)
        self.after(100, self.grab_set)  # Aguardar janela ficar visível

        self.setup_ui()

    def setup_ui(self):
        # Instruções
        instructions = """Para conectar ao YouTube Music, você precisa criar
credenciais OAuth no Google Cloud Console:

1. Acesse: console.cloud.google.com
2. Crie um novo projeto (ou use um existente)
3. Ative a "YouTube Data API v3"
4. Vá em "Credenciais" > "Criar credenciais" > "ID do cliente OAuth"
5. Tipo: "App para TV e dispositivos de entrada limitada"
6. Copie o Client ID e Client Secret abaixo"""

        ctk.CTkLabel(
            self,
            text=instructions,
            font=ctk.CTkFont(size=12),
            justify="left"
        ).pack(padx=20, pady=(20, 10))

        # Link para console
        link_frame = ctk.CTkFrame(self, fg_color="transparent")
        link_frame.pack(fill="x", padx=20)

        ctk.CTkLabel(
            link_frame,
            text="Link:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        self.link_entry = ctk.CTkEntry(link_frame, width=400)
        self.link_entry.pack(side="left", padx=5)
        self.link_entry.insert(0, "https://console.cloud.google.com/apis/credentials")
        self.link_entry.configure(state="readonly")

        # Client ID
        ctk.CTkLabel(
            self,
            text="Client ID:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self.client_id_entry = ctk.CTkEntry(self, width=500, placeholder_text="Cole o Client ID aqui")
        self.client_id_entry.pack(padx=20)

        # Client Secret
        ctk.CTkLabel(
            self,
            text="Client Secret:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self.client_secret_entry = ctk.CTkEntry(self, width=500, placeholder_text="Cole o Client Secret aqui")
        self.client_secret_entry.pack(padx=20)

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self.cancel,
            fg_color="gray40",
            width=100
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Conectar",
            command=self.submit,
            width=100
        ).pack(side="right")

    def submit(self):
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()

        if not client_id or not client_secret:
            messagebox.showerror("Erro", "Preencha Client ID e Client Secret")
            return

        self.result = (client_id, client_secret)
        self.callback(client_id, client_secret)
        self.destroy()

    def cancel(self):
        self.callback(None, None)
        self.destroy()


class BrowserAuthDialog(ctk.CTkToplevel):
    """Dialog para autenticação via headers do browser."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback

        self.title("Autenticação via Browser")
        self.geometry("600x500")
        self.resizable(False, False)

        self.transient(parent)
        self.after(100, self.grab_set)  # Aguardar janela ficar visível

        self.setup_ui()

    def setup_ui(self):
        instructions = """Método alternativo - Autenticação via Browser Headers:

1. Abra o YouTube Music no Firefox ou Chrome (logado na sua conta)
2. Pressione F12 para abrir as Ferramentas de Desenvolvedor
3. Vá na aba "Network" (Rede)
4. Clique em qualquer música para gerar tráfego
5. Procure uma requisição para "music.youtube.com"
6. Clique com botão direito > "Copy" > "Copy as cURL"
7. Cole o comando cURL completo abaixo:"""

        ctk.CTkLabel(
            self,
            text=instructions,
            font=ctk.CTkFont(size=12),
            justify="left"
        ).pack(padx=20, pady=(20, 10))

        self.curl_text = ctk.CTkTextbox(self, height=250, width=550)
        self.curl_text.pack(padx=20, pady=10)

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self.cancel,
            fg_color="gray40",
            width=100
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Autenticar",
            command=self.submit,
            width=100
        ).pack(side="right")

    def submit(self):
        curl_text = self.curl_text.get("1.0", "end").strip()
        if not curl_text:
            messagebox.showerror("Erro", "Cole o comando cURL")
            return

        self.callback(curl_text)
        self.destroy()

    def cancel(self):
        self.callback(None)
        self.destroy()


class SpotifyYTMusicApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Spotify CSV → YouTube Music Transfer")
        self.geometry("850x700")
        self.minsize(750, 600)

        # Variáveis
        self.ytm = None
        self.csv_files = []
        self.is_transferring = False

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Container principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # === Header ===
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="Spotify CSV → YouTube Music",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left")

        # === Connection Frame ===
        conn_frame = ctk.CTkFrame(self)
        conn_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        conn_frame.grid_columnconfigure((0, 1), weight=1)

        # CSV Import
        csv_frame = ctk.CTkFrame(conn_frame)
        csv_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.csv_status = ctk.CTkLabel(
            csv_frame,
            text="Nenhum CSV carregado",
            font=ctk.CTkFont(size=14)
        )
        self.csv_status.pack(side="left", padx=10)

        self.csv_btn = ctk.CTkButton(
            csv_frame,
            text="Importar CSV(s)",
            command=self.import_csv,
            width=140
        )
        self.csv_btn.pack(side="right", padx=10, pady=5)

        # YouTube Music connection
        ytm_frame = ctk.CTkFrame(conn_frame)
        ytm_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.ytm_status = ctk.CTkLabel(
            ytm_frame,
            text="YouTube Music: Desconectado",
            font=ctk.CTkFont(size=14)
        )
        self.ytm_status.pack(side="left", padx=10)

        self.ytm_btn = ctk.CTkButton(
            ytm_frame,
            text="Conectar YT Music",
            command=self.show_auth_options,
            width=140
        )
        self.ytm_btn.pack(side="right", padx=10, pady=5)

        # === Main Content ===
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        # Playlist header
        playlist_header = ctk.CTkFrame(content_frame, fg_color="transparent")
        playlist_header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(
            playlist_header,
            text="Playlists CSV (Exportify)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        self.clear_btn = ctk.CTkButton(
            playlist_header,
            text="Limpar Lista",
            command=self.clear_list,
            width=100,
            fg_color="gray40",
            hover_color="gray30"
        )
        self.clear_btn.pack(side="right")

        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_cb = ctk.CTkCheckBox(
            playlist_header,
            text="Selecionar Todas",
            variable=self.select_all_var,
            command=self.toggle_select_all
        )
        self.select_all_cb.pack(side="right", padx=20)

        # Playlist list (scrollable)
        self.playlist_scroll = ctk.CTkScrollableFrame(content_frame)
        self.playlist_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.playlist_scroll.grid_columnconfigure(0, weight=1)

        self.playlist_checkboxes = []
        self.playlist_vars = []

        # Placeholder message
        self.placeholder_label = ctk.CTkLabel(
            self.playlist_scroll,
            text="Importe arquivos CSV do Exportify\n(exportify.app)",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.placeholder_label.grid(row=0, column=0, pady=50)

        # === Progress Section ===
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Pronto para transferir",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.current_track_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.current_track_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

        # === Transfer Button ===
        self.transfer_btn = ctk.CTkButton(
            self,
            text="Transferir Playlists Selecionadas",
            command=self.start_transfer,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            state="disabled"
        )
        self.transfer_btn.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")

        # === Log Frame ===
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_frame,
            text="Log",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.log_text = ctk.CTkTextbox(log_frame, height=120)
        self.log_text.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    def log(self, message):
        """Adiciona mensagem ao log."""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def import_csv(self):
        """Importa arquivos CSV do Exportify."""
        filepaths = filedialog.askopenfilenames(
            title="Selecione arquivos CSV do Exportify",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~")
        )

        if not filepaths:
            return

        for filepath in filepaths:
            self.load_csv_file(filepath)

        self.display_playlists()
        self.check_ready()

    def load_csv_file(self, filepath):
        """Carrega um arquivo CSV e extrai as músicas."""
        try:
            tracks = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    track_name = row.get('Track Name', '')
                    artists = row.get('Artist Name(s)', '')

                    if track_name:
                        tracks.append({
                            'name': track_name,
                            'artists': artists
                        })

            if tracks:
                playlist_name = Path(filepath).stem
                self.csv_files.append({
                    'name': playlist_name,
                    'filepath': filepath,
                    'tracks': tracks,
                    'tracks_total': len(tracks)
                })
                self.log(f"Carregado: {playlist_name} ({len(tracks)} musicas)")
            else:
                self.log(f"Aviso: Nenhuma musica encontrada em {Path(filepath).name}")

        except Exception as e:
            self.log(f"Erro ao carregar {Path(filepath).name}: {e}")

    def clear_list(self):
        """Limpa a lista de CSVs carregados."""
        self.csv_files = []
        self.display_playlists()
        self.csv_status.configure(text="Nenhum CSV carregado")
        self.check_ready()

    def show_auth_options(self):
        """Mostra opções de autenticação."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Escolha o método de autenticação")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.after(100, dialog.grab_set)  # Aguardar janela ficar visível

        ctk.CTkLabel(
            dialog,
            text="Como deseja conectar ao YouTube Music?",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20)

        # Verificar se já existe oauth.json
        if os.path.exists('oauth.json'):
            ctk.CTkButton(
                dialog,
                text="Usar credenciais salvas (oauth.json)",
                command=lambda: self.use_existing_oauth(dialog),
                width=300
            ).pack(pady=5)

        ctk.CTkButton(
            dialog,
            text="OAuth (Google Cloud Console)",
            command=lambda: self.show_oauth_dialog(dialog),
            width=300
        ).pack(pady=5)

        ctk.CTkButton(
            dialog,
            text="Browser Headers (alternativo)",
            command=lambda: self.show_browser_auth(dialog),
            width=300
        ).pack(pady=5)

    def use_existing_oauth(self, parent_dialog):
        """Usa arquivo oauth.json existente."""
        parent_dialog.destroy()
        self.connect_with_oauth_file()

    def show_oauth_dialog(self, parent_dialog):
        """Mostra dialog para OAuth."""
        parent_dialog.destroy()
        OAuthSetupDialog(self, self.on_oauth_credentials)

    def show_browser_auth(self, parent_dialog):
        """Mostra dialog para autenticação via browser."""
        parent_dialog.destroy()
        BrowserAuthDialog(self, self.on_browser_auth)

    def on_oauth_credentials(self, client_id, client_secret):
        """Callback quando credenciais OAuth são fornecidas."""
        if not client_id or not client_secret:
            return

        self.ytm_btn.configure(state="disabled", text="Conectando...")
        self.log("Iniciando autenticação OAuth...")

        def do_oauth():
            try:
                from ytmusicapi.setup import setup_oauth

                self.after(0, lambda: self.log("Abrindo navegador para login..."))

                setup_oauth(
                    client_id=client_id,
                    client_secret=client_secret,
                    filepath='oauth.json',
                    open_browser=True
                )

                self.ytm = YTMusic('oauth.json')
                self.after(0, self.on_ytmusic_connected)

            except Exception as e:
                self.after(0, lambda: self.log(f"Erro OAuth: {e}"))
                self.after(0, lambda: self.ytm_btn.configure(
                    state="normal", text="Conectar YT Music"
                ))

        threading.Thread(target=do_oauth, daemon=True).start()

    def on_browser_auth(self, curl_text):
        """Callback quando cURL é fornecido."""
        if not curl_text:
            return

        self.ytm_btn.configure(state="disabled", text="Conectando...")
        self.log("Processando headers do browser...")

        def do_browser_auth():
            try:
                # Extrair headers do cURL
                headers = self.parse_curl_headers(curl_text)

                if not headers:
                    raise ValueError("Não foi possível extrair headers do cURL")

                # Salvar headers para uso
                headers_file = 'browser_headers.json'
                with open(headers_file, 'w') as f:
                    json.dump(headers, f, indent=2)

                self.ytm = YTMusic(headers_file)
                self.after(0, self.on_ytmusic_connected)

            except Exception as e:
                self.after(0, lambda: self.log(f"Erro na autenticação: {e}"))
                self.after(0, lambda: self.ytm_btn.configure(
                    state="normal", text="Conectar YT Music"
                ))

        threading.Thread(target=do_browser_auth, daemon=True).start()

    def parse_curl_headers(self, curl_text):
        """Extrai headers de um comando cURL e cria arquivo de autenticação."""
        import re

        # Extrair cookie
        cookie_match = re.search(r"-H ['\"]Cookie:\s*([^'\"]+)['\"]", curl_text, re.IGNORECASE)
        if not cookie_match:
            # Tentar sem aspas (formato diferente)
            cookie_match = re.search(r"-H 'Cookie: ([^']+)'", curl_text)

        if not cookie_match:
            self.after(0, lambda: self.log("Erro: Cookie nao encontrado no cURL"))
            return None

        cookie = cookie_match.group(1).strip()

        # Extrair Authorization (importante para YTMusic)
        auth_match = re.search(r"-H ['\"]Authorization:\s*([^'\"]+)['\"]", curl_text, re.IGNORECASE)
        authorization = auth_match.group(1).strip() if auth_match else ""

        # Extrair x-goog-authuser (opcional)
        auth_user = "0"
        goog_auth_match = re.search(r"-H ['\"]X-Goog-AuthUser:\s*(\d+)['\"]", curl_text, re.IGNORECASE)
        if goog_auth_match:
            auth_user = goog_auth_match.group(1)

        # Extrair User-Agent
        ua_match = re.search(r"-H ['\"]User-Agent:\s*([^'\"]+)['\"]", curl_text, re.IGNORECASE)
        user_agent = ua_match.group(1).strip() if ua_match else "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"

        # Formato esperado pelo ytmusicapi para browser auth
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "cookie": cookie,
            "user-agent": user_agent,
            "x-goog-authuser": auth_user,
            "x-origin": "https://music.youtube.com",
            "origin": "https://music.youtube.com"
        }

        # Adicionar Authorization se existir
        if authorization:
            headers["authorization"] = authorization

        self.after(0, lambda: self.log(f"Headers extraidos: Cookie={'OK' if cookie else 'FALTA'}, Auth={'OK' if authorization else 'FALTA'}"))

        return headers

    def connect_with_oauth_file(self):
        """Conecta usando arquivo oauth.json existente."""
        self.ytm_btn.configure(state="disabled", text="Conectando...")
        self.log("Conectando com credenciais salvas...")

        def do_connect():
            try:
                self.ytm = YTMusic('oauth.json')
                self.after(0, self.on_ytmusic_connected)
            except Exception as e:
                self.after(0, lambda: self.log(f"Erro: {e}"))
                self.after(0, lambda: self.ytm_btn.configure(
                    state="normal", text="Conectar YT Music"
                ))

        threading.Thread(target=do_connect, daemon=True).start()

    def on_ytmusic_connected(self):
        """Callback quando conectado ao YouTube Music."""
        self.ytm_status.configure(text="YouTube Music: Conectado")
        self.ytm_btn.configure(state="disabled", text="Conectado")
        self.log("Conectado ao YouTube Music!")
        self.check_ready()

    def check_ready(self):
        """Verifica se está pronto para transferir."""
        if self.ytm and self.csv_files:
            self.transfer_btn.configure(state="normal")
        else:
            self.transfer_btn.configure(state="disabled")

    def display_playlists(self):
        """Exibe as playlists na interface."""
        for widget in self.playlist_scroll.winfo_children():
            widget.destroy()

        self.playlist_checkboxes = []
        self.playlist_vars = []

        if not self.csv_files:
            self.placeholder_label = ctk.CTkLabel(
                self.playlist_scroll,
                text="Importe arquivos CSV do Exportify\n(exportify.app)",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            self.placeholder_label.grid(row=0, column=0, pady=50)
            self.csv_status.configure(text="Nenhum CSV carregado")
            return

        for i, pl in enumerate(self.csv_files):
            var = ctk.BooleanVar(value=True)
            self.playlist_vars.append(var)

            frame = ctk.CTkFrame(self.playlist_scroll)
            frame.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            frame.grid_columnconfigure(1, weight=1)

            cb = ctk.CTkCheckBox(frame, text="", variable=var, width=24)
            cb.grid(row=0, column=0, padx=(10, 5), pady=8)
            self.playlist_checkboxes.append(cb)

            name_label = ctk.CTkLabel(
                frame, text=pl['name'],
                font=ctk.CTkFont(size=14), anchor="w"
            )
            name_label.grid(row=0, column=1, padx=5, pady=8, sticky="w")

            info_label = ctk.CTkLabel(
                frame, text=f"{pl['tracks_total']} musicas",
                font=ctk.CTkFont(size=12), text_color="gray"
            )
            info_label.grid(row=0, column=2, padx=10, pady=8, sticky="e")

            remove_btn = ctk.CTkButton(
                frame, text="X", width=30, height=30,
                fg_color="gray40", hover_color="red",
                command=lambda idx=i: self.remove_playlist(idx)
            )
            remove_btn.grid(row=0, column=3, padx=5, pady=8)

        self.csv_status.configure(text=f"{len(self.csv_files)} playlist(s) carregada(s)")

    def remove_playlist(self, index):
        """Remove uma playlist da lista."""
        if 0 <= index < len(self.csv_files):
            removed = self.csv_files.pop(index)
            self.log(f"Removido: {removed['name']}")
            self.display_playlists()
            self.check_ready()

    def toggle_select_all(self):
        """Seleciona ou desmarca todas as playlists."""
        select = self.select_all_var.get()
        for var in self.playlist_vars:
            var.set(select)

    def get_selected_playlists(self):
        """Retorna lista de playlists selecionadas."""
        return [self.csv_files[i] for i, var in enumerate(self.playlist_vars) if var.get()]

    def start_transfer(self):
        """Inicia a transferência das playlists selecionadas."""
        selected = self.get_selected_playlists()

        if not selected:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma playlist para transferir.")
            return

        if not self.ytm:
            messagebox.showerror("Erro", "Conecte-se ao YouTube Music primeiro.")
            return

        self.is_transferring = True
        self.transfer_btn.configure(state="disabled", text="Transferindo...")
        self.csv_btn.configure(state="disabled")

        for cb in self.playlist_checkboxes:
            cb.configure(state="disabled")

        threading.Thread(target=self.do_transfer, args=(selected,), daemon=True).start()

    def do_transfer(self, playlists):
        """Executa a transferência em thread separada."""
        total_playlists = len(playlists)

        for pl_idx, playlist in enumerate(playlists):
            self.after(0, lambda p=playlist: self.log(f"\n{'='*40}"))
            self.after(0, lambda p=playlist: self.log(f"Transferindo: {p['name']}"))

            tracks = playlist['tracks']

            if not tracks:
                self.after(0, lambda: self.log("Playlist vazia, pulando..."))
                continue

            self.after(0, lambda t=tracks: self.log(f"Total: {len(t)} musicas"))

            # Criar playlist no YT Music
            self.after(0, lambda: self.progress_label.configure(
                text="Criando playlist no YouTube Music..."
            ))

            try:
                yt_playlist_id = self.ytm.create_playlist(
                    playlist['name'],
                    f"Importada do Spotify - {len(tracks)} musicas"
                )
                self.after(0, lambda: self.log("Playlist criada no YouTube Music"))
            except Exception as e:
                self.after(0, lambda e=e: self.log(f"Erro ao criar playlist: {e}"))
                continue

            # Buscar e adicionar músicas
            found_videos = []
            not_found = []
            total_tracks = len(tracks)

            for i, track in enumerate(tracks):
                progress = (i + 1) / total_tracks
                self.after(0, lambda p=progress: self.progress_bar.set(p))
                self.after(0, lambda idx=i, total=total_tracks, plidx=pl_idx, pltotal=total_playlists:
                    self.progress_label.configure(
                        text=f"Playlist {plidx + 1}/{pltotal} - Musica {idx + 1}/{total}"
                    )
                )
                self.after(0, lambda t=track: self.current_track_label.configure(
                    text=f"{t['name']} - {t['artists']}"
                ))

                video_id = self.search_song(track)

                if video_id:
                    found_videos.append(video_id)
                else:
                    not_found.append(f"{track['name']} - {track['artists']}")

                time.sleep(0.3)

            # Adicionar músicas à playlist
            if found_videos:
                self.after(0, lambda: self.current_track_label.configure(
                    text="Adicionando musicas a playlist..."
                ))

                try:
                    batch_size = 25
                    for i in range(0, len(found_videos), batch_size):
                        batch = found_videos[i:i + batch_size]
                        self.ytm.add_playlist_items(yt_playlist_id, batch)
                        time.sleep(1)
                except Exception as e:
                    self.after(0, lambda e=e: self.log(f"Erro ao adicionar musicas: {e}"))

            # Resumo
            self.after(0, lambda f=found_videos, n=not_found: self.log(
                f"Concluido: {len(f)} encontradas, {len(n)} nao encontradas"
            ))

            if not_found:
                self.after(0, lambda n=not_found: self.log(
                    f"Nao encontradas: {', '.join(n[:3])}{'...' if len(n) > 3 else ''}"
                ))

        self.after(0, self.on_transfer_complete)

    def search_song(self, track):
        """Busca uma música no YouTube Music."""
        query = f"{track['name']} {track['artists']}"
        try:
            results = self.ytm.search(query, filter='songs', limit=1)
            if results:
                return results[0].get('videoId')
        except Exception:
            pass
        return None

    def on_transfer_complete(self):
        """Callback quando a transferência termina."""
        self.is_transferring = False
        self.transfer_btn.configure(
            state="normal",
            text="Transferir Playlists Selecionadas"
        )
        self.csv_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Transferencia concluida!")
        self.current_track_label.configure(text="")

        for cb in self.playlist_checkboxes:
            cb.configure(state="normal")

        self.log("\n" + "="*40)
        self.log("Transferencia concluida!")

        messagebox.showinfo(
            "Concluido",
            "Transferencia de playlists concluida!\nVerifique o log para detalhes."
        )


def main():
    app = SpotifyYTMusicApp()
    app.mainloop()


if __name__ == '__main__':
    main()
