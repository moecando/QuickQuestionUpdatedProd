from django.http import HttpResponseRedirect
from djtest4.MultipleChoice.models import MultipleChoiceQuestion
from djtest4.ViewHelpers import DefaultErrorPage
from djtest4.CustomExceptions import CustomAppError

from settings import DEBUG_PRINT
#taken from internet (i forget where), used to redirect and pass GET arguments
def custom_redirect(url_name, *args, **kwargs):
    from django.core.urlresolvers import reverse 
    import urllib
    url = reverse(url_name, args = args)
    params = urllib.urlencode(kwargs)
    return HttpResponseRedirect(url + "?%s" % params)

    
def UserMustOwnThisQuestion(fn):
    def wrapper(*args, **kwargs):
        question_slug=kwargs['question_slug']
        the_user = args[0].user
        
        try:
            the_question=MultipleChoiceQuestion.objects.get(slug=question_slug)
        except CustomAppError as e:
            return DefaultErrorPage(e, "Could not find the question specified.")
        
        # the current user can only access his questions, not other people's
        if (the_question.linked_survey.author.id != the_user.id):
            return DefaultErrorPage(mesg="You do not have permission to view this question.")
        
        return fn( *args, **kwargs)
    return wrapper

def QuestionIsNotPublished(fn):
    Pub_Or_Not = 'Not_Published'
    def wrapper(*args, **kwargs):
        question_slug=kwargs['question_slug']
        the_user = args[0].user
        
        the_question=MultipleChoiceQuestion.objects.get(slug=question_slug)
        
        if(Pub_Or_Not == 'Not_Published'):
            if (the_question.linked_survey.publishing_set.count() > 0):
                return DefaultErrorPage(mesg="This question is already published and cannot be edited.")
        
        if(Pub_Or_Not == 'Published'):
            if (the_question.linked_survey.publishing_set.count() == 0):
                return DefaultErrorPage(mesg="This question is not published yet.")
        
        
        return fn( *args, **kwargs)
    return wrapper

def QuestionIsPublished(fn):
    Pub_Or_Not = 'Published'
    def wrapper(*args, **kwargs):
        question_slug=kwargs['question_slug']
        the_user = args[0].user
        
        the_question=MultipleChoiceQuestion.objects.get(slug=question_slug)
        
        if(Pub_Or_Not == 'Not_Published'):
            if (the_question.linked_survey.publishing_set.count() > 0):
                return DefaultErrorPage(mesg="This question is already published and cannot be edited.")
        
        if(Pub_Or_Not == 'Published'):
            if (the_question.linked_survey.publishing_set.count() == 0):
                return DefaultErrorPage(mesg="This question is not published yet.")
        
        
        return fn( *args, **kwargs)
    return wrapper

def debugprint(astr):
    
    if DEBUG_PRINT:
        print astr


####for testing


# helper function to say a callable did not raise an exception
def custom_assert_not_raise(TestingClass, func, *args, **kwargs):
   
    try:
        func(args, kwargs)
    except Exception as e:
        TestingClass.fail("function " + func + 'with args ' + args + ' and kwargs ' + kwargs + ' should not raise exception ' + e)
 
         
