# 二维码扫描器使用说明

基于 QReader 的二维码扫描工具,支持图片和PDF文件。

## 功能特点

- ✅ 支持多种图片格式: JPG, JPEG, PNG, BMP, TIFF
- ✅ 支持PDF文件(单页和多页)
- ✅ 使用 QReader (YOLOv8) 实现高精度二维码检测
- ✅ 批量扫描目录
- ✅ 输出详细结果和JSON报告

## 安装步骤

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Poppler (PDF支持必需)

**Windows:**
1. 下载 Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases/
2. 解压到某个目录,例如 `C:\Program Files\poppler`
3. 将 `C:\Program Files\poppler\Library\bin` 添加到系统环境变量 PATH

或者使用 conda:
```bash
conda install -c conda-forge poppler
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

### 3. 安装 pyzbar 依赖

**Windows:**
- 通常不需要额外操作
- 如果遇到 `lizbar-64.dll` 错误,安装 Visual C++ Redistributable Packages for Visual Studio 2013

**Linux:**
```bash
sudo apt-get install libzbar0
```

**macOS:**
```bash
brew install zbar
```

## 使用方法

### 运行扫描器

```bash
python qrcode_scanner.py
```

程序将自动扫描 `files_limis` 和 `files_scetia` 两个目录。

### 自定义使用

```python
from qrcode_scanner import QRCodeScanner

# 初始化扫描器
scanner = QRCodeScanner(model_size='s', min_confidence=0.5)

# 扫描单个文件
result = scanner.scan_file("path/to/file.jpg")
print(result)

# 扫描目录
results = scanner.scan_directory("path/to/directory")
for r in results:
    if r['qrcodes']:
        print(f"文件: {r['file']}")
        for qr in r['qrcodes']:
            print(f"  内容: {qr['content']}")
```

## 输出说明

### 控制台输出

```
文件: DJ028-240037.jpg
类型: image
----------------------------------------------------------------------
  二维码 1:
    内容: https://example.com/qr-code-data
    置信度: 98.50%
```

### JSON 结果文件

结果保存在 `results/qrcode_results.json`:

```json
{
  "scan_time": "2026-04-03T18:00:00",
  "summary": {
    "total_files": 10,
    "success_files": 10,
    "total_qrcodes": 15
  },
  "results": [
    {
      "file": "D:\\code\\trytry\\files_limis\\DJ028-240037.jpg",
      "type": "image",
      "success": true,
      "qrcodes": [
        {
          "content": "二维码内容",
          "confidence": 0.985,
          "bbox": [100, 200, 300, 400]
        }
      ]
    }
  ]
}
```

## 参数说明

### QRCodeScanner 构造函数参数

- `model_size`: 模型大小
  - `'n'` (nano) - 最快,精度较低
  - `'s'` (small) - 推荐,平衡速度和精度
  - `'m'` (medium) - 较慢,精度较高
  - `'l'` (large) - 最慢,精度最高

- `min_confidence`: 最小置信度阈值 (0.0-1.0)
  - 较低值(如 0.3)可以检测更多二维码,但可能有误检
  - 较高值(如 0.7)更严格,可能漏检模糊二维码
  - 推荐值: 0.5

## 性能优化建议

1. **批量处理大量文件**: 使用较小的 model_size (`'n'` 或 `'s'`)
2. **高质量图片**: 可以提高 min_confidence 到 0.6-0.7
3. **模糊或低质量图片**: 降低 min_confidence 到 0.3-0.4
4. **PDF 文件**: 自动使用 300 DPI 转换,确保二维码清晰

## 故障排除

### 问题: 找不到 poppler

**错误信息**: `PDFInfoNotInstalledError: Unable to get page count. Is poppler installed?`

**解决方案**: 按照上面的安装步骤安装 Poppler

### 问题: 无法读取图片

**错误信息**: `无法读取图片`

**解决方案**: 
- 检查文件是否损坏
- 确认文件格式正确
- 尝试用其他图片查看器打开

### 问题: 二维码检测不到

**解决方案**:
- 降低 `min_confidence` 参数
- 尝试使用更大的 `model_size`
- 对于PDF,提高转换DPI(修改代码中的 `dpi=300`)

## 许可证

MIT License