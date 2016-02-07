from collections import OrderedDict
import datetime
from utils import debugprint
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory, inlineformset_factory
from django.http import HttpResponse
from django.shortcuts import HttpResponseRedirect, RequestContext, \
    render_to_response
from django_facebook.decorators import facebook_required_lazy, facebook_required
import json
from django.db import DatabaseError, IntegrityError
from CustomExceptions import CustomAppError

import ViewHelpers
from djtest4.MultipleChoice.forms import MultipleChoiceQuestionForm, \
    MultipleChoiceQuestionModelForm, MultipleChoiceAnswerItemModelForm, \
    MultipleChoiceAnswerItemModelFormset, EmailContactForm, EmailResultsContactForm
from djtest4.MultipleChoice.models import MultipleChoiceQuestion, \
    MultipleChoiceAnswerItem, Publishing, FacebookPublishing, MultipleChoiceSurvey
import utils
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import permission_required
from utils import UserMustOwnThisQuestion, QuestionIsPublished,QuestionIsNotPublished
from django.views.generic import TemplateView
from djtest4.ViewHelpers import GetQuestionFromSlug, GetVoteTally, ConstructFBResultsPostForQuestion, PageForAnswerNotExist, \
PageForIPAddrAlreadyVoted, PageForQuestionNotExist, PageForUserResponseAccepted, GetIpAddress, GetAnswerFromSlug, RegisterUserResponse,\
    ThisPersonAlreadyResponded, SetPersonRespondedToQuestion, post_to_fb_async, AddPubType, ConstructFBPostForQuestion, ConstructFBResultsPostForQuestion,\
    DefaultErrorPage, DeleteRelatedPublishings, UserProfile, SendResultsViaEmail
#from ViewHelpers import *
from rq import Connection, Queue
from redis import Redis
import redis
from rq.decorators import job
import settings


from facebook_custom import custom_connect



#home page if logged in goes to the list-all-questions page
# if not logged in, to login page
@login_required
def home(request):
    return HttpResponseRedirect(reverse('ShowQuestionsList'))

    

@login_required
def AddQuestion(request, **kwargs):
    
    template = 'edit_question.html'
    
    theUser = request.user
    
    #inline formset is a good tool to use to get answers that have a foreign key to a question
    
    MultipleChoiceAnswerItemFormset = inlineformset_factory(MultipleChoiceQuestion, MultipleChoiceAnswerItem, form=MultipleChoiceAnswerItemModelForm,  formset=MultipleChoiceAnswerItemModelFormset, extra=2, can_delete=True)
    
    #POST means user has submitted the form with new question and answer options

    if request.method == 'POST':
        
        #prefix helps distinguish forms from each other
        form = MultipleChoiceQuestionModelForm(request.POST, prefix='Question')
        formset = MultipleChoiceAnswerItemFormset(request.POST, prefix='Answer')
        
        
        if form.is_valid() and formset.is_valid():
            
            
            
            
            try:
                #create new question but don't commit to DB yet as we have to 
                #create the survey object first as the question has a foreign key to the survey object
                
                new_question=form.save(commit=False)
                
                #create new survey, for now each question has a survey object. no more than 1 question per survey for now
                
                new_survey = MultipleChoiceSurvey(create_date= datetime.datetime.now(), author = theUser)
                new_survey.save()
                
                the_new_id = new_survey.id
                
                new_question.linked_survey = MultipleChoiceSurvey.objects.get(id=the_new_id)
                
                new_question.save()
                
                new_question_in_db = MultipleChoiceQuestion.objects.get(id=new_question.id)
                
                new_answers = formset.save(commit=False)
                
                
                for a in new_answers:
                    a.linked_question = new_question_in_db
                    a.save()
            
            #To-do: need to actually do a rollback of all changes here upon getting an unlikely DB error
            #should use Django's atomic.transaction probably
            except (DatabaseError, IntegrityError) as e:
                return DefaultErrorPage(e, "Your question could not be saved due to some problem with the database. Please try again later.")
            
            #redirect to ShowQuestionDetails when done adding a question
            return HttpResponseRedirect(reverse('ShowQuestionDetails', kwargs={'question_slug' : new_question_in_db.slug}))
        else:
        
             #if form is not valid, i.e. the new question has a problem, just rerender the form with errors
            return render_to_response(template, {'form': form, 'formset': formset,  'add_or_edit' : 'add'}, context_instance=RequestContext(request))
            
    
    # if method is GET show a blank form       
    else:
        form = MultipleChoiceQuestionModelForm(prefix='Question')
        formset = MultipleChoiceAnswerItemFormset(prefix='Answer')
    return render_to_response(template, {'form': form, 'formset': formset, 'add_or_edit': 'add'},
        context_instance=RequestContext(request))

