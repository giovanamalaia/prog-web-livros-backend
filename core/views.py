from django.http import JsonResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.db.models import Q, Case, When, Value, IntegerField
from django.core.mail import send_mail
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
import json

from .models import Livro, Interesse, Perfil
from .forms import RegistroForm, LoginForm, PerfilLocalizacaoForm, LivroForm

def check_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Usuário não autenticado.'}, status=401)
    return None

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
                'livros': list(livros_do_genero.values('id', 'titulo', 'autor', 'genero')[:10])
            })

    return JsonResponse({
        'status': 'success',
        'data': {
            'latest_books': list(latest_books.values('id', 'titulo', 'autor', 'genero')),
            'livros_perto': list(livros_perto.values('id', 'titulo', 'autor', 'genero')),
            'livros_por_genero': livros_por_genero,
        }
    })

@require_POST
def registro(request):
    estado_selecionado = request.POST.get('estado') or None
    form = RegistroForm(request.POST, estado_selecionado=estado_selecionado) 

    if form.is_valid():
        user = form.save()
        Perfil.objects.create(
            user=user,
            estado=form.cleaned_data['estado'],
            cidade=form.cleaned_data['cidade'],
        )
        auth_login(request, user)
        return JsonResponse({'status': 'success', 'message': _('Conta criada e login realizado com sucesso!')})
    
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@require_POST
def login(request):
    form = LoginForm(request, data=request.POST)
    if form.is_valid():
        auth_login(request, form.get_user())
        return JsonResponse({'status': 'success', 'message': _('Login realizado com sucesso!')})
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@require_POST
def logout(request):
    auth_logout(request)
    return JsonResponse({'status': 'success', 'message': _('Você saiu da sua conta.')})

@require_POST
def trocar_idioma(request):
    idioma = request.POST.get('language')
    idiomas_disponiveis = {codigo for codigo, _ in settings.LANGUAGES}
    
    if idioma in idiomas_disponiveis:
        translation.activate(idioma)
        if hasattr(request, 'session'):
            request.session['django_language'] = idioma
        
        response = JsonResponse({'status': 'success', 'idioma': idioma})
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, idioma)
        return response
    
    return JsonResponse({'status': 'error', 'message': 'Idioma inválido'}, status=400)

def configuracoes(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)

    if request.method == 'GET':
        return JsonResponse({
            'status': 'success',
            'data': {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'estado': perfil.estado,
                'cidade': perfil.cidade,
            }
        })

    if request.method == 'POST':
        estado_selecionado = request.POST.get('estado') or perfil.estado
        localizacao_form = PerfilLocalizacaoForm(request.POST, estado_selecionado=estado_selecionado)

        if not localizacao_form.is_valid():
            return JsonResponse({'status': 'error', 'errors': localizacao_form.errors}, status=400)

        novo_username = request.POST.get('username', user.username)
        novo_email = request.POST.get('email', user.email)

        if User.objects.filter(username=novo_username).exclude(id=user.id).exists():
            return JsonResponse({'status': 'error', 'message': _('Esse username já está em uso.')}, status=400)

        if User.objects.filter(email=novo_email).exclude(id=user.id).exists():
            return JsonResponse({'status': 'error', 'message': _('Esse e-mail já está cadastrado.')}, status=400)

        user.username = novo_username
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = novo_email
        user.save()

        perfil.estado = localizacao_form.cleaned_data.get('estado') or None
        perfil.cidade = localizacao_form.cleaned_data.get('cidade') or None

        if 'foto_perfil' in request.FILES:
            perfil.foto_perfil = request.FILES.get('foto_perfil')
        perfil.save()

        return JsonResponse({'status': 'success', 'message': _('Configurações salvas com sucesso!')})

def perfil_logado(request): 
    auth_error = check_auth(request)
    if auth_error: return auth_error

    meus_livros = list(Livro.objects.filter(dono=request.user).order_by('-data_adicao').values('id', 'titulo', 'autor', 'status'))
    return JsonResponse({'status': 'success', 'data': {'meus_livros': meus_livros}})

