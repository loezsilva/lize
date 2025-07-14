import glob
import cv2
import numpy as np

from fiscallizeon.celery import app

def get_omr_area_image(image_path):
    image = cv2.imread(image_path)
    blur = cv2.pyrMeanShiftFiltering(image, 11, 21)
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    _, orig_width = image.shape[:2]

    croped_areas = []

    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.015 * peri, True)

        if len(approx) == 4:
            x,y,w,h = cv2.boundingRect(approx)
            if w < orig_width * 0.8:
                continue

            crop_img = image[y:y+h, x:x+w]
            croped_areas.append(crop_img)

    if len(croped_areas) == 1:
        cv2.imwrite(image_path, croped_areas[0])
    elif len(croped_areas) == 2:
        h1, w1  = croped_areas[0].shape[:2]
        h2, w2  = croped_areas[1].shape[:2]

        #Adjust width
        if w1 > w2:
            croped_areas[1] = cv2.resize(croped_areas[1], (w1, h2))
        else:
            croped_areas[0] = cv2.resize(croped_areas[0], (w2, h1))

        # Merging
        if h1 > h2:
            final_img = np.vstack((croped_areas[0], croped_areas[1]))
        else:
            final_img = np.vstack((croped_areas[1], croped_areas[0]))
        
        cv2.imwrite(image_path, final_img)

@app.task
def crop_omr_area_rio(upload_id):
    omr_files = glob.glob(f'tmp/{upload_id}/*.jpg')

    for omr_file in omr_files:
        get_omr_area_image(omr_file)

    return upload_id