import os, csv, requests, shutil
from urllib.parse import urlparse, parse_qs

session = requests.Session()
r = session.get("https://rioeduca-my.sharepoint.com/:f:/g/personal/gaddsme_rioeduca_net/Evx8mCygwqFBlc4LTunWLAQBa1kCiQblIk5BGEiZh1pt7g?e=bsCfHZ")

#prefixo da url dos arquivos: https://rioeduca-my.sharepoint.com/personal/gaddsme_rioeduca_net/_layouts/15/download.aspx?SourceUrl=/personal/gaddsme_rioeduca_net/Documents/Apps/Microsoft Forms/Forms_Backup Cart%C3%B5es Respostas/

files = ["https://rioeduca-my.sharepoint.com/personal/gaddsme_rioeduca_net/_layouts/15/download.aspx?SourceUrl=/personal/gaddsme_rioeduca_net/Documents/Apps/Microsoft Forms/Forms_Backup Cart%C3%B5es Respostas/Pergunta/Digitalizado_20221011-1602_Escola Municipal Pon.pdf", "https://rioeduca-my.sharepoint.com/personal/gaddsme_rioeduca_net/_layouts/15/download.aspx?SourceUrl=/personal/gaddsme_rioeduca_net/Documents/Apps/Microsoft Forms/Forms_Backup Cart%C3%B5es Respostas/Pergunta 2/Digitalizado_20221011-1555_Escola Municipal Pon.pdf", "https://rioeduca-my.sharepoint.com/personal/gaddsme_rioeduca_net/_layouts/15/download.aspx?SourceUrl=/personal/gaddsme_rioeduca_net/Documents/Apps/Microsoft Forms/Forms_Backup Cart%C3%B5es Respostas/Pergunta 3/Digitalizado_20221011-1617_Escola Municipal Pon.pdf", "https://rioeduca-my.sharepoint.com/personal/gaddsme_rioeduca_net/_layouts/15/download.aspx?SourceUrl=/personal/gaddsme_rioeduca_net/Documents/Apps/Microsoft Forms/Forms_Backup Cart%C3%B5es Respostas/Pergunta 4/Digitalizado_20221011-1631_Escola Municipal Pon.pdf"]

for file_url in files:
    file_url = file_url.strip()
    parsed_url = urlparse(file_url)
    captured_value = parse_qs(parsed_url.query)['SourceUrl'][0]
    file_name = captured_value.split("/")[-1]
    file_extension = file_name.split(".")[-1]
    full_path_file = f'tmp/rio_new/{file_name}'

    with session.get(file_url, stream=True) as r:
        tmp_file = os.path.join(full_path_file)
        
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)