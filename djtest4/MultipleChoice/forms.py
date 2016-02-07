

from django import forms
from django.forms.models import BaseModelFormSet, BaseInlineFormSet
from djtest4.MultipleChoice.models import MultipleChoiceQuestion, MultipleChoiceAnswerItem
from django.forms.widgets import TextInput
from djtest4.MultipleChoice.FormHelpers import *

class MultipleChoiceQuestionForm(forms.Form):
    error_css_class = 'error'
    required_css_class = 'required'
    qtext=forms.CharField(help_text="Please enter the question you want to ask:", max_length=500,  widget=forms.widgets.Textarea(attrs={'placeholder': 'type question here', 'class': 'inputwidget' }))
    
    
    
    
    
class MultipleChoiceQuestionModelForm(forms.ModelForm):
    class Meta:
        model = MultipleChoiceQuestion
        fields=['qtext']
    qtext=forms.CharField(max_length=500, required=True, help_text= 'Please enter the question you want to ask:',  error_messages={'required' : 'Please enter a question. '}, widget=forms.Textarea(attrs={'maxlength':500, 'placeholder': 'type question here'}))
        
        
class MultipleChoiceAnswerItemModelForm(forms.ModelForm):
    class Meta:
        model = MultipleChoiceAnswerItem
        fields = ['ans_text']
        widgets = { 'ans_text': TextInput(attrs={'maxlength':80, 'placeholder': 'type answer here'})}
        
class MultipleChoiceAnswerItemModelFormset(BaseInlineFormSet):
    
    def clean(self):
        super(MultipleChoiceAnswerItemModelFormset, self).clean()
        # example custom validation across forms in the formset
        
        #count number of non-null forms
        
        
        #net_filled_out_forms=len(self.initial_forms) + len([x for x in self.extra_forms if x.cleaned_data != {} ] ) -  ( len(self.deleted_forms) if hasattr(self, 'deleted_forms') else 0)
        
        
        #if (net_filled_out_forms < 2):
        #    raise forms.ValidationError("Please supply at least two choices for the answer.")
        
        
        not_empty_init_form = [f for f in self.initial_forms if IsNonEmptyForm(f) ]
        not_empty_extr_form = [f for f in self.extra_forms if IsNonEmptyForm(f) ]
        
        not_empty_init_form_cnt=len(not_empty_init_form)
        
        not_empty_extr_form_cnt=len(not_empty_extr_form)
        
        print not_empty_init_form_cnt
        print not_empty_extr_form_cnt
        
        
        
        total_non_empty_cnt = not_empty_init_form_cnt + not_empty_extr_form_cnt
        
        if (total_non_empty_cnt < 2):
            raise forms.ValidationError("Please supply at least two choices for the answer.")
        
        
        for f in self.initial_forms:
            if f.cleaned_data != {} and ('ans_text' in f.cleaned_data) and (f.cleaned_data['ans_text']).strip() == '' and (f.cleaned_data['DELETE'] == False):
                raise forms.ValidationError('Answer cannot only contain spaces. Please enter some text.')
        
        for f in self.extra_forms:
            if f.cleaned_data != {} and ('ans_text' in f.cleaned_data) and (f.cleaned_data['ans_text']).strip() == '' and (f.cleaned_data['DELETE'] == False):
                raise forms.ValidationError('Answer cannot only contain spaces. Please enter some text.')
        
        
#         NonEmptyForms = 0
#         
#         if len(self.forms) < 2:
#             raise forms.ValidationError("Please supply at least two choices for the answer.")
#         
#         for form in self.forms:
#             # your custom formset validation
#             if form['ans_text'].data != '':
#                 NonEmptyForms=NonEmptyForms+1
#         
#         if NonEmptyForms < 2:
#             raise forms.ValidationError("Please supply at least two choices for the answer.")
#         
        return
        
        
                
class EmailContactForm(forms.Form):
    
    list_of_email_addr=forms.CharField(label="Please enter a list of email addresses:", widget=forms.widgets.Textarea(attrs={'max_length': 1000, 'placeholder': 'type email addresses here',  'class': 'inputwidget' }))
    email_msg_body=forms.CharField(label="Please enter a message that will be shown before the question:",  max_length=1000,  widget=forms.widgets.Textarea(attrs={'max_length': 1000, 'placeholder': 'type email message here', 'class': 'inputwidget' }))  
    user_email=forms.EmailField(label="Please confirm your email address (so we can cc you):")
    
    def clean_list_of_email_addr(self):
        if not ValidateListOfEmailAddresses(self.cleaned_data['list_of_email_addr']):
            raise ValidationError('One or more of the email addresses is invalid, or perhaps you are missing newlines, commas or semicolons to separate the addresses. Please fix and try again.')
        return self.cleaned_data['list_of_email_addr']


    def clean_email_msg_body(self):
        if self.cleaned_data['email_msg_body'].strip() == '':
          raise ValidationError("Message cannot only have spaces. Please enter non-whitespace text.")
        
        return self.cleaned_data['email_msg_body']
    
class EmailResultsContactForm(forms.Form):
    
    list_of_email_addr=forms.CharField(label="Please Enter a list of email addresses:", widget=forms.widgets.Textarea(attrs={'max_length': 1000, 'placeholder': 'type email addresses here',  'class': 'inputwidget' }))
    email_msg_body=forms.CharField(label="Please enter a message that will be shown before the results:",  max_length=1000,  widget=forms.widgets.Textarea(attrs={'max_length': 1000, 'placeholder': 'type email message here', 'class': 'inputwidget' }))  
    user_email=forms.EmailField(label="Please confirm your email address (so we can cc you):")
    
    def clean_email_msg_body(self):
        if self.cleaned_data['email_msg_body'].strip() == '':
            raise ValidationError("Message cannot only have spaces. Please enter non-whitespace text.")
        return self.cleaned_data['email_msg_body']
    
    def clean_list_of_email_addr(self):
        if not ValidateListOfEmailAddresses(self.cleaned_data['list_of_email_addr']):
            raise ValidationError('One or more of the email addresses is invalid, or perhaps you are missing newlines, commas or semicolons to separate the addresses. Please fix and try again.')
        return self.cleaned_data['list_of_email_addr']

    