import glob
import json

import pandas as pd

from django.core.management.base import BaseCommand

from fiscallizeon.omr.functions.main import process_file

class Command(BaseCommand):
    help = 'Retorna planilha com leitura de gabaritos Salta modelo PAS'

    def add_arguments(self, parser):
        parser.add_argument('input_dir', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        input_dir = kwargs['input_dir'][0]
        omr_marker_path = 'fiscallizeon/core/static/omr_marker_salta.jpg'
        with open('fiscallizeon/omr/mappings/salta-pas.json') as json_file:
            template_json = json.load(json_file)

        answers = []
        for file_path in glob.glob(f'{input_dir}/*.*'):
            result = process_file(file_path, template_json, omr_marker_path)
            print('Lido aluno', result.get('Roll'))
            filtered_result = {}
            for k, v in result.items():
                if k.startswith(('a', 'c')) and len(v) > 1:
                    filtered_result[k] = ''
                elif k.startswith('BBlock'):
                    filtered_result[k] = v if len(v) == 3 else '' if len(v) > 3 else ('0' * (3 - len(v)) + v)
                else:
                    filtered_result[k] = v
            answers.append(filtered_result)

        df = pd.DataFrame(answers)

        columns_names = {
            'Roll': 'matricula',
            'Exam': 'prova',
            'BBlock1': 'b1',
            'BBlock2': 'b2',
            'BBlock3': 'b3',
            'BBlock4': 'b4',
            'BBlock5': 'b5',
            'BBlock6': 'b6',
            'BBlock7': 'b7',
            'BBlock8': 'b8',
        }

        df = df.astype(str)
        df = df.rename(columns=columns_names)

        df.drop([
            'a69', 'a70', 'a71', 'a72', 'a73', 'a74', 'a75', 'a76', 'a77', 'a78', 'a79',
            'a80', 'a81', 'a82', 'a83', 'a84', 'a85', 'a86', 'a87', 'a88', 'a89', 'a90',
            'a91', 'a92', 'a93', 'a94', 'a95', 'a96', 'a97', 'a98', 'a99', 'a100', 'c15',
            'c16', 'c17','c18'], axis=1,  inplace=True)

        gabarito = {
            "a1": "C", "a2": "E", "a3": "C", "a4": "C", "a5": "E", "a6": "E", "a7": "E", "a8": "E", "a9": "E", "a10": "C", 
            "a11": "E", "a12": "C", "a13": "E", "a14": "C", "a15": "C", "a16": "E", "a17": "C", "a18": "E", "a19": "E", "a20": "E", 
            "a21": "C", "a22": "C", "a23": "E", "a24": "E", "a25": "C", "a26": "C", "a27": "E", "a28": "E", "a29": "E", "a30": "E", 
            "a31": "C", "a32": "E", "a33": "E", "a34": "C", "a35": "E", "a36": "E", "a37": "C", "a38": "E", "a39": "E", "a40": "E", 
            "a41": "E", "a42": "E", "a43": "C", "a44": "C", "a45": "E", "a46": "C", "a47": "E", "a48": "C", "a49": "E", "a50": "E", 
            "a51": "C", "a52": "C", "a53": "E", "a54": "C", "a55": "E", "a56": "C", "a57": "C", "a58": "E", "a59": "C", "a60": "E", 
            "a61": "C", "a62": "E", "a63": "E", "a64": "C", "a65": "E", "a66": "E", "a67": "C", "a68": "E",

            "b1": "150", "b2": "008", "b3": "018", "b4": "020", "b5": "320", "b6": "324", "b7": "180", "b8": "023",

            "c1": "B", "c2": "A", "c3": "B", "c4": "A", "c5": "A", "c6": "D", "c7": "D", "c8": "B", "c9": "C", "c10": "D", 
            "c11": "D", "c12": "D", "c13": "A", "c14": "C"
        }

        answers_df = df.copy()
        answers_final_df = pd.DataFrame([{'matricula': 'GABARITO', 'prova': '', **gabarito}])
        answers_final_df = pd.concat([answers_final_df, answers_df])
        answers_final_df.to_csv('respostas-pas.csv')
        return

        def map_answers_a(row):
            return row.apply(lambda resposta_aluno: 1 if resposta_aluno == gabarito[row.name] else (-1 if resposta_aluno else 0))
        
        def map_answers_b(row):
            return row.apply(lambda resposta_aluno: 2 if resposta_aluno == gabarito[row.name] else 0)
        
        def map_answers_c(row):
            return row.apply(lambda resposta_aluno: 2 if resposta_aluno == gabarito[row.name] else (-0.667 if resposta_aluno else 0))

        #Contagem de acertos, erros e branco
        count_df = df.copy()
        count_df.iloc[:, 2:] = count_df.iloc[:, 2:].apply(map_answers_a)
        count_df['a_correct'] = (count_df.iloc[:, 10:78] == 1).sum(axis=1)
        count_df['a_incorrect'] = (count_df.iloc[:, 10:78] == -1).sum(axis=1)
        count_df['a_null'] = (count_df.iloc[:, 10:78] == 0).sum(axis=1)
        count_df['b_correct'] = (count_df.iloc[:, 2:10] == 1).sum(axis=1)
        count_df['b_incorrect'] = (count_df.iloc[:, 2:10] == -1).sum(axis=1)
        count_df['b_null'] = (count_df.iloc[:, 2:10] == 0).sum(axis=1)
        count_df['c_correct'] = (count_df.iloc[:, 78:] == 1).sum(axis=1)
        count_df['c_incorrect'] = (count_df.iloc[:, 78:] == -1).sum(axis=1)
        count_df['c_null'] = (count_df.iloc[:, 78:] == 0).sum(axis=1)
        count_df = count_df[['a_correct', 'a_incorrect', 'a_null', 'b_correct', 'b_incorrect', 'b_null', 'c_correct', 'c_incorrect', 'c_null']]
        
        df.iloc[:, 10:78] = df.iloc[:, 10:78].apply(map_answers_a)
        df.iloc[:, 2:10] = df.iloc[:, 2:10].apply(map_answers_b)
        df.iloc[:, 78:] = df.iloc[:, 78:].apply(map_answers_c)

        df.iloc[:, 2:] = df.iloc[:, 2:].astype(float)

        x_pas = 0.8929
        df.iloc[:, 2:] = df.iloc[:, 2:] * x_pas

        ingles_grades_a = df.iloc[:, 10:17]
        artes_grades_a = df.iloc[:, 17:22]
        portugues_grades_a = df.iloc[:, 22:35]
        redacao_grades_a = df.iloc[:, 35:40]
        historia_grades_a = df.iloc[:, 40:49]
        geografia_grades_a = df.iloc[:, 49:58]
        quimica_grades_a = df.iloc[:, 58:63]
        biologia_grades_a = df.iloc[:, 63:68]
        matematica_grades_a = df.iloc[:, 68:78]
        
        quimica_grades_b = df.iloc[:, 2:4]
        biologia_grades_b = df.iloc[:, 4:6]
        matematica_grades_b = df.iloc[:, 6:10]

        ingles_grades_c = df.iloc[:, 78:79]
        artes_grades_c = df.iloc[:, 79:80]
        portugues_grades_c = df.iloc[:, 80:82]
        redacao_grades_c = df.iloc[:, 82:83]
        historia_grades_c = df.iloc[:, 83:86]
        geografia_grades_c = df.iloc[:, 86:89]
        quimica_grades_c = df.iloc[:, 89:90]
        biologia_grades_c = df.iloc[:, 90:91]
        matematica_grades_c = df.iloc[:, 91:92]

        df['total_ingles'] = ingles_grades_a.sum(axis=1) + ingles_grades_c.sum(axis=1)
        df['total_artes'] = artes_grades_a.sum(axis=1) + artes_grades_c.sum(axis=1)
        df['total_portugues'] = portugues_grades_a.sum(axis=1) + portugues_grades_c.sum(axis=1)
        df['total_redacao'] = redacao_grades_a.sum(axis=1) + redacao_grades_c.sum(axis=1)
        df['total_historia'] = historia_grades_a.sum(axis=1) + historia_grades_c.sum(axis=1)
        df['total_geografia'] = geografia_grades_a.sum(axis=1) + geografia_grades_c.sum(axis=1)
        df['total_quimica'] = quimica_grades_a.sum(axis=1) + quimica_grades_b.sum(axis=1) + quimica_grades_c.sum(axis=1)
        df['total_biologia'] = biologia_grades_a.sum(axis=1) + biologia_grades_b.sum(axis=1) + biologia_grades_c.sum(axis=1)
        df['total_matematica'] = matematica_grades_a.sum(axis=1) + matematica_grades_b.sum(axis=1) + matematica_grades_c.sum(axis=1)
        df['total'] = df['total_ingles'] + df['total_artes'] + df['total_portugues'] + df['total_redacao'] + df['total_historia'] + df['total_geografia'] + df['total_quimica'] + df['total_biologia'] + df['total_matematica']
        df['total'] = df['total'].apply(lambda x: round(x, 3))

        df = df.astype(str)
        df = df.join(count_df)
        df = df.set_index('matricula')
        print(df)
        df.to_csv('final_pas.csv')
        # print(df.iloc[:, 92:])
