# HDR sticker

![image](https://github.com/user-attachments/assets/9f36bf27-c341-4db2-b7d1-eea6356917c8)

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
