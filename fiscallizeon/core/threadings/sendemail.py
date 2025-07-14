import threading

from django.core.mail import EmailMessage


class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, to):
        self.subject = subject
        self.html_content = html_content
        self.to = to

        threading.Thread.__init__(self)

    def run (self):
        try:
            msg = EmailMessage(
                self.subject, 
                self.html_content, 
                to=self.to, 
                from_email='Lize <contato@lizeedu.com.br>'
            )
            msg.content_subtype = 'html'
            msg.send()
            
        except Exception as e:
            print("Erro ao enviar email: ", e)
