import boto3
import json 
import os
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
# pearson correlation
from scipy.stats import pearsonr



load_dotenv()

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.getenv('AWS_SESSION_TOKEN')



def claude_body(prompt : str, query : str):
        
    query = [{
        "role": "user",
        "content": query
    }]
    
    return json.dumps({              
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4090,
        "system": prompt,
        "messages": query,
        "temperature": 0.1,
        
    })

def embed_body(chunk_message : str):
    return json.dumps({
        'inputText' : chunk_message,
        
    })

def claude_call( bedrock : boto3.client, 
                user_message : str, 
                query : str,
                model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'):
    
    body = claude_body(user_message, query=query)

    response = bedrock.invoke_model(
        body = body,
        modelId = model_id,
        contentType = 'application/json',
        accept = 'application/json'
    )    


    return json.loads(response['body'].read().decode('utf-8'))

def vision_claude_call( bedrock : boto3.client,
                        user_message : str,
                        query : str,
                        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0:0'):
    
    
    
    body = claude_body(user_message, query=query)

    response = bedrock.invoke_model(
        body = body,
        modelId = model_id,
        contentType = 'application/json',
        accept = 'application/json'
    )    


    return json.loads(response['body'].read().decode('utf-8'))

def embed_call(bedrock : boto3.client, chunk_message : str):
    
    model_id = "amazon.titan-embed-text-v2:0"
    body = embed_body(chunk_message)

    response = bedrock.invoke_model(
        body = body,
        modelId = model_id,
        contentType = 'application/json',
        accept = 'application/json'        
    )    

    return json.loads(response['body'].read().decode('utf-8'))





def generate_prompt_compare_or_info(query):

    return f"""
        En el Estado Peruano se dan miles de licitaciones día a día para proyectos o compras. Estos contratos para que se aprueben pasan por un proceso largo de revisiones y cambios. 
        Tú eres una IA en reconocer que tipo de consulta te están haciendo y eres altamente.

        Dada una consulta tienes que poder clasificar si la consulta pide una comparación entre dos documentos u obtener información, y también tienes que identificar si la consulta pide explícitamente todo el documento o algo particular.

        Si la consulta es una comparación, entonces solamente escribe 'COMPARAR'. Si la consulta es para obtener información, entonces solamente escribe 'INFORMAR'.
        No escribas más que lo que se te ha pedido.

        Si la consulta pide explícitamente todo el documento o algo particular, entonces escribe 'TODO' o 'PARTICULAR' respectivamente. No escribas más que lo que se te ha pedido.

        Esta respuestas las tienes que devolver de esta manera: 

        ('COMPARAR' o 'INFORMAR'),('TODO' o 'PARTICULAR')

        <Query>
        {query}
        </Query>        
        """

def generate_result_based_query(query, final_result):

    return f"""
        En el Estado Peruano se dan miles de licitaciones día a día para proyectos o compras. Estos contratos para que se aprueben pasan por un proceso largo de revisiones y cambios. 
        Tú eres una IA en reconocer que tipo de consulta te están haciendo.

        Dado una query tienes que poder devolver la información solicitada basado en un grupo de respuestas obtenidas donde cada una de estas fue hecha con la query que fue traída como parámetro con un extracto del documento
        que es una seccion. Cada respuesta está separada por un '\\n------------\\n'. Extrae la información que es relevante para la query literalmente como se te ha entregado, no hagas ningún tipo de modificación. 
        Piensa dos veces si la respuesta que estás dando a la consulta es la correcta.

        
        <Query>
        {query}
        </Query>

        <Resultado>
        {final_result}
        </Resultado>

        """
def generate_improve_query():
    return """
        En el Estado Peruano se dan miles de licitaciones día a día para proyectos o compras. Estos contratos para que se aprueben pasan por un proceso largo de revisiones y cambios. 
        Tú eres una IA capaz de mejorar la consulta que se te ha dado con el fin de que el retrieval de la información sea más precisa en comparacion a la query original. Elige la mejor alternativa de mejora. 

        Tu valor de retorno tiene unicamente la query del usuario mejorada. No añadas más información que la que se te ha pedido, 
        tampoco divagues en la respuesta o menciones cosas como  "Después de analizar" o "Luego de revisar". Simplemente responde con la mejora de la query.
    """


# NOTA: Un dato no es RELEVANTE si este trata de una coma, un punto, un o varios espacios, un guión o cualquier otro tipo de dato que no aporte información relevante a la consulta, pues 
        #posiblemente sea un error ligero de lectura hecho por el parser.
        #        

def generate_prompt_for_comparison(retrieved_info, section, doc1, doc2, query):
    return f"""

        En el Estado Peruano se dan miles de licitaciones día a día para proyectos o compras. Estos contratos para que se aprueben pasan por un proceso largo de revisiones y cambios. 
        Tú eres una IA experta en evaluar las diferencias entre estos contratos. 

        Tu objetivo es que dado las diferencias que te he pasado decirme de manera más clara y concisa las diferencias entre los dos documentos. 
        Tienes que tener encuenta que todo lo que está delante de un '-' representa lo que se ha modificado del primer documento, y todo lo que está delante de un '+' representa lo que se ha modificado del segundo documento.
        
        Ten en cuenta que la respuesta que vas a dar sobre las diferencias tiene que guardar una FUERTE relacion con la query dada por el usuario. 

        Te estoy dando como contexto el contenido de ambos documentos (Documento 1 y Documento 2) y la consulta con el fin de que me des una respuesta más precisa.


        Por favor, responde con la información solicitada de manera literal, pero si lo que te he pasado es una cadena vacía o la información traída no guarda relación con lo solicitado, entonces pido exclusivamente que me digas que ambos documentos presentan la misma información. NO TE EXPLAYES MÁS DE LO NECESARIO. 
        Previamente a responder, piensa dos veces si la respuesta que estás dando a la consulta es la correcta. 
        
        
        

        El formato del archivo markdown que vas a generar como respuesta que tieneS que seguir es el siguiente:
            ### <nombre de la seccion y número que se recibe como parámetro>
            <respuesta extraida basda de la seccion>
        
        
        NOTA: Ten cuidado con la respuesta que estás dando realmente existe para ambos documentos, piensa dos veces si la respuesta que estás dando a la consulta es la correcta. Por más que eres una IA experta igual estás sujeta a equivocarte, 
        por lo cual siempre intenta mitigar la posibilidad de extraer información que no es relevante para la consulta o inexistente. 
                
        
        POR NINGÚN MOTIVO DEBES DEJAR DE RESPONDER CON EL FORMATO HTML SOLICITADO. ES TOTALMENTE MANDATORIO QUE RESPONDAS CON EL FORMATO SOLICITADO.        
        NO AÑADAS NINGÚN MENSAJE EXTRA COMO "DESPUES DE ANALIZAR" O "LUEGO DE REVISAR" O "DESPUES DE EXAMINAR" O SIMILARES. SIEMPRE DEBES MANTENER EL ORDEN DESCRIPTO ANTERIORMENTE.
            
        <Seccion>
        {section}
        </Seccion>

        <Diferencias>
        {retrieved_info}
        </Diferencias>

        <Documento1>
        {doc1}
        </Documento1>

        <Documento2>
        {doc2}
        </Documento2>
        """

def generate_prompt_for_retinfo(section,retrieved_info_1, retrieved_info_2 ,query):
    return f"""
        
        En el Estado Peruano se dan miles de licitaciones día a día para proyectos o compras. Estos contratos para que se aprueben pasan por un proceso largo de revisiones y cambios.
        Tú eres una IA experta en el rubro de extraer información exacta de los documentos de licitación basado en la consulta que se te realizó. 

        Dado dos documentos y una consulta, realiza la siguiente tarea en el siguiente orden: 

        1. Examina si la consulta realizada es una comparación o una solicitud de información.
        2. A partir de la consulta, extrae la información que sea relevante de los documentos.                     
        3. Si la consulta es para obtener información, entonces genera una respuesta basado en lo solicitado. 
            3.1 Si la información no se encuentra en los documentos, entonces debes devolver que no se encontró la información solicitada.
        
        4. Por cada respuesta que des, debes citar el extracto de cada documento que te ha llevado a la conclusión mencionada. Verifica dos veces si realmente el extracto existe o no.
        

        NOTA: Ten cuidado con la respuesta que estás dando realmente existe para ambos documentos, piensa dos veces si la respuesta que estás dando a la consulta es la correcta. Por más que eres una IA experta igual estás sujeta a equivocarte, 
        por lo cual siempre intenta mitigar la posibilidad de extraer información que no es relevante para la consulta o inexistente. 
        
        NOTA 2: Si vas a enumerar detalles en tu respuesta cada guión separalo por dos saltos de linea de esta manera '\\n\n'. Caso contrario, solo menciona la información relevante y terminalo en un salto de linea.

        Tu proceso de pensamiento en la parte del formato donde corresponde.
        


        El formato del archivo markdown que vas a generar como respuesta que tiene que seguir es el siguiente:
            ### <nombre y número de la seccion que se recibe como parametro>
            <respuesta extraida basda de la seccion>
            

        POR NINGÚN MOTIVO DEBES DEJAR DE RESPONDER CON EL FORMATO markdown SOLICITADO. ES TOTALMENTE MANDATORIO QUE RESPONDAS CON EL FORMATO SOLICITADO.
        NO AÑADAS NINGÚN MENSAJE EXTRA COMO "DESPUES DE ANALIZAR" O "LUEGO DE REVISAR" O "DESPUES DE EXAMINAR" O SIMILARES. SIEMPRE DEBES MANTENER EL ORDEN DESCRIPTO ANTERIORMENTE.

        <documento 1>
        {retrieved_info_1}
        </documento 1>
        
        <documento 2>
        {retrieved_info_2}
        </documento 2>
        
        <Seccion>
        {section}
        </Seccion>
        
        
        """

"""



<documento 2>
        {retrieved_info_2}
        </documento 2>
"""


"""

Separar dos prompts (Comparar - Informar)
Separar system usuario
Devolver Json con el formato que se pide

"""