from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import base64
import os,uuid
from faster_whisper import WhisperModel
from voice_dictation import record
from gtts import gTTS
import gradio as gr

image_path="data/dog.jpg"
model = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct")
whisper_model =  WhisperModel("base", device="cpu", compute_type="int8")


def transcribe(audio_path):
    result, _ = whisper_model.transcribe(audio_path,language="en")
    text = " ".join([s.text for s in result])
    print(f"Audio Text : {text}")
    return text.strip()
    
def encode_image(image_path):
    with open(image_path,"rb") as f:
        return base64.b64encode(f.read()).decode()

def ask_image(image_path, question):
    image_data = encode_image(image_path)
    message = HumanMessage(
        content=[
            {
                "type":"text",
                "text":question,
            },
            {
                "type":"image_url",
                "image_url":{
                    "url":f"data:image/jpeg;base64,{image_data}"
                }
            }
            
        ],
        max_tokens=500,
    )
    response = model.invoke([message])
    return response.content


def speak_img(text, output_dir ="outputs"):
    os.makedirs(output_dir,exist_ok=True)
    path = f"{output_dir}/{uuid.uuid4()}.mp3"
    tts =gTTS(text=text,lang="en")
    tts.save(path)
    return path

def complete(audio_path,image_path):
    question = transcribe(audio_path)
    answer = ask_image(image_path,question)
    response_path = speak_img(answer)
    print(answer)
    
    return answer, response_path

    
# if __name__=="__main__":
#     answer =complete(image_path)
#     print(answer)
#     os.remove("temp.wav")
    
with gr.Blocks(title="Voice - Visual") as demo:
    gr.Markdown("## Voice - Visual")
    gr.Markdown("Upload an image, ask a question and get an answer back!!!")
    
    with gr.Row():
        audio_input = gr.Audio(
            # sources=["microphone"],
            type="filepath",
            label="Record your question",
        )
        image_input= gr.Image(
            type="filepath",
            label="Upload an Image"
        )
    btn = gr.Button("Ask")
    
   
    answer_out= gr.Textbox(label="Answer :")
    audio_out = gr.Audio(label="Voice response", autoplay=True)
    btn.click(
        fn=complete,
        inputs=[audio_input,image_input],
        outputs=[answer_out,audio_out]
    )
demo.launch()