from django.urls import path
from .views import (
    home, registro, login, logout, favoritos, perfil_logado, 
    perfil_publico, configuracoes, adicionar_livro, detalhe_livro, 
    editar_livro, excluir_livro, criar_interesse, excluir_interesse, 
    aceitar_interesse, recusar_interesse, trocar_idioma
)

urlpatterns = [
    # Autenticação
    path('login/', login, name='login'),
    path('cadastro/', registro, name='registro'),
    path('logout/', logout, name='logout'),

    # Feed / Home
    path('home/', home, name='home'),
    
    # Perfis e Configurações
    path('perfil/', perfil_logado, name='perfil'),
    path('perfil/<int:user_id>/', perfil_publico, name='perfil_publico'),
    path('configuracoes/', configuracoes, name='configuracoes'), 
    path('favoritos/', favoritos, name='favoritos'), 

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