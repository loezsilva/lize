class ClientIsObjectOwnerMixin:
    """
    Filtra objetos em que campo 'client' é igual ao client do usuário logado.
    Se o modelo não tiver 'client', retorna todos os objetos.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        model = queryset.model

        if hasattr(model, 'client'):
            if client := self.request.user.client:
                return queryset.filter(client=client)

        return queryset


class UserIsObjectOwnerMixin:
    """
    Filtra objetos em que campo 'user' é igual ao usuário logado.
    Se o modelo não tiver 'user', retorna todos os objetos.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        model = queryset.model

        if hasattr(model, 'user'):
            return queryset.filter(user=self.request.user)

        return queryset
    

class CreatedByIsObjectOwnerMixin:
    """
    Filtra objetos cujo campo 'created_by' é o usuário logado.
    Se o modelo não tiver 'created_by', retorna todos os objetos.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        model = queryset.model

        if hasattr(model, 'created_by'):
            return queryset.filter(created_by=self.request.user)

        return queryset
    

class SameCoordinationUsersOwnerMixin:
    """
    Filtra objetos cujo campo 'coordinations' inclui alguma coordenação do usuário atual.
    Se o modelo não tiver 'coordinations', retorna todos os objetos.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        model = queryset.model

        if hasattr(model, 'coordinations'):
            coordinations = self.request.user.get_coordinations_cache()
            return queryset.filter(coordinations__in=coordinations).distinct()

        return queryset
    