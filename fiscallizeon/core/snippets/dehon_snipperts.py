# MUDAR AS DISCIPLINAS PARA IT DE ALGUNS CADERNOS

data = [
    {
        "caderno": "3ª SÉRIE QUÍMICA/GRAMÁTICA/QUÍMICA IT/ GRAMÁTICA IT - 19/04 - P2",
        "professor":"kellen",
        "disciplina": "língua portuguesa"
    },
    {
        "caderno": "3ª SÉRIE QUÍMICA/GRAMÁTICA/QUÍMICA IT/ GRAMÁTICA IT - 19/04 - P2",
        "professor":"marcelo",
        "disciplina": "química"
    },
    {
        "caderno": "2ª série química/gramática/química it/ gramática it - 19/04 - P2",
        "professor":"paula",
        "disciplina": "química"
    },
     {
        "caderno": "1ª SÉRIE FÍSICA/ HISTÓRIA/FÍSICA IT - 12/04 - P2 - EXATAS",
        "professor":"JORGE INACIO MARTINS",
        "disciplina": "Física"
    },
     {
        "caderno": "1ª SÉRIE FÍSICA/ HISTÓRIA/ HISTÓRIA IT - 12/04 - P2 - HUMANAS",
        "professor":"DEIVID SANTOS MATEI",
        "disciplina": "História"
    },
     {
        "caderno": "2ª SÉRIE FÍSICA/HISTÓRIA/FÍSICA IT - 12/04 - P2 - EXATAS",
        "professor":"AUREO DANTAS BETTIOL",
        "disciplina": "FÍSICA"
    },
     {
        "caderno": "2ª SÉRIE FÍSICA/HISTÓRIA/ HISTÓRIA IT - 12/04 - P2 - HUMANAS",
        "professor":"DEIVID SANTOS MATEI",
        "disciplina": "HISTÓRIA"
    },
    {
        "caderno": "3ª SÉRIE FÍSICA/HISTÓRIA/FÍSICA IT - 12/04 - P2 - EXATAS",
        "professor":"AUREO DANTAS BETTIOL",
        "disciplina": "FÍSICA"
    },
    {
        "caderno": "3ª SÉRIE FÍSICA/HISTÓRIA/ HISTÓRIA IT - 12/04 - P2 - HUMANAS",
        "professor":"MAURICIO GHEDIN CORREA",
        "disciplina": "HISTÓRIA"
    },
     {
        "caderno": "ADAP - 1ª SÉRIE FÍSICA/ HISTÓRIA/FÍSICA IT - 12/04 - P2 - EXATAS",
        "professor":"JORGE INACIO MARTINS",
        "disciplina": "FÍSICA"
    },
     {
        "caderno": "ADAP - 1ª SÉRIE FÍSICA/ HISTÓRIA/ HISTÓRIA IT - 12/04 - P2 - HUMANAS",
        "professor":"DEIVID SANTOS MATEI",
        "disciplina": "HISTÓRIA"
    },
     {
        "caderno": "ADAP - 2ª SÉRIE FÍSICA/HISTÓRIA/FÍSICA IT - 12/04 - P2 - EXATAS",
        "professor":"AUREO DANTAS BETTIOL",
        "disciplina": "FÍSICA"
    },
    {
        "caderno": "ADAP- 2ª SÉRIE FÍSICA/HISTÓRIA/ HISTÓRIA IT - 12/04 - P2 - HUMANAS",
        "professor":"DEIVID SANTOS MATEI",
        "disciplina": "HISTÓRIA"
    },
    {
        "caderno": "1ª série química/gramática/química it/ - 19/04 - P2",
        "professor":"paula",
        "disciplina": "química"
    },
     {
        "caderno": "ADAP - 3ª SÉRIE FÍSICA/HISTÓRIA/ HISTÓRIA IT - 12/04 - P2 - HUMANAS",
        "professor":"MAURICIO GHEDIN CORREA",
        "disciplina": "HISTÓRIA"
    },
     {
        "caderno": "ADAP - 3ª SÉRIE FÍSICA/HISTÓRIA/FÍSICA IT - 12/04 - P2 - EXATAS",
        "professor":"AUREO DANTAS BETTIOL",
        "disciplina": "FÍSICA"
    },
]
from fiscallizeon.exams.models import Exam
from fiscallizeon.inspectors.models import TeacherSubject, Inspector
from fiscallizeon.subjects.models import Subject
from django.db.models import Q
for d in data:
    print(d['caderno'])
    caderno = Exam.objects.get(
        name__iexact=d['caderno']
    )
    requests = caderno.examteachersubject_set.filter(
        teacher_subject__teacher__name__icontains=d['professor'],
        teacher_subject__subject__name__icontains=d['disciplina']
    )
    print(d['professor'], d['disciplina'], requests.count())
    last_request = requests.order_by('order').last()
    inspector = last_request.teacher_subject.teacher
    subject = Subject.objects.filter(
        Q(client__name__icontains="dehon"),
        Q(name__icontains=d['disciplina']),
        Q(name__icontains="IT")
    ).last()
    print(inspector, subject)
    teacher_subject, created = TeacherSubject.objects.get_or_create(
        teacher=inspector,
        subject=subject
    )
    last_request.teacher_subject = teacher_subject
    last_request.save(skip_hooks=True)




