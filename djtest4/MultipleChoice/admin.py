from django.contrib import admin
from djtest4.MultipleChoice.models import *
import djtest4.MultipleChoice
import inspect



admin.site.register(MultipleChoiceQuestion)
admin.site.register(MultipleChoiceAnswerItem)
admin.site.register(MultipleChoiceSurvey)

admin.site.register(Publishing)
admin.site.register(FacebookPublishing)
admin.site.register(UrlPublishing)
admin.site.register(MultipleChoiceResponse)
admin.site.register(MultipleChoicePostedAnswer)
