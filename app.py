import sys
import os
import logging
from uuid import uuid4
from flask import Flask, session, send_from_directory
from flask_socketio import SocketIO, emit
from google import genai
from google.genai import types
from dotenv import load_dotenv

if sys.platform != "win32":
    try:
        from gevent import monkey
        monkey.patch_all()
    except ImportError:
        pass

load_dotenv()

API_KEY = os.getenv("GENAI_KEY")
if not API_KEY:
    raise RuntimeError("A chave de API 'GENAI_KEY' não foi encontrada.")

MODELO = "gemini-2.5-flash"
MAX_MESSAGE_SIZE = 3000

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "steam_plus_super_secret")

# Configurar CORS para frontend em desenvolvimento e produção
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
    os.getenv("FRONTEND_URL", "")
]
CORS_ORIGINS = [url for url in CORS_ORIGINS if url]

socketio = SocketIO(
    app, 
    cors_allowed_origins=CORS_ORIGINS if CORS_ORIGINS else "*",
    async_mode="threading",
    ping_timeout=60,
    ping_interval=25
)
client = genai.Client(api_key=API_KEY)

active_chats = {}

INSTRUCOES = """
Você é o Sparky, o assistente inteligente da plataforma STEAM+ focada em robótica e cultura maker com blocos LEGO.
Seu público-alvo são alunos e professores do Ensino Fundamental II.

Diretrizes de Resposta:
1. Tom Entusiasta e Educativo: Use analogias de encaixe de blocos de montar, engrenagens e programação.
2. Gamificação NAtiva: Incentive o ganho de XP e a realização das metas semanais dos projetos práticos.
3. Respostas direto ao ponto: Ajude os usuários rapidamente e sempre formate respostas usando negritos organizados.
"""

def get_user_chat():
    if "session_id" not in session:
        session["session_id"] = str(uuid4())
    
    sid = session["session_id"]
    if sid not in active_chats:
        config = types.GenerateContentConfig(
            system_instruction=INSTRUCOES,
            temperature=0.7
        )
        active_chats[sid] = client.chats.create(model=MODELO, config=config)
    return active_chats[sid]

@socketio.on("connect")
def handle_connect():
    try:
        user_session_id = session.get("session_id") or str(uuid4())
        session["session_id"] = user_session_id
        get_user_chat()
        
        logging.info(f"✅ Cliente conectado: {user_session_id}")
        emit("status_conexao", {
            "data": "Conectado",
            "session_id": user_session_id,
            "timestamp": str(__import__('datetime').datetime.now())
        })
    except Exception as e:
        logging.error(f"❌ Erro na conexão: {str(e)}", exc_info=True)
        emit("erro", {"erro": "Falha ao conectar. Tente novamente."})

@socketio.on("enviar_mensagem")
def handle_message(data):
    try:
        texto = data.get("mensagem", "").strip()
        if not texto:
            emit("erro", {"erro": "A mensagem não pode estar em branco."})
            return

        if len(texto) > MAX_MESSAGE_SIZE:
            emit("erro", {"erro": f"Mensagem muito longa (máx: {MAX_MESSAGE_SIZE} caracteres)"})
            return

        logging.info(f"📨 Mensagem recebida da sessão {session.get('session_id')}: {texto[:50]}...")
        
        chat = get_user_chat()
        resposta = chat.send_message(texto)
        
        logging.info(f"✅ Resposta gerada: {resposta.text[:50]}...")
        emit("nova_mensagem", {
            "remetente": "bot",
            "texto": resposta.text,
            "timestamp": str(__import__('datetime').datetime.now())
        })
    except Exception as e:
        logging.error(f"❌ Erro ao processar mensagem: {str(e)}", exc_info=True)
        emit("erro", {"erro": "Ocorreu um erro ao gerar a resposta. Tente novamente."})

@app.route('/')
def serve_frontend():
    """Serve o arquivo HTML principal e arquivos estáticos"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'chatbot_steam_frontend')
    return send_from_directory(frontend_path, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS, etc)"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'chatbot_steam_frontend')
    return send_from_directory(frontend_path, filename)

@app.route('/health')
def health():
    """Endpoint de verificação de saúde do servidor"""
    return {"status": "ok", "service": "STEAM+ Sparky Chatbot", "timestamp": str(__import__('datetime').datetime.now())}

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)