@never_cache
@login_required
@UserMustOwnThisQuestion
def ShowQuestionDetails(request, question_slug=''):
    
 
    
    
    #parse GET parameters if any, i use them to post status messages about success of various operations to the user    
    just_published_on_FB = request.GET.get('just_published_on_FB', False)
    just_published_via_email = request.GET.get('just_published_via_email', False)
    just_published_results_on_FB = request.GET.get('just_published_results_on_FB', False)
    just_published_results_via_email = request.GET.get('just_published_results_via_email', False)
    fb_post_error = request.GET.get('fb_post_error', False)
    
    template = 'show_question_details.html'
    
    theQuestion = MultipleChoiceQuestion.objects.get(slug=question_slug)
    theAnswers = theQuestion.multiplechoiceansweritem_set.all().order_by('pk')
    
    #get total # of votes for this question so far, and which answer they voted for
    vote_tally,total_votes = GetVoteTally(theAnswers)
        
    #list of when this question was published to FB or via email, could be empty for non-published questions
    publishing_list = theQuestion.linked_survey.publishing_set.all().order_by('-publish_date')
    
    
    #if this question was published, note which type, either FB or email
    is_published = (len(publishing_list) > 0)
    
    for p in publishing_list:
        
       ViewHelpers.AddPubType(p)
    
    
    #note that the vote_tally is a json string that gets assigned to an element in the DOM
    # that google api can then use to render a pie chart
    
    return render_to_response(template, {'question' : theQuestion, 'answers' : theAnswers, 'is_published' : \
                                         is_published, 'just_published_on_FB' : just_published_on_FB, 'just_published_via_email' : just_published_via_email,  
                                         'just_published_results_on_FB' : just_published_results_on_FB, 'just_published_results_via_email' : just_published_results_via_email, 'fb_post_error' : fb_post_error, 
                                         'vote_tally' : json.dumps(vote_tally),  \
                              'publishing_list' : publishing_list, 'is_results_page' : False, 'total_votes': total_votes}, \
                              context_instance=RequestContext(request))

@login_required
@UserMustOwnThisQuestion
@QuestionIsNotPublished
def EditQuestion(request, question_slug='', **kwargs):

#def inline_formset(request, form_class, template):
    template = 'edit_question.html'
    
    MultipleChoiceAnswerItemFormset = inlineformset_factory(MultipleChoiceQuestion, MultipleChoiceAnswerItem,  form=MultipleChoiceAnswerItemModelForm, formset=MultipleChoiceAnswerItemModelFormset, extra=1, can_delete=True)
    theQuestion = MultipleChoiceQuestion.objects.get(slug=question_slug)
   
    # if POST the user submitted changes to the question. So validate and save to DB
    if request.method == 'POST':
        
        form = MultipleChoiceQuestionModelForm( request.POST, prefix="Question", instance=theQuestion)
        formset = MultipleChoiceAnswerItemFormset(request.POST, prefix="Answer", instance=theQuestion)
        
        is_question_form_valid = form.is_valid()
        is_answer_formset_valid = formset.is_valid()
        
        if is_question_form_valid and is_answer_formset_valid:
            
            try:
                form.save()
                formset.save()
            except (DatabaseError, IntegrityError) as e:
                return DefaultErrorPage(e, mesg="Could not save your changes to the question due to a database error. Try again later.")
            
            #redirect to the show the updated question
                
            return  HttpResponseRedirect(reverse('ShowQuestionDetails', kwargs={'question_slug' : question_slug}))
        else: #form is invalid, re-render form with errors
           
            return render_to_response(template, {'form': form, 'formset': formset, 'question': theQuestion, 'add_or_edit' : 'edit'}, context_instance=RequestContext(request))
    #handle GET
    #render the form
    else:
        form = MultipleChoiceQuestionModelForm(prefix="Question", instance=theQuestion)
        formset = MultipleChoiceAnswerItemFormset(prefix="Answer", instance=theQuestion)
    return render_to_response(template, {'form': form, 'formset': formset, 'question': theQuestion, 'add_or_edit': 'edit' },
        context_instance=RequestContext(request))

