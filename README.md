# poc-comp-documentos-marcos

# Instalar 

```bash
python3 -m venv .venv 
pip install -r requirements.txt
```

# Variables de entorno
Añade el archivo .env en la carpeta DB. 

# Ejecutar el código 

- La BD está actualmente cargada con la data de los PDF's de tdr_v4 y tdr_v6. Si deseas cambiar de pdf (no escaneado), entonces en el archivo `embedding.py` modifica la llamada a la función `for_making_a_db` y en el archivo `main.py` modifica la función `query_function`
- Si quieres editar las queries, en el archivo main.py hay una lista que se llama queries. 
- Si quieres editar los prompts, en ai_call.py 

```bash
python3 main.py
```
