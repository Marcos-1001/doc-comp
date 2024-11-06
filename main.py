from ai_call import embed_call, claude_call, generate_prompt_compare_or_info, generate_prompt_for_retinfo,  generate_result_based_query, generate_prompt_for_comparison
from embedding import retrieve_info, info_sections, diferences_between_docs
from pprint import pprint
import boto3
from tqdm import tqdm
import time 
import concurrent.futures
import json

bedrock_runtime =  boto3.client( 
                                service_name = 'bedrock-runtime', 
                                region_name='us-east-1', 
                            )



def is_comparison(bedrock: boto3.client, 
                  query: str) -> bool:
    """
    This function determines if the query is a comparison or a question
    """

    prompt = generate_prompt_compare_or_info(query)

    response = claude_call(bedrock=bedrock,                            
                           user_message=prompt, 
                            query=query
                            )['content'][0]['text']
    
    return response



def call_claude_comparison(bedrock: boto3.client,    
                           section: str,                           
                            retrieved_info_1: str,
                            retrieved_info_2: str,
                            query: str, 
                            username: str = "user"
                        ) -> str:
    """
    This function calls the model and returns the response
    """
    
    differences = diferences_between_docs(sections=section, username=username)
    
    
    differences = [f"{difference[0]}: {difference[1]}" for  difference in differences]

    #print (differences)
    
    prompt = generate_prompt_for_comparison(retrieved_info=differences,
                                            section=section,
                                            doc1=  retrieved_info_1,
                                            doc2=   retrieved_info_2,
                                            query=query
                                            )

    call = claude_call(bedrock=bedrock, 
                        user_message=prompt,
                        query=query)
    
    return  call['content'][0]['text']

def call_claude_async(bedrock: boto3.client, 
                      section: str,
                      retrieved_info_1: str,
                        retrieved_info_2: str,
                        query: str,
                        username: str = "user"
                        ) -> str:
                        
    """
    This function calls the model and returns the response
    """
    prompt = generate_prompt_for_retinfo(section=section,
                                        retrieved_info_1= retrieved_info_1, 
                                        retrieved_info_2= retrieved_info_2, 
                                        query=query)
    call = claude_call(bedrock=bedrock, 
                        user_message=prompt,
                        query=query)
    
    return  call['content'][0]['text']
                      

def query_function(bedrock : boto3.client, 
                   query : str, 
                   top_k : int = 4,
                   user : str = "user" ) -> str:
    """
    This function retrieves the top_k most similar chunks to the query based on the cosine similarity of the embeddings
    """
    
    
    response = is_comparison(bedrock, query)

    #print(response)
    #exit()

    #query = improve_query(bedrock, query)
    
    retrieved_info_doc1 = retrieve_info(bedrock, query, top_k, username=user)
    retrieved_sections = list(set([section for section, chunk in retrieved_info_doc1]))
    
    # Gets the content of the sections and joins them in a single string 
    print("----------------------------------------------")
    print("Secciones encontradas: ", retrieved_sections)
    print("----------------------------------------------")
    content_sections_1 = info_sections(retrieved_sections, document_1=f"doc1-{user}")
    content_sections_2 = info_sections(retrieved_sections, document_1=f"doc2-{user}")

    async_func = call_claude_async
    if 'COMPARAR' in response:     
        print("ESTAMOS COMPARANDO")
        async_func = call_claude_comparison


    result = [""] * len(content_sections_1)
    for content in range(len(content_sections_1)):
        print(f"Seccion: {content_sections_1[content][0]}")
    # Use ThreadPoolExecutor to parallelize the calls to the model
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Create a list of futures
        """
        All functions have the same parameters 
                            (bedrock, section, retrieved_info_1, retrieved_info_2, query)
        
        Remember that info_sections returns a list of tuples with the section and the content
        """

        futures = [executor.submit(
                                    async_func, bedrock, 
                                    content_sections_1[content][0], 
                                    content_sections_1[content][1], 
                                    content_sections_2[content][1], 
                                    query,
                                    user                                    
                                ) 
                   for content in range(len(content_sections_1))]
        


        # Collect the results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result[i] = future.result()
    
    # convert string to dictionary
    

    result = sorted(result)
    
         
    return "\n\n".join(result)
    

    


    

