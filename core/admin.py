from django.contrib import admin
from .models import Perfil, Livro, Interesse

class LivroAdmin(admin.ModelAdmin):
    readonly_fields = ('data_adicao',) # data de adição do livro
    list_display = ('titulo', 'autor', 'dono', 'status', 'data_adicao') 
    search_fields = ('titulo', 'autor') # permitindo filtrar por título e autor

admin.site.register(Perfil)
admin.site.register(Livro, LivroAdmin)
admin.site.register(Interesse)