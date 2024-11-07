import boto3 
import os
import json
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import DB.db_connection as db
from tqdm import tqdm
from ai_call import embed_call, claude_call, generate_prompt_compare_or_info
from pprint import pprint
from difflib import SequenceMatcher, unified_diff
from sqlalchemy import and_


""" ----------------- CREDENTIALS -----------------""" 
load_dotenv()
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.getenv('AWS_SESSION_TOKEN')
""" ------------------------------------------------ """ 








def info_sections(retrieved_sections : list, document_1 : str = "tdr_v4"):
    """
    This function retrieves the information from all the sections in the list

    Parameters:
    retrieved_sections : list
        The list of sections to retrieve
    document : str
        The document to retrieve the sections from
    
    Returns:
    str
        The content of the sections    
    """
    document_1 = document_1.replace(".json", "")
    doc1 = json.load(open(os.path.join(os.getcwd(), 'jsons', f"{document_1}.json")))
    visited_sections = {}
    sections_content = []

    # Query -> chunk : 4.2
    # 4.2 : CHILDREN: 4.2.1, 4.2.2, 4.2.3  

    for section in retrieved_sections:
        stack = [section]

        while len(stack) > 0:
            section = stack[-1]
            stack.pop()


            if section in visited_sections:
                continue
            
            visited_sections[section] = True

            if section in doc1:
                
                if doc1[section]['content'] != "":
                    sections_content.append((section , doc1[section]['content']))

                children = doc1[section]['children']
                for child in children:
                    if child not in visited_sections:
                        stack.append(child)
    
    print("-------------------------------------")            
    print(f"Secciones mandadas al LLM:  {[f'{section[0]}' for section in sections_content]}")
    print("-------------------------------------")
    

    return sections_content


def diferences_between_docs(sections, username= "username"):

    """
    This function returns the differences between the sections of the two documents

    Parameters:
    sections : list
        The list of sections to retrieve the differences from
    
    Returns:
    str
        The differences between the sections    
    """
    """db.diff_table.difference"""

    # ESTO ES MUY INEFICIENTE - HAY QUE CAMBIARLO, NO PUEDO ESTAR TRAYENDO TODA LA TABLA
    #print("Username: ", username)

    differences = db.Session.execute(
        db.select(db.diff_table.section, db.diff_table.difference ).filter(
            and_(db.diff_table.username == username , db.diff_table.section == sections)
            )
    )
    print(f"Username: {username} - Sections: {sections}")
    
    return differences
    
    

def retrieve_info(bedrock : boto3.client, query, top_k=4, document = "tdr_v4", username = "username"):
    """
    Returns the top_k most similar chunks to the query based on the cosine similarity of the embeddings

    Parameters:
    bedrock : boto3.client
        The bedrock client
    query : str
        The query to search for
    top_k : int
        The number of most similar chunks to return

    Returns:
    list
        A list of tuples with the section [0] and the chunk [1]

    """
    document = document.replace(".json", "")

    query_embedding = embed_call(bedrock, query)['embedding']
    
    KNN = db.Session.execute(
        db.select(db.Chunks_table.section,
                  db.Chunks_table.chunk).filter(db.Chunks_table.username == username )
                  .order_by(
                db.Chunks_table.embedding.cosine_distance(query_embedding)
            ).limit(top_k))

    KNN = [row for row in KNN]

    
    return KNN
    
    
def insert_data(elements: list):    
    
    db.Session.add_all(elements)
    try:
        db.Session.commit()  # Commits the transaction
    except Exception as e:
        db.Session.rollback()  # Rollback in case of any error
        print(f"Error occurred: {e}")


def make_chunk_table(bedrock : boto3.client, knowledge_base : dict,  document_id: str, username = "username"):

    """
    This function creates takes the chunks from every section in the document and creates a table with the embeddings    
    """
    
    knowledge_base_content = [text for text in knowledge_base.values()]
    knowledge_base_key = [key for key in knowledge_base.keys()]
    elements = []




    for key in tqdm(range(0, len(knowledge_base_key))):
        for chunk in range(0, len(knowledge_base_content[key])):
            
            response_body = embed_call(bedrock, knowledge_base_content[key][chunk] )
            elements.append(
                                db.Chunks_table(
                                            section = knowledge_base_key[key],
                                            document = document_id, 
                                            chunk = knowledge_base_content[key][chunk], 
                                            embedding = response_body['embedding'],
                                            username = username
                                )
                            )
    print(f"The number of elements is {len(elements)}") 
    insert_data(elements)    






def make_diff_table(document_1, document_2, username = "username"):
    """
    This function creates a table with the differences between the sections
    """

    folder_path = os.getcwd()
    doc1 = json.load(open(os.path.join(folder_path, 'jsons', f"{document_1}.json")))
    doc2 = json.load(open(os.path.join(folder_path, 'jsons', f"{document_2}.json")))
    
    
    diff_list = []

    used_keys = {}

    for key in doc1:
        used_keys[key] = True
        if key not in doc2:
            diff_list.append(
                    db.diff_table(
                        section = key,
                        difference = f"Esta seccion no existe en el {document_2}",
                        username = username
                    )
                )
        else: 
            diff_ratio = SequenceMatcher(None, doc1[key]['content'], doc2[key]['content']).ratio()

            if diff_ratio <  1:

                diff = unified_diff(doc1[key]['content'].splitlines(), doc2[key]['content'].splitlines(), lineterm="")
                diff = "\n".join(diff)
                diff_list.append(
                    db.diff_table(
                        section = key,
                        difference = diff,
                        username = username
                    )
                )
    for key in doc2:
        if key not in used_keys:            
            diff_list.append(
                    db.diff_table(
                        section = key,
                        difference = f"Esta seccion no existe en el {document_1}",
                        username = username
                    )
                )
    
    insert_data(diff_list)


    
    

def for_making_a_db(bedrock_runtime, document_1 = "tdr_v4", document_2 = "tdr_v6", username = "username"):
    
    
    currrent_directory = os.getcwd()
    document_1_op = os.path.join(currrent_directory, 'jsons', f"{document_1}_small80.json")
    with open(document_1_op) as f:
        knowledge_base_1 = json.load(f)

    document_2_op = os.path.join(currrent_directory, 'jsons', f"{document_2}_small80.json")
    with open(document_2_op) as f:
        knowledge_base_2 = json.load(f)
    
    
    
    make_chunk_table(bedrock_runtime, knowledge_base_1,  document_id=document_1, username = username)
    make_chunk_table(bedrock_runtime, knowledge_base_2,  document_id=document_2, username = username)
    make_diff_table(document_1, document_2, username = username)
    



def truncate_the_tables(username = "username"):


    # truncate all row with the username "username"
    db.Session.execute(db.Chunks_table.__table__.delete().where(db.Chunks_table.username == username))
    db.Session.execute(db.diff_table.__table__.delete().where(db.diff_table.username == username))
    
    db.Session.commit()
    db.Session.close()






#if __name__ == '__main__':    
    
    #for_making_a_db(bedrock_runtime)
    #print(claude_call(bedrock_runtime, "\n\nHuman: Cual es el proposito del documento?\n\nAssistant:", 'anthropic.claude-v2'))
    
    #for_making_a_db(bedrock_runtime, document_1="T NUBE 1", document_2="TDR AMAZONAS NUBE 2")
    #for_making_a_db(bedrock_runtime, document_1="tdr_scanned", document_2="tdr_scanned_2")