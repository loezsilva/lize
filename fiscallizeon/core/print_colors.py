class color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_error(text):
    print(color.FAIL, text ,color.ENDC)

def print_warning(text):
    print(color.WARNING, text ,color.ENDC)

def print_success(text):
    print(color.OKGREEN, text ,color.ENDC)

def print_info(text):
    print(color.OKBLUE, text ,color.ENDC)

def print_header(text):
    print(color.HEADER, text ,color.ENDC)

def print_underline(text):
    print(color.UNDERLINE, text ,color.ENDC)

def print_bold(text):
    print(color.BOLD, text ,color.ENDC)
