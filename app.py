from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from google.api_core import exceptions
import json
import random

load_dotenv()

app = Flask(__name__)

# Configurar Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'sua-api-key-aqui')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Prompt do sistema
system_prompt = """
Você é o Recomenda.ai, um chatbot especializado em entretenimento.

Você recomenda:
- músicas
- filmes
- séries
- animes

Responda sempre em português.
Respeite pedidos do usuário, mas sinta-se à vontade para ser criativo e surpreender com suas recomendações.
Respeite preferências, como gêneros, atores/atrizes, álbuns ou artistas.
Responda apenas com mensagens curtas, diretas e divertidas. Evite respostas longas ou explicativas.
Faça uma breve descrição do que está recomendando, mas sem spoilers. Use emojis para tornar a conversa mais leve e divertida.
Seja sempre breve e direto, mas com um toque de humor. Se o usuário pedir algo específico, tente atender, mas se não for possível, surpreenda com uma recomendação relacionada.
Suas respostas devem conter no maximo 2 linhas de texto, e sempre incluir emojis para tornar a conversa mais leve e divertida.
Não diga seu nome entre aspas, asteriscos ou colchetes. Apenas responda como Recomenda.ai, de forma natural.
"""

# Manter histórico da conversa
historico_conversa = [
    {"role": "user", "parts": [system_prompt]}
]

# Criar chat persistente
chat = model.start_chat(history=historico_conversa)

# Carregar recomendações locais
with open("entretenimento.json", "r", encoding="utf-8") as f:
    entretenimento = json.load(f)

# Função para detectar categoria a partir do texto do usuário
def detectar_categoria(texto):

    texto = texto.lower()

    if "filme" in texto:
        return "filmes"

    if "serie" in texto or "série" in texto:
        return "series"

    if "anime" in texto:
        return "animes"

    if "musica" in texto or "música" in texto:
        return "musicas"

    return None

# Função para detectar gênero a partir do texto do usuário
def detectar_genero(texto):

    generos = [
        "acao",
        "comedia",
        "drama",
        "suspense",
        "fantasia",
        "pop",
        "rock",
        "rap",
        "eletronica"
    ]

    texto = texto.lower()

    for g in generos:
        if g in texto:
            return g

    return None

# Cache e controle de chamadas
cache_respostas = {}

ultima_chamada = 0

TEMPO_MINIMO = 2  # segundos entre chamadas API

# Fallback local
def recomendacao_local(entrada):

    categoria = detectar_categoria(entrada)

    genero = detectar_genero(entrada)

    if categoria and genero:

        lista = entretenimento.get(categoria, {}).get(genero, [])

        if lista:
            return f"🎵🎬🎮 Sei a recomendação perfeita pra você! 😎\n\n{random.choice(lista)}"

    # fallback aleatório
    categoria = random.choice(list(entretenimento.keys()))

    sub = random.choice(list(entretenimento[categoria].keys()))

    item = random.choice(entretenimento[categoria][sub])

    return f"🚀 Segura essa! Tenho uma recomendação que vai te surpreender 😏:\n{item}"

# Função para chamar a IA
def responder(entrada, max_tentativas=3):

    global ultima_chamada

    print("Pergunta:", entrada)

    # Verificar cache
    if entrada in cache_respostas:
        print("Resposta vinda do cache")
        return cache_respostas[entrada]

    # Evitar spam de chamadas
    agora = time.time()

    if agora - ultima_chamada < TEMPO_MINIMO:
        espera = TEMPO_MINIMO - (agora - ultima_chamada)
        time.sleep(espera)

    ultima_chamada = time.time()

    print("Chamando Gemini...")

    for tentativa in range(max_tentativas):

        try:

            response = chat.send_message(entrada)

            if response and response.text:

                resposta = response.text

                # Manter apenas as últimas 20 mensagens no histórico para evitar sobrecarga
                chat.history = chat.history[-20:]

                # Salvar no cache
                cache_respostas[entrada] = resposta

                return resposta

        except exceptions.ResourceExhausted:

            if tentativa < max_tentativas - 1:
                tempo = min(2 ** tentativa, 10)
                print(f"Quota excedida, tentando novamente em {tempo}s")
                time.sleep(tempo)

        except Exception as e:

            print("Erro na IA:", e)
            break

    print("Usando fallback local")

    return recomendacao_local(entrada)

# Página inicial
@app.route("/")
def index():
    return render_template("index.html")

# Endpoint do chatbot
@app.route("/chat", methods=["POST"])
def chat_api():
    # Força o Flask a entender o JSON, mesmo que o header venha ligeiramente diferente
    data = request.get_json(force=True) 

    # No seu HTML você usou "mensagem", então aqui mantemos "mensagem"
    user_input = data.get("mensagem", "").strip()

    print(f"Mensagem recebida: {user_input}") # Isso ajuda a ver no log se chegou algo

    if not user_input:
        return jsonify({"resposta": "Digite alguma mensagem! 🎧"})

    if len(user_input) > 200:
        return jsonify({"resposta": "Mensagem muito longa 😅!"})

    # Chama a função que processa a IA ou o Fallback
    resposta_final = responder(user_input)

    # Retorna exatamente o que o seu JS espera: {"resposta": "texto"}
    return jsonify({"resposta": resposta_final})


# Rodar servidor
if __name__ == '__main__':
    app.run()