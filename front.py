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
    embedding.truncate_the_tables(user)
    # save as pdf 
    with open(os.path.join(folder_path, 'pdfs', f'doc1-{user}.pdf'), 'wb') as f:
        f.write(doc1.getbuffer())
    with open(os.path.join(folder_path, 'pdfs', f'doc2-{user}.pdf'), 'wb') as f:
        f.write(doc2.getbuffer())
    st.write('Documentos cargados')

    # open the pdfs
    with st.spinner('Convirtiendo los documentos a texto...'):
        for i in range(1, 3):
            pdf_path = os.path.join(folder_path, 'pdfs', f'doc{i}-{user}.pdf')
            save_path = os.path.join(folder_path, 'jsons', f'doc{i}-{user}.json')
            doc = pymupdf.open(pdf_path)
            parsing_pdf.from_pdf_to_dictionary(doc, output_path=save_path)
    
    with st.spinner('Procesando los documentos...'):
        parsing_pdf.big2small(os.path.join(folder_path, 'jsons', f"doc1-{user}.json"))
        parsing_pdf.big2small(os.path.join(folder_path, 'jsons', f"doc2-{user}.json"))
    
    with st.spinner('Ingestando documentos...'):
        embedding.for_making_a_db(bedrock_runtime, document_1 = f"doc1-{user}", document_2 = f"doc2-{user}", username= user)
    



st.title('Comparador de documentos')
# usuario
st.write('Bienvenido a nuestro comparador de documentos')


user = st.text_input('Por favor, introduce tu correo electrónico')


# 
st.write('Por favor, sube dos documentos TDR no escaneados para poder compararlos')
# Make a chat 
# submit two documents
doc1 = st.file_uploader('Carga el documento 1')
doc2 = st.file_uploader('Carga el documento 2')

# check if docs are already uploaded in the system


if (user is not None and '@' in user.lower()):
    if doc1 is not None and doc2 is not None and st.button('Subir documentos'):     
        converting_pdf(doc1, doc2, user)

    exist_doc1 = os.path.exists(os.path.join(folder_path, 'jsons', f"doc1-{user}.json"))
    exist_doc2 = os.path.exists(os.path.join(folder_path, 'jsons', f"doc2-{user}.json"))
    print(exist_doc1, exist_doc2)
    
    
    if  exist_doc1 and exist_doc2:
        st.subheader('Chat')
        prompt = st.chat_input('Haz una pregunta sobre los documentos')
        if prompt :
            st.write(prompt)

            with st.spinner('Revisando documentos...'):
                response = main.query_function(bedrock_runtime, prompt, user=user)

            #print(response)
            st.markdown('Esto es lo que hemos encontrado en los documentos:')
            st.markdown(response)
            prompt = None