#mudar senha do usuário e logar ele em seguida
profs = [
["beatriz.pfeiffer@colegiodehon.com.br","08078572079"],
["daniel.costa6@colegiodehon.com.br","00690584592"],
["suelen.machado@colegiodehon.com.br","05392335085"],
["alexandre.paes@colegiodehon.com.br","0211816502"],
["paloma.domingos@colegiodehon.com.br","05225100304"],
["aureo.bettiol@colegiodehon.com.br","56479103755"],
["luana.michels@colegiodehon.com.br","00860386431"],
["mario.souza@colegiodehon.com.br","02627402068"],
["elisangela.mafei@colegiodehon.com.br","03075116618"],
["camila.mauricio@colegiodehon.com.br","06001336672"],
["cintia.abreu@colegiodehon.com.br","05241114829"],
["silva.maisa@colegiodehon.com.br","08398453710"],
["maria.margotti@colegiodehon.com.br","04224570456"],
["camila.wesling@colegiodehon.com.br","04430423686"],
["paula.andre1@colegiodehon.com.br","05767706742"],
["santos.paloma@colegiodehon.com.br","05459552043"],
["correa.janaina@colegiodehon.com.br","06126385073"],
["vitoria.neves@colegiodehon.com.br","11053663222"],
["aline.mendonca1@colegiodehon.com.br","07400575005"],
["alves.daiane@colegiodehon.com.br","0086591775"],
["edson.souza8@colegiodehon.com.br","05629522034"],
["ellen.estevam@colegiodehon.com.br","9129515708"],
["fabio.ballmann@colegiodehon.com.br","00388100006"],
["otavio.silveira@colegiodehon.com.br","0441026331"],
["cleber.mafioletti@colegiodehon.com.br","08332453690"],
["sabrina.justino@colegiodehon.com.br","0042521853"],
["silvania.maia@colegiodehon.com.br","7534224593"],
["leticia.rocha1@colegiodehon.com.br","0702464837"],
["tatiane.sombrio@colegiodehon.com.br","05013705945"],
["uliano.patricia@colegiodehon.com.br","03058705689"],
["dyeiniffer.zapelini@colegiodehon.com.br","07429705079"],
["larissa.silva32@colegiodehon.com.br","86473145571"],
["julia.correa2@colegiodehon.com.br","11771658097"],
["fernandes.liliane@colegiodehon.com.br","06039422996"],
["iara.martins@colegiodehon.com.br","10098554789"],
["luiz.luz1@colegiodehon.com.br","71165653759"],
["lucas.rodrigues16@colegiodehon.com.br","11012576581"],
["fernando.menegaz@colegiodehon.com.br","0262573798"],
["deivid.matei@colegiodehon.com.br","04848334952"],
["elaine.souza@colegiodehon.com.br","81282339494"],
["sidneia.antunes@colegiodehon.com.br","01670432728"],
["paula.pereira9@colegiodehon.com.br","1033296973"],
["ana.silva149@colegiodehon.com.br","09499673895"],
["alessandra.almeida@colegiodehon.com.br","0056782638"],
["samira.pereira@colegiodehon.com.br","06920351412"],
["maria.souza15@colegiodehon.com.br","0208724041"],
["thiago.flores@colegiodehon.com.br","00360116213"],
["cleide.tenfen@colegiodehon.com.br","02939705699"],
["maria.aguiar5@colegiodehon.com.br","0896259875"],
["jorge.martins@colegiodehon.com.br","07980541209"],
["michels.cardoso@colegiodehon.com.br","0900225951"],
["luana.fuhrmann@colegiodehon.com.br","05563102659"],
["andre.silva@colegiodehon.com.br","0048192097"],
["giane.figueredo@colegiodehon.com.br","09590705899"],
["fabio.camilo@colegiodehon.com.br","03999358889"],
["roecker.marcos@colegiodehon.com.br","04972120212"],
["gladys.silva@colegiodehon.com.br","6962453233"],
["leila.camargo@colegiodehon.com.br","0286414084"],
["maria.amorim2@colegiodehon.com.br","10270593235"],
["greice.bitencourt@colegiodehon.com.br","0665082948"],
["daniela.vieira3@colegiodehon.com.br","07100706821"],
["maria.machado38@colegiodehon.com.br","06338705698"],
["yanni.siqueira@colegiodehon.com.br","0090793732"],
["joao.medeiros18@colegiodehon.com.br","11042145845"],
["rodolfo.prieto@colegiodehon.com.br","8895791757"],
["cleber.correa@colegiodehon.com.br","0228088319"],
["joao.michels@colegiodehon.com.br","07334457058"],
["kelly.silva@colegiodehon.com.br","04119117613"],
["thamyris.silva@colegiodehon.com.br","05949336622"],
["ana.inacio1@colegiodehon.com.br","0413699253"],
["cecilia.ribeiro@colegiodehon.com.br","0073899608"],
["cleber.fernandes@colegiodehon.com.br","0045193660"],
["fernanda.neves3@colegiodehon.com.br","0585737102"],
["pedro.espindola@colegiodehon.com.br","05072424399"],
["rosangela.zanelato@colegiodehon.com.br","0087299792"],
["rodrigo.veronez@colegiodehon.com.br","02891694727"],
["andrea.medeiros1@colegiodehon.com.br","91000100167"],
["amanda.souza4@colegiodehon.com.br","08418462581"],
["sabrina.costa1@colegiodehon.com.br","11847657556"],
["geruza.souza@colegiodehon.com.br","7953753211"],
["bona.fernanda@colegiodehon.com.br","05168705697"],
["daiani.bo@colegiodehon.com.br","07148705692"],
["silva.danielly@colegiodehon.com.br","07960501820"],
["jucelia.catene@colegiodehon.com.br","05722705012"],
["leonardo.inacio@colegiodehon.com.br","0056185954"],
["paula.sombrio@colegiodehon.com.br","03184542182"],
["anne.souza@colegiodehon.com.br","08684387287"],
["gabriela.hilario@colegiodehon.com.br","11055615392"],
["mauricio.correa@colegiodehon.com.br","04555654012"],
["samantha.miguel@colegiodehon.com.br","0038831112"],
["josenir.silva@colegiodehon.com.br","8224822578"],
["kellen.rodrigues@colegiodehon.com.br","0069488105"],
["meurer.karine@colegiodehon.com.br","09257706820"],
["leticia.herdt@colegiodehon.com.br","08233638208"],
["daiana.vedova@colegiodehon.com.br","03374541639"],
["maristela.simiano@colegiodehon.com.br","769932399"],
["camila.mattos@colegiodehon.com.br","04867114621"],
["giselle.horacio@colegiodehon.com.br","30814381509"],
["marcelo.camargo@colegiodehon.com.br","732686182"],
["joyce.serafim@colegiodehon.com.br","10477590407"],
["alessandro.delfino@colegiodehon.com.br","00748555932"],
["marcelo.martins6@colegiodehon.com.br","00783515940"],
["jaison.mattei@colegiodehon.com.br","0246323626"],
["tatiane.leal@colegiodehon.com.br","8463515091"],
["fernando.braga@colegiodehon.com.br","8879092796"],
["clovis.silva@colegiodehon.com.br","7900652907"],
["deivid.geraldi@colegiodehon.com.br","05612105601"],
["edina.kulkamp@colegiodehon.com.br","08895643136"],
["mariana.campos1@colegiodehon.com.br","04328394613"],
["rosana.silva2@colegiodehon.com.br","07456421349"],
["daiane.thomaz@colegiodehon.com.br","0301024449"],
["iveti.aurelio@colegiodehon.com.br","02420630447"],
["angelina.nogaredo@colegiodehon.com.br","00019117421"],
["gilvan.medeiros@colegiodehon.com.br","07108354402"],
["dayane.souza@colegiodehon.com.br","02756351075"],
["renata.sampaio@colegiodehon.com.br","0405890492"],
["miriane.roecker@colegiodehon.com.br","1080957468"]
 ]

