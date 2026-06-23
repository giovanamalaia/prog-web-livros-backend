from .models import Interesse

# Parte para trazer as notificações de interesses pendentes para o dono do livro

def notificacoes(request):
    if not request.user.is_authenticated:
        return {'notificacoes_interesses': []}

    qs = (Interesse.objects
          .filter(livro__dono=request.user, status='pendente')
          .select_related('usuario', 'livro')
          .order_by('-data')[:10])

    return {'notificacoes_interesses': qs}