#this gets called via Ajax from the page rendered by the next view, RespondToQuestion
#this actually processes the user's vote 
#has no auth as anyone can vote if they have the link
def RegisterVote(request, question_slug='', answer_slug=''):

    try:
        theQuestion = GetQuestionFromSlug(question_slug)
    
    except CustomAppError as e:
        return PageForQuestionNotExist(e)
    try:
        theAnswer = GetAnswerFromSlug(answer_slug)
    
    except CustomAppError as e:
        return PageForAnswerNotExist(e)
    
    source_ip_addr = GetIpAddress(request)
    response_data = {}
    
    if settings.COOKIE_BLOCKING == 'True':
        if ThisPersonAlreadyResponded(request, theQuestion):
            response_data['result']='Denied'
            response_data['message']='you_already_voted'
            return HttpResponse(json.dumps(response_data), content_type="application/json")
    
    
    try:
        #actually save the user's vote to the DB
        RegisterUserResponse(theQuestion, theAnswer, source_ip_addr)
        SetPersonRespondedToQuestion(request, theQuestion)
        response_data['result'] = 'Success'
        response_data['message'] = 'Vote Registered for %s' % theAnswer.ans_text
        
    except Exception as e:
        response_data['result'] = 'failed'
        response_data['message'] = e.message

    return HttpResponse(json.dumps(response_data), content_type="application/json")
    

#this is for general anonymous users
#should have no auth, anyone can vote if given the link

def RespondToQuestion(request, question_slug='', answer_slug='', redirect_url = '', **kwargs ):
    
    #see if question is already answered by this IP address
    
    try:
        theQuestion = GetQuestionFromSlug(question_slug)
    
    except CustomAppError as e:
        return DefaultErrorPage(e, "Could not find the question you specified.")
    try:
        theAnswer = GetAnswerFromSlug(answer_slug)
    
    except CustomAppError as e:
        return DefaultErrorPage(e, "Could not find the answer you specified.")
    
    # turns out blocking by IP is not effective, you could block an entire house
    # as it will use the IP assigned by the ISP
    # instead we will use cookies
    
    #source_ip_addr = GetIpAddress(request)
    
    #turn OFF while developing...turn on later
    
    
    if settings.COOKIE_BLOCKING == 'True':
        if ThisPersonAlreadyResponded(request, theQuestion):
            return PageForIPAddrAlreadyVoted(theQuestion)
    
    #if we made it here, the user hasn't already replied. Return success
    #although actually the AJAX call this page makes will actually cause the vote to register
    #had to do that, as Heroku or FB or some non-humans were sending GET to this page
    #and registering votes which distorting the vote
    
    return PageForUserResponseAccepted(theQuestion, theAnswer, request, redirect_url)
    
#this is only for debugging purposes
# 
# def ShowPublishedQuestion(request, question_slug=''):
#     
#      
#     try:
#         theQuestion = GetQuestionFromSlug(question_slug)
#     
#     except CustomAppError as e:
#         return PageForQuestionNotExist(e)
#     
#     return render_to_response('show_published_question.html', {'question': theQuestion},  context_instance=RequestContext(request))
#     
#     


#This is the home page for people who are logged in.
#It shows all the questions the user has created in reverse chronological order of creation
@login_required
def ShowQuestionsList(request, **kwargs):
    
    #theUser = kwargs['auth_user']
    
    theUser = request.user
    just_deleted_question = request.GET.get('just_deleted_question', False)
    
    all_questions = MultipleChoiceQuestion.objects.filter(linked_survey__author__pk=theUser.pk).order_by('-linked_survey__create_date')
    
    for q in all_questions:
        q.pub_list = q.linked_survey.publishing_set.all().order_by('-publish_date')
        if q.pub_list.count() > 0:
            q.is_published = True
        else:
            q.is_published = False
        for p in q.pub_list:
            AddPubType(p)
    
    
    return render_to_response('show_all_questions.html', {'all_questions': all_questions, 'just_deleted_question' : just_deleted_question}, \
                                context_instance=RequestContext(request))

#this is the front page of the web site
#is has a button to log in using a facebook account
def LoginPage(request):
    
    theUser = request.user
    
    return render_to_response('LoginPage.html', {'theUser' : theUser},  context_instance=RequestContext(request))


@login_required   
def Logout(request):
    
    logout(request )
    return HttpResponseRedirect(reverse('LoginPage'))
    pass



#This view is called if the user decides to publish the question to facebook
#it will launch an asynchronous task via RQ to post to FB by passing it an access_token
# and the post text
#the facebook_required decorator created by django-facebook app, ensures we have the access token
# by prompting the user to authorize if necessary

