import os
import pymupdf
import re
import json
from pprint import pprint
from deepdiff import DeepDiff
from difflib import SequenceMatcher, unified_diff

def replace_special_characters(text: str) -> str:

    return text.replace(
        "\u00e1", "a").replace(
        "\u00e9", "e").replace(
        "\u00ed", "i").replace(
        "\u00f3", "o").replace(
        "\u00fa", "u").replace(
        "\u00f1", "n").replace(
        "\u00c1", "A").replace(
        "\u00c9", "E").replace(
        "\u00cd", "I").replace(
        "\u00d3", "O").replace(
        "\u00da", "U").replace(
        "\u00d1", "N").replace(
        "\u00fc", "u").replace(
        "\u00dc", "U")


def discover_head_text(text: str) -> str:
    """
    This function is used to discover the head text of the section
    Parameters:
        text: str
            The text to be analyzed
    Returns:
        str
            The head text of the document
    """
    head_text=  ""
    for line in text:
        real_line = " ".join(line[4].split('\n'))
        real_line = replace_special_characters(real_line)
        
        for word in real_line.split(' '):
            if word != "INDICE":
                head_text += word + " "
            else:
                return head_text
    
    return head_text


def avoid_head_foot(text: str, head_text : str) -> bool:
    """
    This function is used to identify the head and foot of the document and avoid them
    Parameters:
        text: str
            The text to be analyzed
        head_text: str
            The head text of the document
    Returns:
        bool
            True if the text is the head or foot of the document
    """
    
    # text intersection
    similarity_counter = 0 
    
    for word in text.split(' '):
        if word in head_text:
            similarity_counter += 1


    return re.match(r'(Pagina\s*)?(\d+)\s+de\s+(\d+)', text) or similarity_counter >= 0.98 * len(text.split(' '))
        
def parsing_table(table):
    """
    This function is used to parse a table
    Parameters:
        table: pymupdf.Table
            The table to be parsed
    Returns:
        list
            The table parsed

    - El problema con las tablas que las celdas combinadas generan None's en la lectura de la tabla
    - Inutilizado por el momento 
    """


    row = table.rows[0]
    
    

    table_extract = table.extract()
    table_content = [ [None]* len(table_extract[0])]  

    for row in table_extract: # Avoiding the header
        row_content = []
        
        for cell in  range(len(row)):
            cell_content = row[cell]
            if cell_content == None:
                cell_content = table_content[-1][cell]
            row_content.append(cell_content)
            
        table_content.append(row_content)

    #pprint(table_content)

    final_string = ""
    for row in table_content:
        if None not in row:
            final_string += " ".join(row).replace('\n', '') + "\n"
        else:
            final_string += ""
    
    return table_content



def index_from_indices_page(text: str):
    index = {}
    for line in text:
        real_line = line[4].replace('\n', ' ').replace('  ', ' ')
        real_line = replace_special_characters(real_line)
        
        if re.match(r'(\d+\.)+\s+\w', real_line):
                        
            

            # This line is to avoid the page number and tabs
            limit = len(real_line)
            izq_limit = 0
            for idx in range(len(real_line)-1, 0, -1):
                if not real_line[idx].isalpha():
                    limit = idx
                else: 
                    break
            # -------------------------------------------
            
            real_line = real_line[:limit]
            for idx in range(0, len(real_line)):
                if real_line[idx].isalpha():
                    izq_limit = idx
                    break
            key = real_line[izq_limit:]
                    

            
            index[key] = real_line
                    
    return index

def erase_last_spaces(text: str) -> str:
    """
    This function is used to erase the last spaces of a text
    Parameters:
        text: str
            The text to be analyzed
    Returns:
        str
            The text without the last spaces
    """
    for idx in range(len(text)-1, 0, -1):
        if text[idx] != ' ':
            return text[:idx+1]
    return text

