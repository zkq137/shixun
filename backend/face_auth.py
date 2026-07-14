"""
Face authentication module — 高精度版本.
- 人脸检测: OpenCV Haar cascade (精确定位人脸区域)
- 人脸对齐: 基于眼睛检测的旋转校正
- 特征提取: CLAHE 自适应直方图均衡化 + 多尺寸 LBP 特征
- 特征比较: OpenCV LBPH 识别器
"""

import base64
import logging
import os
import math

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── 加载 Haar cascade ─────────────────────────────────
_cv2_data = os.path.join(os.path.dirname(cv2.__file__), "data")

_FACE_CASCADE = cv2.CascadeClassifier(
    os.path.join(_cv2_data, "haarcascade_frontalface_default.xml")
)
_EYE_CASCADE = cv2.CascadeClassifier(
    os.path.join(_cv2_data, "haarcascade_eye.xml")
)

_HAS_FRONTAL_FACE = not _FACE_CASCADE.empty()
_HAS_EYE = not _EYE_CASCADE.empty()

logger.info(f"Haar frontal-face: {'OK' if _HAS_FRONTAL_FACE else 'N/A'}")
logger.info(f"Haar eye:          {'OK' if _HAS_EYE else 'N/A'}")


# ── 工具函数 ───────────────────────────────────────────

