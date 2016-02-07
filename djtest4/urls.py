from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
from djtest4.views import About
admin.autodiscover()


urlpatterns = patterns('',
    # Examples:
     url(r'^$', 'djtest4.views.home', name='home'),
    # url(r'^djtest4/', include('djtest4.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
     url(r'^admin/', include(admin.site.urls)),
     url(r'^Question/(?P<question_slug>[^/]*)/Edit/', 'djtest4.views.EditQuestion', name='EditQuestion'),
     url(r'^Question/Add', 'djtest4.views.AddQuestion', name='AddQuestion'),
     url(r'^Question/vote/(?P<question_slug>[^/]*)/(?P<answer_slug>[^/]*)/RegisterVote', 'djtest4.views.RegisterVote', name='RegisterVote'),
     url(r'^Question/vote/(?P<question_slug>[^/]*)/ShowAnswersAndResults', 'djtest4.views.ajax_ShowAnswersAndResults', name='ajax_ShowAnswersAndResults'),
     
     url(r'^Question/vote/(?P<question_slug>[^/]*)/(?P<answer_slug>[^/]*)', 'djtest4.views.RespondToQuestion', name='RespondToQuestion'),
     
     
     #url(r'^Question/(?P<question_slug>[^/]*)/display', 'djtest4.views.ShowPublishedQuestion', name='ShowPublishedQuestion'),
     url(r'^Question/All', 'djtest4.views.ShowQuestionsList', name='ShowQuestionsList'),
     url(r'^Question/(?P<question_slug>[^/]*)/Details', 'djtest4.views.ShowQuestionDetails', name='ShowQuestionDetails'),
     url('r^$', 'djtest4.views.home', name = 'home'),
     
     #i think these are required by django_facebook app
     url(r'^facebook/', include('django_facebook.urls')),
     url(r'^accounts/', include('django_facebook.auth_urls')),
     
     
     url(r'^login/', 'djtest4.views.LoginPage', name = 'LoginPage'),
     url(r'^logout/', 'djtest4.views.Logout', name = 'Logout'),
     
     url(r'^Question/(?P<question_slug>[^/]*)/Publish', 'djtest4.views.PublishQuestionToFacebook', name='PublishQuestionToFacebook'),
     url(r'^Question/(?P<question_slug>[^/]*)/Delete', 'djtest4.views.DeleteQuestion', name='DeleteQuestion'),
     url(r'^Question/(?P<question_slug>[^/]*)/ShowEmailForm', 'djtest4.views.ShowEmailForm', name='ShowEmailForm'),
     url(r'^About/', About.as_view(), name='About'),
     url(r'^Question/(?P<question_slug>[^/]*)/Results/', 'djtest4.views.ResultsPageForAnonymousUsers', name = 'ResultsPageForAnonymousUsers'),
     url(r'^Question/(?P<question_slug>[^/]*)/ShowResultsEmailForm', 'djtest4.views.ShowResultsEmailForm', name = 'ShowResultsEmailForm'),
     url(r'^Question/(?P<question_slug>[^/]*)/PostResultsToFacebook', 'djtest4.views.PostResultsToFacebook', name = 'PostResultsToFacebook'),
     #url(r'^connect/', 'djtest4.views.custom_connect', name='custom_connect'),

     
)
