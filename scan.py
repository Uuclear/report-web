import cv2
import os

# wechat_qrcode 模型路径
MODEL_DIR = "d:/code/trytry/models"

def create_detector():
    """创建 wechat_qrcode 检测器"""
    return cv2.wechat_qrcode_WeChatQRCode(
        os.path.join(MODEL_DIR, "detect.prototxt"),
        os.path.join(MODEL_DIR, "detect.caffemodel"),
        os.path.join(MODEL_DIR, "sr.prototxt"),
        os.path.join(MODEL_DIR, "sr.caffemodel")
    )

def decode_qrcode(detector, image_path):
    """解码图片中的二维码"""
    img = cv2.imread(image_path)
    if img is None:
        return None, f"无法读取图片: {image_path}"
    
    results, points = detector.detectAndDecode(img)
    return list(results) if results else [], None

def main():
    detector = create_detector()
    
    # 要处理的图片
    images = [
        r"d:\code\trytry\files\GC01-page1.png",
        r"d:\code\trytry\files\GT118-page1.png",
        r"d:\code\trytry\files\GT118-page2.png",
        r"d:\code\trytry\files\GT118-page3.png",
        r"d:\code\trytry\test.jpg",
    ]
    
    print("=" * 50)
    print("微信二维码解码结果 (wechat_qrcode)")
    print("=" * 50)
    
    for img_path in images:
        name = os.path.basename(img_path)
        results, error = decode_qrcode(detector, img_path)
        
        if error:
            print(f"\n{name}: {error}")
        elif results:
            print(f"\n{name}: 检测到 {len(results)} 个二维码")
            for i, r in enumerate(results):
                print(f"  [{i+1}] {r.strip()}")
        else:
            print(f"\n{name}: 未检测到二维码")

if __name__ == "__main__":
    main()