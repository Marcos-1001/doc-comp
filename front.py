import os
import streamlit as st
import parsing_pdf
import embedding
import pymupdf
import main
import boto3

folder_path = os.getcwd()
bedrock_runtime =  boto3.client(
                                service_name = 'bedrock-runtime',
                                region_name='us-east-1',
                            )   

def converting_pdf(doc1, doc2, user):
    embedding.truncate_the_tables()
    # save as pdf 
    with open(os.path.join(folder_path, 'pdfs', 'doc1.pdf'), 'wb') as f:
        f.write(doc1.getbuffer())
    with open(os.path.join(folder_path, 'pdfs', 'doc2.pdf'), 'wb') as f:
        f.write(doc2.getbuffer())
    st.write('Documentos cargados')

    # open the pdfs
    with st.spinner('Convirtiendo los documentos a texto...'):
        for i in range(1, 3):
            pdf_path = os.path.join(folder_path, 'pdfs', f'doc{i}.pdf')
            save_path = os.path.join(folder_path, 'jsons', f'doc{i}.json')
            doc = pymupdf.open(pdf_path)
            parsing_pdf.from_pdf_to_dictionary(doc, output_path=save_path)
    
    with st.spinner('Procesando los documentos...'):
        parsing_pdf.big2small(os.path.join(folder_path, 'jsons', "doc1.json"))
        parsing_pdf.big2small(os.path.join(folder_path, 'jsons', "doc2.json"))
    
    with st.spinner('Creando la base de datos...'):
        embedding.for_making_a_db(bedrock_runtime, document_1 = "doc1", document_2 = "doc2", user = user)
    



st.title('Comparador de documentos')
# usuario
st.write('Bienvenido a nuestro comparador de documentos')
user = st.text_input('Por favor, introduce tu nombre')

# 
st.write('Por favor, sube dos documentos para poder compararlos')
# Make a chat 
# submit two documents
doc1 = st.file_uploader('Carga el documento 1')
doc2 = st.file_uploader('Carga el documento 2')




if doc1 is not None and doc2 is not None and st.button('Subir documentos') and user is not None:     
    converting_pdf(doc1, doc2, user)

    
st.subheader('Chat')

prompt = st.chat_input('Haz una pregunta sobre los documentos')
if prompt:
    with st.spinner('Revisando documentos...'):
        response = main.query_function(bedrock_runtime, prompt, user=user)
    
    print(response)
    st.markdown('Esto es lo que hemos encontrado en los documentos:')
    st.markdown(response)
    prompt = None




