'''
Created on Nov 7, 2013

@author: mo
'''
from __future__ import with_statement
import unittest

from django.test import TestCase
from django.test import TransactionTestCase
from djtest4.MultipleChoice.FormHelpers import *
from djtest4.MultipleChoice.models import *
from djtest4.ViewHelpers import ExtractListOfEmails
from djtest4 import ViewHelpers
#copied this lsit of imports from django_facebook's test.py


from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.test.client import Client, RequestFactory
from django_facebook import exceptions as facebook_exceptions, \
    settings as facebook_settings, signals
from django_facebook.api import get_facebook_graph, FacebookUserConverter, \
    get_persistent_graph
from django_facebook.auth_backends import FacebookBackend
from django_facebook.connect import _register_user, connect_user, \
    CONNECT_ACTIONS
from django_facebook.middleware import FacebookCanvasMiddleWare
from django_facebook.test_utils.mocks import RequestMock
from django_facebook.test_utils.testcases import FacebookTest, LiveFacebookTest
from django_facebook.utils import cleanup_oauth_url, get_profile_model, \
    ScriptRedirect, get_user_model, get_user_attribute, try_get_profile, \
    get_instance_for_attribute, update_user_attributes
from functools import partial
from mock import Mock, patch
from open_facebook.api import FacebookConnection, FacebookAuthorization, \
    OpenFacebook
from open_facebook.exceptions import FacebookSSLError, FacebookURLError
import logging
import mock
from mock import patch
from django.utils import unittest
from django_facebook.models import OpenGraphShare
from django.contrib.contenttypes.models import ContentType
from open_facebook.exceptions import FacebookUnreachable, OAuthException
from djtest4.utils import custom_assert_not_raise



#end copy from django_facebook

class TestEmailDistListValidation(unittest.TestCase):
    
    
    
        
                      
    '''helper function that can apply a given function to a column of an array and make sure the results match the second 
    column'''
    def multiple_val_check(self,arr_of_arr,func):
        for arr in arr_of_arr:
            if arr[1]:
                self.assert_(func(arr[0]), str(arr[0]) + ' did not evaluate to ' + str(arr[1]))
            else:
                self.assertFalse(func(arr[0]), str(arr[0]) + ' did not evaluate to ' + str(arr[1]))       
    
    

    #tests basic regex
    def test_email_basic(self):
        
        test_arr=[ ['moecando@gmail.com', True],
         ['moecandogmail.com', False],
         ['blahasdf,adsfads@gmail.com', False],
         ['blah blah@gamil.com', False]]
        
        msg="oops, that was bad."
        
        self.multiple_val_check(test_arr, validate_email_addr_custom)
        
    #tests regex that handles emails with brackets like Outlook makes, or gmail makes                          
    def test_validate_emails_with_header(self):
        
        test_arr=[ ['john<john@gmail.com>', True],
                  ['"White,John"<john@gmail.com>', True],
                  ['"mike mince"<mikegmail.com>', False],
                  ['john, beat<mike@beat.com>', False],
                  ['john@john.com', False]
                  ]
        
        
        self.multiple_val_check(test_arr, ValidateEmailAddressWithHeader)
        
        
    def test_validate_emails_with_or_without_header(self):
        
        test_arr=[ ['john<john@gmail.com>', True],
                  ['"White,John"<john@gmail.com>', True],
                  ['"mike mince"<mikegmail.com>', False],
                  ['john, beat<mike@beat.com>', False],
                  ['john@john.com', True],
                  ['asdfasdfasd asdfasf@asdfasf.asdfasd', False],
                  ['mike@burning.', False],
                  ['     \r\n\r\nsteven pinker<spinker@mit.du>', True]
                  ]
        
        
        self.multiple_val_check(test_arr, ValidateEmailAddressWithOrWithoutHeader)


    # the most useful test that validates a whole list of emails is valid
    def test_validate_email_list(self):
        test_arr=[ ['john<john@gmail.com>;mike.bertuglia@yahoo.com, "neimeth, joanne"<jneimeth@outlook.com>,', True],
                  ['john<john@gmail.com>;mike.bertuglia@yahoo.com,\r\n"neimeth, joanne"<jneimeth@outlook.com>,', True],
                  ['"mike mince"<mikegmail.com>,', False],
                  ['\nmike@blah.com; john burds <jb@microsoft.com>;violet parsons<vparsons@kells.com>', True],
                  
                  ['john, beat<mike@beat.com>,', False],
                  ['\r\n\r\nmike@blah.com; john burds <jb@microsoft.com>;\n\n\n\n     violet parsons<vparsons@kells.com>\r\n\n ', True]
                  ]
         
        
        self.multiple_val_check(test_arr, ValidateListOfEmailAddresses)

    #tests that ExtractListOfEmails extracts the emails properly
    def test_extract_emails(self):
        
        test_list_1 = 'john<john@gmail.com>;mike.bertuglia@yahoo.com, "neimeth, joanne"<jneimeth@outlook.com>'
        
        extracted_emails = ExtractListOfEmails(test_list_1)
        
        self.assertEqual(extracted_emails, ['john<john@gmail.com>', 'mike.bertuglia@yahoo.com',  '"neimeth, joanne"<jneimeth@outlook.com>'], 
                         'Extraction did not work for list '+ test_list_1 + '. Evaluated to ' + str(extracted_emails))
        
        



