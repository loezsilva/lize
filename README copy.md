# Lize Edu

Sistema de gerenciamento de processo avaliativo.

## Como desenvolver?

1. Clone o repositório.
2. Crie um virtualenv com Python 3+.
3. Ative o virtualenv.
4. Instale as dependências.
5. Configure a instância com o .env
6. Execute o projeto.

```console
git clone https://github.com/lizeedu/lizeedu.git lizeedu
cd lizeedu
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp contrib/env-sample .env
python manage.py runserver
```
