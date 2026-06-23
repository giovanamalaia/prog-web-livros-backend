import random
import urllib.request
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from core.models import Livro

class Command(BaseCommand):
    help = 'Popula o banco de dados com 40 livros fictícios e capas aleatórias'

    def handle(self, *args, **kwargs):
        # usuário para ser o dono desses livros
        user, created = User.objects.get_or_create(
            username='biblioteca_central',
            defaults={'first_name': 'Biblioteca', 'email': 'bib@livro.com'}
        )
        if created:
            user.set_password('senha123')
            user.save()
            self.stdout.write(self.style.SUCCESS('Usuário "biblioteca_central" criado com sucesso.'))

        # nomes aleatorios
        titulos_parte1 = ['O Enigma', 'A Sombra', 'O Segredo', 'A Jornada', 'O Cântico', 'A Dança', 'O Império', 'A Lenda', 'O Vale', 'A Queda']
        titulos_parte2 = ['do Tempo', 'das Galáxias', 'de Fogo', 'Esquecido', 'das Sombras', 'do Rei', 'Invisível', 'de Gelo', 'Perdido', 'da Morte']
        
        autores_nomes = ['Ana', 'Carlos', 'Marina', 'Rafael', 'Julia', 'Lucas', 'Sofia', 'Pedro', 'Laura', 'Gabriel']
        autores_sobrenomes = ['Silva', 'Santos', 'Oliveira', 'Costa', 'Rodrigues', 'Ferreira', 'Alves', 'Gomes', 'Martins', 'Ribeiro']

        estados_possiveis = ['N', 'SN', 'U']
        
        generos_possiveis = [escolha[0] for escolha in Livro.GENERO_CHOICES]

        self.stdout.write('Iniciando a criação de 40 livros. Isso pode demorar cerca de 1 a 2 minutos por causa do download das capas...')

        livros_criados = 0

        # loop para criar 40 livros
        for i in range(40):
            titulo_gerado = f"{random.choice(titulos_parte1)} {random.choice(titulos_parte2)}"
            autor_gerado = f"{random.choice(autores_nomes)} {random.choice(autores_sobrenomes)}"
            estado_gerado = random.choice(estados_possiveis)
            genero_gerado = random.choice(generos_possiveis)

            # para evitar títulos iguais
            if not Livro.objects.filter(titulo=titulo_gerado).exists():
                livro = Livro(
                    titulo=titulo_gerado,
                    autor=autor_gerado,
                    estado=estado_gerado,
                    genero=genero_gerado,
                    dono=user
                )

                # imagens aletorias pra capa
                capa_url = f"https://picsum.photos/seed/livro_falso_{i}_{random.randint(1, 1000)}/400/600"

                try:
                    req = urllib.request.Request(
                        capa_url, 
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    resultado = urllib.request.urlopen(req)
                    
                    nome_arquivo = f"capa_fake_{i}.jpg"
                    livro.capa.save(nome_arquivo, ContentFile(resultado.read()), save=False)
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Erro ao baixar a capa: {e}"))

                livro.save()
                livros_criados += 1
                self.stdout.write(self.style.SUCCESS(f"[{livros_criados}/40] Livro '{livro.titulo}' criado!"))

        self.stdout.write(self.style.SUCCESS(f'🎉 Sucesso! {livros_criados} livros foram adicionados ao seu banco de dados.'))