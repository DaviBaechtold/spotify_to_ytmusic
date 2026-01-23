# Spotify to YouTube Music Transfer

Transfira suas playlists do Spotify para o YouTube Music usando link direto ou arquivos CSV.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Funcionalidades

- **Importar via Link do Spotify**: cole o link da playlist e importe direto
- **Importar via CSV**: use arquivos CSV do [Exportify](https://exportify.app) como alternativa
- **Merge de playlists**: adiciona apenas musicas novas em playlists existentes
- **Cancelar transferencia**: cancele a qualquer momento, musicas ja adicionadas permanecem
- **Reconectar YouTube Music**: desconecte e reconecte facilmente se houver erros
- Visualiza suas playlists do YouTube Music
- Busca automatica das musicas no YouTube Music
- Cria playlists automaticamente ou faz merge com existentes
- Interface grafica moderna (tema escuro)
- Barra de progresso em tempo real
- Log detalhado das operacoes

## Pre-requisitos

- Python 3.10 ou superior
- Conta no YouTube Music

## Instalacao

```bash
git clone https://github.com/seu-usuario/spotify-to-ytmusic.git
cd spotify-to-ytmusic
pip install -r requirements.txt
```

## Como Usar

### 1. Executar o programa

```bash
python gui.py
```

### 2. Conectar ao YouTube Music

Clique em "Conectar YT Music" e escolha um metodo de autenticacao.

> Dica: Apos conectar, o botao vira "Desconectar". Use-o para reconectar caso ocorra algum erro de autenticacao.

#### Opcao A: Browser Headers (Recomendado)

1. Abra [music.youtube.com](https://music.youtube.com) no navegador (logado)
2. Pressione F12 para abrir as Ferramentas de Desenvolvedor
3. Va na aba "Network" (Rede)
4. Clique em qualquer musica para gerar trafego
5. Encontre uma requisicao para `music.youtube.com`
6. Clique com botao direito > "Copy" > "Copy as cURL"
7. Cole no campo da aplicacao

#### Opcao B: OAuth (Google Cloud Console)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um novo projeto
3. Ative a "YouTube Data API v3"
4. Va em "Credenciais" > "Criar credenciais" > "ID do cliente OAuth"
5. Tipo: "App para TV e dispositivos de entrada limitada"
6. Copie o Client ID e Client Secret para a aplicacao

### 3. Importar playlists do Spotify

Voce tem duas opcoes:

#### Opcao A: Link do Spotify (Recomendado)

1. Clique em "Link Spotify"
2. Cole o link da playlist publica (ex: `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`)
3. A playlist sera importada automaticamente

> Nota: Funciona apenas com playlists publicas. Nao precisa de conta de desenvolvedor.

#### Opcao B: CSV (Alternativa)

1. Acesse [exportify.app](https://exportify.app)
2. Faca login com sua conta Spotify
3. Clique em "Export" nas playlists desejadas
4. Clique em "CSV" na aplicacao e selecione os arquivos

### 4. Transferir

1. Para cada playlist, clique em "Destino" para escolher:
   - **Nova playlist**: cria uma playlist nova no YouTube Music
   - **Merge**: adiciona apenas as musicas que ainda nao existem
2. Marque as playlists que deseja transferir
3. Clique em "Transferir Playlists Selecionadas"
4. Durante a transferencia, o botao vira "Cancelar" (vermelho) - clique para interromper

> Nota: Ao cancelar, as musicas ja adicionadas permanecem na playlist.

### Modo Merge

O modo merge compara as musicas com as da playlist existente no YouTube Music e:
- Pula musicas que ja existem na playlist
- Adiciona apenas as musicas novas
- Mostra um relatorio detalhado no final

## Screenshots

### Tela Principal
```
+-------------------------------------------------------------+
|  Spotify CSV -> YouTube Music                               |
+-------------------------------------------------------------+
|  [CSV] [Link Spotify]          [Conectar/Desconectar]       |
+-------------------------------------------------------------+
|  +---------------------+---------------------+               |
|  | Spotify             | YouTube Music       |               |
|  +---------------------+---------------------+               |
|  | Playlists do Spotify        [Todas] [Limpar]             |
|  | +---------------------------------------------------+    |
|  | | [x] MPB           -> Merge: mpb      [Destino][X] |    |
|  | | [x] Rock Anos 80  -> Nova playlist   [Destino][X] |    |
|  | | [x] Jazz Classics 38 musicas         [Destino][X] |    |
|  | +---------------------------------------------------+    |
|  +----------------------------------------------------------+
+-------------------------------------------------------------+
|  Playlist 1/3 - Musica 25/50                                |
|  ================----------  50%                            |
|  Construcao - Chico Buarque                                 |
+-------------------------------------------------------------+
|  [  Transferir Playlists Selecionadas / Cancelar  ]         |
+-------------------------------------------------------------+
|  Log                                                        |
|  Importado: MPB (50 musicas)                                |
|  Conectado ao YouTube Music!                                |
+-------------------------------------------------------------+
```

## Estrutura do Projeto

```
spotify-to-ytmusic/
+-- gui.py              # Interface grafica principal
+-- requirements.txt    # Dependencias Python
+-- .gitignore          # Arquivos ignorados pelo Git
+-- README.md           # Este arquivo
```

## Dependencias

- [requests](https://github.com/psf/requests) - Para buscar dados de playlists do Spotify
- [ytmusicapi](https://github.com/sigma67/ytmusicapi) - API nao-oficial do YouTube Music
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Interface grafica moderna

## Limitacoes

- Links do Spotify funcionam apenas com playlists publicas
- Algumas musicas podem nao ser encontradas no YouTube Music (diferencas de catalogo)
- A autenticacao via browser headers expira apos algum tempo (~2 anos)
- Rate limiting: ha uma pausa entre buscas para evitar bloqueios

## Contribuindo

Contribuicoes sao bem-vindas! Sinta-se a vontade para abrir issues ou pull requests.

## License

MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.
