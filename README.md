# Spotify CSV to YouTube Music Transfer

Transfira suas playlists do Spotify para o YouTube Music usando arquivos CSV exportados do [Exportify](https://exportify.app).

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Funcionalidades

- Interface gráfica moderna (tema escuro)
- Importa múltiplos arquivos CSV de uma vez
- **Merge de playlists**: adiciona apenas músicas novas em playlists existentes
- Visualiza suas playlists do YouTube Music
- Busca automática das músicas no YouTube Music
- Cria playlists automaticamente ou faz merge com existentes
- Barra de progresso em tempo real
- Log detalhado das operações
- Relatório de músicas adicionadas, já existentes e não encontradas

## Pré-requisitos

- Python 3.10 ou superior
- Conta no YouTube Music

## Instalação

```bash
git clone https://github.com/seu-usuario/spotify-to-ytmusic.git
cd spotify-to-ytmusic
pip install -r requirements.txt
```

## Como Usar

### 1. Exportar playlists do Spotify

1. Acesse [exportify.app](https://exportify.app)
2. Faça login com sua conta Spotify
3. Clique em "Export" nas playlists desejadas
4. Salve os arquivos CSV

### 2. Executar o programa

```bash
python gui.py
```

### 3. Conectar ao YouTube Music

Clique em "Conectar YT Music" e escolha um método de autenticação:

#### Opção A: Browser Headers (Recomendado)

1. Abra [music.youtube.com](https://music.youtube.com) no navegador (logado)
2. Pressione F12 para abrir as Ferramentas de Desenvolvedor
3. Vá na aba "Network" (Rede)
4. Clique em qualquer música para gerar tráfego
5. Encontre uma requisição para `music.youtube.com`
6. Clique com botão direito > "Copy" > "Copy as cURL"
7. Cole no campo da aplicação

#### Opção B: OAuth (Google Cloud Console)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um novo projeto
3. Ative a "YouTube Data API v3"
4. Vá em "Credenciais" > "Criar credenciais" > "ID do cliente OAuth"
5. Tipo: "App para TV e dispositivos de entrada limitada"
6. Copie o Client ID e Client Secret para a aplicação

### 4. Importar e transferir

1. Clique em "Importar CSV(s)"
2. Selecione os arquivos CSV exportados do Exportify
3. Para cada playlist, clique em "Destino" para escolher:
   - **Nova playlist**: cria uma playlist nova no YouTube Music
   - **Merge**: selecione uma playlist existente para adicionar apenas as músicas que ainda não existem
4. Marque as playlists que deseja transferir
5. Clique em "Transferir Playlists Selecionadas"

### Modo Merge

O modo merge compara as músicas do CSV com as da playlist existente no YouTube Music e:
- Pula músicas que já existem na playlist
- Adiciona apenas as músicas novas
- Mostra um relatório detalhado no final

## Screenshots

### Tela Principal
```
┌─────────────────────────────────────────────────────────────┐
│  Spotify CSV → YouTube Music                                │
├─────────────────────────────────────────────────────────────┤
│  [Importar CSV(s)]              [Conectar YT Music]         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┬──────────────────┐                     │
│  │ CSV (Spotify)   │ YouTube Music    │                     │
│  ├─────────────────┴──────────────────┤                     │
│  │ Playlists CSV (Exportify)  [Todas] [Limpar]              │
│  │ ┌───────────────────────────────────────────────┐        │
│  │ │ ☑ MPB           → Merge: mpb      [Destino][X]│        │
│  │ │ ☑ Rock Anos 80  → Nova playlist   [Destino][X]│        │
│  │ │ ☑ Jazz Classics 38 músicas        [Destino][X]│        │
│  │ └───────────────────────────────────────────────┘        │
│  └──────────────────────────────────────────────────────────┤
├─────────────────────────────────────────────────────────────┤
│  Playlist 1/3 - Música 25/50                                │
│  ████████████████░░░░░░░░░░░░░░░░  50%                      │
│  Construção - Chico Buarque                                 │
├─────────────────────────────────────────────────────────────┤
│  [      Transferir Playlists Selecionadas      ]            │
├─────────────────────────────────────────────────────────────┤
│  Log                                                        │
│  Carregado: MPB (50 músicas)                                │
│  Conectado ao YouTube Music!                                │
└─────────────────────────────────────────────────────────────┘
```

### Dialog de Seleção de Destino
```
┌───────────────────────────────────────────────────────[X]───┐
│  CSV: mpb (4 músicas)                                       │
│                                                             │
│  Escolha o destino no YouTube Music:                        │
│                                                             │
│  [✓] Criar nova playlist                                    │
│  [ ] Merge com playlist existente (adiciona apenas novas)   │
│                                                             │
│  Suas playlists no YouTube Music:                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [ ] Liked Music (? músicas)                         │    │
│  │ [ ] ovo_bate_cabeça (237 músicas)                   │    │
│  │ [ ] Episodes for Later (? músicas)                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Cancelar]                              [Confirmar]        │
└─────────────────────────────────────────────────────────────┘
```

## Estrutura do Projeto

```
spotify-to-ytmusic/
├── gui.py              # Interface gráfica principal
├── requirements.txt    # Dependências Python
├── .gitignore          # Arquivos ignorados pelo Git
└── README.md           # Este arquivo
```

## Dependências

- [ytmusicapi](https://github.com/sigma67/ytmusicapi) - API não-oficial do YouTube Music
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Interface gráfica moderna

## Limitações

- Algumas músicas podem não ser encontradas no YouTube Music (diferenças de catálogo)
- A autenticação via browser headers expira após algum tempo (~2 anos)
- Rate limiting: há uma pausa entre buscas para evitar bloqueios

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## License

MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.