def main():

    min_time = 100000
    max_time = -1
    avg_time = 0



    """
    Queries antiguas
        "Hablame sobre los plazos",
        "Dame información sobre los servicios de gestion de identidad y acceso",
        "Dentro de las caracteristicas de la nube, es obligatoria la certificacion ISO 27020?",
        "Es cierto que el postor debe acreditar 30000 soles como el monto facturado acumulado?",
        "El servicio de gestion de dns debe tener minimo de disponibilidad del 70.9%?",
        "Con que anexos cuenta?",
        "Cuales son las formas de pago?",
    """

    """
    
    
    """

    queries = [

        #"Cuáles son las diferencias entre las características y condiciones del servicio a contratar para los 2 documentos?",
        #"Que es lo mas relevante en tomar en cuenta en las otras consideraciones para la ejecucion de la prestacion?",
        #"De la seccion 2, 3 y 6 del documento, qué información diferencia ambos documentos?",
        #"Que diferencias se encuentran dentro las consideraciones para la ejecucion de prestacion",        
        "Nosotros como desarrolladores, cuáles son los principales cambios en todo el documento que debemos tener en cuenta en el segundo documento?" 
    ]

    for query in queries:
    
    
        chrono = time.time()
        
        print(f"Query: {query}")
        text = query_function(bedrock_runtime, query)
        # Write the response to a file
        with open("response.txt", "w") as file:
            file.write(text)
        
        time_query = time.time() - chrono
        min_time = min(min_time, time_query)
        max_time = max(max_time, time_query)
        avg_time += time_query/len(queries)
    
    

    print(f"Min time: {min_time}")
    print(f"Max time: {max_time}")
    print(f"Avg time: {avg_time}")
    
    

    """print(query_function(bedrock_runtime,
                         "Hablame sobre los plazos"))
    
    
    print(query_function(bedrock_runtime, 
                         "Dame información sobre los servicios de gestion de identidad y acceso")) 
    print("----------------------------------------------")
    print(query_function(bedrock_runtime, 
                         "Cuales son las diferencias entre los documentos para la subseccion soporte?")) 
    print("----------------------------------------------")
    print(query_function(bedrock_runtime, 
                         "Es cierto que el postor debe acreditar 30000 soles como el monto facturado acumulado?"))
    print("----------------------------------------------")
    print(query_function(bedrock_runtime, 
                         "El servicio de gestion de dns debe tener minimo de disponibilidad del 70.9%?"))
    print("----------------------------------------------")
    print(query_function(bedrock_runtime, 
                         "Con que anexos cuenta?"))
    print("----------------------------------------------")
    print(query_function(bedrock_runtime, 
                         "Cuales son las formas de pago?"))"""
    """
    """

    """
    print(query_function(bedrock_runtime, 
                         "Cuales son las diferencias entre ambos documentos para redis?"))
    print(time.time()-time_set)
    print("----------------------------------------------")
    time_set = time.time()
    print(query_function(bedrock_runtime, 
                         "Cuales son las diferencias entre ambos documentos para personal clave?"))                  
    print(time.time()-time_set)
    print("----------------------------------------------")
    time_set = time.time()
    print(query_function(bedrock_runtime, 
                         "Cuanto es el monto minimo facturado para participar de la licitacion en el primer documento?"))                  
    print(time.time()-time_set)
    print("----------------------------------------------")
    time_set = time.time()
    print(query_function(bedrock_runtime, 
                         "Cual es la certificación que trata sobre la calidad?"))      
    print(time.time()-time_set)
    print("----------------------------------------------")
    time_set = time.time()
    print(query_function(bedrock_runtime, 
                         "Cuales son las diferencias entre ambos documentos para la forma de pago?"))      
    print(time.time()-time_set)
    print("----------------------------------------------")
    time_set = time.time()
    print(query_function(bedrock_runtime, 
                         "Cuáles son las diferencias entre las características y condiciones del servicio a contratar para los 2 documentos?"))
    
    print("----------------------------------------------")
    time_set = time.time()
    print(query_function(bedrock_runtime, 
                         "Nosotros como desarrolladores, cuáles son los principales cambios que debemos tener en cuenta en el segundo documento?"))
    """
    



    #while True:
     #   query = input("Ingrese su pregunta: ")
      #  print(query_function(bedrock_runtime, query))
       # print("\n--------------------\n")
    
if __name__ == '__main__':
    main()



"""
- NO LLAMAR A LAS FUNCIONES DE BD 
- COT -> DIVIDIR EN SISTEMA Y HUMANO
- PEDIR AL LLM QUE EXPLIQUE SU RESPUESTA

"""