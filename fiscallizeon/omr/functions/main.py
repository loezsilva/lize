"""

Designed and Developed by-
Udayraj Deshmukh
https://github.com/Udayraj123

"""

import re
import cv2
import numpy as np

from fiscallizeon.omr.functions import config
from fiscallizeon.omr.functions import utils
from fiscallizeon.omr.functions.template import Template

# Local globals
filesMoved=0
filesNotMoved=0

from glob import glob
from csv import QUOTE_NONNUMERIC
from time import localtime, strftime, time

def processOMR(template, omrResp):
    # Note: This is a reference function. It is not part of the OMR checker
    # So its implementation is completely subjective to user's requirements.
    csvResp = {}

    # symbol for absent response
    UNMARKED_SYMBOL = ''

    # print("omrResp",omrResp)

    # Multi-column/multi-row questions which need to be concatenated
    for qNo, respKeys in template.concats.items():
        csvResp[qNo] = ''.join([omrResp.get(k, UNMARKED_SYMBOL)
                                for k in respKeys])

    # Single-column/single-row questions
    for qNo in template.singles:
        csvResp[qNo] = omrResp.get(qNo, UNMARKED_SYMBOL)

    return csvResp


def process_file(sheet_file, template_json, marker_path=None, no_crop=True, file_buffered=False):
    template = Template(template_json, marker_path)
    
    if file_buffered:
        inOMR = cv2.imdecode(np.frombuffer(sheet_file.read(), np.uint8), cv2.IMREAD_GRAYSCALE)
        filename = None
    else:
        finder = re.search(r'(.*)/(.*)', sheet_file, re.IGNORECASE)
        if(finder):
            _, filename = finder.groups()
        else:
            print("Error: Filepath not matching to Regex: " + sheet_file)

        inOMR = cv2.imread(sheet_file, cv2.IMREAD_GRAYSCALE)

    inOMR = cv2.GaussianBlur(inOMR,(3,3), 0)
    (_, inOMR) = cv2.threshold(inOMR, 127, 255, cv2.THRESH_BINARY)

    OMRCrop = utils.getROI(inOMR, filename, noCropping=no_crop)

    if(OMRCrop is None):
        print("Arquivo não pode ser lido")

    if template.marker is not None:
        OMRCrop = utils.handle_markers(OMRCrop, template.marker, filename)

    OMRresponseDict, final_marked, MultiMarked, multiroll = \
        utils.readResponse(template, OMRCrop, name='',
                        savedir=None, autoAlign=False)

    return processOMR(template, OMRresponseDict) 