@facebook_required_lazy(scope=['publish_actions'])
@login_required
@UserMustOwnThisQuestion
def PublishQuestionToFacebook(request, graph, question_slug=''):
    
#     debugprint('starting publish func: ' + str(datetime.datetime.now()))
#     debugprint('method=' + request.method)
#     
    
    #should never happen, but if we don't get a graph object passed in from the facebook decorator,
    #we must go back to the question page with an error
    if not graph:
        return utils.custom_redirect('ShowQuestionDetails', question_slug, fb_post_error=True)
    
    # skip exception handling here, the decorator already checked
    theQuestion = GetQuestionFromSlug(question_slug)
#     
    #first create a publishing object to represent that this question is now in 'published' state
    # and no longer be changed
    try:
        
        IsAlreadyPublished = (theQuestion.linked_survey.publishing_set.count() > 0)
        
        new_publishing = FacebookPublishing(linked_survey=theQuestion.linked_survey, publish_date = datetime.datetime.now(), dummy_field='dummy_data')
                
        new_publishing.save()
                
        #create bit.ly url's for the voting url's
        
        theAnswers = theQuestion.multiplechoiceansweritem_set.all().order_by('pk')
        
        ViewHelpers.CreateURLsForAnswersIfNeeded(question_slug, IsAlreadyPublished, theAnswers)
    
    #need to add rollback/transaction here, actually the whole view should be in a transaction
    #and rolled back if any problems
    except (DatabaseError, IntegrityError) as e:
        return DefaultErrorPage(e, mesg="There was a problem posting your question to facebook due to a database or other error. Please try again later.")
    
    fb_post_str = ConstructFBPostForQuestion(theQuestion,theAnswers)
    
#     debugprint('before call to post to FB ' + str(datetime.datetime.now()) + ' ' + request.method)
#     debugprint('method=' + request.method)
#     #result = graph.set('me/feed', message=fb_post_str)
    
    #creates an asynchronous task using RQ to post to Facebook passing it the access token
    # and post text
    try:
        asynch_post_job = ViewHelpers.post_to_fb_async.delay(graph.access_token, fb_post_str)
    except Exception as e:
        return utils.custom_redirect('ShowQuestionDetails', question_slug, fb_post_error=True)
#     debugprint('after call to post to FB ' + str(datetime.datetime.now()) + ' ' + request.method)
#     debugprint('method=' + request.method)
    
    return utils.custom_redirect('ShowQuestionDetails', question_slug, just_published_on_FB=True)



#this posts the results of the vote to Facebook
# very similar to the above view but for results, not the question
@facebook_required_lazy(scope=['publish_actions'])
@login_required
@UserMustOwnThisQuestion
@QuestionIsPublished
def PostResultsToFacebook(request, graph, question_slug=''):
    
    
    if not graph:
        return utils.custom_redirect('ShowQuestionDetails', question_slug, fb_post_error=True)
    
    theQuestion = GetQuestionFromSlug(question_slug)
    fb_post_str = ConstructFBResultsPostForQuestion(theQuestion)
    try:
        #result = graph.set('me/feed', message=fb_post_str)
        asynch_post_job = ViewHelpers.post_to_fb_async.delay(graph.access_token, fb_post_str)
    
    except Exception as e:
        return utils.custom_redirect('ShowQuestionDetails', question_slug, fb_post_error=True)
    
    return utils.custom_redirect('ShowQuestionDetails', question_slug, just_published_results_on_FB=True)
    

@login_required
@UserMustOwnThisQuestion
def DeleteQuestion(request, question_slug=''):
    
    if request.method != "POST":
        return DefaultErrorPage(mesg="Delete does not work with GET.")
    
    theQuestion = GetQuestionFromSlug(question_slug)
    try:
        DeleteRelatedPublishings(theQuestion)
        linked_survey = theQuestion.linked_survey
        theQuestion.delete()
        linked_survey.delete()
    
    #need to add transcation/rollback here
    except (DatabaseError, IntegrityError) as e:
        return DefaultErrorPage(e, "Could not delete this question due to a database error.")
        
    return utils.custom_redirect('ShowQuestionsList', just_deleted_question=True)



