from django.db import models
from django.contrib.auth.models import User
from django_extensions.db.fields import AutoSlugField
import djtest4.settings as settings
# Create your models here.

# AUTH_TYPE_CHOICES = (
#                      ('ANON', 'ANONYMOUS'),
#                      ('OPTIONAL', 'OPTIONAL'),
#                      ('REQUIRED', 'REQUIRED'),
#                      
#                      
#                      
#                      )


#survey has only one question for now, but could have more at a later point


class MultipleChoiceSurvey(models.Model):
    create_date = models.DateTimeField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    #auth_type = models.CharField(choices=AUTH_TYPE_CHOICES)
    
    
    def __unicode__(self):
        return "Survey from %s" % self.create_date.__str__()
    
    pass

class MultipleChoiceQuestion(models.Model):
    qtext = models.CharField(blank=False,max_length=500)
    linked_survey = models.ForeignKey(MultipleChoiceSurvey)
    slug = AutoSlugField(populate_from='qtext')
    #newfield = models.TextField()
    pass

#a single multiple choice answer choice
#usually there will be 2-5 options but in theory can have unlimited

class MultipleChoiceAnswerItem(models.Model):
    linked_question = models.ForeignKey(MultipleChoiceQuestion)
    ans_text = models.TextField(blank=False,max_length=80)
    slug = AutoSlugField(populate_from='ans_text')
    shortcut_url = models.URLField(blank=True)
    
    class Meta:
        ordering=['id']
    #xtra = models.CharField(max_length=20)
    

#represents a publishing of the survey to Facebook or to an email or for testing purposes, to a URL

class Publishing(models.Model):
    publish_date = models.DateTimeField()
    linked_survey = models.ForeignKey(MultipleChoiceSurvey)
    

class FacebookPublishing(Publishing):
    dummy_field = models.CharField(max_length=15)
    fb_post_id = models.CharField(max_length=100)
    
class UrlPublishing(Publishing):
    publish_url = models.URLField()

    
class EmailPublishing(Publishing):
    
    email_msg_body = models.TextField(max_length=1000)
    subject_line = models.CharField(max_length=250)

class EmailList(models.Model):
    linked_publishing = models.OneToOneField(EmailPublishing)

class EmailContact(models.Model):
    email_address = models.CharField(max_length=255)
    linked_email_list = models.ForeignKey(EmailList)


    




class MultipleChoiceResponse(models.Model):
    last_name = models.CharField(max_length=100) #for non-anonymous responses
    first_and_middle = models.CharField(max_length=100) # for non-anonymous responses
    ip_address = models.IPAddressField()
    response_time = models.DateTimeField()

class MultipleChoicePostedAnswer(models.Model):
    linked_answer = models.ForeignKey(MultipleChoiceAnswerItem)
    linked_response = models.ForeignKey(MultipleChoiceResponse)
    

class UserProfile(models.Model):
    linked_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    working_email = models.EmailField()

    