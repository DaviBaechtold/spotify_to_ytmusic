#!/usr/bin/env python3
"""
Spotify to YouTube Music Transfer - GUI Version

Interface gráfica para transferir playlists do Spotify (via link ou CSV)
para o YouTube Music, com suporte a merge de playlists existentes.
"""

import csv
import json
import os
import re
import threading
import time
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ytmusicapi import YTMusic

import requests

# Configuração do tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SpotifyLinkDialog(ctk.CTkToplevel):
    """Dialog para importar playlist via link do Spotify."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback

        self.title("Importar Playlist do Spotify")
        self.geometry("550x200")
        self.resizable(False, False)

        self.transient(parent)
        self.after(100, self.grab_set)

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(
            self,
            text="Cole o link da playlist do Spotify:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            self,
            text="Exemplo: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(0, 10))

        self.link_entry = ctk.CTkEntry(self, width=500, placeholder_text="https://open.spotify.com/playlist/...")
        self.link_entry.pack(padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(btn_frame, text="Cancelar", command=self.cancel, fg_color="gray40", width=100).pack(side="left")
        ctk.CTkButton(btn_frame, text="Importar", command=self.submit, width=100).pack(side="right")

    def submit(self):
        link = self.link_entry.get().strip()
        if not link or "spotify.com" not in link:
            messagebox.showerror("Erro", "Cole um link válido do Spotify")
            return
        self.callback(link)
        self.destroy()

    def cancel(self):
        self.callback(None)
        self.destroy()


class OAuthSetupDialog(ctk.CTkToplevel):
    """Dialog para configurar OAuth do Google."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.result = None

        self.title("Configurar YouTube Music OAuth")
        self.geometry("550x400")
        self.resizable(False, False)

        self.transient(parent)
        self.after(100, self.grab_set)

        self.setup_ui()

    def setup_ui(self):
        instructions = """Para conectar ao YouTube Music, você precisa criar
credenciais OAuth no Google Cloud Console:

1. Acesse: console.cloud.google.com
2. Crie um novo projeto (ou use um existente)
3. Ative a "YouTube Data API v3"
4. Vá em "Credenciais" > "Criar credenciais" > "ID do cliente OAuth"
5. Tipo: "App para TV e dispositivos de entrada limitada"
6. Copie o Client ID e Client Secret abaixo"""

        ctk.CTkLabel(
            self, text=instructions,
            font=ctk.CTkFont(size=12), justify="left"
        ).pack(padx=20, pady=(20, 10))

        link_frame = ctk.CTkFrame(self, fg_color="transparent")
        link_frame.pack(fill="x", padx=20)

        ctk.CTkLabel(link_frame, text="Link:", font=ctk.CTkFont(size=12)).pack(side="left")

        self.link_entry = ctk.CTkEntry(link_frame, width=400)
        self.link_entry.pack(side="left", padx=5)
        self.link_entry.insert(0, "https://console.cloud.google.com/apis/credentials")
        self.link_entry.configure(state="readonly")

        ctk.CTkLabel(self, text="Client ID:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.client_id_entry = ctk.CTkEntry(self, width=500, placeholder_text="Cole o Client ID aqui")
        self.client_id_entry.pack(padx=20)

        ctk.CTkLabel(self, text="Client Secret:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.client_secret_entry = ctk.CTkEntry(self, width=500, placeholder_text="Cole o Client Secret aqui")
        self.client_secret_entry.pack(padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(btn_frame, text="Cancelar", command=self.cancel, fg_color="gray40", width=100).pack(side="left")
        ctk.CTkButton(btn_frame, text="Conectar", command=self.submit, width=100).pack(side="right")

    def submit(self):
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()
        if not client_id or not client_secret:
            messagebox.showerror("Erro", "Preencha Client ID e Client Secret")
            return
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
        self.after(100, self.grab_set)

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

        ctk.CTkLabel(self, text=instructions, font=ctk.CTkFont(size=12), justify="left").pack(padx=20, pady=(20, 10))

        self.curl_text = ctk.CTkTextbox(self, height=250, width=550)
        self.curl_text.pack(padx=20, pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(btn_frame, text="Cancelar", command=self.cancel, fg_color="gray40", width=100).pack(side="left")
        ctk.CTkButton(btn_frame, text="Autenticar", command=self.submit, width=100).pack(side="right")

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


class PlaylistSelectDialog(ctk.CTkToplevel):
    """Dialog para selecionar playlist destino (nova ou existente para merge)."""

    def __init__(self, parent, csv_playlist, yt_playlists, callback):
        super().__init__(parent)
        self.callback = callback
        self.csv_playlist = csv_playlist
        self.yt_playlists = yt_playlists
        self.selected_playlist = None
        self.playlist_checkboxes = []

        self.title(f"Destino: {csv_playlist['name']}")
        self.geometry("520x550")
        self.resizable(False, False)

        self.transient(parent)
        self.after(100, self.grab_set)

        # Permitir fechar com X
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.setup_ui()

    def setup_ui(self):
        # Botão X no canto superior direito
        close_btn = ctk.CTkButton(
            self, text="X", width=30, height=30,
            fg_color="gray40", hover_color="red",
            command=self.cancel
        )
        close_btn.place(x=480, y=10)

        ctk.CTkLabel(
            self,
            text=f"CSV: {self.csv_playlist['name']} ({self.csv_playlist['tracks_total']} musicas)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="Escolha o destino no YouTube Music:",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(5, 15))

        # Opção: Criar nova
        self.choice_var = ctk.StringVar(value="new")

        new_frame = ctk.CTkFrame(self, fg_color="transparent")
        new_frame.pack(fill="x", padx=20, pady=5)

        self.new_cb = ctk.CTkCheckBox(
            new_frame,
            text="Criar nova playlist",
            font=ctk.CTkFont(size=13),
            command=self.on_new_selected,
            checkbox_width=22,
            checkbox_height=22,
            border_width=2
        )
        self.new_cb.pack(anchor="w")
        self.new_cb.select()  # Selecionado por padrão

        # Opção: Merge com existente
        merge_frame = ctk.CTkFrame(self, fg_color="transparent")
        merge_frame.pack(fill="x", padx=20, pady=5)

        self.merge_cb = ctk.CTkCheckBox(
            merge_frame,
            text="Merge com playlist existente (adiciona apenas novas)",
            font=ctk.CTkFont(size=13),
            command=self.on_merge_selected,
            checkbox_width=22,
            checkbox_height=22,
            border_width=2
        )
        self.merge_cb.pack(anchor="w")

        # Lista de playlists do YT Music
        self.playlists_label = ctk.CTkLabel(
            self,
            text="Suas playlists no YouTube Music:",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.playlists_label.pack(anchor="w", padx=25, pady=(10, 5))

        self.playlist_scroll = ctk.CTkScrollableFrame(self, height=200)
        self.playlist_scroll.pack(fill="x", padx=20, pady=5)

        self.playlist_var = ctk.StringVar(value="")

        if not self.yt_playlists:
            ctk.CTkLabel(
                self.playlist_scroll,
                text="Nenhuma playlist encontrada",
                text_color="gray"
            ).pack(pady=20)
        else:
            for pl in self.yt_playlists:
                cb = ctk.CTkCheckBox(
                    self.playlist_scroll,
                    text=f"{pl['title']} ({pl.get('count', '?')} musicas)",
                    font=ctk.CTkFont(size=12),
                    command=lambda pid=pl['playlistId']: self.on_playlist_selected(pid),
                    checkbox_width=20,
                    checkbox_height=20,
                    border_width=2
                )
                cb.pack(anchor="w", pady=3)
                self.playlist_checkboxes.append((cb, pl['playlistId'], pl['title']))

        # Iniciar com playlists desabilitadas
        self.update_playlist_state()

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20, side="bottom")

        ctk.CTkButton(
            btn_frame, text="Cancelar", command=self.cancel,
            fg_color="gray40", hover_color="gray30", width=100
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Confirmar", command=self.submit,
            width=100
        ).pack(side="right")

    def on_new_selected(self):
        """Quando 'Criar nova' é selecionado."""
        if self.new_cb.get():
            self.merge_cb.deselect()
            self.choice_var.set("new")
            # Desmarcar todas as playlists
            for cb, _, _ in self.playlist_checkboxes:
                cb.deselect()
            self.update_playlist_state()

    def on_merge_selected(self):
        """Quando 'Merge' é selecionado."""
        if self.merge_cb.get():
            self.new_cb.deselect()
            self.choice_var.set("merge")
            self.update_playlist_state()
        else:
            # Se desmarcou merge, volta para new
            self.new_cb.select()
            self.choice_var.set("new")
            self.update_playlist_state()

    def on_playlist_selected(self, playlist_id):
        """Quando uma playlist é selecionada."""
        # Desmarcar outras playlists (apenas uma pode ser selecionada)
        for cb, pid, _ in self.playlist_checkboxes:
            if pid != playlist_id:
                cb.deselect()
            elif cb.get():
                self.playlist_var.set(playlist_id)
                # Marcar merge automaticamente
                self.merge_cb.select()
                self.new_cb.deselect()
                self.choice_var.set("merge")

        # Se nenhuma está selecionada, limpar
        any_selected = any(cb.get() for cb, _, _ in self.playlist_checkboxes)
        if not any_selected:
            self.playlist_var.set("")

    def update_playlist_state(self):
        """Atualiza estado visual das playlists (habilitado/desabilitado)."""
        is_merge = self.choice_var.get() == "merge"

        for cb, _, _ in self.playlist_checkboxes:
            if is_merge:
                cb.configure(state="normal", text_color=("gray10", "gray90"))
            else:
                cb.configure(state="disabled", text_color="gray50")
                cb.deselect()

    def submit(self):
        choice = self.choice_var.get()

        if choice == "merge":
            playlist_id = self.playlist_var.get()
            if not playlist_id:
                messagebox.showwarning("Aviso", "Selecione uma playlist para fazer merge")
                return
            # Encontrar o nome da playlist
            playlist_name = next((p['title'] for p in self.yt_playlists if p['playlistId'] == playlist_id), "")
            self.callback("merge", playlist_id, playlist_name)
        else:
            self.callback("new", None, None)

        self.destroy()

    def cancel(self):
        self.callback(None, None, None)
        self.destroy()


class SpotifyYTMusicApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Spotify CSV → YouTube Music Transfer")
        self.geometry("900x750")
        self.minsize(800, 650)

        self.ytm = None
        self.csv_files = []
        self.yt_playlists = []
        self.is_transferring = False
        self.cancel_transfer = False

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # === Header ===
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="Spotify CSV → YouTube Music",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left")

        # === Connection Frame ===
        conn_frame = ctk.CTkFrame(self)
        conn_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        conn_frame.grid_columnconfigure((0, 1), weight=1)

        # Spotify Import
        spotify_frame = ctk.CTkFrame(conn_frame)
        spotify_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.spotify_status = ctk.CTkLabel(spotify_frame, text="Nenhuma playlist", font=ctk.CTkFont(size=14))
        self.spotify_status.pack(side="left", padx=10)

        self.link_btn = ctk.CTkButton(spotify_frame, text="Link Spotify", command=self.import_spotify_link, width=100)
        self.link_btn.pack(side="right", padx=5, pady=5)

        self.csv_btn = ctk.CTkButton(spotify_frame, text="CSV", command=self.import_csv, width=60, fg_color="gray40")
        self.csv_btn.pack(side="right", padx=5, pady=5)

        # YouTube Music connection
        ytm_frame = ctk.CTkFrame(conn_frame)
        ytm_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.ytm_status = ctk.CTkLabel(ytm_frame, text="YouTube Music: Desconectado", font=ctk.CTkFont(size=14))
        self.ytm_status.pack(side="left", padx=10)

        self.ytm_btn = ctk.CTkButton(ytm_frame, text="Conectar YT Music", command=self.show_auth_options, width=140)
        self.ytm_btn.pack(side="right", padx=10, pady=5)

        # === Main Content - Tabview ===
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        self.tab_csv = self.tabview.add("Spotify")
        self.tab_ytm = self.tabview.add("YouTube Music")

        self.setup_csv_tab()
        self.setup_ytm_tab()

        # === Progress Section ===
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Pronto para transferir", font=ctk.CTkFont(size=12))
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.current_track_label = ctk.CTkLabel(progress_frame, text="", font=ctk.CTkFont(size=11), text_color="gray")
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
        self.transfer_btn.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="ew")

        # === Log Frame ===
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="Log", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.log_text = ctk.CTkTextbox(log_frame, height=100)
        self.log_text.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    def setup_csv_tab(self):
        """Configura a aba de CSVs."""
        self.tab_csv.grid_columnconfigure(0, weight=1)
        self.tab_csv.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self.tab_csv, fg_color="transparent")
        header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(header, text="Playlists do Spotify", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.clear_btn = ctk.CTkButton(header, text="Limpar", command=self.clear_list, width=80, fg_color="gray40", hover_color="gray30")
        self.clear_btn.pack(side="right")

        self.select_all_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(header, text="Selecionar Todas", variable=self.select_all_var, command=self.toggle_select_all).pack(side="right", padx=20)

        # Lista
        self.csv_scroll = ctk.CTkScrollableFrame(self.tab_csv)
        self.csv_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.csv_scroll.grid_columnconfigure(0, weight=1)

        self.playlist_checkboxes = []
        self.playlist_vars = []

        self.csv_placeholder = ctk.CTkLabel(
            self.csv_scroll,
            text="Importe playlists usando o botao 'Link Spotify'\nou CSV do Exportify (exportify.app)",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.csv_placeholder.grid(row=0, column=0, pady=50)

    def setup_ytm_tab(self):
        """Configura a aba do YouTube Music."""
        self.tab_ytm.grid_columnconfigure(0, weight=1)
        self.tab_ytm.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self.tab_ytm, fg_color="transparent")
        header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(header, text="Suas Playlists no YouTube Music", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.refresh_ytm_btn = ctk.CTkButton(header, text="Atualizar", command=self.load_ytm_playlists, width=100, state="disabled")
        self.refresh_ytm_btn.pack(side="right")

        # Lista
        self.ytm_scroll = ctk.CTkScrollableFrame(self.tab_ytm)
        self.ytm_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.ytm_scroll.grid_columnconfigure(0, weight=1)

        self.ytm_placeholder = ctk.CTkLabel(
            self.ytm_scroll,
            text="Conecte-se ao YouTube Music para ver suas playlists",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.ytm_placeholder.grid(row=0, column=0, pady=50)

    def log(self, message):
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def import_csv(self):
        filepaths = filedialog.askopenfilenames(
            title="Selecione arquivos CSV do Exportify",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~")
        )
        if not filepaths:
            return
        for filepath in filepaths:
            self.load_csv_file(filepath)
        self.display_csv_playlists()
        self.check_ready()

    def import_spotify_link(self):
        """Importa playlist via link do Spotify."""
        SpotifyLinkDialog(self, self.on_spotify_link)

    def on_spotify_link(self, link):
        """Callback quando link do Spotify é fornecido."""
        if not link:
            return

        # Extrair playlist ID
        playlist_id = self.extract_spotify_playlist_id(link)
        if not playlist_id:
            messagebox.showerror("Erro", "Link inválido. Use um link de playlist do Spotify.")
            return

        self.log(f"Importando playlist do Spotify...")
        self.link_btn.configure(state="disabled", text="Carregando...")

        def do_import():
            error_msg = None
            try:
                # Buscar dados da playlist via web scraping
                playlist_name, tracks = self.fetch_spotify_playlist(playlist_id)

                if not tracks:
                    raise ValueError("Não foi possível obter as músicas da playlist.\nVerifique se a playlist é pública.")

                # Adicionar à lista
                self.csv_files.append({
                    'name': playlist_name,
                    'filepath': None,
                    'tracks': tracks,
                    'tracks_total': len(tracks),
                    'target': None,
                    'target_name': None,
                    'source': 'spotify'
                })

                self.after(0, lambda n=playlist_name, t=len(tracks): self.log(f"Importado: {n} ({t} musicas)"))
                self.after(0, self.display_csv_playlists)
                self.after(0, self.check_ready)

            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: self.log(f"Erro ao importar: {msg}"))
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", f"Erro ao importar playlist:\n{msg}"))
            finally:
                self.after(0, lambda: self.link_btn.configure(state="normal", text="Link Spotify"))

        threading.Thread(target=do_import, daemon=True).start()

    def fetch_spotify_playlist(self, playlist_id):
        """Busca dados de uma playlist pública do Spotify usando o embed player."""
        tracks = []
        playlist_name = "Spotify Playlist"

        session = requests.Session()

        # Método 1: Usar o embed player do Spotify
        try:
            # O embed player carrega dados de playlists públicas
            embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://open.spotify.com/',
            }

            resp = session.get(embed_url, headers=headers, timeout=20)

            if resp.status_code == 200:
                html = resp.text

                # O embed contém dados JSON no HTML
                # Procurar por dados no script de inicialização
                data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*type="application/json">(.+?)</script>', html, re.DOTALL)
                if data_match:
                    try:
                        data = json.loads(data_match.group(1))
                        # Navegar pela estrutura do Next.js
                        props = data.get('props', {}).get('pageProps', {})

                        # Extrair nome da playlist
                        if 'state' in props:
                            state = props['state']
                            if 'data' in state and 'entity' in state['data']:
                                entity = state['data']['entity']
                                playlist_name = entity.get('name', playlist_name)

                                # Extrair tracks
                                trackList = entity.get('trackList', [])
                                for item in trackList:
                                    track_name = item.get('title', '')
                                    track_artists = item.get('subtitle', '')
                                    if track_name:
                                        tracks.append({'name': track_name, 'artists': track_artists})
                    except (json.JSONDecodeError, KeyError) as e:
                        self.after(0, lambda msg=str(e): self.log(f"Parse embed falhou: {msg}"))

                # Fallback: procurar padrões alternativos no HTML do embed
                if not tracks:
                    # Procurar por "title" e "subtitle" (format do embed)
                    pattern = r'"title"\s*:\s*"([^"]+)"\s*,\s*"subtitle"\s*:\s*"([^"]+)"'
                    matches = re.findall(pattern, html)
                    for title, subtitle in matches:
                        if title and len(title) > 1 and subtitle:
                            tracks.append({'name': title, 'artists': subtitle})

                    # Procurar nome da playlist
                    name_match = re.search(r'"name"\s*:\s*"([^"]{2,100})"[^}]*"type"\s*:\s*"playlist"', html)
                    if name_match:
                        playlist_name = name_match.group(1)

        except Exception as e:
            self.after(0, lambda msg=str(e): self.log(f"Embed falhou: {msg}"))

        # Método 2: Tentar página normal com scraping mais agressivo
        if not tracks:
            self.after(0, lambda: self.log("Tentando scraping da pagina..."))
            try:
                url = f"https://open.spotify.com/playlist/{playlist_id}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                resp = session.get(url, headers=headers, timeout=20)

                if resp.status_code == 200:
                    html = resp.text

                    # Tentar extrair do __NEXT_DATA__
                    next_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
                    if next_match:
                        try:
                            data = json.loads(next_match.group(1))
                            playlist_name, tracks = self._parse_next_data(data)
                        except:
                            pass

                    # Tentar application/ld+json (schema.org)
                    if not tracks:
                        ld_match = re.search(r'<script type="application/ld\+json">(.+?)</script>', html, re.DOTALL)
                        if ld_match:
                            try:
                                ld_data = json.loads(ld_match.group(1))
                                if ld_data.get('name'):
                                    playlist_name = ld_data['name']
                                for t in ld_data.get('track', []):
                                    name = t.get('name', '')
                                    artist = ''
                                    if 'byArtist' in t:
                                        ba = t['byArtist']
                                        if isinstance(ba, dict):
                                            artist = ba.get('name', '')
                                        elif isinstance(ba, list):
                                            artist = ", ".join([a.get('name', '') for a in ba])
                                    if name:
                                        tracks.append({'name': name, 'artists': artist})
                            except:
                                pass

            except Exception as e:
                self.after(0, lambda msg=str(e): self.log(f"Scraping falhou: {msg}"))

        # Método 3: oembed para nome
        if not playlist_name or playlist_name == "Spotify Playlist":
            try:
                oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/playlist/{playlist_id}"
                oembed_resp = session.get(oembed_url, timeout=10)
                if oembed_resp.status_code == 200:
                    playlist_name = oembed_resp.json().get('title', playlist_name)
            except:
                pass

        # Remover duplicatas
        if tracks:
            seen = set()
            unique = []
            for t in tracks:
                key = f"{t['name'].lower().strip()}|{t['artists'].lower().strip()}"
                if key not in seen:
                    seen.add(key)
                    unique.append(t)
            tracks = unique

        if not tracks:
            raise ValueError("Não foi possível encontrar dados da playlist.\nVerifique se a playlist é pública.")

        return playlist_name, tracks

    def _parse_next_data(self, data):
        """Tenta extrair dados do __NEXT_DATA__ do Spotify."""
        playlist_name = "Spotify Playlist"
        tracks = []

        # Navegar por diferentes estruturas possíveis
        def find_tracks(obj, depth=0):
            if depth > 10:
                return []
            found = []
            if isinstance(obj, dict):
                # Verificar se é um objeto de track
                if 'name' in obj and 'artists' in obj and isinstance(obj.get('artists'), list):
                    artists = ", ".join([a.get('name', '') for a in obj['artists'] if isinstance(a, dict)])
                    if obj['name'] and artists:
                        found.append({'name': obj['name'], 'artists': artists})

                # Continuar buscando em sub-objetos
                for key, value in obj.items():
                    found.extend(find_tracks(value, depth + 1))

            elif isinstance(obj, list):
                for item in obj:
                    found.extend(find_tracks(item, depth + 1))

            return found

        # Tentar encontrar o nome da playlist
        def find_playlist_name(obj, depth=0):
            if depth > 10:
                return None
            if isinstance(obj, dict):
                if obj.get('__typename') == 'Playlist' and 'name' in obj:
                    return obj['name']
                if 'playlist' in obj and isinstance(obj['playlist'], dict) and 'name' in obj['playlist']:
                    return obj['playlist']['name']
                for value in obj.values():
                    result = find_playlist_name(value, depth + 1)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_playlist_name(item, depth + 1)
                    if result:
                        return result
            return None

        name = find_playlist_name(data)
        if name:
            playlist_name = name

        tracks = find_tracks(data)

        # Remover duplicatas mantendo ordem
        seen = set()
        unique_tracks = []
        for t in tracks:
            key = f"{t['name']}|{t['artists']}"
            if key not in seen:
                seen.add(key)
                unique_tracks.append(t)

        return playlist_name, unique_tracks

    def extract_spotify_playlist_id(self, url):
        """Extrai o ID da playlist de um link do Spotify."""
        # https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
        # https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
        match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
        return match.group(1) if match else None

    def load_csv_file(self, filepath):
        try:
            tracks = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    track_name = row.get('Track Name', '')
                    artists = row.get('Artist Name(s)', '')
                    if track_name:
                        tracks.append({'name': track_name, 'artists': artists})

            if tracks:
                playlist_name = Path(filepath).stem
                self.csv_files.append({
                    'name': playlist_name,
                    'filepath': filepath,
                    'tracks': tracks,
                    'tracks_total': len(tracks),
                    'target': None,  # Será definido: 'new' ou {'merge': playlist_id}
                    'target_name': None
                })
                self.log(f"Carregado: {playlist_name} ({len(tracks)} musicas)")
            else:
                self.log(f"Aviso: Nenhuma musica encontrada em {Path(filepath).name}")
        except Exception as e:
            self.log(f"Erro ao carregar {Path(filepath).name}: {e}")

    def clear_list(self):
        self.csv_files = []
        self.display_csv_playlists()
        self.spotify_status.configure(text="Nenhuma playlist")
        self.check_ready()

    def display_csv_playlists(self):
        for widget in self.csv_scroll.winfo_children():
            widget.destroy()

        self.playlist_checkboxes = []
        self.playlist_vars = []

        if not self.csv_files:
            self.csv_placeholder = ctk.CTkLabel(
                self.csv_scroll,
                text="Importe playlists usando o botao 'Link Spotify'\nou CSV do Exportify (exportify.app)",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            self.csv_placeholder.grid(row=0, column=0, pady=50)
            self.spotify_status.configure(text="Nenhuma playlist")
            return

        for i, pl in enumerate(self.csv_files):
            var = ctk.BooleanVar(value=True)
            self.playlist_vars.append(var)

            frame = ctk.CTkFrame(self.csv_scroll)
            frame.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            frame.grid_columnconfigure(1, weight=1)

            cb = ctk.CTkCheckBox(frame, text="", variable=var, width=24)
            cb.grid(row=0, column=0, padx=(10, 5), pady=8)
            self.playlist_checkboxes.append(cb)

            name_label = ctk.CTkLabel(frame, text=pl['name'], font=ctk.CTkFont(size=14), anchor="w")
            name_label.grid(row=0, column=1, padx=5, pady=8, sticky="w")

            # Mostrar destino se definido
            target_text = f"{pl['tracks_total']} musicas"
            if pl.get('target') == 'merge' and pl.get('target_name'):
                target_text = f"→ Merge: {pl['target_name']}"
            elif pl.get('target') == 'new':
                target_text = f"→ Nova playlist"

            info_label = ctk.CTkLabel(frame, text=target_text, font=ctk.CTkFont(size=12), text_color="gray")
            info_label.grid(row=0, column=2, padx=5, pady=8, sticky="e")

            # Botão para escolher destino
            dest_btn = ctk.CTkButton(
                frame, text="Destino", width=70, height=28,
                command=lambda idx=i: self.choose_destination(idx),
                state="normal" if self.ytm else "disabled"
            )
            dest_btn.grid(row=0, column=3, padx=5, pady=8)

            remove_btn = ctk.CTkButton(
                frame, text="X", width=30, height=28,
                fg_color="gray40", hover_color="red",
                command=lambda idx=i: self.remove_playlist(idx)
            )
            remove_btn.grid(row=0, column=4, padx=5, pady=8)

        self.spotify_status.configure(text=f"{len(self.csv_files)} playlist(s)")

    def choose_destination(self, index):
        """Abre dialog para escolher destino da playlist."""
        if not self.ytm:
            messagebox.showwarning("Aviso", "Conecte-se ao YouTube Music primeiro")
            return

        csv_playlist = self.csv_files[index]

        def on_choice(action, playlist_id, playlist_name):
            if action is None:
                return
            if action == "new":
                self.csv_files[index]['target'] = 'new'
                self.csv_files[index]['target_name'] = None
                self.log(f"{csv_playlist['name']}: Nova playlist")
            else:  # merge
                self.csv_files[index]['target'] = 'merge'
                self.csv_files[index]['target_id'] = playlist_id
                self.csv_files[index]['target_name'] = playlist_name
                self.log(f"{csv_playlist['name']}: Merge com '{playlist_name}'")
            self.display_csv_playlists()

        PlaylistSelectDialog(self, csv_playlist, self.yt_playlists, on_choice)

    def remove_playlist(self, index):
        if 0 <= index < len(self.csv_files):
            removed = self.csv_files.pop(index)
            self.log(f"Removido: {removed['name']}")
            self.display_csv_playlists()
            self.check_ready()

    def toggle_select_all(self):
        select = self.select_all_var.get()
        for var in self.playlist_vars:
            var.set(select)

    def load_ytm_playlists(self):
        """Carrega playlists do YouTube Music."""
        if not self.ytm:
            return

        self.refresh_ytm_btn.configure(state="disabled", text="Carregando...")
        self.log("Carregando playlists do YouTube Music...")

        def do_load():
            try:
                playlists = self.ytm.get_library_playlists(limit=50)
                self.yt_playlists = playlists or []
                self.after(0, self.display_ytm_playlists)
                self.after(0, lambda: self.log(f"Encontradas {len(self.yt_playlists)} playlists no YouTube Music"))
            except Exception as e:
                self.after(0, lambda: self.log(f"Erro ao carregar playlists: {e}"))
            finally:
                self.after(0, lambda: self.refresh_ytm_btn.configure(state="normal", text="Atualizar"))

        threading.Thread(target=do_load, daemon=True).start()

    def display_ytm_playlists(self):
        """Exibe playlists do YouTube Music."""
        for widget in self.ytm_scroll.winfo_children():
            widget.destroy()

        if not self.yt_playlists:
            ctk.CTkLabel(
                self.ytm_scroll,
                text="Nenhuma playlist encontrada",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            ).grid(row=0, column=0, pady=50)
            return

        for i, pl in enumerate(self.yt_playlists):
            frame = ctk.CTkFrame(self.ytm_scroll)
            frame.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            frame.grid_columnconfigure(0, weight=1)

            name_label = ctk.CTkLabel(frame, text=pl.get('title', 'Sem nome'), font=ctk.CTkFont(size=14), anchor="w")
            name_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

            count = pl.get('count', '?')
            info_label = ctk.CTkLabel(frame, text=f"{count} musicas", font=ctk.CTkFont(size=12), text_color="gray")
            info_label.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        # Atualizar botões de destino nos CSVs
        self.display_csv_playlists()

    # === Autenticação ===

    def show_auth_options(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Escolha o método de autenticação")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.after(100, dialog.grab_set)

        ctk.CTkLabel(dialog, text="Como deseja conectar ao YouTube Music?", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)

        if os.path.exists('oauth.json'):
            ctk.CTkButton(dialog, text="Usar credenciais salvas (oauth.json)", command=lambda: self.use_existing_oauth(dialog), width=300).pack(pady=5)

        if os.path.exists('browser_headers.json'):
            ctk.CTkButton(dialog, text="Usar headers salvos", command=lambda: self.use_existing_headers(dialog), width=300).pack(pady=5)

        ctk.CTkButton(dialog, text="OAuth (Google Cloud Console)", command=lambda: self.show_oauth_dialog(dialog), width=300).pack(pady=5)
        ctk.CTkButton(dialog, text="Browser Headers (alternativo)", command=lambda: self.show_browser_auth(dialog), width=300).pack(pady=5)

    def use_existing_oauth(self, dialog):
        dialog.destroy()
        self.connect_with_file('oauth.json')

    def use_existing_headers(self, dialog):
        dialog.destroy()
        self.connect_with_file('browser_headers.json')

    def show_oauth_dialog(self, dialog):
        dialog.destroy()
        OAuthSetupDialog(self, self.on_oauth_credentials)

    def show_browser_auth(self, dialog):
        dialog.destroy()
        BrowserAuthDialog(self, self.on_browser_auth)

    def on_oauth_credentials(self, client_id, client_secret):
        if not client_id or not client_secret:
            return

        self.ytm_btn.configure(state="disabled", text="Conectando...")
        self.log("Iniciando autenticação OAuth...")

        def do_oauth():
            try:
                from ytmusicapi.setup import setup_oauth
                self.after(0, lambda: self.log("Abrindo navegador para login..."))
                setup_oauth(client_id=client_id, client_secret=client_secret, filepath='oauth.json', open_browser=True)
                self.ytm = YTMusic('oauth.json')
                self.after(0, self.on_ytmusic_connected)
            except Exception as e:
                self.after(0, lambda: self.log(f"Erro OAuth: {e}"))
                self.after(0, lambda: self.ytm_btn.configure(state="normal", text="Conectar YT Music"))

        threading.Thread(target=do_oauth, daemon=True).start()

    def on_browser_auth(self, curl_text):
        if not curl_text:
            return

        self.ytm_btn.configure(state="disabled", text="Conectando...")
        self.log("Processando headers do browser...")

        def do_browser_auth():
            try:
                headers = self.parse_curl_headers(curl_text)
                if not headers:
                    raise ValueError("Não foi possível extrair headers do cURL")

                with open('browser_headers.json', 'w') as f:
                    json.dump(headers, f, indent=2)

                self.ytm = YTMusic('browser_headers.json')
                self.after(0, self.on_ytmusic_connected)
            except Exception as e:
                self.after(0, lambda: self.log(f"Erro na autenticação: {e}"))
                self.after(0, lambda: self.ytm_btn.configure(state="normal", text="Conectar YT Music"))

        threading.Thread(target=do_browser_auth, daemon=True).start()

    def parse_curl_headers(self, curl_text):
        cookie_match = re.search(r"-H ['\"]Cookie:\s*([^'\"]+)['\"]", curl_text, re.IGNORECASE)
        if not cookie_match:
            cookie_match = re.search(r"-H 'Cookie: ([^']+)'", curl_text)

        if not cookie_match:
            self.after(0, lambda: self.log("Erro: Cookie nao encontrado no cURL"))
            return None

        cookie = cookie_match.group(1).strip()

        auth_match = re.search(r"-H ['\"]Authorization:\s*([^'\"]+)['\"]", curl_text, re.IGNORECASE)
        authorization = auth_match.group(1).strip() if auth_match else ""

        auth_user = "0"
        goog_auth_match = re.search(r"-H ['\"]X-Goog-AuthUser:\s*(\d+)['\"]", curl_text, re.IGNORECASE)
        if goog_auth_match:
            auth_user = goog_auth_match.group(1)

        ua_match = re.search(r"-H ['\"]User-Agent:\s*([^'\"]+)['\"]", curl_text, re.IGNORECASE)
        user_agent = ua_match.group(1).strip() if ua_match else "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"

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

        if authorization:
            headers["authorization"] = authorization

        self.after(0, lambda: self.log(f"Headers extraidos: Cookie=OK, Auth={'OK' if authorization else 'FALTA'}"))
        return headers

    def connect_with_file(self, filepath):
        self.ytm_btn.configure(state="disabled", text="Conectando...")
        self.log(f"Conectando com {filepath}...")

        def do_connect():
            try:
                self.ytm = YTMusic(filepath)
                self.after(0, self.on_ytmusic_connected)
            except Exception as e:
                self.after(0, lambda: self.log(f"Erro: {e}"))
                self.after(0, lambda: self.ytm_btn.configure(state="normal", text="Conectar YT Music"))

        threading.Thread(target=do_connect, daemon=True).start()

    def on_ytmusic_connected(self):
        self.ytm_status.configure(text="YouTube Music: Conectado")
        self.ytm_btn.configure(state="normal", text="Desconectar", command=self.disconnect_ytmusic)
        self.refresh_ytm_btn.configure(state="normal")
        self.log("Conectado ao YouTube Music!")
        self.load_ytm_playlists()
        self.check_ready()

    def disconnect_ytmusic(self):
        """Desconecta do YouTube Music para permitir reconexão."""
        self.ytm = None
        self.yt_playlists = []
        self.ytm_status.configure(text="YouTube Music: Desconectado")
        self.ytm_btn.configure(text="Conectar YT Music", command=self.show_auth_options)
        self.refresh_ytm_btn.configure(state="disabled")
        self.display_ytm_playlists()
        self.display_csv_playlists()  # Atualizar botões de destino
        self.check_ready()
        self.log("Desconectado do YouTube Music")

    def check_ready(self):
        if self.ytm and self.csv_files:
            self.transfer_btn.configure(state="normal")
        else:
            self.transfer_btn.configure(state="disabled")

    def get_selected_playlists(self):
        return [self.csv_files[i] for i, var in enumerate(self.playlist_vars) if var.get()]

    # === Transferência ===

    def start_transfer(self):
        selected = self.get_selected_playlists()

        if not selected:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma playlist para transferir.")
            return

        if not self.ytm:
            messagebox.showerror("Erro", "Conecte-se ao YouTube Music primeiro.")
            return

        self.is_transferring = True
        self.cancel_transfer = False
        self.transfer_btn.configure(text="Cancelar", command=self.cancel_transfer_operation, fg_color="red", hover_color="darkred")
        self.csv_btn.configure(state="disabled")
        self.link_btn.configure(state="disabled")

        for cb in self.playlist_checkboxes:
            cb.configure(state="disabled")

        threading.Thread(target=self.do_transfer, args=(selected,), daemon=True).start()

    def cancel_transfer_operation(self):
        """Cancela a operação de transferência em andamento."""
        self.cancel_transfer = True
        self.transfer_btn.configure(state="disabled", text="Cancelando...")
        self.log("Cancelando transferencia...")

    def do_transfer(self, playlists):
        total_playlists = len(playlists)
        was_cancelled = False

        for pl_idx, playlist in enumerate(playlists):
            # Verificar cancelamento
            if self.cancel_transfer:
                was_cancelled = True
                break

            self.after(0, lambda p=playlist: self.log(f"\n{'='*40}"))
            self.after(0, lambda p=playlist: self.log(f"Transferindo: {p['name']}"))

            tracks = playlist['tracks']

            if not tracks:
                self.after(0, lambda: self.log("Playlist vazia, pulando..."))
                continue

            # Verificar se é merge ou nova playlist
            is_merge = playlist.get('target') == 'merge'
            yt_playlist_id = playlist.get('target_id') if is_merge else None
            existing_tracks = set()

            if is_merge and yt_playlist_id:
                self.after(0, lambda n=playlist.get('target_name'): self.log(f"Modo: MERGE com '{n}'"))
                self.after(0, lambda: self.progress_label.configure(text="Carregando musicas existentes..."))

                # Carregar músicas existentes da playlist
                try:
                    yt_playlist = self.ytm.get_playlist(yt_playlist_id, limit=None)
                    if yt_playlist and 'tracks' in yt_playlist:
                        for track in yt_playlist['tracks']:
                            if track and track.get('title'):
                                # Normalizar para comparação
                                title = track['title'].lower().strip()
                                artists = ""
                                if track.get('artists'):
                                    artists = ", ".join([a['name'] for a in track['artists']]).lower().strip()
                                existing_tracks.add(f"{title}|{artists}")

                    self.after(0, lambda n=len(existing_tracks): self.log(f"Musicas existentes na playlist: {n}"))
                except Exception as e:
                    self.after(0, lambda e=e: self.log(f"Erro ao carregar playlist existente: {e}"))
            else:
                # Criar nova playlist
                self.after(0, lambda: self.log("Modo: NOVA PLAYLIST"))
                self.after(0, lambda: self.progress_label.configure(text="Criando playlist no YouTube Music..."))

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
            skipped = []
            total_tracks = len(tracks)

            for i, track in enumerate(tracks):
                # Verificar cancelamento
                if self.cancel_transfer:
                    was_cancelled = True
                    self.after(0, lambda f=len(found_videos): self.log(f"Cancelado. {f} musicas foram adicionadas antes do cancelamento."))
                    # Adicionar as músicas encontradas até agora
                    if found_videos:
                        try:
                            self.ytm.add_playlist_items(yt_playlist_id, found_videos)
                        except:
                            pass
                    break

                progress = (i + 1) / total_tracks
                self.after(0, lambda p=progress: self.progress_bar.set(p))
                self.after(0, lambda idx=i, total=total_tracks, plidx=pl_idx, pltotal=total_playlists:
                    self.progress_label.configure(text=f"Playlist {plidx + 1}/{pltotal} - Musica {idx + 1}/{total}")
                )
                self.after(0, lambda t=track: self.current_track_label.configure(text=f"{t['name']} - {t['artists']}"))

                # Verificar se já existe (para merge)
                if is_merge:
                    track_key = f"{track['name'].lower().strip()}|{track['artists'].lower().strip()}"
                    # Verificação mais flexível
                    already_exists = False
                    for existing in existing_tracks:
                        existing_title = existing.split('|')[0]
                        if track['name'].lower().strip() in existing_title or existing_title in track['name'].lower().strip():
                            already_exists = True
                            break

                    if already_exists:
                        skipped.append(f"{track['name']} - {track['artists']}")
                        continue

                video_id = self.search_song(track)

                if video_id:
                    found_videos.append(video_id)
                else:
                    not_found.append(f"{track['name']} - {track['artists']}")

                time.sleep(0.3)

            # Se foi cancelado, sair do loop de playlists
            if was_cancelled:
                break

            # Adicionar músicas à playlist
            if found_videos:
                self.after(0, lambda: self.current_track_label.configure(text="Adicionando musicas a playlist..."))

                try:
                    batch_size = 25
                    for i in range(0, len(found_videos), batch_size):
                        if self.cancel_transfer:
                            break
                        batch = found_videos[i:i + batch_size]
                        self.ytm.add_playlist_items(yt_playlist_id, batch)
                        time.sleep(1)
                except Exception as e:
                    self.after(0, lambda e=e: self.log(f"Erro ao adicionar musicas: {e}"))

            # Resumo
            summary = f"Adicionadas: {len(found_videos)}"
            if skipped:
                summary += f", Ja existiam: {len(skipped)}"
            if not_found:
                summary += f", Nao encontradas: {len(not_found)}"

            self.after(0, lambda s=summary: self.log(s))

            if not_found and len(not_found) <= 5:
                self.after(0, lambda n=not_found: self.log(f"  Nao encontradas: {', '.join(n)}"))

        self.after(0, lambda c=was_cancelled: self.on_transfer_complete(c))

    def search_song(self, track):
        query = f"{track['name']} {track['artists']}"
        try:
            results = self.ytm.search(query, filter='songs', limit=1)
            if results:
                return results[0].get('videoId')
        except Exception:
            pass
        return None

    def on_transfer_complete(self, was_cancelled=False):
        self.is_transferring = False
        self.cancel_transfer = False
        self.transfer_btn.configure(
            state="normal",
            text="Transferir Playlists Selecionadas",
            command=self.start_transfer,
            fg_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("#36719F", "#144870")
        )
        self.csv_btn.configure(state="normal")
        self.link_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.current_track_label.configure(text="")

        for cb in self.playlist_checkboxes:
            cb.configure(state="normal")

        self.log("\n" + "="*40)

        if was_cancelled:
            self.progress_label.configure(text="Transferencia cancelada")
            self.log("Transferencia cancelada pelo usuario")
            messagebox.showinfo("Cancelado", "Transferencia cancelada.\nAs musicas ja adicionadas permanecem nas playlists.")
        else:
            self.progress_label.configure(text="Transferencia concluida!")
            self.log("Transferencia concluida!")
            messagebox.showinfo("Concluido", "Transferencia de playlists concluida!\nVerifique o log para detalhes.")

        # Recarregar playlists do YT Music
        self.load_ytm_playlists()


def main():
    app = SpotifyYTMusicApp()
    app.mainloop()


if __name__ == '__main__':
    main()