def from_pdf_to_dictionary(document: pymupdf.Document, output_path: str = None):
    """
    Extracts the text from a pdf document and saves it in a jsonfile
    Parameters: 
        document: pymupdf.Document
            The pdf document to extract the text from
        output_path: str
            The path to save the json file    
    """
    
    

    index_by_subsect = {}
    key = None

    head_text = discover_head_text(document[1].get_text('blocks'))
    
    # This line is to avoid errors between the index and the title in the document
    correct_indices = index_from_indices_page(document[1].get_text('blocks'))
    
    document_size = len(document)
    text_block = ""
            
    # [2, final] Avoiding the title and index pages
    shift = 0 
    for page in range(2, document_size):
        text = document[page].get_text('blocks')

        for line in text:
            # This code line gives the text of the line
            real_line = line[4].replace('\n', ' ').replace('  ', ' ')
            real_line = replace_special_characters(real_line)

            # This segments the text into sections
            if re.match(r'^(\d+\.)+\s+\w', real_line):
                if key is not None: 
                    index_by_subsect[key]['content'] = text_block.replace('.', '.\n').replace('-', '●') # TEMPORAL - LA IDEA ES GUARDARLO COMO UNA LINEA ENTERA  
                    
        
                section_text = None
                key = erase_last_spaces(real_line)
                
                key_list = key.split(' ')



                # This avoids the case when the section is too long
        
                if len(key_list) > 10:
                    new_key = key_list[0] + " " + key_list[1]

                    for word in range(2, len(key_list)):
                        if key_list[word].isupper() or key_list[word].islower():
                            new_key += " " + key_list[word]
                        else:
                            break

                    section_text = " ".join(key_list[word:])
                    key = new_key

                
                # GET ONLY THE TITLE OF THE SECTION
                for idx in range(len(key)):
                    if key[idx].isalpha():
                        break                
                tempkey = key[idx:]
                numkey = key.split(' ')[0]
                
                
                # Replace the key with the correct one
                is_in_correct : bool = False
                for _key in list(correct_indices.keys()):
                    if _key in tempkey:
                        key = correct_indices[_key]
                        is_in_correct = True
                        break

                if not is_in_correct and len(numkey) > 2:
                    
                        lastkey = 0
                        all_keys = list(index_by_subsect.keys())
                        for _key in range(len(all_keys)):
                            if len(all_keys[_key].split(' ')[0].split('.'))  < len(numkey.split('.')):
                                lastkey = _key
                        
                        
                        


                        key = all_keys[lastkey].split(' ')[0] + key[len(all_keys[lastkey].split(' ')[0]) :]



                    
                    

                # --------------------------------

                
                index_by_subsect[key] = {}
                index_by_subsect[key]['content'] = ""
                index_by_subsect[key]['children'] = []
                index_by_subsect[key]['parent'] = ""
                text_block = section_text if section_text is not None else ""
            
            elif avoid_head_foot(real_line, head_text=head_text):  # This avoids the page number and the head
                continue

            elif key is not None:   # This fills the sections with the text
                text_block += " " + real_line
        
        
        if page == document_size - 1:
            index_by_subsect[key]['content'] = text_block.replace('.', '.\n').replace('-', '●')
    
    



    """ This piece of code is to concatenate the name of the sections with subsections"""
    
    for key in index_by_subsect:
        key_number = key.split(' ')[0] # this gets the number of the section - 1.1, 1.2, 1.3, etc
        
        key_number_l = key_number.split('.')  # this gets the first number of the section - 1, 2, 3, etc
        key_number_l = key_number_l[:len(key_number_l)-1] 

        children = []
        
    
        
        for key2 in index_by_subsect: 
            key2_number = key2.split(' ')[0]
            
            key2_number_l = key2_number.split('.')
            key2_number_l = key2_number_l[:len(key2_number_l)-1]

            #print(f"\t{key2_number} - {key2_number_l} - {key_number != key2_number} - {len(key_number_l)+1 == len(key2_number_l)} - {key2_number.startswith(key_number)}")
            
            if key_number != key2_number and len(key_number_l)+1 == len(key2_number_l) and key2_number.startswith(key_number): 
                children.append(key2)
                index_by_subsect[key2]['parent'] = key


        index_by_subsect[key]['children'] = children        

        """"""
    index_by_subsect["Documento completo"] = {}
    index_by_subsect["Documento completo"]['parent'] = ""
    index_by_subsect["Documento completo"]['children'] = []
    index_by_subsect["Documento completo"]['content'] = "Esto abarca absolutamente todo el documento completo"
    for key in index_by_subsect:
        if index_by_subsect[key]['parent'] == "":
            index_by_subsect["Documento completo"]["children"].append(key)




    # save in json file
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index_by_subsect, f)


def big2small(document: str, chunk_size: int = 80): 
    """
    This function is gonna take every element's content in the json file and divide it into smaller parts
    """
    doc = json.load(open(document))
    new_doc = {}
    for key in doc:
        new_doc[key] = []
        
        
        element_to_list = doc[key]['content'].split(' ')
        for i in range(0, len(element_to_list), chunk_size):
            new_doc[key].append(key + " "+ " ".join(element_to_list[i:min(i+80, len(element_to_list))]))
    
    with open(document[:-5] + f"_small{chunk_size}.json", 'w', encoding='utf-8') as f:
        json.dump(new_doc, f)
    
    
        


    # save in plain text


if __name__ == '__main__':
    folder_path = os.getcwd()
    # extract text from pdf
    
    for file in os.listdir(os.path.join(folder_path, 'pdfs')):
        if file.endswith('.pdf'):
            pdf_path = os.path.join(folder_path, 'pdfs', file)
            save_path = os.path.join(folder_path, 'jsons', file.replace('.pdf', '.json'))
            print(f"Extracting text from {pdf_path}")
            doc = pymupdf.open(pdf_path)  
            from_pdf_to_dictionary(doc, output_path=save_path)
    
    
    

    
    big2small(os.path.join(folder_path, 'jsons', "tdr_v4.json"))
    big2small(os.path.join(folder_path, 'jsons', "tdr_v6.json"))
    
    """
    tdr_v4 = json.load(open(os.path.join(folder_path, 'jsons', "TDR AMAZONAS NUBE 1.json")))
    tdr_v6 = json.load(open(os.path.join(folder_path, 'jsons', "TDR AMAZONAS NUBE 2.json")))
    i =0 
    for key in tdr_v4:
        print("----"*20)
        #pprint(tdr_v4[key][0])
        #pprint(tdr_v6[key][0])
        print(key)            
        if key not in tdr_v6:
            print(f"No in tdr_v6")
            continue
        if SequenceMatcher(None, tdr_v4[key][0], tdr_v6[key][0]).ratio() < 1:
            diff = unified_diff(tdr_v4[key][0].splitlines(), tdr_v6[key][0].splitlines(), lineterm="")
            print("\n".join(diff))
        else: 
            print("No differences")
        print("----"*20)
        """


                  


    
