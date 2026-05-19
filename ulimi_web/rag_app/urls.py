from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # 🔐 Auth
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 🚀 Root → Login FIRST
    path('', lambda request: redirect('login')),

    # 📊 Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # 💬 Chatbot UI
    path('chat/', views.home, name='chat'),

    # 🌍 Multilingual Chat UI (🔥 THIS WAS MISSING)
    path('chat-multilingual/', views.chat_multilingual_page, name='chat_multilingual'),

    # 🤖 Chatbot API
    path('ask/', views.ask_question, name='ask'),
    path('ask-multilingual/', views.ask_question_multilingual, name='ask_multilingual'),

    # 🌽 Prediction
    path('predict/', views.predict_page, name='predict'),
    path('predict-api/', views.predict_api, name='predict_api'),

    # 🗑 Delete
    path("delete-activity/<int:activity_id>/", views.delete_activity, name="delete_activity"),
    path("delete-all-activities/", views.delete_all_activities, name="delete_all_activities"),

    path('text-to-speech/', views.text_to_speech_api, name='text_to_speech'),
    path('speech-to-text/', views.speech_to_text_api, name='speech_to_text'),
]