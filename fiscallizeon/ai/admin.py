from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db.models import Sum, Avg, Value

from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field

from .models import OpenAIQuery, AIModel, QuestionImprove





class OpenAIQueryResource(resources.ModelResource):
    user = Field(attribute='user__name')
    client = Field(attribute='client__name')
    ai_model = Field(attribute='ai_model__identifier')

    class Meta:
        model = OpenAIQuery
        fields = (
            'id',
            'created_at',
            'updated_at',
            'user_prompt',
            'gpt_model',
            'input_tokens',
            'output_tokens',
            'finish_reason',
            'prompt_category',
            'user',
            'client',
            'ai_model',
            'cost',
        )
        export_order = [
            'id',
            'created_at',
            'updated_at',
            'user_prompt',
            'gpt_model',
            'input_tokens',
            'output_tokens',
            'finish_reason',
            'prompt_category',
            'user',
            'client',
            'ai_model',
            'cost',
        ]


class TotalAveragesChangeList(ChangeList):
    fields_to_total = ['cost']

    def get_total_values(self, queryset):
        total =  OpenAIQuery()
        total.pk = None
        total.custom_alias_name = "Total"

        for field in self.fields_to_total:
            setattr(total, field, list(queryset.aggregate(Sum(field)).items())[0][1])

        return total

    # def get_average_values(self, queryset):
    #     average =  OpenAIQuery()
    #     average.pk = None
    #     average.custom_alias_name = "Média"

    #     for field in self.fields_to_total:
    #         setattr(average, field, list(queryset.aggregate(Avg(field)).items())[0][1])
    #     return average

    def get_results(self, request):
        super().get_results(request)

        total = self.get_total_values(self.queryset)
        # average = self.get_average_values(self.queryset)

        len(self.result_list) # force queryset evaluation

        self.result_list._result_cache.append(total)
        # self.result_list._result_cache.append(average)


@admin.register(QuestionImprove)
class QuestionImproveAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at')
    autocomplete_fields = ( 'question', 'topics', 'abilities', 'competences', 'applied_topics', 'applied_abilities', 'applied_competences')

@admin.register(OpenAIQuery)
class OptionAnswerAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ('get_client', 'gpt_model', 'input_tokens', 'output_tokens', 'cost', 'user_prompt', 'created_at')
    list_filter = ('ai_model', 'gpt_model', 'created_at', 'client')
    search_fields = ('user_prompt',)
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('client', 'user', 'ai_model')
    resource_class = OpenAIQueryResource

    def get_changelist(self, request, **kwargs):
        return TotalAveragesChangeList

    def get_client(self, obj):
        if hasattr(obj, 'custom_alias_name'):
            return obj.custom_alias_name

        return obj.client

    get_client.short_description = 'Cliente'


@admin.register(AIModel)
class AIModelModelAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'input_price', 'output_price')
    search_fields = ('identifier',)