from fiscallizeon.accounts.models import User

for p in profs:
    try:
        user = User.objects.get(email__iexact=p[0])
        user.must_change_password = True
        user.set_password(p[1])
        user.save()
        print(p[0], "Deu certo")
    except Exception as e:
        print(p[0], e)

from django.core.cache import cache
from django.db.models import Q
from fiscallizeon.accounts.models import User
keys = cache.keys('django.contrib.sessions.cache*')

for p in profs:
    try:
        user = User.objects.get(email__iexact=p[0])
        for k in keys:
            data = cache.get(k)
            if data and data.get('_auth_user_id', '') == str(user.pk):
                cache.delete(k)
    except Exception as e:
        pass
## fim mudar senha e deslugar professor

from django.utils.crypto import get_random_string
from fiscallizeon.accounts.models import User

users = User.objects.filter(is_active=True, email__icontains="-dehon").distinct()
total = users.count()

for index, user in enumerate(users, 1):
    print(f"{index}/{total}")
    user.username = user.username + get_random_string(
        length=16, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789"
    )
    user.email = user.email + get_random_string(
        length=16, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789"
    )
    user.save()

from django.core.cache import cache

keys = cache.keys("django.contrib.sessions.cache*")

# Construa um set com os IDs dos usuários para busca rápida
user_ids = [str(id) for id in users.values_list("pk", flat=True)]

# Itera pelas chaves uma única vez
for k in keys:
    data = cache.get(k)
    if not data:
        continue
    user_id = data.get("_auth_user_id")
    if user_id in user_ids:
        cache.delete(k)