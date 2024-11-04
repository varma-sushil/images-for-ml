from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fake_useragent import UserAgent

from urllib.parse import quote
import pandas as pd
import time

excel_file = 'Indice de Entrenamiento- Citricos (2).xlsx'
excel_data  = pd.read_excel(excel_file, header=1, sheet_name='Plagas')
excel_data = excel_data.drop(excel_data.columns[0:2], axis=1)
excel_data = excel_data.reset_index(drop=True)

ua = UserAgent()
user_agent = ua.random

chrome_options = Options()
chrome_options.add_argument(f'user-agent={user_agent}')



def get_required_data(df: pd.DataFrame):

    data = []
    for _, row in df.iterrows():
        disease_type = row["Tipo"]
        # print(f'index: {index} \ntype: {disease_type}')

        sub_type = row["Subtipo"]
        # print(f'subtype: {sub_type}')

        common_name = row["Nombre Común"]
        # print(f'common name: {common_name}')

        scientific_name = row["Nombre Científico"]
        # print(f'scientific name: {scientific_name}')

        affected_part = row["Parte Afectada"] if not pd.isna(row["Parte Afectada"]) else 'plant body'
        # print(f'affected part: {affected_part}')

        affected_species = row["Especie Afectada"] if not pd.isna(row["Especie Afectada"])  else 'citrus plant'
        # print(f'affected_species: {affected_species}')

        damage = row["Daño"] if not pd.isna(row["Daño"]) else 'damage'
        # print(f'damage: {damage} \n')

        keyword_data = {
            "type": disease_type,
            'sub_type': sub_type,
            'common_name': common_name,
            'scientific_name': scientific_name,
            'affected_part': affected_part,
            'affected_species': affected_species,
            'damage': damage
        }

        data.append(keyword_data)

    return data

master_queries = [
    '[nombre_común] en plantas de [especies_afectadas] - [Subtipo] ([Nombre Científico]) en [parte_afectada]. El daño visible incluye [Daño]',
    'Síntomas de infección por [nombre_común] en [especies_afectadas] - [Subtipo] ([Nombre Científico])',
    'Primer plano de la infestación de [Subtipo] ([Nombre Científico]) en [especies_afectadas]',
    'Vista detallada de [nombre_común] en [especies_afectadas] - [Subtipo] ([Nombre Científico]). [parte_afectada] presenta [Daño]',
    'Infestación de [Subtipo] ([Nombre Científico]) en [especies_afectadas], afectando [parte_afectada]. Indicios incluyen [Daño]',
    'Síntomas de [nombre_común] ([Nombre Científico]) en [especies_afectadas], afectando específicamente [parte_afectada]',
    'Imágenes de alta calidad de [nombre_común] que afectan [parte_afectada] de plantas cítricas, mostrando [Daño]',
    '[nombre_común] que afecta a [especies_afectadas] - [Subtipo] ([Nombre Científico]), afectando [parte_afectada]'
]

data = get_required_data(excel_data)
queries = []
for search_keyword in data:

    # print(search_keyword.keys())
    for query in master_queries:
        result = query.replace('[nombre_común]', search_keyword['common_name'])
        result = result.replace('[especies_afectadas]', search_keyword['affected_species'])
        result = result.replace('[Subtipo]', search_keyword['sub_type'])
        result = result.replace('[Nombre Científico]', search_keyword['scientific_name'])
        result = result.replace('[parte_afectada]', search_keyword['affected_part'])
        result = result.replace('[Daño]', search_keyword['damage'])

        result = ' '.join(result.split())
        queries.append(result)

result = {}
count = 0
for query in queries[16:24]:
    query = quote(query)
    print(query)
    driver = webdriver.Chrome(options=chrome_options)
    url = f'https://www.google.es/search?q={query}&gl=es&tbm=isch&num=100&location=Spain&uule=w+CAIQICIFU3BhaW4'

    driver.get(url)
    time.sleep(5)

    img_elements = driver.find_elements(By.XPATH, '//h3/a')
    images = []
    for element in img_elements:
        a_tag = element.get_attribute('innerHTML')
        images.append(a_tag)

    result[count] = images
    count+=1

    driver.close()

print(result)