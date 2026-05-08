# DocExtractor

提取并还原道客巴巴(doc88)预览文档为 PDF，尽量保留文本、形状与图片。

## 技术点

- 解析页面中的 `m_main.init(...)` 配置并解码 `pageInfo`
- 自定义 base64 码表还原页面 ID
- 下载 PH/PK EBT 分片，使用 zlib 解压并合成 SWF
- 使用 ffdec 将 SWF 转 PDF/SVG，必要时用 svg2pdf 转换
- 用 pypdf 合并为单一 PDF，并发加速下载与转换

## 使用方法

1) 安装 Python 3.10+ 与 Java
2) 安装依赖

```bash
pip3 install -r requirements.txt
```

3) 运行

```bash
python3 main.py
```

4) 输入完整链接，例如：

```
https://www.doc88.com/p-72520953037047.html
```
