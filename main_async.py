from google_drive.google_drive_client import authenticate_drive, get_or_create_gd_folder, upload_file
import google.generativeai as genai
from dotenv import load_dotenv
from urllib.parse import quote
import pandas as pd
import requests
import base64
import logging
import json
import ssl
import os
import asyncio
import aiohttp
from datetime import datetime

ssl._create_default_https_context = ssl._create_unverified_context

# directories
current_directory = os.getcwd()
image_base_dir = os.path.join(current_directory, 'Images')
os.makedirs(image_base_dir, exist_ok=True)

# Log directory
log_directory = os.path.join(current_directory, 'logs')
os.makedirs(log_directory, exist_ok=True)

# Log file path
log_file = os.path.join(log_directory, f'{datetime.today().date()}.log')

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)


master_queries_for_plagas = [
    '[nombre_común] en plantas de [especies_afectadas] - [Subtipo] ([Nombre Científico]) en [parte_afectada]. El daño visible incluye [Daño]',
    'Síntomas de infección por [nombre_común] en [especies_afectadas] - [Subtipo] ([Nombre Científico])',
    'Primer plano de la infestación de [Subtipo] ([Nombre Científico]) en [especies_afectadas]',
    'Vista detallada de [nombre_común] en [especies_afectadas] - [Subtipo] ([Nombre Científico]). [parte_afectada] presenta [Daño]',
    'Infestación de [Subtipo] ([Nombre Científico]) en [especies_afectadas], afectando [parte_afectada]. Indicios incluyen [Daño]',
    'Síntomas de [nombre_común] ([Nombre Científico]) en [especies_afectadas], afectando específicamente [parte_afectada]',
    'Imágenes de alta calidad de [nombre_común] que afectan [parte_afectada] de plantas cítricas, mostrando [Daño]',
    '[nombre_común] que afecta a [especies_afectadas] - [Subtipo] ([Nombre Científico]), afectando [parte_afectada]'
    # '[Nombre Científico]',
    # '[Nombre Científico] - [nombre_común]',
    # '[Nombre Científico] - [nombre_común] - [parte_afectada]',
    # '[Nombre Científico] - [nombre_común] - [Subtipo]',
    # '[Nombre Científico] - [nombre_común] - [Subtipo] - [Daño]',
    # '[nombre_común]',
    # '[nombre_común] - [Subtipo]',
    # '[nombre_común] - [Subtipo]- [parte_afectada]',
    # '[nombre_común] - [parte_afectada]',
    # '[nombre_común] - [parte_afectada] - [Daño]'
]
master_queries_for_Deficiencias = [
    "Imágenes de [disorder] mostrando [characteristic] en [affected_part]",
    "Síntomas de [disorder] con [characteristic] visible en [affected_part]",
    "Primer plano de [disorder] con [characteristic] en [affected_part]",
    "[characteristic] como síntoma de [disorder] que afecta [affected_part]",
    "Vista detallada de [disorder] con [characteristic] afectando [affected_part]",
    "Imágenes de alta resolución de [disorder] y [characteristic] en [affected_part]",
    "[disorder] causando [characteristic] en [affected_part]",
    "Signos visibles de [Disorder] - [Characteristic] en [affected_part]",
]


async def get_or_create_folder( folder_name, base_dir=image_base_dir):
    """
    Retrieve folder path or create it if it doesn't exist.
    """
    image_folder_path = os.path.join(base_dir, folder_name)
    os.makedirs(image_folder_path, exist_ok=True)

    return image_folder_path


async def load_excel_data(excel_file, sheet_name):
    """
    Load and preprocess the Excel data.
    """
    try:
        data = pd.read_excel(excel_file, header=1, sheet_name=sheet_name)
        if sheet_name == 'Plagas':
            data = data.drop(data.columns[:2], axis=1).reset_index(drop=True)
        elif sheet_name == 'Deficiencias':
            data.rename(columns={data.columns[0]: 'disorders'}, inplace=True)
        else:
            raise ValueError(f"Sheet name '{sheet_name}' not recognized.")
        return data
    except FileNotFoundError:
        logging.error(f"File {excel_file} not found.")
        return None
    except Exception as e:
        logging.error(f"Error loading Excel data: {e}")
        return None


