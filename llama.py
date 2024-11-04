import base64
import boto3
import os
import re
import json
import parsing_pdf
from PIL import Image
import pymupdf
from tqdm import tqdm
def claude_body(query : list):
        
    query = [{
        "role": "user",
        "content": query
    }]
    
    return json.dumps({              
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4090,
        "messages": query,
        "temperature": 0.0,
        
    })


def vision_claude_call( bedrock : boto3.client,
                        query : str,
                        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'):
    
    
    
    body = claude_body( query=query)

    response = bedrock.invoke_model(
        body = body,
        modelId = model_id,
        contentType = 'application/json',
        accept = 'application/json'
    )    


    return json.loads(response['body'].read().decode('utf-8'))

bedrock = boto3.client(service_name = 'bedrock-runtime', 
                                region_name='us-east-1', 
                    )


images_path = []
current_dir = os.getcwd()   

for pdf in os.listdir('/home/marcos/Amber/poc-comp-documentos-marcos/pdf_images'):
    if pdf.endswith('.png'):
        with open(f'/home/marcos/Amber/poc-comp-documentos-marcos/pdf_images/{pdf}', 'rb') as file:
            image = file.read()
        
        image = base64.b64encode(image).decode('utf-8')

        images_path.append({
            "type" : "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image
            }
        })

images_path.append({
    "type"  : "text",
    "text": "Quiero que me extraigas el texto de este documento presente"
})
print(vision_claude_call(bedrock=bedrock,                         
                        query=images_path))
