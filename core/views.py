from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.db.models import Q, Case, When, Value, IntegerField
from django.core.mail import send_mail
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Livro, Interesse, Perfil
from .forms import RegistroForm, LoginForm, PerfilLocalizacaoForm, LivroForm

def check_auth(request):
    if not request.user.is_authenticated:
        return Response({'status': 'error', 'message': 'Usuário não autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)
    return None

def _capa_url(request, livro):
    if livro.capa:
        return request.build_absolute_uri(livro.capa.url)
    return None

def _serialize_livro(request, livro):
    return {
        'id': livro.id,
        'titulo': livro.titulo,
        'autor': livro.autor,
        'genero': livro.genero,
        'status': livro.status,
        'capa_url': _capa_url(request, livro),
    }

@extend_schema(
    summary="Carregar Home",
    description="Retorna os livros disponíveis, agrupados por recentes, próximos e por gênero.",
    tags=["Home"],
    parameters=[OpenApiParameter(name='q', description='Termo de busca', required=False, type=OpenApiTypes.STR)]
)
@api_view(['GET'])
def home(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    livros_disponiveis = Livro.objects.filter(disponivel=True).exclude(dono=request.user)

    q = request.GET.get('q', '').strip()
    if q:
        termos = [termo for termo in q.split() if termo]
        for termo in termos:
            livros_disponiveis = livros_disponiveis.filter(
                Q(titulo__istartswith=termo) | Q(titulo__icontains=f" {termo}") |
                Q(autor__istartswith=termo) | Q(autor__icontains=f" {termo}")
            )
        latest_books = livros_disponiveis.order_by('-data_adicao')
    else:
        latest_books = livros_disponiveis.order_by('-data_adicao')[:20]

    livros_perto = Livro.objects.none()
    perfil_usuario = getattr(request.user, 'perfil', None)
    
    if perfil_usuario:
        estado_usuario = getattr(perfil_usuario, 'estado', None)
        cidade_usuario = getattr(perfil_usuario, 'cidade', None)
        
        if estado_usuario and cidade_usuario:
            livros_perto = (
                livros_disponiveis.filter(dono__perfil__estado=estado_usuario)
                .annotate(
                    mesma_cidade=Case(
                        When(dono__perfil__cidade=cidade_usuario, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                ).order_by('-mesma_cidade', '-data_adicao')[:20]
            )
        elif estado_usuario:
            livros_perto = livros_disponiveis.filter(dono__perfil__estado=estado_usuario).order_by('-data_adicao')[:20]

    livros_por_genero = []
    for slug_genero, nome_bonito in Livro.GENERO_CHOICES:
        livros_do_genero = livros_disponiveis.filter(genero=slug_genero).order_by('-data_adicao')
        if livros_do_genero.exists():
            livros_por_genero.append({
                'titulo_secao': nome_bonito.upper(),
                'livros': [_serialize_livro(request, l) for l in livros_do_genero[:10]]
            })

    return Response({
        'status': 'success',
        'data': {
            'latest_books': [_serialize_livro(request, l) for l in latest_books],
            'livros_perto': [_serialize_livro(request, l) for l in livros_perto],
            'livros_por_genero': livros_por_genero,
        }
    }, status=status.HTTP_200_OK)

@extend_schema(summary="Registrar Usuário", tags=["Autenticação"])
@api_view(['POST'])
def registro(request):
    estado_selecionado = request.data.get('estado') or None
    form = RegistroForm(request.data, estado_selecionado=estado_selecionado) 

    if form.is_valid():
        user = form.save()
        Perfil.objects.create(
            user=user,
            estado=form.cleaned_data['estado'],
            cidade=form.cleaned_data['cidade'],
        )
        auth_login(request, user)
        return Response({'status': 'success', 'message': _('Conta criada e login realizado com sucesso!')}, status=status.HTTP_201_CREATED)
    
    return Response({'status': 'error', 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(summary="Login de Usuário", tags=["Autenticação"])
@api_view(['POST'])
def login(request):
    form = LoginForm(request, data=request.data)
    if form.is_valid():
        auth_login(request, form.get_user())
        return Response({'status': 'success', 'message': _('Login realizado com sucesso!')}, status=status.HTTP_200_OK)
    return Response({'status': 'error', 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(summary="Logout", tags=["Autenticação"])
@api_view(['POST'])
def logout(request):
    auth_logout(request)
    return Response({'status': 'success', 'message': _('Você saiu da sua conta.')}, status=status.HTTP_200_OK)

@extend_schema(summary="Trocar Idioma", tags=["Configurações"])
@api_view(['POST'])
def trocar_idioma(request):
    idioma = request.data.get('language')
    idiomas_disponiveis = {codigo for codigo, _ in settings.LANGUAGES}
    
    if idioma in idiomas_disponiveis:
        translation.activate(idioma)
        if hasattr(request, 'session'):
            request.session['django_language'] = idioma
        
        response = Response({'status': 'success', 'idioma': idioma}, status=status.HTTP_200_OK)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, idioma)
        return response
    
    return Response({'status': 'error', 'message': 'Idioma inválido'}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(summary="Ver/Editar Configurações de Perfil", tags=["Configurações"])
@api_view(['GET', 'POST'])
def configuracoes(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)

    if request.method == 'GET':
        foto_perfil_url = request.build_absolute_uri(perfil.foto_perfil.url) if perfil.foto_perfil else None
        return Response({
            'status': 'success',
            'data': {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'estado': perfil.estado,
                'cidade': perfil.cidade,
                'foto_perfil_url': foto_perfil_url,
            }
        }, status=status.HTTP_200_OK)

    if request.method == 'POST':
        estado_selecionado = request.data.get('estado') or perfil.estado
        localizacao_form = PerfilLocalizacaoForm(request.data, estado_selecionado=estado_selecionado)

        if not localizacao_form.is_valid():
            return Response({'status': 'error', 'errors': localizacao_form.errors}, status=status.HTTP_400_BAD_REQUEST)

        novo_username = request.data.get('username', user.username)
        novo_email = request.data.get('email', user.email)

        if User.objects.filter(username=novo_username).exclude(id=user.id).exists():
            return Response({'status': 'error', 'message': _('Esse username já está em uso.')}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=novo_email).exclude(id=user.id).exists():
            return Response({'status': 'error', 'message': _('Esse e-mail já está cadastrado.')}, status=status.HTTP_400_BAD_REQUEST)

        user.username = novo_username
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = novo_email
        user.save()

        perfil.estado = localizacao_form.cleaned_data.get('estado') or None
        perfil.cidade = localizacao_form.cleaned_data.get('cidade') or None

        if 'foto_perfil' in request.FILES:
            perfil.foto_perfil = request.FILES.get('foto_perfil')
        perfil.save()

        return Response({'status': 'success', 'message': _('Configurações salvas com sucesso!')}, status=status.HTTP_200_OK)

@extend_schema(summary="Listar Livros do Usuário Logado", tags=["Perfil"])
@api_view(['GET'])
def perfil_logado(request): 
    auth_error = check_auth(request)
    if auth_error: return auth_error

    meus_livros = [_serialize_livro(request, l) for l in Livro.objects.filter(dono=request.user).order_by('-data_adicao')]
    return Response({'status': 'success', 'data': {'meus_livros': meus_livros}}, status=status.HTTP_200_OK)

@extend_schema(summary="Listar Perfil Público de Outro Usuário", tags=["Perfil"])
@api_view(['GET'])
def perfil_publico(request, user_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        perfil_user = User.objects.get(id=user_id)
        livros_dono = list(Livro.objects.filter(dono=perfil_user).order_by('-data_adicao').values('id', 'titulo', 'autor', 'status'))
        return Response({
            'status': 'success',
            'data': {
                'username': perfil_user.username,
                'first_name': perfil_user.first_name,
                'livros': livros_dono
            }
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'Usuário não encontrado'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(summary="Adicionar Novo Livro", tags=["Livros"])
@api_view(['POST'])
def adicionar_livro(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    form = LivroForm(request.data, request.FILES, include_status=False)
    if form.is_valid():
        livro = form.save(commit=False)
        livro.dono = request.user
        livro.save()
        return Response({'status': 'success', 'message': _('Livro adicionado com sucesso!'), 'livro_id': livro.id}, status=status.HTTP_201_CREATED)
    
    return Response({'status': 'error', 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(summary="Detalhes de um Livro Específico", tags=["Livros"])
@api_view(['GET'])
def detalhe_livro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id)
    except Livro.DoesNotExist:
        return Response({'status': 'error', 'message': 'Livro não encontrado'}, status=status.HTTP_404_NOT_FOUND)

    meu_interesse = None
    if request.user != livro.dono:
        interesse_obj = Interesse.objects.filter(usuario=request.user, livro=livro).first()
        if interesse_obj:
            meu_interesse = interesse_obj.status

    capa_url = _capa_url(request, livro)

    return Response({
        'status': 'success',
        'data': {
            'id': livro.id,
            'titulo': livro.titulo,
            'autor': livro.autor,
            'genero': livro.genero,
            'status': livro.status,
            'disponivel': livro.disponivel,
            'dono_id': livro.dono.id,
            'dono_username': livro.dono.username,
            'meu_interesse': meu_interesse,
            'capa_url': capa_url,
        }
    }, status=status.HTTP_200_OK)

@extend_schema(summary="Excluir Livro Próprio", tags=["Livros"])
@api_view(['POST', 'DELETE'])
def excluir_livro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id, dono=request.user)
        livro.delete()
        return Response({'status': 'success', 'message': _('Livro excluído com sucesso!')}, status=status.HTTP_200_OK)
    except Livro.DoesNotExist:
        return Response({'status': 'error', 'message': 'Livro não encontrado ou você não tem permissão'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(summary="Editar Livro Próprio", tags=["Livros"])
@api_view(['POST', 'PUT'])
def editar_livro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id, dono=request.user)
    except Livro.DoesNotExist:
        return Response({'status': 'error', 'message': 'Livro não encontrado ou não pertence a você'}, status=status.HTTP_404_NOT_FOUND)

    status_anterior = livro.status
    form = LivroForm(request.data, request.FILES, instance=livro, include_status=True)
    
    if form.is_valid():
        livro = form.save()
        if status_anterior != 'trocado' and livro.status == 'trocado':
            Interesse.objects.filter(livro=livro, status='pendente').update(status='recusado')

        return Response({'status': 'success', 'message': _('Livro atualizado com sucesso!')}, status=status.HTTP_200_OK)
    
    return Response({'status': 'error', 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(summary="Criar Interesse em um Livro", tags=["Interesses"])
@api_view(['POST'])
def criar_interesse(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id)
    except Livro.DoesNotExist:
        return Response({'status': 'error', 'message': 'Livro não encontrado'}, status=status.HTTP_404_NOT_FOUND)

    if livro.dono == request.user:
        return Response({'status': 'error', 'message': _('Você não pode demonstrar interesse no seu próprio livro.')}, status=status.HTTP_400_BAD_REQUEST)

    interesse, criado = Interesse.objects.get_or_create(
        usuario=request.user,
        livro=livro,
        defaults={'status': 'pendente'}
    )

    if criado:
        if livro.dono.email: 
            assunto = _("Boas notícias! Alguém quer seu livro: %(titulo)s") % {'titulo': livro.titulo}
            mensagem = _("Alguém demonstrou interesse no seu livro %(titulo)s. Acesse a plataforma!") % {'titulo': livro.titulo}
            try: send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [livro.dono.email], fail_silently=True)
            except Exception: pass
        return Response({'status': 'success', 'message': _('Interesse registrado!')}, status=status.HTTP_201_CREATED)
    
    return Response({'status': 'info', 'message': _('Você já demonstrou interesse nesse livro.')}, status=status.HTTP_200_OK)

@extend_schema(summary="Excluir Interesse Criado", tags=["Interesses"])
@api_view(['POST', 'DELETE'])
def excluir_interesse(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    apagados, _ = Interesse.objects.filter(usuario=request.user, livro_id=livro_id).delete()
    if apagados:
        return Response({'status': 'success', 'message': 'Interesse removido.'}, status=status.HTTP_200_OK)
    return Response({'status': 'error', 'message': 'Interesse não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(summary="Listar Livros Favoritados", tags=["Interesses"])
@api_view(['GET'])
def favoritos(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    interesses = Interesse.objects.filter(usuario=request.user).select_related('livro').order_by('-data')
    q = request.GET.get('q', '').strip()
    
    if q:
        termos = [termo for termo in q.split() if termo]
        for termo in termos:
            interesses = interesses.filter(
                Q(livro__titulo__istartswith=termo) | Q(livro__titulo__icontains=f" {termo}") |
                Q(livro__autor__istartswith=termo) | Q(livro__autor__icontains=f" {termo}")
            )

    interesses_data = [{
        'id': i.id,
        'status_interesse': i.status,
        'livro_id': i.livro.id,
        'livro_titulo': i.livro.titulo,
        'livro_autor': i.livro.autor,
        'livro_capa_url': _capa_url(request, i.livro),
    } for i in interesses]

    return Response({'status': 'success', 'data': interesses_data}, status=status.HTTP_200_OK)

@extend_schema(summary="Aceitar Interesse Recebido", tags=["Interesses"])
@api_view(['POST'])
def aceitar_interesse(request, interesse_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        interesse = Interesse.objects.get(id=interesse_id, livro__dono=request.user)
    except Interesse.DoesNotExist:
        return Response({'status': 'error', 'message': 'Interesse não encontrado'}, status=status.HTTP_404_NOT_FOUND)

    interesse.status = 'aceito'
    interesse.save()

    livro = interesse.livro
    livro.status = 'reservado'
    livro.disponivel = False
    livro.save(update_fields=['status', 'disponivel'])

    return Response({'status': 'success', 'message': _('Interesse aceito! Contatos enviados por email.')}, status=status.HTTP_200_OK)

@extend_schema(summary="Recusar Interesse Recebido", tags=["Interesses"])
@api_view(['POST'])
def recusar_interesse(request, interesse_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        interesse = Interesse.objects.get(id=interesse_id, livro__dono=request.user)
    except Interesse.DoesNotExist:
        return Response({'status': 'error', 'message': 'Interesse não encontrado'}, status=status.HTTP_404_NOT_FOUND)

    interesse.status = 'recusado'
    interesse.save()

    return Response({'status': 'success', 'message': _('Interesse recusado.')}, status=status.HTTP_200_OK)

from django.http import JsonResponse

def custom_404(request, exception=None):
    return JsonResponse({'status': 'error', 'message': 'Recurso ou endpoint não encontrado.'}, status=404)

def custom_500(request):
    return JsonResponse({'status': 'error', 'message': 'Erro interno no servidor da API.'}, status=500)

def custom_403(request, exception=None):
    return JsonResponse({'status': 'error', 'message': 'Permissão negada.'}, status=403)

def custom_400(request, exception=None):
    return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)