from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q, Case, When, Value, IntegerField
from django.core.mail import send_mail
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.shortcuts import get_object_or_404
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Livro, Interesse, Perfil, DesejoFuturo
from .forms import RegistroForm, LoginForm, PerfilLocalizacaoForm, LivroForm

def check_auth(request):
    if not request.user.is_authenticated:
        return Response({'status': 'error', 'message': 'Usuário não autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)
    return None

def livro_resumo(livro, request):
    return {
        'id': livro.id,
        'titulo': livro.titulo,
        'autor': livro.autor,
        'genero': livro.genero,
        'estado': livro.estado,
        'status': livro.status,
        'disponivel': livro.disponivel,
        'capa_url': request.build_absolute_uri(livro.capa.url) if livro.capa else None,
    }

def perfil_foto_url(perfil, request):
    if perfil and perfil.foto_perfil:
        return request.build_absolute_uri(perfil.foto_perfil.url)
    return None

def enviar_email_recuperacao_senha(user, frontend_url):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{frontend_url}/?reset=1&uid={uid}&token={token}"
    nome = user.first_name or user.username
    mensagem = (
        f"Olá {nome},\n\n"
        "Recebemos uma solicitação para redefinir sua senha no Livrô.\n\n"
        f"Acesse o link abaixo para criar uma nova senha:\n{reset_url}\n\n"
        "Se você não solicitou essa alteração, ignore este e-mail."
    )
    send_mail(
        'Recuperação de senha - Livrô',
        mensagem,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

@extend_schema(summary="Obter CSRF Token", tags=["Autenticação"])
@ensure_csrf_cookie
@api_view(['GET'])
def csrf(request):
    return Response({'status': 'success', 'csrfToken': get_token(request)}, status=status.HTTP_200_OK)

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
                'livros': [livro_resumo(livro, request) for livro in livros_do_genero[:10]]
            })

    return Response({
        'status': 'success',
        'data': {
            'latest_books': [livro_resumo(livro, request) for livro in latest_books],
            'livros_perto': [livro_resumo(livro, request) for livro in livros_perto],
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

@extend_schema(summary="Solicitar Recuperação de Senha", tags=["Autenticação"])
@api_view(['POST'])
def solicitar_recuperacao_senha(request):
    email = request.data.get('email', '').strip()
    frontend_url = request.data.get('frontend_url', 'http://127.0.0.1:5173').rstrip('/')

    if not email:
        return Response({'status': 'error', 'message': 'Informe o e-mail cadastrado.'}, status=status.HTTP_400_BAD_REQUEST)

    usuarios = User.objects.filter(email__iexact=email, is_active=True)

    for user in usuarios:
        enviar_email_recuperacao_senha(user, frontend_url)

    return Response({
        'status': 'success',
        'message': 'Se o e-mail estiver cadastrado, enviaremos um link de recuperação.'
    }, status=status.HTTP_200_OK)

@extend_schema(summary="Solicitar Redefinição de Senha do Usuário Logado", tags=["Configurações"])
@api_view(['POST'])
def solicitar_redefinicao_senha_logado(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    if not request.user.email:
        return Response({'status': 'error', 'message': 'Cadastre um e-mail antes de redefinir a senha.'}, status=status.HTTP_400_BAD_REQUEST)

    frontend_url = request.data.get('frontend_url', 'http://127.0.0.1:5173').rstrip('/')
    enviar_email_recuperacao_senha(request.user, frontend_url)
    return Response({'status': 'success', 'message': 'Enviamos um link de redefinição para o seu e-mail.'}, status=status.HTTP_200_OK)

@extend_schema(summary="Confirmar Nova Senha", tags=["Autenticação"])
@api_view(['POST'])
def confirmar_recuperacao_senha(request):
    uid = request.data.get('uid')
    token = request.data.get('token')
    senha = request.data.get('new_password1')
    confirmar_senha = request.data.get('new_password2')

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'status': 'error', 'message': 'Link de recuperação inválido.'}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({'status': 'error', 'message': 'Link de recuperação expirado ou inválido.'}, status=status.HTTP_400_BAD_REQUEST)

    form = SetPasswordForm(user, {
        'new_password1': senha,
        'new_password2': confirmar_senha,
    })

    if not form.is_valid():
        return Response({'status': 'error', 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

    form.save()
    return Response({'status': 'success', 'message': 'Senha alterada com sucesso. Faça login novamente.'}, status=status.HTTP_200_OK)

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
    perfil, perfil_criado = Perfil.objects.get_or_create(user=user)

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
                'foto_perfil_url': perfil_foto_url(perfil, request),
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

    perfil, perfil_criado = Perfil.objects.get_or_create(user=request.user)
    meus_livros = [livro_resumo(livro, request) for livro in Livro.objects.filter(dono=request.user).order_by('-data_adicao')]
    return Response({
        'status': 'success',
        'data': {
            'username': request.user.username,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'cidade': perfil.cidade,
            'foto_perfil_url': perfil_foto_url(perfil, request),
            'meus_livros': meus_livros
        }
    }, status=status.HTTP_200_OK)

@extend_schema(summary="Listar Perfil Público de Outro Usuário", tags=["Perfil"])
@api_view(['GET'])
def perfil_publico(request, user_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        perfil_user = User.objects.get(id=user_id)
        livros_dono = [livro_resumo(livro, request) for livro in Livro.objects.filter(dono=perfil_user).order_by('-data_adicao')]
        return Response({
            'status': 'success',
            'data': {
                'username': perfil_user.username,
                'first_name': perfil_user.first_name,
                'foto_perfil_url': perfil_foto_url(getattr(perfil_user, 'perfil', None), request),
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
        livro = Livro.objects.select_related('dono', 'dono__perfil').get(id=livro_id)
    except Livro.DoesNotExist:
        return Response({'status': 'error', 'message': 'Livro não encontrado'}, status=status.HTTP_404_NOT_FOUND)

    meu_interesse = None
    meu_desejo_futuro = False
    if request.user != livro.dono:
        interesse_obj = Interesse.objects.filter(usuario=request.user, livro=livro).first()
        if interesse_obj:
            meu_interesse = interesse_obj.status
        meu_desejo_futuro = DesejoFuturo.objects.filter(usuario=request.user, livro=livro).exists()

    return Response({
        'status': 'success',
        'data': {
            'id': livro.id,
            'titulo': livro.titulo,
            'autor': livro.autor,
            'genero': livro.genero,
            'status': livro.status,
            'disponivel': livro.disponivel,
            'estado': livro.estado,
            'capa_url': request.build_absolute_uri(livro.capa.url) if livro.capa else None,
            'dono_id': livro.dono.id,
            'dono_username': livro.dono.username,
            'dono_foto_perfil_url': perfil_foto_url(getattr(livro.dono, 'perfil', None), request),
            'is_owner': request.user == livro.dono,
            'meu_interesse': meu_interesse,
            'meu_desejo_futuro': meu_desejo_futuro
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
            nome_dono = livro.dono.first_name or livro.dono.username
            nome_interessado = request.user.username or request.user.first_name
            mensagem = _(
                "Olá %(nome_dono)s,\n\n"
                "O usuário %(nome_interessado)s acabou de demonstrar interesse em trocar o seu livro '%(titulo)s'.\n\n"
                "Acesse a plataforma para aceitar ou recusar a solicitação!\n\n"
                "Abraços,\n"
                "Equipe do Livrô"
            ) % {
                'nome_dono': nome_dono.title(),
                'nome_interessado': nome_interessado,
                'titulo': livro.titulo,
            }
            try:
                send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [livro.dono.email], fail_silently=False)
            except Exception as exc:
                print(f"Erro ao tentar enviar email: {exc}")
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

@extend_schema(summary="Adicionar Livro aos Desejos Futuros", tags=["Desejos Futuros"])
@api_view(['POST'])
def criar_desejo_futuro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id)
    except Livro.DoesNotExist:
        return Response({'status': 'error', 'message': 'Livro não encontrado'}, status=status.HTTP_404_NOT_FOUND)

    if livro.dono == request.user:
        return Response({'status': 'error', 'message': 'Você não pode adicionar seu próprio livro aos desejos futuros.'}, status=status.HTTP_400_BAD_REQUEST)

    _, criado = DesejoFuturo.objects.get_or_create(usuario=request.user, livro=livro)
    if criado:
        return Response({'status': 'success', 'message': 'Livro salvo nos desejos futuros.'}, status=status.HTTP_201_CREATED)
    return Response({'status': 'info', 'message': 'Este livro já está nos seus desejos futuros.'}, status=status.HTTP_200_OK)

@extend_schema(summary="Remover Livro dos Desejos Futuros", tags=["Desejos Futuros"])
@api_view(['POST', 'DELETE'])
def excluir_desejo_futuro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    apagados, _ = DesejoFuturo.objects.filter(usuario=request.user, livro_id=livro_id).delete()
    if apagados:
        return Response({'status': 'success', 'message': 'Livro removido dos desejos futuros.'}, status=status.HTTP_200_OK)
    return Response({'status': 'error', 'message': 'Desejo futuro não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(summary="Listar Desejos Futuros", tags=["Desejos Futuros"])
@api_view(['GET'])
def desejos_futuros(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    desejos = DesejoFuturo.objects.filter(usuario=request.user).select_related('livro').order_by('-data')
    q = request.GET.get('q', '').strip()

    if q:
        termos = [termo for termo in q.split() if termo]
        for termo in termos:
            desejos = desejos.filter(
                Q(livro__titulo__istartswith=termo) | Q(livro__titulo__icontains=f" {termo}") |
                Q(livro__autor__istartswith=termo) | Q(livro__autor__icontains=f" {termo}")
            )

    desejos_data = [{
        'id': desejo.id,
        'livro_id': desejo.livro.id,
        'livro_titulo': desejo.livro.titulo,
        'livro_autor': desejo.livro.autor,
        'livro_capa_url': request.build_absolute_uri(desejo.livro.capa.url) if desejo.livro.capa else None
    } for desejo in desejos]

    return Response({'status': 'success', 'data': desejos_data}, status=status.HTTP_200_OK)

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
        'livro_capa_url': request.build_absolute_uri(i.livro.capa.url) if i.livro.capa else None
    } for i in interesses]

    return Response({'status': 'success', 'data': interesses_data}, status=status.HTTP_200_OK)

@extend_schema(summary="Listar Notificações de Interesses Recebidos", tags=["Interesses"])
@api_view(['GET'])
def notificacoes(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    interesses = (
        Interesse.objects
        .filter(livro__dono=request.user, status='pendente')
        .select_related('usuario', 'livro')
        .order_by('-data')[:10]
    )

    data = [{
        'id': interesse.id,
        'usuario_id': interesse.usuario.id,
        'usuario_nome': interesse.usuario.first_name or interesse.usuario.username,
        'usuario_foto_perfil_url': perfil_foto_url(getattr(interesse.usuario, 'perfil', None), request),
        'livro_id': interesse.livro.id,
        'livro_titulo': interesse.livro.titulo,
        'data': interesse.data.isoformat(),
    } for interesse in interesses]

    return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)

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

    dono = interesse.livro.dono
    interessado = interesse.usuario
    nome_dono = dono.first_name or dono.username
    nome_interessado = interessado.first_name or interessado.username

    if dono.email:
        assunto_dono = _("Match! Você aceitou trocar: %(titulo)s") % {'titulo': livro.titulo}
        msg_dono = _(
            "Olá %(nome_dono)s,\n\n"
            "Você acabou de aceitar a solicitação de %(nome_interessado)s para o livro '%(titulo)s'.\n\n"
            "Para combinar a troca, entre em contato diretamente pelo e-mail:\n"
            "%(email)s\n\n"
            "Boas trocas!\n"
            "Equipe do Livrô"
        ) % {
            'nome_dono': nome_dono.title(),
            'nome_interessado': nome_interessado.title(),
            'titulo': livro.titulo,
            'email': interessado.email,
        }
        try:
            send_mail(assunto_dono, msg_dono, settings.DEFAULT_FROM_EMAIL, [dono.email], fail_silently=False)
        except Exception as exc:
            print(f"Erro ao enviar e-mail para o dono: {exc}")

    if interessado.email:
        assunto_interessado = _("Deu Match! Seu interesse em %(titulo)s foi aceito!") % {'titulo': livro.titulo}
        msg_interessado = _(
            "Olá %(nome_interessado)s,\n\n"
            "Ótimas notícias! O usuário %(nome_dono)s aceitou o seu interesse pelo livro '%(titulo)s'.\n\n"
            "Para combinar os detalhes da troca, mande um e-mail para:\n"
            "%(email)s\n\n"
            "Boas trocas!\n"
            "Equipe do Livrô"
        ) % {
            'nome_interessado': nome_interessado.title(),
            'nome_dono': nome_dono.title(),
            'titulo': livro.titulo,
            'email': dono.email,
        }
        try:
            send_mail(assunto_interessado, msg_interessado, settings.DEFAULT_FROM_EMAIL, [interessado.email], fail_silently=False)
        except Exception as exc:
            print(f"Erro ao enviar e-mail para o interessado: {exc}")

    return Response({'status': 'success', 'message': _('Interesse aceito! Os e-mails de contato foram enviados para os dois.')}, status=status.HTTP_200_OK)

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

    interessado = interesse.usuario
    livro = interesse.livro
    nome_interessado = interessado.first_name or interessado.username

    if interessado.email:
        assunto_interessado = _("Atualização sobre o livro: %(titulo)s") % {'titulo': livro.titulo}
        msg_interessado = _(
            "Olá %(nome_interessado)s,\n\n"
            "Infelizmente, o dono do livro '%(titulo)s' não pôde aceitar a sua solicitação de troca neste momento. "
            "O livro pode já ter sido prometido a outra pessoa.\n\n"
            "Não desanime! Continue explorando a plataforma para encontrar outras opções.\n\n"
            "Abraços,\n"
            "Equipe do Livrô"
        ) % {
            'nome_interessado': nome_interessado.title(),
            'titulo': livro.titulo,
        }
        try:
            send_mail(assunto_interessado, msg_interessado, settings.DEFAULT_FROM_EMAIL, [interessado.email], fail_silently=False)
        except Exception as exc:
            print(f"Erro ao enviar e-mail de recusa: {exc}")

    return Response({'status': 'success', 'message': _('O interesse foi recusado e o usuário foi notificado.')}, status=status.HTTP_200_OK)

from django.http import JsonResponse

def custom_404(request, exception=None):
    return JsonResponse({'status': 'error', 'message': 'Recurso ou endpoint não encontrado.'}, status=404)

def custom_500(request):
    return JsonResponse({'status': 'error', 'message': 'Erro interno no servidor da API.'}, status=500)

def custom_403(request, exception=None):
    return JsonResponse({'status': 'error', 'message': 'Permissão negada.'}, status=403)

def custom_400(request, exception=None):
    return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)