async def extract_keywords_plagas(df_row):
    """
    Extracts keywords for search query from pandas dataframe row.
    """
    disease_type = df_row["Tipo"]
    # print(f'index: {index} \ntype: {disease_type}')

    sub_type = df_row["Subtipo"]
    # print(f'subtype: {sub_type}')

    common_name = df_row["Nombre Común"]
    # print(f'common name: {common_name}')

    scientific_name = df_row["Nombre Científico"]
    # print(f'scientific name: {scientific_name}')

    affected_part = df_row["Parte Afectada"] if not pd.isna(df_row["Parte Afectada"]) else 'plant body'
    # print(f'affected part: {affected_part}')

    affected_species = df_row["Especie Afectada"] if not pd.isna(df_row["Especie Afectada"])  else 'citrus plant'
    # print(f'affected_species: {affected_species}')

    damage = df_row["Daño"] if not pd.isna(df_row["Daño"]) else 'damage'
    # print(f'damage: {damage} \n')

    keyword_data = {
        "Tipo": disease_type,
        'Subtipo': sub_type,
        'nombre_común': common_name,
        'Nombre Científico': scientific_name,
        'parte_afectada': affected_part,
        'especies_afectadas': affected_species,
        'Daño': damage
    }

    return keyword_data


async def extract_keywords_defici(disorder, row):
    """
    Extract keywords specific to 'Deficiencias' from the data row.
    """
    return {
        'disorder': disorder,
        'characteristic': row["Característica"],
        'affected_part': row["Parte Afectada"] or 'plant body'
    }


async def generate_queries(query_templates, keywords):
    """
    Generate search queries based on templates and keywords.
    """
    queries = []
    for template in query_templates:
        query = template
        for key, value in keywords.items():
            query = query.replace(f'[{key}]', value)
        queries.append(query)
    return queries


# async def generate_queries(keywords):
#     """
#     Generate search queries based on keywords.
#     """
#     queries = []
#     for query in master_queries:
#         result = query.replace('[nombre_común]', keywords['common_name'])
#         result = result.replace('[especies_afectadas]', keywords['affected_species'])
#         result = result.replace('[Subtipo]', keywords['sub_type'])
#         result = result.replace('[Nombre Científico]', keywords['scientific_name'])
#         result = result.replace('[parte_afectada]', keywords['affected_part'])
#         result = result.replace('[Daño]', keywords['damage'])

#         result = ' '.join(result.split())
#         queries.append(result)

#     return queries


async def fetch_query_data(session, query, proxy):
    """
    Get data from the URL with retries for resiliency.
    """
    url = f'https://www.google.es/search?q={quote(query)}&gl=es&tbm=isch&num=100&location=Spain&uule=w+CAIQICIFU3BhaW4&brd_json=1'
    try:
        logging.info(f"Fetching data for {query}")
        async with session.get(url, proxy=proxy, ssl=False) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except Exception as e:
        logging.error(f"Error fetching data from {url}: {e}")
        return None


async def get_search_results(queries, proxy):
    """
    Retrieve SERP results for all queries
    """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_query_data(session, query, proxy) for query in queries]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result]


async def get_unique_image_urls(results: list) -> set:
    """
    Extract unique image URLs from SERP results.
    """
    image_urls = {image['image'] for query_result in results for image in query_result.get('images', [])}

    return image_urls


def save_image(image_url, file_path):
    """
    Save image to file from a URL or base64 encoded data.
    """
    try:
        if image_url.startswith("data:image"):
            image_data = base64.b64decode(image_url.split(',')[1])
            with open(file_path, 'wb') as img_file:
                img_file.write(image_data)
        else:
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            with open(file_path, 'wb') as img_file:
                img_file.write(response.content)

        logging.info(f"Image saved at: {file_path}")
    except Exception as e:
        logging.error(f"Error saving image from {image_url}: {e}")
        print(f"Error saving image from {image_url}: {e}")


async def check_image_relevance(model, prompt, image_path):
    """
    Check relevancy of an image based on keywords using Gemini.
    """
    try:
        myfile = genai.upload_file(image_path)
        # print(f"{myfile=}")

        result = model.generate_content([myfile, prompt])
        # print(f"{result.text=}")
        response_json = json.loads(result.text)

        return int(response_json.get("score_1_to_10", 0)) > 7 and response_json.get("Final_Verdict") == "Y"
    except Exception as e:
        logging.error(f"Error checking image relevance for {image_path}: {e}")
        print(f"Error checking image relevance for {image_path}: {e}")


