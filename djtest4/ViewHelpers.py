# functions that help the view functions
    
    
    
from decimal import Decimal
import json    
import datetime
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.core.validators import ValidationError, validate_email
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import Context
from django.shortcuts import HttpResponseRedirect, RequestContext, \
    render_to_response
from django.template.loader import get_template
import re
import requests
from django.db import DatabaseError, IntegrityError

from django.core.mail import EmailMultiAlternatives
from CustomExceptions import CustomAppError
from djtest4.MultipleChoice.FormHelpers import EmailListRegExes
from djtest4.MultipleChoice.models import MultipleChoiceQuestion, \
    MultipleChoiceSurvey, MultipleChoiceAnswerItem, MultipleChoicePostedAnswer, \
    MultipleChoiceResponse, EmailPublishing, EmailContact, EmailList, UserProfile
from collections import OrderedDict

import settings
from rq import Connection, Queue
from redis import Redis
import redis
from rq.decorators import job
from open_facebook.api import OpenFacebook

#global variables to access the RQ asynchronous stuff



#for debugging
# def authenticate_default(fn):
#     def wrapper(*args, **kwargs):
#         user=authenticate(username='mo', password='password')
#         kwargs['auth_user']=user
#         return fn( *args, **kwargs)
#     return wrapper


#from stackoverflow, get's ip from POST data
#actually not used anymore

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def GetIpAddress(request):
    return get_client_ip(request)


def QuestionNotExist(aQuestion):
    return aQuestion == None

def PageForQuestionNotExist(e):
    return DefaultErrorPage(an_exception=e)

def PageForAnswerNotExist(e):
    return DefaultErrorPage(an_exception=e)

def PageForIPAddrAlreadyVoted(theQuestion):
    return render_to_response('already_voted_page.html', {})

#after the user votes show a page containing results so far
def PageForUserResponseAccepted(theQuestion, theAnswer, theRequest, redirect_url):
    
    theAnswers = theQuestion.multiplechoiceansweritem_set.all()
    vote_tally,total_votes = GetVoteTally(theAnswers)
    
    is_published = (theQuestion.linked_survey.publishing_set.count() > 0)
    
    
    return render_to_response('register_user_response_success.html', {'theQuestion' : theQuestion, 'theAnswer' : theAnswer, 'answers' : theAnswers, 'is_published' : \
                                         is_published,  'is_results_page' : True, 'vote_tally' : json.dumps(vote_tally), 'total_votes': total_votes}, \
                              context_instance=RequestContext(theRequest))

#shows many kinds of error, generic
def DefaultErrorPage(an_exception=None, mesg=None):
    return render_to_response('default_error_page.html', {'exception': an_exception, 'message' : mesg})
    


# gets question from MultipleChoiceQuestions given the slug field
def GetQuestionFromSlug(aQuestionSlug):
    
    try:
        return MultipleChoiceQuestion.objects.get(slug=aQuestionSlug)
    except MultipleChoiceQuestion.DoesNotExist as e:
        raise CustomAppError([e], "Question does not exist or not uniquely identifiable by slug")
    except MultipleChoiceQuestion.MultipleObjectsReturned as e:
        raise CustomAppError([e], "Question does not exist or not uniquely identifiable by slug")
    
def GetAnswerFromSlug(anAnswerSlug):
    try:
        return MultipleChoiceAnswerItem.objects.get(slug=anAnswerSlug)
    except MultipleChoiceAnswerItem.DoesNotExist as e:
        raise CustomAppError([e], "Answer does not exist or not uniquely identifiable by slug")
    except MultipleChoiceAnswerItem.MultipleObjectsReturned as e:
        raise CustomAppError([e], "Answer does not exist or not uniquely identifiable by slug")

#check session state to see the user voted on the question already
def ThisPersonAlreadyResponded(request, theQuestion):
    return request.session.get('voted' + theQuestion.slug, 'NotVoted') == 'AlreadyVoted'

#sets the session to record that the user answered this question already
def SetPersonRespondedToQuestion(request, theQuestion):
    request.session['voted' + theQuestion.slug]='AlreadyVoted'

