# HDR sticker

本工具可以将 SDR 亮度范围的图片部分区域提升到 HDR 亮度，输出一张可以在微信、飞书等使用的 HDR 表情包图片。

![image](https://github.com/user-attachments/assets/817bf2e5-884d-4f20-96ee-bf1d59e29fa9)


需要准备两张 PNG 图片：
- 图片 1：正常亮度范围的底图
- 图片 2：需要 HDR 提亮的区域，使用 Alpha 通道划分（**Alpha 通道颜色需要抖动为 2bit**）

example 目录下包含转换完成的图像示例

---

安装依赖：
```
pip install pillow
```

执行转换：
```
python hdr.py
```