async def extract_pagas_excel_data(df, proxy, model, drive, parent_id):
    """
    Extract data from Excel, perform search, and save images.
    """

    data_set = {}
    data = []
    for _, row in df.iloc[:5].iterrows():

        keywords = await extract_keywords_plagas(row)
        queries = await generate_queries(master_queries_for_plagas, keywords)
        search_result = await get_search_results(queries, proxy)

        unique_image_urls = await get_unique_image_urls(search_result)
        image_folder_path = await get_or_create_folder(row["Tipo"])
        drive_image_folder_id = get_or_create_gd_folder(drive, row["Tipo"], parent_id=parent_id)

        for count, image_url in enumerate(unique_image_urls):

            image_file_path = os.path.join(
                image_folder_path,
                f'{row["Nombre Científico"]}_image_{count}.jpg'
                )

            save_image(image_url, image_file_path)

            prompt = f"""Please tell me whether the image given is of this or not check thourghly ,
                    common name: {keywords['nombre_común']}
                    scientific name: {keywords['Nombre Científico']}
                    Based on your assessment give relevancy score on the scale of 1 to 10."
                    Return the response strictly in json format:
                    {{
                    "score_1_to_10":"numberscore_out_of_10_here",
                    "Final_Verdict":"Y/N"
                    }}"""

            if await check_image_relevance(model, prompt, image_file_path):
                upload_file(drive, image_file_path, drive_image_folder_id)
            else:
                logging.info(f"Irrelevant image removed: {image_file_path}")
                print(f"Irrelevant image removed: {image_file_path}")

        data_set[row["Nombre Científico"]] = search_result
        data.append(data_set)

    return data


async def extract_defici_excel_data(df, proxy, model, drive, parent_id):
    """
    Extract data from Excel, perform search, and save images for deficiency.
    """
    current_disorder = None

    for _, row in df.iterrows():

        if pd.isna(row["Característica"]):
            current_disorder = row["disorders"]
        else:
            keywords = {
                'characteristic': row["Característica"],
                'affected_part': row["Parte Afectada"]
            }
            queries = await generate_queries(master_queries_for_Deficiencias, keywords)
            search_result = await get_search_results(queries, proxy)

            unique_image_urls = await get_unique_image_urls(search_result)
            image_folder_path = await get_or_create_folder(current_disorder)
            drive_image_folder_id = get_or_create_gd_folder(drive, current_disorder, parent_id=parent_id)

            for count, image_url in enumerate(unique_image_urls):

                image_file_path = os.path.join(
                    image_folder_path,
                    f'{current_disorder}_image_{count}.jpg'
                    )
                save_image(image_url, image_file_path)

                prompt = f"""Please tell me whether the image given is of this or not check thourghly ,
                    characteristics: {keywords['characteristic']}
                    disorder: {current_disorder}
                    Based on your assessment give relevancy score on the scale of 1 to 10."
                    Return the response strictly in json format:
                    {{
                    "score_1_to_10":"numberscore_out_of_10_here",
                    "Final_Verdict":"Y/N"
                    }}"""

                if await check_image_relevance(model, prompt, image_file_path):
                    upload_file(drive, image_file_path, drive_image_folder_id)
                else:
                    logging.info(f"Irrelevant image removed: {image_file_path}")
                    print(f"Irrelevant image removed: {image_file_path}")


async def main():
    # load environment variable
    load_dotenv()

    host = os.getenv('host')
    port = os.getenv('port')
    username = os.getenv('proxy_username')
    password = os.getenv('proxy_password')

    proxies = {
        'http': f'http://{username}:{password}@{host}:{port}',
        'https': f'http://{username}:{password}@{host}:{port}'
    }

    proxy = f'http://{username}:{password}@{host}:{port}'

    # Gemini setup
    api_key = os.getenv('google_api_key')
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-1.5-flash", generation_config={
        "temperature": 1.3,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json"
    })

    # google drive
    service_account_creds = os.path.join(current_directory, 'service_account.json')
    drive_service = authenticate_drive(service_account_creds)
    parent_folder_id = os.getenv('google_drive_parent_folder_id')

    excel_file = os.path.join(current_directory,'Indice de Entrenamiento- Citricos (2).xlsx')

    plagas_excel_data = await load_excel_data(excel_file,sheet_name='Plagas')
    data = await extract_pagas_excel_data(plagas_excel_data, proxy, model, drive_service, parent_folder_id)

    defici_excel_data = load_excel_data(excel_file,sheet_name='Deficiencias')
    await extract_defici_excel_data(defici_excel_data, proxy, model, drive_service, parent_folder_id)

    with open("new_data.json", 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':

    asyncio.run(main())
