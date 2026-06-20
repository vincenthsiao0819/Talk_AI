import pyaudio
import numpy as np
from openwakeword.model import Model
import speech_recognition as sr
import urllib.request
import urllib.error
import json
import socket
import time
import os
import sys

def log(*args):
    print(*args)
    sys.stdout.flush()

log("Loading openwakeword model 'Hey Jarvis'...")
try:
    oww_model = Model(wakeword_models=["C:/Users/magic/WelcomeAPI/models/hey_jarvis_v0.1.onnx"], inference_framework="onnx")
except Exception as e:
    log("Failed to load model:", e)
    sys.exit(1)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280

log("Initializing PyAudio...")
audio = pyaudio.PyAudio()

try:
    mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
except Exception as e:
    log("Failed to open microphone stream:", e)
    sys.exit(1)

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 400

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"

def trigger_tts(text):
    try:
        log("Triggering TTS:", text)
        req = urllib.request.Request("http://127.0.0.1:8081/speak")
        req.add_header('Content-Type', 'application/json')
        response = urllib.request.urlopen(req, data=json.dumps({"text": text}).encode('utf-8'), timeout=2)
        log("TTS Trigger Response:", response.getcode())
    except Exception as e:
        log("TTS Error:", e)

def send_to_mac(text):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect(("127.0.0.1", 5005))
        s.send(text.encode('utf-8'))
        s.close()
        log("Sent to Mac:", text)
    except Exception as e:
        log("Socket error:", e)

def recognize_with_whisper(audio_data):
    if not OPENAI_API_KEY:
        log("No OpenAI API key found, falling back to Google STT")
        return recognizer.recognize_google(audio_data, language="zh-TW")
    
    try:
        wav_data = audio_data.get_wav_data()
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body = []
        body.append(f"--{boundary}")
        body.append('Content-Disposition: form-data; name="file"; filename="audio.wav"')
        body.append('Content-Type: audio/wav')
        body.append('')
        body.append(wav_data)
        
        body.append(f"--{boundary}")
        body.append('Content-Disposition: form-data; name="model"')
        body.append('')
        body.append(b'whisper-1')
        
        body.append(f"--{boundary}")
        body.append('Content-Disposition: form-data; name="language"')
        body.append('')
        body.append(b'zh')
        
        body.append(f"--{boundary}--")
        body.append(b'')
        
        body_bytes = bytearray()
        for item in body:
            if isinstance(item, str):
                body_bytes.extend(item.encode('utf-8'))
                body_bytes.extend(b'\r\n')
            elif isinstance(item, bytes):
                body_bytes.extend(item)
                body_bytes.extend(b'\r\n')
                
        req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions")
        req.add_header('Authorization', f'Bearer {OPENAI_API_KEY}')
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        
        log("Sending audio to Whisper API...")
        response = urllib.request.urlopen(req, data=body_bytes, timeout=15)
        result = json.loads(response.read().decode('utf-8'))
        return result.get('text', '')
        
    except urllib.error.HTTPError as e:
        log("Whisper API HTTP Error:", e.code, e.read().decode('utf-8'))
        return ""
    except Exception as e:
        log("Whisper API Error:", str(e))
        return ""

log("Ears are listening for 'Hey Jarvis'...")
while True:
    try:
        pcm = mic_stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(pcm, dtype=np.int16)
        
        prediction = oww_model.predict(audio_data)
        if list(prediction.values())[0] > 0.5:
            log("Wake word 'Hey Jarvis' detected!")
            trigger_tts("我在")
            
            time.sleep(0.5) 
            
            with sr.Microphone() as source:
                log("Listening for command...")
                try:
                    audio_input = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                    log("Recognizing with Whisper...")
                    text = recognize_with_whisper(audio_input)
                    log("You said: " + text)
                    if text:
                        send_to_mac(text)
                except sr.WaitTimeoutError:
                    log("Timeout waiting for speech")
                except Exception as e:
                    log("Speech recognition error:", e)
            
            oww_model.reset()
            log("Ears are listening for 'Hey Jarvis'...")
    except Exception as e:
        log("Main loop error:", e)
        time.sleep(1)