def decode_base64_image(image_b64: str) -> np.ndarray:
    """将 base64 图片解码为 OpenCV BGR 数组."""
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(image_b64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


def _align_face(face_img, gray):
    """
    基于眼睛位置进行人脸对齐（旋转使眼睛水平）.
    返回对齐后的 BGR 图像.
    """
    if not _HAS_EYE:
        return face_img

    h, w = face_img.shape[:2]
    eyes = _EYE_CASCADE.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=8, minSize=(20, 20), maxSize=(w // 2, h // 2)
    )

    if len(eyes) < 2:
        return face_img

    # 取面积最大的两只眼睛
    eyes = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
    (x1, y1, w1, h1), (x2, y2, w2, h2) = eyes[0], eyes[1]

    # 计算眼睛中心
    cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
    cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2

    # 计算旋转角度
    dx = cx2 - cx1
    dy = cy2 - cy1
    angle = math.degrees(math.atan2(dy, dx))

    # 旋转校正
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    aligned = cv2.warpAffine(face_img, rot_mat, (w, h), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return aligned


def detect_face(image_b64: str):
    """
    检测 + 对齐 + 预处理人脸，返回归一化灰度图 (128x128).

    返回: (face_preprocessed | None, message)
    """
    img = decode_base64_image(image_b64)
    if img is None:
        return None, "图片解码失败"

    h, w = img.shape[:2]
    face_roi = None

    # ── 1. Haar cascade 检测人脸 ────────────────────
    if _HAS_FRONTAL_FACE:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_eq = cv2.equalizeHist(gray)
        faces = _FACE_CASCADE.detectMultiScale(
            gray_eq, scaleFactor=1.08, minNeighbors=6, minSize=(100, 100)
        )
        if len(faces) > 0:
            (x, y, bw, bh) = max(faces, key=lambda r: r[2] * r[3])
            # 向上/下扩展 30% 以包含下巴和额头
            margin_x = int(bw * 0.15)
            margin_y_top = int(bh * 0.20)
            margin_y_bottom = int(bh * 0.15)
            x = max(0, x - margin_x)
            y = max(0, y - margin_y_top)
            bw = min(w - x, bw + 2 * margin_x)
            bh = min(h - y, bh + margin_y_top + margin_y_bottom)
            face_roi = img[y: y + bh, x: x + bw]

    # ── 2. 回退：中央区域 ────────────────────────────
    if face_roi is None:
        cw, ch = int(w * 0.6), int(h * 0.6)
        x = (w - cw) // 2
        y = (h - ch) // 2
        face_roi = img[y: y + ch, x: x + cw]
        logger.info("回退到中央区域模式")

    # ── 3. 人脸对齐（旋转校正）───────────────────────
    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_aligned_bgr = _align_face(face_roi, face_gray)

    # ── 4. CLAHE 自适应直方图均衡化 ─────────────────
    face_gray = cv2.cvtColor(face_aligned_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    face_clahe = clahe.apply(face_gray)

    # ── 5. 高斯滤波去噪 ─────────────────────────────
    face_blur = cv2.GaussianBlur(face_clahe, (3, 3), 0)

    # ── 6. 缩放到 128x128 ────────────────────────────
    face_resized = cv2.resize(face_blur, (128, 128), interpolation=cv2.INTER_AREA)

    return face_resized, "ok"


def get_face_encoding(image_b64: str):
    """
    提取人脸特征编码（展平的像素数组，128x128 = 16384 元素）.
    返回: (encoding_list | None, message)
    """
    face, msg = detect_face(image_b64)
    if face is None:
        return None, msg
    return face.flatten().tolist(), "ok"


def compare_faces(known_encoding, unknown_encoding, tolerance=120):
    """
    比较两个人脸特征是否匹配.
    使用 LBPH 识别器进行距离计算.

    Args:
        known_encoding: 已知人脸特征
        unknown_encoding: 待比较人脸特征
        tolerance: LBPH confidence 阈值（越小越严格，推荐 80~150）

    Returns:
        (is_match: bool, similarity: float 0~1)
    """
    try:
        return _compare_lbph(known_encoding, unknown_encoding, tolerance)
    except Exception as e:
        logger.error(f"LBPH 比较失败: {e}")
        return _compare_cosine(known_encoding, unknown_encoding)


def _compare_lbph(known_encoding, unknown_encoding, tolerance=120):
    """LBPH 距离比较（自适应尺寸）"""
    # 自适应尺寸：兼容 64x64 和 128x128
    known_size = int(np.sqrt(len(known_encoding)))
    unknown_size = int(np.sqrt(len(unknown_encoding)))
    target_size = min(known_size, unknown_size, 128)

    known_img = np.array(known_encoding, dtype=np.uint8).reshape(known_size, known_size)
    unknown_img = np.array(unknown_encoding, dtype=np.uint8).reshape(unknown_size, unknown_size)

    # 统一缩放到 target_size
    if known_size != target_size:
        known_img = cv2.resize(known_img, (target_size, target_size))
    if unknown_size != target_size:
        unknown_img = cv2.resize(unknown_img, (target_size, target_size))

    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=2, neighbors=16, grid_x=8, grid_y=8
    )
    recognizer.train([known_img], np.array([1]))
    label, confidence = recognizer.predict(unknown_img)

    is_match = confidence < tolerance
    similarity = max(0, 1 - confidence / (tolerance * 2))
    logger.debug(f"LBPH confidence={confidence:.1f}, match={is_match}, sim={similarity:.3f}")
    return is_match, float(similarity)


def _compare_cosine(known_encoding, unknown_encoding, tolerance=0.25):
    """余弦相似度比较（备用）"""
    known_arr = np.array(known_encoding, dtype=np.float32)
    unknown_arr = np.array(unknown_encoding, dtype=np.float32)
    dot = np.dot(known_arr, unknown_arr)
    norm = np.linalg.norm(known_arr) * np.linalg.norm(unknown_arr)
    if norm == 0:
        return False, 0.0
    similarity = dot / norm
    return similarity > (1 - tolerance), float(similarity)
    known_arr = np.array(known_encoding, dtype=np.float32)
    unknown_arr = np.array(unknown_encoding, dtype=np.float32)

    dot = np.dot(known_arr, unknown_arr)
    norm = np.linalg.norm(known_arr) * np.linalg.norm(unknown_arr)
    if norm == 0:
        return False, 0.0
    similarity = dot / norm
    is_match = similarity > (1 - tolerance)
    return is_match, float(similarity)
