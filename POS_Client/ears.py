import pyaudio
import numpy as np
from openwakeword.model import Model
import speech_recognition as sr
import urllib.request
import json
import socket
import time
import os

# Create standard output flush for logging
import sys
def log(*args):
    print(*args)
    sys.stdout.flush()

log("Loading openwakeword model 'alexa'...")
try:
    oww_model = Model(wakeword_models=["C:/Users/magic/WelcomeAPI/models/hey_long_xia.onnx"], inference_framework="onnx")
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
# Improve SR speed
recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 400

def trigger_tts(text):
    try:
        req = urllib.request.Request("http://127.0.0.1:8081/speak")
        req.add_header('Content-Type', 'application/json')
        urllib.request.urlopen(req, data=json.dumps({"text": text}).encode('utf-8'), timeout=2)
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

log("Ears are listening for 'Hey Long Xia'...")
while True:
    try:
        pcm = mic_stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(pcm, dtype=np.int16)
        
        prediction = oww_model.predict(audio_data)
        if list(prediction.values())[0] > 0.5:
            log("Wake word 'Hey Long Xia' detected!")
            trigger_tts("我在")
            
            # Flush the mic buffer
            time.sleep(0.5) 
            
            with sr.Microphone() as source:
                log("Listening for command...")
                try:
                    audio_input = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    log("Recognizing...")
                    text = recognizer.recognize_google(audio_input, language="zh-TW")
                    log("You said: " + text)
                    if text:
                        send_to_mac(text)
                except sr.WaitTimeoutError:
                    log("Timeout waiting for speech")
                except sr.UnknownValueError:
                    log("Could not understand audio")
                except Exception as e:
                    log("Speech recognition error:", e)
            
            # Flush internal state of openwakeword to avoid re-trigger
            oww_model.reset()
            log("Ears are listening for 'Hey Long Xia'...")
    except Exception as e:
        log("Main loop error:", e)
        time.sleep(1)
