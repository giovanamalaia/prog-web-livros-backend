from django.urls import path
from .views import (
    csrf, home, registro, login, logout, favoritos, notificacoes, perfil_logado, 
    perfil_publico, configuracoes, adicionar_livro, detalhe_livro, 
    editar_livro, excluir_livro, criar_interesse, excluir_interesse, 
    aceitar_interesse, recusar_interesse, solicitar_recuperacao_senha,
    confirmar_recuperacao_senha, trocar_idioma
)

urlpatterns = [
    # Autenticação
    path('csrf/', csrf, name='csrf'),
    path('login/', login, name='login'),
    path('cadastro/', registro, name='registro'),
    path('logout/', logout, name='logout'),
    path('senha/recuperar/', solicitar_recuperacao_senha, name='solicitar_recuperacao_senha'),
    path('senha/confirmar/', confirmar_recuperacao_senha, name='confirmar_recuperacao_senha'),

    # Feed / Home
    path('home/', home, name='home'),
    
    # Perfis e Configurações
    path('perfil/', perfil_logado, name='perfil'),
    path('perfil/<int:user_id>/', perfil_publico, name='perfil_publico'),
    path('configuracoes/', configuracoes, name='configuracoes'), 
    path('favoritos/', favoritos, name='favoritos'), 
    path('notificacoes/', notificacoes, name='notificacoes'),

    # CRUD de Livros
    path('adicionar-livro/', adicionar_livro, name='adicionar_livro'),
    path('livro/<int:livro_id>/', detalhe_livro, name='detalhe_livro'),
    path('editar-livro/<int:livro_id>/', editar_livro, name='editar_livro'),
    path('excluir-livro/<int:livro_id>/', excluir_livro, name='excluir_livro'),

    # Ações de Interesse (Match)
    path('livro/<int:livro_id>/interesse/', criar_interesse, name='criar_interesse'),
    path('livro/<int:livro_id>/interesse/excluir/', excluir_interesse, name='excluir_interesse'),
    path('interesse/<int:interesse_id>/aceitar/', aceitar_interesse, name='aceitar_interesse'),
    path('interesse/<int:interesse_id>/recusar/', recusar_interesse, name='recusar_interesse'),

    # Extras
    path('idioma/', trocar_idioma, name='trocar_idioma'),
]