def perfil_publico(request, user_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        perfil_user = User.objects.get(id=user_id)
        livros_dono = list(Livro.objects.filter(dono=perfil_user).order_by('-data_adicao').values('id', 'titulo', 'autor', 'status'))
        return JsonResponse({
            'status': 'success',
            'data': {
                'username': perfil_user.username,
                'first_name': perfil_user.first_name,
                'livros': livros_dono
            }
        })
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Usuário não encontrado'}, status=404)

@require_POST
def adicionar_livro(request):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    form = LivroForm(request.POST, request.FILES, include_status=False)
    if form.is_valid():
        livro = form.save(commit=False)
        livro.dono = request.user
        livro.save()
        return JsonResponse({'status': 'success', 'message': _('Livro adicionado com sucesso!'), 'livro_id': livro.id})
    
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

def detalhe_livro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id)
    except Livro.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Livro não encontrado'}, status=404)

    meu_interesse = None
    if request.user != livro.dono:
        interesse_obj = Interesse.objects.filter(usuario=request.user, livro=livro).first()
        if interesse_obj:
            meu_interesse = interesse_obj.status

    return JsonResponse({
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
            'meu_interesse': meu_interesse
        }
    })

@require_POST
def excluir_livro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id, dono=request.user)
        livro.delete()
        return JsonResponse({'status': 'success', 'message': _('Livro excluído com sucesso!')})
    except Livro.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Livro não encontrado ou você não tem permissão'}, status=404)

@require_POST
def editar_livro(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id, dono=request.user)
    except Livro.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Livro não encontrado ou não pertence a você'}, status=404)

    status_anterior = livro.status
    form = LivroForm(request.POST, request.FILES, instance=livro, include_status=True)
    
    if form.is_valid():
        livro = form.save()
        if status_anterior != 'trocado' and livro.status == 'trocado':
            Interesse.objects.filter(livro=livro, status='pendente').update(status='recusado')

        return JsonResponse({'status': 'success', 'message': _('Livro atualizado com sucesso!')})
    
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@require_POST
def criar_interesse(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        livro = Livro.objects.get(id=livro_id)
    except Livro.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Livro não encontrado'}, status=404)

    if livro.dono == request.user:
        return JsonResponse({'status': 'error', 'message': _('Você não pode demonstrar interesse no seu próprio livro.')}, status=400)

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
        return JsonResponse({'status': 'success', 'message': _('Interesse registrado!')})
    
    return JsonResponse({'status': 'info', 'message': _('Você já demonstrou interesse nesse livro.')})

@require_POST
def excluir_interesse(request, livro_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    apagados, _ = Interesse.objects.filter(usuario=request.user, livro_id=livro_id).delete()
    if apagados:
        return JsonResponse({'status': 'success', 'message': 'Interesse removido.'})
    return JsonResponse({'status': 'error', 'message': 'Interesse não encontrado.'}, status=404)

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
        'livro_autor': i.livro.autor
    } for i in interesses]

    return JsonResponse({'status': 'success', 'data': interesses_data})

@require_POST
def aceitar_interesse(request, interesse_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        interesse = Interesse.objects.get(id=interesse_id, livro__dono=request.user)
    except Interesse.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Interesse não encontrado'}, status=404)

    interesse.status = 'aceito'
    interesse.save()

    livro = interesse.livro
    livro.status = 'reservado'
    livro.disponivel = False
    livro.save(update_fields=['status', 'disponivel'])

    return JsonResponse({'status': 'success', 'message': _('Interesse aceito! Contatos enviados por email.')})

@require_POST
def recusar_interesse(request, interesse_id):
    auth_error = check_auth(request)
    if auth_error: return auth_error

    try:
        interesse = Interesse.objects.get(id=interesse_id, livro__dono=request.user)
    except Interesse.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Interesse não encontrado'}, status=404)

    interesse.status = 'recusado'
    interesse.save()

    return JsonResponse({'status': 'success', 'message': _('Interesse recusado.')})


def custom_404(request, exception=None):
    return JsonResponse({
        'status': 'error', 
        'message': 'Recurso ou endpoint não encontrado.'
    }, status=404)

def custom_500(request):
    return JsonResponse({
        'status': 'error', 
        'message': 'Erro interno no servidor da API.'
    }, status=500)

def custom_403(request, exception=None):
    return JsonResponse({
        'status': 'error', 
        'message': 'Permissão negada.'
    }, status=403)

def custom_400(request, exception=None):
    return JsonResponse({
        'status': 'error', 
        'message': 'Requisição inválida.'
    }, status=400)