class FBAuthTests(FacebookTest):

    fixtures=['TestDataMultiple', 'facebookuserdata']

    def setUp(self):
        #call FacebookTest's set up to create the dummy user
        super(FBAuthTests, self).setUp()
        self.url = reverse('ShowQuestionsList')
        self.target_url = r'''http://testserver/login/?next=/Question/All'''

    def tearDown(self):
        pass


    def test_show_login_when_not_authenticated(self):
        '''
        We should redirect to the login page of the app
        '''
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, self.target_url, target_status_code=200)
        
        
    def test_show_questions_list_when_authenticated(self):
        self.mock_authenticated()
        #django_facebook sets up this user in FacebookTest code
        res=self.client.login(facebook_email='fake@mellowmorning.com')
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, "Your Questions")
        
    def test_post_to_facebook(self):
        
        question_text = "This is a new question?"
        answer_one = "Answer number one"
        answer_two = "Answer number two"
        question_elem_name = 'Question-qtext'
        answer_one_elem_name = 'Answer-0-ans_text'
        answer_two_elem_name = 'Answer-1-ans_text'
        add_question_url =  reverse('AddQuestion')
        
        #login
        res=self.client.login(facebook_email='fake@mellowmorning.com')
        
        #create a question so we can then try to post it to FB
        new_question_id=Helpers.CreateQuestionHelper(self, add_question_url, question_text, answer_one, answer_two)
        
        post_to_fb_url = reverse('PublishQuestionToFacebook', kwargs={'question_slug' : MultipleChoiceQuestion.objects.get(id=new_question_id).slug})
        
        #mock-authenticate to FB
        self.mock_authenticated()
        
        with patch('djtest4.ViewHelpers.post_to_fb_async.delay') as mock_method:
            
           result= self.client.post(post_to_fb_url, {})
            
        
        self.assertTrue(mock_method.assert_is_called)
        
        #self.assertTrue(mock_method.call_args[0][0].find('')!=-1)
        
        self.assertTrue(mock_method.call_args[0][1].find('This is a new question?')!=-1)
        
        
        
        
        
class Helpers(object):

    @staticmethod
    def CreateQuestionHelper(TestInstance, add_question_url, question_text, answer_one, answer_two):
        post_dict = {'Question-qtext':question_text, 'Answer-0-linked_question':'', 'Answer-0-id':'', 'Answer-0-ans_text':answer_one, 'Answer-1-linked_question':'', 'Answer-1-id':'', 'Answer-1-ans_text':answer_two, 'Answer-TOTAL_FORMS':2, 'Answer-INITIAL_FORMS':0, 
            'Answer-MAX_NUM_FORMS':1000}
        result=TestInstance.client.post(add_question_url, post_dict)
        try:
            question_id = MultipleChoiceQuestion.objects.get(qtext='This is a new question?').id
        except Exception as e:
            TestInstance.fail("question should exist")
        TestInstance.assertTrue(MultipleChoiceAnswerItem.objects.filter(linked_question__id=question_id, ans_text=answer_one).exists(), 'Answer item should exist ')
        TestInstance.assertTrue(MultipleChoiceAnswerItem.objects.filter(linked_question__id=question_id, ans_text=answer_two).exists(), 'Answer item should exist ')

        return question_id
  
        
#use TranscationTestCase as it supports fixtures which I like

