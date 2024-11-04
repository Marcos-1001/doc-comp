import boto3
import os
from pdf2image import convert_from_path
import re
import json
import parsing_pdf
from PIL import Image
import pymupdf
from tqdm import tqdm
 
def convert_pdf_to_image(pdf_path, folder_path):
    print(pdf_path)
    images = convert_from_path(pdf_path)
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(folder_path, f'page_{i}.jpg')
        image.save(image_path, 'JPEG')
        image_paths.append(image_path)
    return image_paths


def extract_text_from_page(page):

    text = page.get_text('blocks')
    text = [block[4] for block in text]
    if len(text) >= 1: 
        return text
        
    
    pix = page.get_pixmap()
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    image.save('page.jpg')
    
    with open('page.jpg', 'rb') as file:
        image = file.read()    
        client = boto3.client('textract', region_name='us-east-1')

        response = client.detect_document_text(Document={'Bytes': image})
        text = []
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                text.append(item['Text'])
        
    # erase page.jpg
    os.remove('page.jpg')

    return text
    

def big2small(document, chunk_size=80): 
    """
    This function is gonna take every element's content in the json file and divide it into smaller parts
    """
    doc = json.load(open(document))
    new_doc = {}
    for key in doc:
        new_doc[key] = []

        element_to_list = doc[key].split(' ')
        
        for i in range(0, len(element_to_list), chunk_size):
            new_doc[key].append(key + " "+ " ".join(element_to_list[i:min(i+80, len(element_to_list))]))
    
    with open(document[:-5] + f"_small{chunk_size}.json", 'w', encoding='utf-8') as f:
        json.dump(new_doc, f)


def scanning_pdf(pdf_path, start_page=0, end_page=1000):
    path = os.path.join(os.getcwd(), "pdfs",pdf_path)

    document = pymupdf.open(path)
    text = ''


    sections_content = {}
    sections_name = {}
    section = ''
    header =  ''


    for page in tqdm(range(start_page, min(len(document), end_page))):
        text = extract_text_from_page(document[page])
        


        for line in range(len(text)):
        

            real_line = parsing_pdf.replace_special_characters(text[line])
            real_line = real_line.replace('\\"', '').replace('\n', ' ').replace('  ', ' ').replace('-', '●')
            
            
            if real_line in header:
                continue
            elif re.match(r'^[IXVL]+\.\d*', real_line) or re.match(r'^(\d+\.)+\s+\w', real_line):              
                section = real_line
                if len(section.split()) == 1: 
                    section = section + ' ' + parsing_pdf.replace_special_characters(text[line+1])

                    line += 1
                
                sections_content[section] = ''

                
                sections_name[section.split()[0]] = section # SAVES THE SECTION NUMBER AS KEY AND ALL THE SECTION NAME AS VALUE 
                
            elif section in sections_content:
                sections_content[section] += real_line + ' '
            else: 
                header += real_line + ' '
        
        



        final_sections_content = {}

        for section in sections_content:
            section_number = section.split()[0].split('.')
            concat_num =  ''
            final_section_name =  ''
            for number in range(len(section_number)):
                if section_number[number] == '': 
                    continue
                elif number == 0:
                    concat_num += section_number[number]+ '.'
                    if concat_num in sections_name:
                        final_section_name += sections_name[concat_num]
                
                else:             
                    concat_num += section_number[number] 
                    if concat_num in sections_name:
                        final_section_name += " " + sections_name[concat_num]
                    concat_num += '.'
                
                
                

            final_sections_content[final_section_name] = sections_content[section]
    
    #print(final_sections_content)
    json.dump(final_sections_content, open('jsons/tdr_v4.json', 'w'))
    return final_sections_content


    



result = scanning_pdf('tdr_v4.pdf', start_page=2 )
#print(result)
big2small('jsons/tdr_v4.json')
            

# Concat txt files in a single file

"""text = concat_txt_files('pdf_text')







"""




"""


json.dump(final_sections_content, open('jsons/tdr_scanned_2.json', 'w'))

big2small('jsons/tdr_scanned_2.json')
    
"""