#not used anymore. was used to track IP addresses
def ThisIPAddressAlreadyResponded(theQuestion, source_ip_addr):
    
    existing_responses = MultipleChoicePostedAnswer.objects.filter(linked_answer__linked_question=theQuestion)
    
    existing_with_same_ip = existing_responses.filter(linked_response__ip_address=source_ip_addr)
    
    if (existing_with_same_ip):
        return True
    else:
        return False


#saves the user's vote to the DB
def RegisterUserResponse(theQuestion, theAnswer, source_ip_addr):
    
    new_response = MultipleChoiceResponse(ip_address = source_ip_addr, response_time = datetime.datetime.now(), last_name = '', first_and_middle = '')
    
    new_response.save()
    
    new_answer = MultipleChoicePostedAnswer(linked_response=new_response,linked_answer=theAnswer) 
    
    
    #FIX-ME: should be in a transaction probably
    
    new_answer.save()
    
#returns ASCII text for the Facebook post
def ConstructFBPostForQuestion(theQuestion, theAnswers):
    
    
    
    question_template = get_template('facebook_post_template.txt')
    
    context = Context({'theQuestion': theQuestion, 'theAnswers' : theAnswers})
    
    return question_template.render(context)

#returns ASCII text for facebook results posts
def ConstructFBResultsPostForQuestion(theQuestion):
    
    template = get_template('facebook_results_post_template.html')
    
    theAnswers = theQuestion.multiplechoiceansweritem_set.all()
    
    vote_tally_with_pct, total_votes = GetVoteTallyWithPercentages(theAnswers)
    
    context = Context({'theQuestion': theQuestion,  'vote_tally_with_pct' : vote_tally_with_pct, 'total_votes': total_votes, 'domain_with_port': settings.DOMAIN_USED_WITH_PROTOCOL_AND_PORT})
    
    return template.render(context)

#accesses BIT.ly via it's API and gets a shortcut url for a given 'long' url
def CreateShortcutUrl(src_url):
    
    payload = {'access_token' : settings.BITLY_TOKEN, 'longUrl' : src_url}
    resp=requests.get(settings.BITLY_SHORTEN_URL, params=payload)
    
    return resp.json()['data']['url']
    
#adds on a 'tag' field to a publishing object showing if it's a fb or email publishing
#useful when rendering the publishing history in templates
def AddPubType(a_publishing):
    
     a_publishing.pub_type = 'Facebook'
     try:
        a_publishing.facebookpublishing
    
     except Exception as e:
            
        a_publishing.pub_type = 'email'
     return
 
#when deleting a question, erase it's publishings from the DB as well
def DeleteRelatedPublishings(a_question):
     
     #this is inefficient for large #'s of records but we have only a few publishings 
     #per question most likely
     
     linked_survey = a_question.linked_survey
     linked_publishings = GetAllPublishings(linked_survey)
     for p in linked_publishings:
         p.delete() 
    
    
def GetAllPublishings(linked_survey):
    return linked_survey.publishing_set.all()
    
                                            
#called by ShowEmailForm to extract the email address list, message, and user email
#also creates the publishing objects in the DB
                                        