class BasicTests(TransactionTestCase):
  
    fixtures=['TestDataMultiple', 'facebookuserdata']
  
    def setUp(self):
        self.first_question=MultipleChoiceQuestion.objects.get(qtext='Is this the first test question?')
        self.second_question=MultipleChoiceQuestion.objects.get(qtext='is this the second test question?') 
        self.first_question_first_answer=MultipleChoiceAnswerItem.objects.get(ans_text='Answer one')
        result=self.client.login(facebook_email="pubmo1789@gmail.com")
        self.assertTrue(result, "could not login as test user....tests will fail ")
        
        
    def test_CheckFixtureLoaded(self):
        self.assert_(MultipleChoiceQuestion.objects.filter(qtext='Is this the first test question?').exists(), 'Fixtures did not load')
          
  
    def test_Voting(self):
        #votes for a question's answer by http-ing to the vote url
        
        vote_url = reverse('RegisterVote', kwargs={ 'question_slug' : self.first_question.slug, 'answer_slug' : self.first_question_first_answer.slug} )
        self.client.get( vote_url)
          
        #check there is a MultipleChoicePostedAnswer for the particular answer given
        self.assertTrue(MultipleChoicePostedAnswer.objects.filter(linked_answer__id=self.first_question_first_answer.id).exists(), 'No posted answer for voted answer')
    
    

    def test_create_question(self): 
        
        
        
        add_question_url =  reverse('AddQuestion')
        
        question_text = "This is a new question?"
        answer_one = "Answer number one"
        answer_two = "Answer number two"
        question_elem_name = 'Question-qtext'
        answer_one_elem_name = 'Answer-0-ans_text'
        answer_two_elem_name = 'Answer-1-ans_text'
        Helpers.CreateQuestionHelper(self, add_question_url, question_text, answer_one, answer_two)
    
    #questions that are published cannot be edited---once sent to FB or via email, they are locked from editing
    def test_cannot_edit_published_question(self):
        
        
        question_slug = self.first_question.slug
            
        edit_question_url =  reverse('EditQuestion', kwargs={'question_slug': question_slug})
        
        question_text = "This is a new question?--changed"
        answer_one = "Answer number one--changed"
        answer_two = "Answer number two--changed"
        question_elem_name = 'Question-qtext'
        answer_one_elem_name = 'Answer-0-ans_text'
        answer_two_elem_name = 'Answer-1-ans_text'
        
        try:
            question_id = MultipleChoiceQuestion.objects.get(qtext=self.first_question.qtext).id
        except:
            self.fail("this shouldn't happen: question created in setup() should exist")
            
        
        post_dict={ 'Question-qtext' : question_text, 'Answer-0-linked_question' : question_id, 'Answer-0-id':'', 'Answer-0-ans_text': answer_one, 'Answer-1-linked_question' : question_id,
                   'Answer-1-id' : '', 'Answer-1-ans_text' : answer_two, 'Answer-TOTAL_FORMS':2, 'Answer-INITIAL_FORMS':0,  
                   'Answer-MAX_NUM_FORMS' :1000}
        
        
        
        result=self.client.post(edit_question_url, post_dict)
        
        self.assertContains(result, "This question is already published", 1, 200)
        
       
        #same as previous test but changes should go through as they are on the second test question which is not published yet
    def test_edit_question(self):
        
        question_slug = self.second_question.slug

    
        edit_question_url =  reverse('EditQuestion', kwargs={'question_slug': question_slug})
        
        question_text = "This is a new question?--changed"
        answer_one = "Answer number one--changed"
        answer_two = "Answer number two--changed"
        question_elem_name = 'Question-qtext'
        answer_one_elem_name = 'Answer-0-ans_text'
        answer_two_elem_name = 'Answer-1-ans_text'
        
        try:
            question_id = MultipleChoiceQuestion.objects.get(qtext=self.second_question.qtext).id
        except:
            self.fail("this shouldn't happen: question created in setup() should exist")
            
        
        post_dict={ 'Question-qtext' : question_text, 'Answer-0-linked_question' : question_id, 'Answer-0-id':'', 'Answer-0-ans_text': answer_one, 'Answer-1-linked_question' : question_id,
                   'Answer-1-id' : '', 'Answer-1-ans_text' : answer_two, 'Answer-TOTAL_FORMS':2, 'Answer-INITIAL_FORMS':0,  
                   'Answer-MAX_NUM_FORMS' :1000}
        
        
        
        result=self.client.post(edit_question_url, post_dict)
        
        try:
            question_id=MultipleChoiceQuestion.objects.get(qtext=question_text).id
        except Exception as e:
            self.fail("question should exist with changed content")
        
        
        self.assertTrue(MultipleChoiceAnswerItem.objects.filter(linked_question__id=question_id, ans_text=answer_one).exists(), 'Answer item should exist with changed content ')
        self.assertTrue(MultipleChoiceAnswerItem.objects.filter(linked_question__id=question_id, ans_text=answer_two).exists(), 'Answer item should exist with changed content ')
    
        print MultipleChoiceQuestion.objects.get(qtext=question_text).qtext
        print MultipleChoiceAnswerItem.objects.get(ans_text=answer_one).ans_text


    def test_delete_question(self):
    
    
        question_slug = self.second_question.slug
    
        
        delete_question_url =  reverse('DeleteQuestion', kwargs={'question_slug': question_slug})
    
        self.client.post(delete_question_url, {})
        
        self.assertRaises(MultipleChoiceQuestion.DoesNotExist, lambda: MultipleChoiceQuestion.objects.get(slug=self.second_question.slug))
    
    

    
    def test_send_question_via_email(self):
        
        with patch('djtest4.ViewHelpers.Send_Email') as mock_method:
            
            #ViewHelpers.Send_Email_Helper("testing", "moecando@gmail.com", ["moecando@gmail.com"], "test content", 'test_content')

            subject_should_be = 'Publiusmous Mousowsky has a quick question for you...'
            content_should_be=u'\n\nYou have a received a request to answer a quick question from Publiusmous Mousowsky.\n\nPubliusmous says,\n\nThis is a test prelude message!\n\nIs this the first test question?\n\nPlease click one of the links below:\n\nAnswer one: http://bit.ly/1eNuM8o\nAnswer two: http://bit.ly/HNmUFI\nAnswer three: http://bit.ly/HNmUFK\nAnswer four: http://bit.ly/1eNuMoY\n'
            html_content_should_be='\n<br/>\n<span style="padding-left:30px;  font-size:1.1em;"> <br/><br/>You have a received a request to answer a quick question from Publiusmous Mousowsky.\n<br/><br/></span>\n\n\n\n<table style="width:100%">\n<tr>\n<td style="width:10%"/>\n<td colspan=3>\n<span style="font-style:italic; font-weight:bold;">Publiusmous says,<br/><br/> </span>\n<span> This is a test prelude message!<br/> </span>\n</td>\n<td style="width:18%"/>\n</tr>\n</table>\n\n\n<table style="width:100%">\n<tr>\n<td style="width:10%"/>\n<td colspan=3 >\n<strong><h3 style="color:darkred">Is this the first test question?</h3></strong>\n\nPlease click one to answer:\n<br/>\n<a href="http://bit.ly/1eNuM8o" style="font-size:1.2em"><br/>Answer one</a>\n<a href="http://bit.ly/HNmUFI" style="font-size:1.2em"><br/>Answer two</a>\n<a href="http://bit.ly/HNmUFK" style="font-size:1.2em"><br/>Answer three</a>\n<a href="http://bit.ly/1eNuMoY" style="font-size:1.2em"><br/>Answer four</a>\n\n</td>\n<td style="width:18%"/>\n</tr>\n</table>'
            
            send_question_via_email_url = reverse('ShowEmailForm', kwargs={'question_slug' : self.second_question.slug})
            
            post_dict={'list_of_email_addr' : 'receiver@blah.com', 
                       'email_msg_body': 'This is a test prelude message!', 'user_email' : 'user@email.com'}
            
            self.client.post(send_question_via_email_url, post_dict)
            
            
        #check ViewHelpers.send_email is called with the right arguments
        
        self.assertTrue(mock_method.assert_called)
        self.assertTrue(mock_method.call_args[0][0].find('Publiusmous')!=-1)
        
        #elf.assertTrue(mock_method.call_args[0][1].find('moecando@gmail.com')!=-1)
        self.assertTrue('receiver@blah.com' in mock_method.call_args[0][2])
        self.assertTrue('user@email.com' in mock_method.call_args[0][2])
        
        self.assertTrue(mock_method.call_args[0][3].find('This is a test prelude')!=-1)
        self.assertTrue(mock_method.call_args[0][4].find('This is a test prelude')!=-1)
        
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()