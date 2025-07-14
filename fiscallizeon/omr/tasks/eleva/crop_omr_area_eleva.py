import glob
import cv2
import numpy as np

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload


TRANSF_SIZE = 1024


def calculate_contour_features(contour):
    moments = cv2.moments(contour)
    return cv2.HuMoments(moments)


def calculate_corner_features(corner_image_path):
    corner_img = cv2.imread(corner_image_path)
    corner_img_gray = cv2.cvtColor(corner_img, cv2.COLOR_BGR2GRAY)
    contours, hierarchy = cv2.findContours(
        corner_img_gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) != 2:
        raise RuntimeError(
            'Did not find the expected contours when looking for the corner')

    corner_contour = next(ct
                          for i, ct in enumerate(contours)
                          if hierarchy[0][i][3] != -1)

    return calculate_contour_features(corner_contour)


def normalize(im):
    im_gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(im_gray, (3, 3), 0)

    return cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 77, 10)


def get_approx_contour(contour, tol=.01):
    epsilon = tol * cv2.arcLength(contour, True)
    return cv2.approxPolyDP(contour, epsilon, True)


def get_contours(image_gray):
    contours, _ = cv2.findContours(
        image_gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return map(get_approx_contour, contours)


def get_corners(contours, corner_image_path):
    corner_features = calculate_corner_features(corner_image_path)
    return sorted(
        contours,
        key=lambda c: features_distance(
                corner_features,
                calculate_contour_features(c)))[:4]


def get_bounding_rect(contour):
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    return np.int0(box)


def features_distance(f1, f2):
    return np.linalg.norm(np.array(f1) - np.array(f2))


def get_centroid(contour):
    m = cv2.moments(contour)
    x = int(m["m10"] / m["m00"])
    y = int(m["m01"] / m["m00"])
    return (x, y)


def sort_points_counter_clockwise(points):
    origin = np.mean(points, axis=0)

    def positive_angle(p):
        x, y = p - origin
        ang = np.arctan2(y, x)
        return 2 * np.pi + ang if ang < 0 else ang

    return sorted(points, key=positive_angle)


def get_outmost_points(contours):
    all_points = np.concatenate(contours)
    return get_bounding_rect(all_points)


def perspective_transform(img, points):
    source = np.array(
        points,
        dtype="float32")

    dest = np.array([
        [TRANSF_SIZE, TRANSF_SIZE],
        [0, TRANSF_SIZE],
        [0, 0],
        [TRANSF_SIZE, 0]],
        dtype="float32")

    transf = cv2.getPerspectiveTransform(source, dest)
    warped = cv2.warpPerspective(img, transf, (TRANSF_SIZE, TRANSF_SIZE))
    return warped


def get_croped(source_file, omr_marker_path):
    im_orig = cv2.imread(source_file)
    im_normalized = normalize(im_orig)
    contours = get_contours(im_normalized)
    corners = get_corners(contours, omr_marker_path)
    outmost = sort_points_counter_clockwise(get_outmost_points(corners))
    return perspective_transform(im_orig, outmost)

@app.task
def crop_omr_area_eleva(upload_id):
    omr_files = glob.glob(f'tmp/{upload_id}/*.jpg')
    omr_upload = OMRUpload.objects.get(pk=upload_id)
    omr_marker = omr_upload.omr_category.get_omr_marker_path()

    for i, omr_file in enumerate(sorted(omr_files), 1):
        try:
            cropped_img = get_croped(omr_file, omr_marker)
            cv2.imwrite(omr_file, cropped_img)
        except Exception as e:
            print(e)
            omr_upload.append_processing_log(f'Delimitadores não encontrados - Página {i}')

    return upload_id