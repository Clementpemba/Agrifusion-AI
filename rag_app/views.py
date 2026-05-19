from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

import os

from .rag_engine import initialize_rag, generate_answer
from .predictor import predict_yield
from .models import Activity
from .translator import translator

@require_POST
@login_required
def speech_to_text_api(request):
    import tempfile
    import os
    import traceback
    import speech_recognition as sr
    from pydub import AudioSegment

    # ✅ FORCE FFmpeg PATH (CRITICAL FIX)
    AudioSegment.converter = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-full_build\bin\ffmpeg.exe"
    AudioSegment.ffprobe = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-full_build\bin\ffprobe.exe"

    webm_path = None
    wav_path = None

    try:
        audio_file = request.FILES.get('audio')

        if not audio_file:
            return JsonResponse({"error": "No audio file received"}, status=400)

        # ✅ Save uploaded audio safely
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            webm_path = tmp.name

        wav_path = webm_path.replace(".webm", ".wav")

        # ✅ Auto-detect format (IMPORTANT FIX)
        audio = AudioSegment.from_file(webm_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")

        # ✅ Speech recognition
        recognizer = sr.Recognizer()

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data)

        return JsonResponse({
            "text": text,
            "status": "success"
        })

    except sr.UnknownValueError:
        return JsonResponse({
            "error": "Could not understand audio"
        })

    except sr.RequestError as e:
        return JsonResponse({
            "error": "Speech API error",
            "details": str(e)
        })

    except Exception as e:
        print("🔥 FULL SPEECH ERROR:")
        traceback.print_exc()

        return JsonResponse({
            "error": "Speech processing failed",
            "details": str(e)
        })

    finally:
        # ✅ CLEANUP (VERY IMPORTANT)
        try:
            if webm_path and os.path.exists(webm_path):
                os.remove(webm_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except:
            pass


@login_required
def text_to_speech_api(request):
    text = request.GET.get("text", "")
    lang = request.GET.get("lang", "ny")

    if not text:
        return JsonResponse({"error": "No text provided"})

    audio_path = translator.text_to_speech(text, lang)

    if not audio_path:
        return JsonResponse({"error": "TTS failed"})

    return FileResponse(open(audio_path, "rb"), content_type="audio/mpeg")

@login_required
def chat_multilingual_page(request):
    return render(request, "rag_app/chat_multilingual.html")
# -------------------------------
# INIT RAG ONCE
# -------------------------------
ik_retriever, hd_retriever, llm = initialize_rag()


# -------------------------------
# AUTH
# -------------------------------
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            return render(request, "rag_app/signup.html", {"error": "Username already exists"})

        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect("dashboard")

    return render(request, "rag_app/signup.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("dashboard")

        return render(request, "rag_app/login.html", {"error": "Invalid credentials"})

    return render(request, "rag_app/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# -------------------------------
# CORE PAGES
# -------------------------------
@login_required
def dashboard(request):
    activities = Activity.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "rag_app/dashboard.html", {
        "activities": activities
    })


@login_required
def home(request):
    return render(request, "rag_app/index.html")


@login_required
def predict_page(request):
    return render(request, "rag_app/predict.html")


# -------------------------------
# ASK QUESTION (🔥 FIXED FINAL)
# -------------------------------
@login_required
def ask_question(request):

    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse({"error": "No question provided"}, status=400)

    try:
        rag_response = generate_answer(query, ik_retriever, hd_retriever, llm)

        # ALWAYS expect flat structure now (FIXED ENGINE)
        return JsonResponse({
            "indigenous_insight": rag_response.get("indigenous_insight", "Not available"),
            "scientific_insight": rag_response.get("scientific_insight", "Not available"),
            "recommendation": rag_response.get("recommendation", "Not available"),
            "risk": rag_response.get("risk", "Not available"),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return JsonResponse({
            "error": "Server crashed",
            "details": str(e)
        }, status=500)


# -------------------------------
# MULTILINGUAL CHAT (FIXED)
# -------------------------------
@login_required
def ask_question_multilingual(request):

    query = request.GET.get("q", "")
    lang = request.GET.get("lang", "ny")

    if not query:
        return JsonResponse({"error": "No question provided"})

    detected_lang = translator.detect_language(query)

    if detected_lang in ["ny", "tum"]:
        query = translator.translate_to_english(query, detected_lang)

    rag_response = generate_answer(query, ik_retriever, hd_retriever, llm)

    response = {
        "indigenous_insight": rag_response.get("indigenous_insight", ""),
        "scientific_insight": rag_response.get("scientific_insight", ""),
        "recommendation": rag_response.get("recommendation", ""),
        "risk": rag_response.get("risk", ""),
    }

    if lang in ["ny", "tum"]:
        response = {
            k: translator.translate_from_english(v, lang)
            for k, v in response.items()
        }

    return JsonResponse(response)


# -------------------------------
# PREDICTION API (UNCHANGED BUT SAFE)
# -------------------------------
@login_required
def predict_api(request):

    try:
        data = {
            "Latitude": float(request.GET.get("lat")),
            "Longitude": float(request.GET.get("lon")),
            "Soil_Type": request.GET.get("soil"),
            "Fertilizer": request.GET.get("fert"),
            "Pesticide_Amount": float(request.GET.get("pest")),
            "Avg_Temp_C": float(request.GET.get("temp")),
            "Rainfall_mm": float(request.GET.get("rain")),
            "Humidity_%": float(request.GET.get("hum")),
        }

        result = round(float(predict_yield(data)), 2)

        query = f"Farming advice for {data['Soil_Type']} soil with rainfall {data['Rainfall_mm']}"

        rag_response = generate_answer(query, ik_retriever, hd_retriever, llm)

        advice = rag_response.get("recommendation", "")

        Activity.objects.create(
            user=request.user,
            action_type="prediction",
            content=str(data),
            result=str(result)
        )

        return JsonResponse({
            "prediction": result,
            "advice": advice
        })

    except Exception as e:
        return JsonResponse({"error": str(e)})


# -------------------------------
# DELETE FUNCTIONS
# -------------------------------
@require_POST
@login_required
def delete_activity(request, activity_id):
    try:
        Activity.objects.get(id=activity_id, user=request.user).delete()
        return JsonResponse({"success": True})
    except:
        return JsonResponse({"error": "Not found"})


@require_POST
@login_required
def delete_all_activities(request):
    Activity.objects.filter(user=request.user).delete()
    return JsonResponse({"success": True})