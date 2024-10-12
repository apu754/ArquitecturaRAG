from flask import Blueprint, render_template, request
import os
import PyPDF2
import google.generativeai as genai

# Configurar la API de Gemini
os.environ["API_KEY"] = "APIKEy"
genai.configure(api_key=os.environ["API_KEY"])

main = Blueprint('main', __name__)


def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()
    
    print(text)    
    return text

def retrieve_documents_from_text(text, query, k=3):
    results = []
    query_keywords = query.lower().split()  # Divide la pregunta en palabras clave
    
    # Busca por párrafos en lugar de oraciones
    for paragraph in text.split("\n\n"):  # Dividir por párrafos
        paragraph_lower = paragraph.lower()
        # Busca si alguna palabra clave está en el párrafo
        if any(keyword in paragraph_lower for keyword in query_keywords):
            results.append(paragraph.strip())
        if len(results) >= k:
            break
    
    print("Documentos recuperados:", results)  # Verifica los resultados
    return results




def generate_answer(query, retrieved_docs, custom_prompt=None):
    # Construir el prompt con la opción de modificarlo
    if custom_prompt:
        combined_prompt = f"{custom_prompt}\n\nDocumentos relevantes:\n" + "\n".join(retrieved_docs) + f"\n\nPregunta: {query}\nRespuesta:"
    else:
        combined_prompt = f"Pregunta: {query}\n\nDocumentos relevantes extraídos del archivo PDF:\n" + "\n".join(retrieved_docs) + "\nPor favor, responde únicamente basándote en los documentos proporcionados. Si no hay información relacionada en los documentos, indica que no se encontró una respuesta adecuada."


    # Utilizar el modelo de Gemini para generar la respuesta
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(combined_prompt)

    # Obtener el texto generado (respuesta)
    answer = response.text

    # Contar los tokens (si el modelo permite obtener la cantidad de tokens usados)
    if hasattr(response, 'tokens_used'):
        tokens_used = response.tokens_used
    else:
        # Aproximación del conteo de tokens
        tokens_used = len(combined_prompt.split())

    return answer, tokens_used



@main.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        if "file" not in request.files or request.files["file"].filename == "":
            return "No se ha seleccionado ningún archivo."

        file = request.files["file"]  # El archivo subido
        question = request.form["question"]
        selected_prompt = request.form["prompt"]

        if file and question and selected_prompt:
            # Leer el contenido del archivo directamente desde la memoria sin guardarlo
            text = extract_text_from_pdf(file)  # 'file' es un archivo en memoria

            # Procesar los documentos y generar respuesta
            retrieved_docs = retrieve_documents_from_text(text, question)

            # Verificar si se encontraron documentos relevantes
            if not retrieved_docs:
                return render_template("result.html",
                                       question=question,
                                       docs=[],
                                       answer="El documento cargado no contiene información relevante para la pregunta formulada.",
                                       tokens=0,
                                       prompt=selected_prompt,
                                       doc_name=file.filename)

            # Crear el prompt personalizado con los documentos extraídos
            answer, tokens_used = generate_answer(question, retrieved_docs, selected_prompt)

            return render_template("result.html", 
                                   question=question, 
                                   docs=retrieved_docs, 
                                   answer=answer, 
                                   tokens=tokens_used, 
                                   prompt=selected_prompt, 
                                   doc_name=file.filename)

    return render_template("index.html")




