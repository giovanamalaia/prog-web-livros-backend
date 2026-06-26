# Livro - Backend API

Backend do projeto **Livro**, uma plataforma de troca de livros entre usuarios. Esta API foi desenvolvida em **Django** e **Django REST Framework**, sem HTML/CSS/JavaScript no backend, conforme a proposta do trabalho.

## Integrantes

- Giovana Malaia Pinheiro - 2312080
- Luana Pinho Bueno Pena - 2312082

## Links

- Repositorio do backend: https://github.com/giovanamalaia/prog-web-livros-backend
- Repositorio do frontend: https://github.com/giovanamalaia/prog-web-livros-frontend.git
- Site do backend/API: adicionar link publicado
- Site do frontend: adicionar link publicado
- Swagger: `/swagger/`
- Schema OpenAPI: `/api/schema/`
- Redoc: `/redoc/`

## Escopo do projeto

O sistema permite que usuarios cadastrem livros para troca, naveguem pelo catalogo, demonstrem interesse em livros de outros usuarios e gerenciem solicitacoes recebidas. Tambem ha uma lista separada de **desejos futuros**, para salvar livros que o usuario quer acompanhar sem enviar uma solicitacao de troca ao dono.

Funcionalidades principais:

- Cadastro, login e logout.
- Recuperacao de senha por e-mail.
- Redefinicao de senha para usuario logado por link enviado ao e-mail.
- Perfil com foto, estado e cidade.
- CRUD completo de livros.
- API REST para listar, consultar, cadastrar, editar e excluir livros.
- Interesses de troca com notificacoes para o dono do livro.
- Aceite e recusa de interesses.
- Lista de desejos futuros sem notificar o dono.
- Upload de capas de livros e fotos de perfil.
- Documentacao da API com Swagger e Redoc.

## Como rodar localmente

### 1. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar e-mail

Crie um arquivo `.env` na raiz do backend:

```env
EMAIL_USER=seu_email@gmail.com
EMAIL_PASSWORD=sua_senha_de_app
```

O envio de e-mail usa SMTP do Gmail. Para testes locais, utilize uma senha de aplicativo.

### 4. Aplicar migracoes

```bash
python manage.py migrate
```

### 5. Rodar servidor

```bash
python manage.py runserver
```

A API ficara disponivel em:

```text
http://127.0.0.1:8000/api/
```

## Principais endpoints

### Autenticacao e senha

- `POST /api/cadastro/`
- `POST /api/login/`
- `POST /api/logout/`
- `POST /api/senha/recuperar/`
- `POST /api/senha/redefinir-logado/`
- `POST /api/senha/confirmar/`

### Livros

- `GET /api/home/`
- `POST /api/adicionar-livro/`
- `GET /api/livro/<id>/`
- `POST /api/editar-livro/<id>/`
- `PUT /api/editar-livro/<id>/`
- `POST /api/excluir-livro/<id>/`
- `DELETE /api/excluir-livro/<id>/`

### Interesses de troca

- `GET /api/favoritos/`
- `POST /api/livro/<id>/interesse/`
- `DELETE /api/livro/<id>/interesse/excluir/`
- `GET /api/notificacoes/`
- `POST /api/interesse/<id>/aceitar/`
- `POST /api/interesse/<id>/recusar/`

### Desejos futuros

- `GET /api/desejos-futuros/`
- `POST /api/livro/<id>/desejo-futuro/`
- `DELETE /api/livro/<id>/desejo-futuro/excluir/`

## CRUD implementado

### Livro

- Create: cadastrar livro.
- Read: listar livros e consultar detalhe.
- Update: editar livro e status.
- Delete: excluir livro do proprio usuario.

### Interesse

- Create: demonstrar interesse em um livro.
- Read: listar interesses do usuario e notificacoes recebidas.
- Update: aceitar ou recusar interesse.
- Delete: remover interesse.

### Desejo futuro

- Create: salvar livro como desejo futuro.
- Read: listar desejos futuros.
- Delete: remover livro dos desejos futuros.

## Gerencia de usuario

- Endpoints protegidos exigem usuario autenticado.
- Cada usuario ve seus proprios livros, interesses e desejos futuros.
- O dono do livro pode editar/excluir seu livro e aceitar/recusar interesses recebidos.
- Um usuario nao pode demonstrar interesse nem salvar como desejo futuro o proprio livro.

## Manual de uso da API

1. Crie uma conta em `POST /api/cadastro/`.
2. Faca login em `POST /api/login/`.
3. Cadastre livros em `POST /api/adicionar-livro/`.
4. Consulte o catalogo em `GET /api/home/`.
5. Consulte detalhes em `GET /api/livro/<id>/`.
6. Use `POST /api/livro/<id>/interesse/` para demonstrar interesse real em troca.
7. Use `POST /api/livro/<id>/desejo-futuro/` para guardar um livro sem notificar o dono.
8. Consulte e teste os endpoints pelo Swagger em `/swagger/`.

## O que foi testado e funcionou

- Cadastro, login e logout.
- CRUD de livros com upload de capa.
- Listagem de livros por home, perfil e perfil publico.
- Detalhe do livro com foto do dono.
- Criacao e remocao de interesse.
- Notificacoes de interesse para o dono.
- Aceite e recusa de interesse.
- Lista de desejos futuros sem envio de notificacao ao dono.
- Recuperacao/redefinicao de senha por e-mail.
- Swagger e schema OpenAPI.
- `python manage.py check`.
- `python manage.py migrate`.

## O que nao funcionou ou exige atencao

- O envio de e-mails depende das variaveis `EMAIL_USER` e `EMAIL_PASSWORD`. Sem SMTP configurado, os fluxos de recuperacao de senha e notificacoes por e-mail podem falhar. Fora isso, tudo pareceu funcionar! 
