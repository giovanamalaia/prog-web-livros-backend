from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

ESTADO_UF_CHOICES = [
    ('AC', 'Acre'),
    ('AL', 'Alagoas'),
    ('AP', 'Amapá'),
    ('AM', 'Amazonas'),
    ('BA', 'Bahia'),
    ('CE', 'Ceará'),
    ('DF', 'Distrito Federal'),
    ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'),
    ('MA', 'Maranhão'),
    ('MT', 'Mato Grosso'),
    ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'),
    ('PA', 'Pará'),
    ('PB', 'Paraíba'),
    ('PR', 'Paraná'),
    ('PE', 'Pernambuco'),
    ('PI', 'Piauí'),
    ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'),
    ('RO', 'Rondônia'),
    ('RR', 'Roraima'),
    ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'),
    ('SE', 'Sergipe'),
    ('TO', 'Tocantins'),
]

# model de perfil 
class Perfil(models.Model): 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil') 
    
    estado = models.CharField(max_length=2, choices=ESTADO_UF_CHOICES, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True) 
    foto_perfil = models.ImageField(upload_to='fotos_perfil/', blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"
    

# model de livro
class Livro(models.Model):
    STATUS_CHOICES = [
        ('disponivel', _('Disponível')),
        ('reservado', _('Reservado')),
        ('trocado', _('Trocado')),
    ]
    ESTADO_CHOICES = [
        ('N', _('Novo')),
        ('SN', _('Semi-novo')),
        ('U', _('Usado')),
    ]
    GENERO_CHOICES = [
        ('ficcao_geral', _('Ficção Geral')),
        ('nao_ficcao_geral', _('Não Ficção Geral')),
        ('fantasia', _('Fantasia')),
        ('ficcao_cientifica', _('Ficção Científica')),
        ('romance', _('Romance')),
        ('misterio_suspense', _('Mistério & Suspense')),
        ('terror', _('Terror')),
        ('aventura', _('Aventura')),
        ('jovem_adulto', _('Jovem Adulto')),
        ('infantil', _('Infantil & Infanto-juvenil')),
        ('hq_manga', _('HQs, Mangás & Graphic Novels')),
        ('biografia', _('Biografia')),
        ('autoajuda', _('Autoajuda')),
        ('academico', _('Acadêmicos')),
        ('historia_politica', _('História & Política')),
        ('religiao', _('Religião & Espiritualidade')),
        ('classica', _('Literatura Clássica')),
        ('contemporanea', _('Literatura Contemporânea')),
        ('drama', _('Drama')),
        ('poesia', _('Poesia')),
        ('teatro', _('Teatro (Peças)')),
        ('outros', _('Outros')),
    ]

    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=200)
    estado = models.CharField(max_length=2, choices=ESTADO_CHOICES)

    genero = models.CharField(max_length=30, choices=GENERO_CHOICES, default='outros')

    capa = models.ImageField(upload_to='capas/', blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')
    dono = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livros')
    data_adicao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} por {self.autor}"

# model de interesse
class Interesse(models.Model):
    STATUS_CHOICES = [
        ('pendente', _('Pendente')),
        ('aceito', _('Aceito')),
        ('recusado', _('Recusado')),
    ]
    # quem quer o livro, qual livro e quando demonstrou interesse
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interesses')
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name='interessados')
    data = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    def __str__(self):
        return f"{self.usuario.username} tem interesse em {self.livro.titulo}"
    
