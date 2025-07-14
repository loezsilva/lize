import re
from bs4 import BeautifulSoup
from fiscallizeon.questions.models import Question
import latex2mathml.converter as latex_converter

def remove_nested_math_tags(html):
    soup = BeautifulSoup(html, "html.parser")

    # Encontra todas as tags <math>
    for math in soup.find_all("math"):
        # Remove qualquer <math> dentro deste <math>
        for nested_math in math.find_all("math"):
            nested_math.unwrap()  # remove a tag, mantendo o conteúdo

        # Também remove tags </math> escritas como texto por engano
        for tag in math.find_all(text=lambda t: "</math>" in t or "<math>" in t):
            tag.replace_with(tag.replace("<math>", "").replace("</math>", ""))

    return str(soup)

def clean_latex(latex_expr):
    latex_expr = latex_expr.strip()
    # Remove chaves externas, se presentes e não houver comandos antes
    if latex_expr.startswith("{") and latex_expr.endswith("}"):
        inner = latex_expr[1:-1]
        # só remove se não tiver comandos como \frac, \sqrt no início
        if not re.match(r'\\[a-zA-Z]+', inner):
            return inner.strip()
    return latex_expr

def replace_latex_with_mathml(text):
    def to_mathml(match):
        latex_expr = clean_latex(match.group(1))
        try:
            mathml = latex_converter.convert(latex_expr)
            if re.search(r'<(mi|mn|mo|msup|mfrac|msqrt)', mathml):
                return mathml
            else:
                print(f"⚠️ MathML não confiável: {latex_expr}")
                return f"<code>{latex_expr}</code>"
        except Exception as e:
            print(f"❌ Erro ao converter: {latex_expr} -> {e}")
            return match.group(0)
    return re.sub(r'\\\\\((.*?)\\\\\)', to_mathml, text)