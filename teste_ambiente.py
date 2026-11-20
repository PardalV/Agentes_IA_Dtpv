from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()  # lê o .env e carrega a chave

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")

resposta = llm.invoke("Qual foi o ano da segunda guerra mundial?")
print(resposta.content)

from langchain_core.tools import tool

@tool
def somar(a: int, b: int) -> int:
    """Soma dois números inteiros."""
    return a + b

llm_com_ferramentas = llm.bind_tools([somar])

resposta = llm_com_ferramentas.invoke("Quanto é 17 + 25?")
print(resposta.tool_calls)