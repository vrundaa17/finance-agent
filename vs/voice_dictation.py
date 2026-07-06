from faster_whisper import WhisperModel
import pyaudio, wave
import pyautogui, time,pyperclip
from gtts import gTTS
import threading
from m import call_llm
from dotenv import load_dotenv
load_dotenv()
import os,uuid


MODEL_SIZE  = "base"
SAMPLE_RATE = 16000
CHUNK       = 1024
TEMP_FILE   = "temp.wav"
last_insert=" "

def record():
    '''This function is used for recording the voice input on pressing the ENTER KEY'''
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    input("Press ENTER")
    print("Recording... press ENTER to stop Recording")

    frames = []
    stop = threading.Event()

    def wait_for_stop():
        input()
        stop.set()

    t = threading.Thread(target=wait_for_stop)
    t.start()

    while not stop.is_set():
        frames.append(stream.read(CHUNK, exception_on_overflow=False))

    print("Done!\n")
    stream.stop_stream()
    stream.close()

    with wave.open(TEMP_FILE, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    audio.terminate()
    return TEMP_FILE


def transcribe(audio_path, model):
    segments, info = model.transcribe(audio_path)
    # print(f"Language: {info.language}")
    text = " ".join([s.text for s in segments])
    return text.strip()

def type_text(text):
    print(f"Typing... {text}")
    time.sleep(2)
    pyperclip.copy(text)
    pyautogui.hotkey("command", "v")
    # pyautogui.typewrite(text, interval=0.05)



def replace_last_text(new_text):
    global last_insert
    for _ in range(len(last_insert)):
        pyautogui.press("left")
    pyautogui.keyDown("shift")
    
    
    for _ in range(len(last_insert)):
        pyautogui.press("right")
    pyautogui.keyUp("shift")
    
    pyperclip.copy(new_text)
    pyautogui.hotkey("command","v")
    
    last_insert = new_text
    


if __name__ == "__main__":
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("\n\nSay STOP to terminate the voice assistant")
    history=[]
    while True:
        

        audio_path = record()
        text = transcribe(audio_path, model)
        print(f"Transcribed:\n\t{text}\n")
        os.remove(audio_path)

        if text.lower().startswith("hello"):
            print("LLM...")
            response = call_llm(text, last_insert,history)
            print(f"LLM Response:\n\t{response}\n")
            
            replace_last_text(response)

            print("\n\nSay STOP to terminate the voice assistant")
            
        elif text.lower().startswith("stop"):
            print("\n Happy to serve you... toodles!!!")
            break
        
        else:
            type_text(text)
            last_insert= text
            print("\n\nSay STOP to terminate the voice assistant")
            
        history.append({"role": "user", "content": f"[Dictated text]: {text}"})
        history.append({"role": "assistant", "content": "ok"})
            
# this needs to change if it tells change this than the text should be replaced and not written down

# This is the sample of the calling.There is no text to change the grammar of. Please provide some text, There is no text to change the grammar of. Please provide some text, and I will be happy to assist you.
# This is a sample recording.¡Halo! ¡Al fin hecho en Instagram!
# This is a sample recording.This is where a zombie rises.
# The sun comes out in the east.
# Transcribed:
#         East is where the sun comes out

# Typing... East is where the sun comes out


# Say STOP to terminate the voice assistant
# Press ENTER
# Recording... press ENTER to stop Recording

# Done!

# Transcribed:
#         Hello! Change the grammar!

# LLM...
# LLM Response:
#         The sun comes out in the east.