def ParseInputAndSaveModels(form, current_user, theQuestion):
    
    #1. Create an EmailPublishing object and then parse all the emails from the list and save them to Contacts model objects
    #2. save the e-mail message to the database
    #3. save the user's email address to his profile
    #4. 
    
    try:
        
        new_email_publishing = EmailPublishing(publish_date=datetime.datetime.now(), linked_survey=theQuestion.linked_survey, email_msg_body=form.cleaned_data['email_msg_body'], subject_line='Quick Question')
        new_email_list = EmailList()
        
        new_email_publishing.save()
        
        new_email_list.linked_publishing = new_email_publishing
        
        new_email_list.save()
        
        list_of_emails  = ExtractListOfEmails(form.cleaned_data['list_of_email_addr'])
        
        
        
        #TO-DO: This is inefficient. Bulk creates should be done with raw sql and one giant query, instead of one per contact.
    #     for em in list_of_emails:
    #         new_contact = EmailContact(email_address=em, linked_email_list = new_email_list)
    #         new_contact.save()
    #         
    #     
        
        email_obj_list = [ EmailContact(email_address = em, linked_email_list = new_email_list) for em in list_of_emails]
        
        EmailContact.objects.bulk_create(email_obj_list)
        
        try:
            user_prof=UserProfile.objects.get(linked_user__pk=current_user.pk)
        except UserProfile.DoesNotExist:
            user_prof = UserProfile()
            user_prof.linked_user = current_user
        
        user_prof.working_email = form.cleaned_data['user_email']
        
        user_prof.save()
    
    #need to add rollback/transaction here
    except (DatabaseError, IntegrityError) as e:
        return DefaultErrorPage(e, mesg="Could not process the email form due to a database error. Please try again later.")
    
    return {'publishing' : new_email_publishing, 'list_of_emails' : list_of_emails}

#uses regex to extract all emails
def ExtractListOfEmails(list_of_addr):
    
    email_list_regex=re.compile(EmailListRegExes.emails_for_extraction_with_find_all, re.VERBOSE | re.IGNORECASE)
    
    matches_iterator = re.finditer(email_list_regex, list_of_addr)
    
    matches_list = []
    
    contact_list = []
    
    for i in matches_iterator:
        matches_list.append(i)
        
    for elem in matches_list:
        contact_list.append(elem.groupdict('the_email')['the_email'])
    
    return contact_list
       
            


#if question is being published just now (not published yet), then 
#added shortcut urls via BIT.ly api
def CreateURLsForAnswersIfNeeded(question_slug, IsAlreadyPublished, theAnswers):
    if not IsAlreadyPublished:
        for ans in theAnswers:
            ans.shortcut_url = CreateShortcutUrl(settings.DOMAIN_USED_WITH_PROTOCOL_AND_PORT + reverse('RespondToQuestion', kwargs={'question_slug':question_slug, 'answer_slug':ans.slug}))
            ans.save()


#returns a txt and html email of the question
def ConstructEmailForQuestion(current_user, email_msg_body, theQuestion):
    
    
    #check is greater than one because we just created a publishing
    IsAlreadyPublished = (theQuestion.linked_survey.publishing_set.count() > 1)
    
    question_template = get_template('email_post_template.txt')
    question_html_template = get_template('email_post_template.html')
    theAnswers =theQuestion.multiplechoiceansweritem_set.all().order_by('pk')
    
    CreateURLsForAnswersIfNeeded(theQuestion.slug, IsAlreadyPublished, theAnswers)
    
    context = Context({'theQuestion': theQuestion, 'theAnswers' : theAnswers, 'current_user' : current_user, 'email_msg_body' : email_msg_body})
    
    txt_template = question_template.render(context)
    html_template = question_html_template.render(context)

    return [txt_template, html_template]

def ConstructQuestionEmailSubjectLine(current_user):
    return "%s %s has a quick question for you..." % (current_user.first_name, current_user.last_name)

#send the question via email
def SendQuestionViaEmail(publishing_and_list_of_emails_dict, current_user, form, theQuestion):
    
    publishing = publishing_and_list_of_emails_dict['publishing']
    list_of_emails = publishing_and_list_of_emails_dict['list_of_emails']
    
    
    email_msg_body = form.cleaned_data['email_msg_body']
    from_address = settings.FROM_EMAIL
    cc_email=form.cleaned_data['user_email']
    
    #add user so he gets a copy--change to a BCC when have time
    list_of_emails.append(cc_email)
    
    email_body_arr = ConstructEmailForQuestion(current_user, email_msg_body, theQuestion)
    subject = ConstructQuestionEmailSubjectLine(current_user)
    
    

    subject, from_email, to = subject, from_address, list_of_emails
    text_content = email_body_arr[0]
    html_content = email_body_arr[1]
    
    Send_Email(subject, from_email, to, text_content, html_content)
    
    return