@login_required
@UserMustOwnThisQuestion
def ShowEmailForm(request, question_slug=''):
    
    theQuestion = GetQuestionFromSlug(question_slug)
    
    #if POST we are processing the email form and we need to validate and send out the email
    if request.method == "POST":
        form = EmailContactForm(request.POST)
        
        if form.is_valid():
            
            #process the form by setting the question to published, extracting the email addresses to send to,
            #and the user's own address
            
            publishing_and_email_dict=ViewHelpers.ParseInputAndSaveModels(form, request.user, theQuestion)
            
            #send the email
            ViewHelpers.SendQuestionViaEmail(publishing_and_email_dict, request.user, form, theQuestion)
            
            return utils.custom_redirect('ShowQuestionDetails', question_slug, just_published_via_email=True)
        else:
            return render_to_response('email_contact_form.html', {'form' : form,  'question' : theQuestion}, context_instance=RequestContext(request))
            
    #if this is a GET show the email form
    else:
        
        #if user has a profile, get it so we can display the user's email address, else don't worry about it
        userprof = None
        
        try:
            userprof = UserProfile.objects.get(linked_user__id=request.user.id)
            
        except UserProfile.DoesNotExist:
            pass
        
        form = EmailContactForm(initial={'user_email' : userprof.working_email if userprof else ''})
            
        return render_to_response('email_contact_form.html', {'form' : form, 'question' : theQuestion}, context_instance=RequestContext(request))



#similar to the above view but for sending results not the question itself
@login_required
@UserMustOwnThisQuestion
@QuestionIsPublished
def ShowResultsEmailForm(request, question_slug=''):
    
    theQuestion = GetQuestionFromSlug(question_slug)
    
    current_user = request.user
    
    if request.method == "POST":
        form = EmailResultsContactForm(request.POST)
        
        
        if form.is_valid():
            
            #save working email if not already there
            
            try:
                user_prof=UserProfile.objects.get(linked_user__pk=current_user.pk)
            except UserProfile.DoesNotExist:
                user_prof = UserProfile()
                user_prof.linked_user = current_user
    
            user_prof.working_email = form.cleaned_data['user_email']
    
            user_prof.save()
            
            list_of_emails = ViewHelpers.ExtractListOfEmails(form.cleaned_data['list_of_email_addr'])
            
            #send the email
            
            
            SendResultsViaEmail(theQuestion, current_user, form, list_of_emails)
            
            return utils.custom_redirect('ShowQuestionDetails', question_slug, just_published_results_via_email=True)
        else:
            return render_to_response('email_contact_form.html', {'form' : form,  'question' : theQuestion}, context_instance=RequestContext(request))
            

    else:
        
        userprof = None
        
        try:
            userprof = UserProfile.objects.get(linked_user__id=request.user.id)
            
        except UserProfile.DoesNotExist:
            pass
        
        form = EmailResultsContactForm(initial={'user_email' : userprof.working_email if userprof else ''})
            
        return render_to_response('email_contact_form.html', {'form' : form, 'question' : theQuestion}, context_instance=RequestContext(request))


#just show the static about page
class About(TemplateView):

    template_name = 'about.html'
    
    
#shows the result of a question's vote
#no auth needed, anyone can see results given the link

@QuestionIsPublished
def ResultsPageForAnonymousUsers(request, question_slug):
    
    template = 'show_question_details.html'
    
    return ShowResults(request, question_slug, IsAjax=False)
    

#this gets called via Ajax and actually shows the vote results in the post-vote page
# see template register_user_response_success.html

@QuestionIsPublished
def ajax_ShowAnswersAndResults(request,question_slug):
    return ShowResults(request, question_slug, IsAjax=True)

#anyone can see results, so no authentication needed
#if called via ajax from the post-vote page, return an HTML fragment containing
# the answers, votes, and JSON data of the votes

#if called directly, show the results
#uses the same template as the Question Details page
#that template handles several different scenarios and shows different fields depending

def ShowResults(request, question_slug, IsAjax=False):
    
    template = 'show_question_details.html' if IsAjax==False else 'answer_and_chart_sub_template.html'
    
    try:
        theQuestion = GetQuestionFromSlug(question_slug)
    
    except CustomAppError as e:
        return DefaultErrorPage(e, mesg="Could not find the question specified.")
    
    #get the answer choices and get the vote counts
    
    theAnswers = theQuestion.multiplechoiceansweritem_set.all()
    vote_tally,total_votes = GetVoteTally(theAnswers)
    
    is_published = (theQuestion.linked_survey.publishing_set.count() > 0)
    
    
    return render_to_response(template, {'question' : theQuestion, 'answers' : theAnswers, 'is_published' : \
                                         is_published,  'is_results_page' : True, 'vote_tally' : json.dumps(vote_tally), 'total_votes': total_votes}, \
                              context_instance=RequestContext(request))
    
