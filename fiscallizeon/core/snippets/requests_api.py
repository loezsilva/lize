import requests

# URL base da API
base_url = "https://app.lizeedu.com.br/api/v2/teachers/"

# Lista para armazenar os resultados
results = []
headers = {"Authorization": "Token f3c08c4421d9092542ca096b465e468e25cefa51"}
# Iniciar a primeira solicitação
response = requests.get(base_url, headers=headers)

# Contador de página
page_count = 1

# Verificar se a solicitação foi bem-sucedida
if response.status_code == 200:
    data = response.json()
    results.extend(data['results'])
    
    # Verificar cada resultado na primeira página
    for result in data['results']:
        if result.get('email') == 'adilson.junior@rededecisao.com.br':
            print(f"Encontrado 'adilson.junior@rededecisao.com.br' na página {page_count}")
    
    # Iterar pelas páginas enquanto houver uma próxima página
    while data['next']:
        next_url = data['next']
        response = requests.get(next_url, headers=headers)
        page_count += 1
        
        if response.status_code == 200:
            data = response.json()
            results.extend(data['results'])
            
            # Verificar cada resultado na página atual
            for result in data['results']:
                if result.get('email') == 'adilson.junior@rededecisao.com.br':
                    print(next_url)
                    print(f"Encontrado 'adilson.junior@rededecisao.com.br' na página {page_count}")
        else:
            print("Erro ao buscar próxima página:", response.status_code)
            break
else:
    print("Erro na primeira solicitação:", response.status_code)

# Agora 'results' contém todos os resultados
print("Número total de resultados:", len(results))