def ConstructResultsEmailForQuestion(theQuestion, current_user, email_msg_body):
    
   
    
        #check is greater than one because we just created a publishing
    IsAlreadyPublished = (theQuestion.linked_survey.publishing_set.count() > 1)
    
    results_txt_template = get_template('email_results_template.txt')
    results_html_template = get_template('email_results_template.html')
    theAnswers =theQuestion.multiplechoiceansweritem_set.all()
    
    vote_tally_with_pct, total_votes = GetVoteTallyWithPercentages(theAnswers)
   
    
    context = Context({'theQuestion': theQuestion, 'theAnswers' : theAnswers, 'current_user' : current_user, 'email_msg_body' : email_msg_body,
                       'vote_tally_with_pct' : vote_tally_with_pct, 'total_votes': total_votes, 'domain_with_port': settings.DOMAIN_USED_WITH_PROTOCOL_AND_PORT})
    
    txt_template = results_txt_template.render(context)
    html_template = results_html_template.render(context)

    return [txt_template, html_template]

def ConstructResultsEmailSubjectLine(current_user, theQuestionText):
    return '%s %s has sent you survey results for the quick question %s' % (current_user.first_name, current_user.last_name,  '"' + 
                                                                      (theQuestionText[:50] +    '...' if len(theQuestionText) > 50 else theQuestionText) + '"')

#for debugging
def Send_Email_Helper(subject, from_email, to, text_content, html_content):
    return Send_Email(subject, from_email, to, text_content, html_content)
    

def Send_Email(subject, from_email, to, text_content, html_content):
    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def SendResultsViaEmail(theQuestion, current_user, form, list_of_emails):
    
    email_msg_body = form.cleaned_data['email_msg_body']
    from_address =  settings.FROM_EMAIL
    
    
    cc_email=form.cleaned_data['user_email']
    
    #add user so he gets a copy--change to a BCC when have time
    list_of_emails.append(cc_email)
    
    email_body_arr = ConstructResultsEmailForQuestion(theQuestion, current_user, email_msg_body)
    subject = ConstructResultsEmailSubjectLine(current_user, theQuestion.qtext)
    
    

    subject, from_email, to = subject, from_address, list_of_emails
    text_content = email_body_arr[0]
    html_content = email_body_arr[1]
    
    Send_Email(subject, from_email, to, text_content, html_content)
    
    return
 
#counts total votes and gets vote tally
def GetVoteTally(theAnswers):
    vote_tally = OrderedDict()
    total_votes = 0
    for ans in theAnswers:
        ans.vote_count = ans.multiplechoicepostedanswer_set.count()
        vote_tally[ans.ans_text] = ans.vote_count
        total_votes = total_votes + ans.vote_count
    return (vote_tally, total_votes)

#same as above but also makes percentages
def GetVoteTallyWithPercentages(theAnswers):
    vote_tally = []
    
    total_votes = 0 
    for ans in theAnswers:
        ans.vote_count = ans.multiplechoicepostedanswer_set.count()
        total_votes = total_votes + ans.vote_count
    
    for ans in theAnswers:
        vote_tally.append( { 'ans_text' : ans.ans_text, 'vote_count': ans.vote_count, 'vote_pct' : ((Decimal(ans.vote_count) / Decimal(total_votes if total_votes > 0 else 100)) * 100).quantize(Decimal('0.01'))})
    
    return vote_tally, total_votes

#not used anmore i think, for debugging
def formset_manual_clean(formset):
    
    try:
        formset.clean()
        
    except ValidationError as e:
        return e
    
    return None

#wrapper for RQ functionality
class QueueContainer(object):
    
    import os
    redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

    conn = redis.from_url(redis_url)
    redis_conn = conn
    the_queue = Queue(connection=redis_conn)
    
  
    
    
#asynch func that is called by RQ to post to facebook

@job('low', connection = QueueContainer.redis_conn, timeout=settings.DEFAULT_ASYNC_TIMEOUT)
def post_to_fb_async(access_token, msg):
    
    
    
    fb = OpenFacebook(access_token)
    
    fb.set("me/feed", message=msg)
    
